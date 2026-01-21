"""
observability.py

OpenTelemetry initialization for FastAPI service with dual-backend architecture:
- Standard infrastructure traces → Jaeger (or any OTLP-compatible backend)
- GenAI traces (OpenInference) → Phoenix (open source) or Arize AX (enterprise)

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
    - Phoenix/Arize AX exporter for GenAI traces only (based on ARIZE_MODE)
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
    # Phoenix / Arize AX exporter
    # (ONLY GenAI spans go here)
    # ------------------------------------
    if arize_mode == "phoenix":
        arize_endpoint = os.getenv("ARIZE_ENDPOINT")
        if not arize_endpoint:
            print(
                "[observability] WARNING: ARIZE_MODE=phoenix but ARIZE_ENDPOINT not set. "
                "Skipping Phoenix exporter."
            )
        else:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter as PhoenixOTLPExporter,
            )

            phoenix_exporter = PhoenixOTLPExporter(endpoint=arize_endpoint)
            phoenix_batch_processor = BatchSpanProcessor(phoenix_exporter)

            # Wrap with filter to only send GenAI spans
            phoenix_filtered_processor = OpenInferenceOnlySpanProcessor(phoenix_batch_processor)
            tracer_provider.add_span_processor(phoenix_filtered_processor)
            print(f"[observability] Phoenix exporter enabled (GenAI spans only) -> {arize_endpoint}")

    elif arize_mode == "ax":
        arize_endpoint = os.getenv("ARIZE_ENDPOINT")
        arize_api_key = os.getenv("ARIZE_API_KEY")
        arize_space_id = os.getenv("ARIZE_SPACE_ID")

        if not all([arize_endpoint, arize_api_key, arize_space_id]):
            print(
                "[observability] WARNING: ARIZE_MODE=ax requires ARIZE_ENDPOINT, "
                "ARIZE_API_KEY, and ARIZE_SPACE_ID. Skipping Arize AX exporter."
            )
        else:
            from arize.otel import HTTPSpanExporter

            # Type narrowing: at this point we know these are not None
            assert arize_endpoint is not None
            assert arize_api_key is not None
            assert arize_space_id is not None

            ax_exporter = HTTPSpanExporter(
                endpoint=arize_endpoint,
                api_key=arize_api_key,
                space_id=arize_space_id,
            )
            ax_batch_processor = BatchSpanProcessor(ax_exporter)

            # Wrap with filter to only send GenAI spans
            ax_filtered_processor = OpenInferenceOnlySpanProcessor(ax_batch_processor)
            tracer_provider.add_span_processor(ax_filtered_processor)
            print(f"[observability] Arize AX exporter enabled (GenAI spans only) -> {arize_endpoint}")

    elif arize_mode == "disabled":
        print("[observability] Phoenix/Arize disabled")

    else:
        print(f"[observability] WARNING: Unknown ARIZE_MODE '{arize_mode}', skipping")

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
