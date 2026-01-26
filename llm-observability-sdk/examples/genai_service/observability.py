"""
observability.py

OpenTelemetry initialization for FastAPI service with dual-backend architecture:
- Standard infrastructure traces → Jaeger (or any OTLP-compatible backend)
- GenAI traces (OpenInference) → Phoenix (open source) or Arize AX (enterprise)

This example demonstrates the "nurse handoff" pattern from PRD_02:
- User sets up their own TracerProvider with infrastructure exporters
- llmops.arize.instrument_existing_tracer() adds Arize as an additional destination
- GenAI spans go to both backends; infrastructure spans only to Jaeger

Environment Variables:
    SERVICE_NAME          - Service name for traces (default: "genai-service")
    DEPLOYMENT_ENV        - Environment (default: "local")
    OTEL_ENABLED          - Enable OTLP export to Jaeger (default: "true")
    OTEL_ENDPOINT         - OTLP HTTP endpoint (default: "http://localhost:4318/v1/traces")
    OTEL_CONSOLE_DEBUG    - Enable console span exporter for debugging (default: "false")

    ARIZE_MODE            - GenAI trace backend: "phoenix", "ax", or "disabled" (default: "disabled")
    ARIZE_ENDPOINT        - Endpoint URL (required for phoenix and ax modes)
    ARIZE_API_KEY         - API key (required for ax mode only)
    ARIZE_SPACE_ID        - Space ID (required for ax mode only)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

if TYPE_CHECKING:
    from fastapi import FastAPI


def _get_bool_env(name: str, default: bool = False) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(name, str(default)).lower()
    return value in ("true", "1", "yes")


def setup_opentelemetry(app: FastAPI | None = None) -> TracerProvider:
    """
    Set up OpenTelemetry with a single global TracerProvider.

    Configures:
    - Console exporter for debugging (if OTEL_CONSOLE_DEBUG=true)
    - OTLP exporter for infrastructure traces to Jaeger (if OTEL_ENABLED=true)
    - FastAPI auto-instrumentation for HTTP spans (if app provided)
    - Phoenix/Arize AX exporter for GenAI traces only (based on ARIZE_MODE)
    - Google ADK instrumentation for GenAI semantic spans

    Args:
        app: Optional FastAPI application instance. If provided, FastAPI
             auto-instrumentation will be applied using the same TracerProvider.
             This creates HTTP spans (GET /health, POST /chat, etc.) that will
             appear in Jaeger but be filtered from Arize (no openinference.span.kind).

    Returns:
        TracerProvider instance for lifecycle management (shutdown)
    """
    # ------------------------------------
    # Configuration from environment
    # ------------------------------------
    service_name = os.getenv("SERVICE_NAME", "genai-service")
    deployment_env = os.getenv("DEPLOYMENT_ENV", "local")
    otel_enabled = _get_bool_env("OTEL_ENABLED", default=True)
    otel_endpoint = os.getenv("OTEL_ENDPOINT", "http://localhost:4318/v1/traces")
    arize_mode = os.getenv("ARIZE_MODE", "disabled").lower()
    console_debug = _get_bool_env("OTEL_CONSOLE_DEBUG", default=False)

    # ------------------------------------
    # Resource (identifies the service)
    # ------------------------------------
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": deployment_env,
        }
    )

    # ------------------------------------
    # Global TracerProvider
    # ------------------------------------
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # ------------------------------------
    # Console exporter (debug mode)
    # ------------------------------------
    if console_debug:
        console_processor = SimpleSpanProcessor(ConsoleSpanExporter())
        tracer_provider.add_span_processor(console_processor)
        print("[observability] Console span exporter enabled")

    # ------------------------------------
    # OTLP exporter → Jaeger/Tempo
    # (ALL spans go here)
    # ------------------------------------
    if otel_enabled:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint)
        otlp_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(otlp_processor)
        print(f"[observability] OTLP exporter enabled → {otel_endpoint}")

    # ------------------------------------
    # FastAPI auto-instrumentation
    # (Creates HTTP spans for all routes)
    # ------------------------------------
    # These spans do NOT have openinference.span.kind attribute, so they will
    # be filtered out by OpenInferenceSpanFilter when sending to Arize.
    # They will still appear in Jaeger (all spans go there).
    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        print("[observability] FastAPI auto-instrumentation enabled")

    # ------------------------------------
    # Phoenix / Arize AX exporter
    # (ONLY GenAI spans go here)
    # ------------------------------------
    # Using llmops SDK's instrument_existing_tracer() for the "nurse handoff" pattern:
    # - Adds Arize as additional export destination
    # - Only sends GenAI (OpenInference) spans by default
    # - Applies Google ADK auto-instrumentation

    if arize_mode == "phoenix":
        arize_endpoint = os.getenv("ARIZE_ENDPOINT")
        if not arize_endpoint:
            print(
                "[observability] WARNING: ARIZE_MODE=phoenix but ARIZE_ENDPOINT not set. "
                "Skipping Phoenix exporter."
            )
        else:
            # Phoenix (open source) uses standard OTLP without auth
            # We still use the SDK's OpenInferenceSpanFilter for consistency
            from llmops._internal.span_filter import OpenInferenceSpanFilter
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter as PhoenixOTLPExporter,
            )

            phoenix_exporter = PhoenixOTLPExporter(endpoint=arize_endpoint)
            phoenix_batch_processor = BatchSpanProcessor(phoenix_exporter)

            # Wrap with filter to only send GenAI spans
            phoenix_filtered_processor = OpenInferenceSpanFilter(phoenix_batch_processor)
            tracer_provider.add_span_processor(phoenix_filtered_processor)
            print(f"[observability] Phoenix exporter enabled (GenAI spans only) -> {arize_endpoint}")

            # Apply Google ADK instrumentation manually for Phoenix mode
            from openinference.instrumentation.google_adk import GoogleADKInstrumentor

            GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
            print("[observability] Google ADK instrumentation enabled")

    elif arize_mode == "ax":
        # Use llmops SDK with config file for Arize AX
        # Config file (llmops.yaml) contains:
        # - endpoint, api_key, space_id (from ${ENV_VAR} substitution)
        # - project_name for Arize AX dashboard
        # - filter_to_genai_spans=true (only GenAI spans go to Arize)
        # - auto-instrumentation settings for Google ADK
        import llmops

        llmops.arize.instrument_existing_tracer(config_path="llmops.yaml")
        print("[observability] Arize AX exporter enabled via llmops SDK (GenAI spans only)")

    elif arize_mode == "disabled":
        print("[observability] Phoenix/Arize disabled")
        # Still apply Google ADK instrumentation for local development
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
        print("[observability] Google ADK instrumentation enabled")

    else:
        print(f"[observability] WARNING: Unknown ARIZE_MODE '{arize_mode}', skipping")

    print(
        f"[observability] Initialized: service={service_name}, "
        f"env={deployment_env}, otel={otel_enabled}, arize_mode={arize_mode}"
    )

    return tracer_provider


def shutdown_opentelemetry(tracer_provider: TracerProvider) -> None:
    """
    Shutdown OpenTelemetry and flush any remaining spans.

    Args:
        tracer_provider: The TracerProvider returned from setup_opentelemetry()
    """
    print("[observability] Shutting down and flushing traces...")
    tracer_provider.shutdown()
    print("[observability] Shutdown complete")
