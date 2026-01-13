"""Generic OTLP backend implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from llmops._internal.logging import log_info

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import SpanProcessor


class OTLPBackend:
    """
    Generic OTLP backend configuration.

    This backend sends spans via OTLP to any compatible collector
    (Tempo, Jaeger, Datadog, etc.).

    Note: This backend does NOT enable any auto-instrumentation.
    Use PhoenixBackend if you need auto-instrumentation support.
    """

    def __init__(self, endpoint: str, headers: dict[str, str] | None = None):
        """
        Initialize OTLP backend.

        Args:
            endpoint: OTLP endpoint (e.g., "http://localhost:4318/v1/traces")
            headers: Optional HTTP headers for authentication
        """
        self.endpoint = endpoint
        self.headers = headers or {}

    def setup(
        self,
        service_name: str,
        span_processors: list[SpanProcessor] | None = None,
    ) -> TracerProvider:
        """
        Configure OpenTelemetry with generic OTLP exporter.

        Args:
            service_name: Service name for traces
            span_processors: Additional processors (e.g., privacy filter)

        Returns:
            Configured TracerProvider
        """
        # Create resource
        resource = Resource.create({SERVICE_NAME: service_name})

        # Create provider
        provider = TracerProvider(resource=resource)

        # Add custom processors first
        if span_processors:
            for processor in span_processors:
                provider.add_span_processor(processor)

        # Add OTLP exporter
        exporter = OTLPSpanExporter(
            endpoint=self.endpoint,
            headers=self.headers,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))

        # Set as global provider
        trace.set_tracer_provider(provider)

        log_info(f"OTLP backend configured: {self.endpoint}")

        return provider
