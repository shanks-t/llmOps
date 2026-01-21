"""Telemetry setup and TracerProvider creation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from llmops.config import LLMOpsConfig

logger = logging.getLogger(__name__)


def create_tracer_provider(config: LLMOpsConfig) -> TracerProvider:
    """Create and configure a TracerProvider with OTLP exporter.

    Args:
        config: Validated SDK configuration.

    Returns:
        Configured TracerProvider set as the global provider.
    """
    # Build resource attributes
    resource_attrs: dict[str, str] = {
        SERVICE_NAME: config.service.name,
    }
    if config.service.version:
        resource_attrs[SERVICE_VERSION] = config.service.version

    resource = Resource.create(resource_attrs)
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter
    headers: dict[str, str] = {}
    if config.arize.api_key:
        headers["authorization"] = f"Bearer {config.arize.api_key}"
    if config.arize.space_id:
        headers["x-arize-space-id"] = config.arize.space_id

    exporter = OTLPSpanExporter(
        endpoint=config.arize.endpoint,
        headers=headers if headers else None,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    logger.debug(
        "TracerProvider configured with endpoint: %s", config.arize.endpoint
    )

    return provider


def create_noop_tracer_provider() -> TracerProvider:
    """Create a minimal TracerProvider without exporters.

    This is used in permissive mode when configuration is invalid.
    The provider is functional but doesn't export any spans.

    Returns:
        Minimal TracerProvider without exporters.
    """
    resource = Resource.create({SERVICE_NAME: "llmops-noop"})
    provider = TracerProvider(resource=resource)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    logger.debug("No-op TracerProvider configured (permissive mode fallback)")

    return provider
