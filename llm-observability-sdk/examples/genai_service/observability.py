"""
observability.py

OpenTelemetry initialization for FastAPI service with dual-backend architecture:
- Standard infrastructure traces → Jaeger (or any OTLP-compatible backend)
- GenAI traces (OpenInference) → Arize

Environment Variables:
    SERVICE_NAME          - Service name for traces (default: "genai-service")
    DEPLOYMENT_ENV        - Environment (default: "local")
    OTEL_ENABLED          - Enable OTLP export to Jaeger (default: "true")
    OTEL_ENDPOINT         - OTLP HTTP endpoint (default: "http://localhost:4318/v1/traces")
    ARIZE_ENABLED         - Enable Arize GenAI export (default: "true")
    ARIZE_API_KEY         - Arize API key (required if ARIZE_ENABLED)
    ARIZE_SPACE_ID        - Arize space ID (required if ARIZE_ENABLED)
    ARIZE_PROJECT_NAME    - Arize project name (default: "genai-service")
    OTEL_CONSOLE_DEBUG    - Enable console span exporter for debugging (default: "false")
"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


def _get_bool_env(name: str, default: bool = False) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(name, str(default)).lower()
    return value in ("true", "1", "yes")


class OpenInferenceOnlySpanProcessor(SpanProcessor):
    """
    Filters spans so that ONLY OpenInference (GenAI) spans
    are forwarded to the delegate processor.

    Uses the openinference.span.kind attribute as the invariant
    to identify GenAI-related spans.
    """

    def __init__(self, delegate_processor: SpanProcessor):
        self._delegate = delegate_processor

    def on_start(self, span, parent_context=None) -> None:
        # Do nothing on start - we don't want to affect span creation or sampling
        pass

    def on_end(self, span) -> None:
        attributes = span.attributes or {}

        # Only forward spans with OpenInference semantic attribute
        if "openinference.span.kind" in attributes:
            self._delegate.on_end(span)

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int | None = None) -> bool:
        if timeout_millis is None:
            return self._delegate.force_flush()
        return self._delegate.force_flush(timeout_millis)


def setup_opentelemetry() -> TracerProvider:
    """
    Set up OpenTelemetry with a single global TracerProvider.

    Configures:
    - Console exporter for debugging (if OTEL_CONSOLE_DEBUG=true)
    - OTLP exporter for infrastructure traces to Jaeger (if OTEL_ENABLED=true)
    - Arize exporter for GenAI traces only (if ARIZE_ENABLED=true)
    - Google ADK instrumentation for GenAI semantic spans

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
    arize_enabled = _get_bool_env("ARIZE_ENABLED", default=True)
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
    # Arize exporter
    # (ONLY GenAI spans go here)
    # ------------------------------------
    if arize_enabled:
        arize_api_key = os.getenv("ARIZE_API_KEY")
        arize_space_id = os.getenv("ARIZE_SPACE_ID")

        if not arize_api_key or not arize_space_id:
            print(
                "[observability] WARNING: ARIZE_ENABLED=true but "
                "ARIZE_API_KEY or ARIZE_SPACE_ID not set. Skipping Arize exporter."
            )
        else:
            from arize.otel import HTTPSpanExporter

            arize_project_name = os.getenv("ARIZE_PROJECT_NAME", service_name)

            arize_exporter = HTTPSpanExporter(
                space_id=arize_space_id,
                api_key=arize_api_key,
                project_name=arize_project_name,
            )
            arize_batch_processor = BatchSpanProcessor(arize_exporter)

            # Wrap with filter to only send GenAI spans
            arize_filtered_processor = OpenInferenceOnlySpanProcessor(arize_batch_processor)
            tracer_provider.add_span_processor(arize_filtered_processor)
            print(
                f"[observability] Arize exporter enabled (GenAI spans only) → {arize_project_name}"
            )

    # ------------------------------------
    # Google ADK instrumentation
    # ------------------------------------
    # Must run AFTER tracer provider is set.
    # Will emit OpenInference semantic spans for GenAI operations.
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor

    GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
    print("[observability] Google ADK instrumentation enabled")

    print(
        f"[observability] Initialized: service={service_name}, "
        f"env={deployment_env}, otel={otel_enabled}, arize={arize_enabled}"
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
