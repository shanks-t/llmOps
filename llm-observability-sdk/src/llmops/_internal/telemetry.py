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
    """Create and configure a TracerProvider.

    Supports two modes:
    1. arize.otel.register (preferred if available and use_arize_otel=True)
    2. Manual OTLP setup with TLS certificate support (fallback)

    Args:
        config: Validated SDK configuration.

    Returns:
        Configured TracerProvider set as the global provider.
    """
    # Try arize.otel.register first (if enabled and available)
    if config.arize.use_arize_otel:
        try:
            return _create_via_arize_otel(config)
        except ImportError:
            logger.debug("arize-otel not installed, using manual OTLP setup")

    # Fallback: manual OTLP setup with TLS support
    return _create_via_manual_otlp(config)


def _create_via_arize_otel(config: LLMOpsConfig) -> TracerProvider:
    """Create TracerProvider using arize.otel.register.

    The arize.otel package automatically reads TLS certificate settings
    from standard OTEL environment variables (OTEL_EXPORTER_OTLP_CERTIFICATE).

    Args:
        config: Validated SDK configuration.

    Returns:
        TracerProvider created by arize.otel.register.

    Raises:
        ImportError: If arize-otel package is not installed.
    """
    from arize.otel import register  # type: ignore[import-not-found]

    logger.debug("Using arize.otel.register for TracerProvider creation")

    # Build kwargs, only passing non-None values
    kwargs: dict[str, str | None] = {}
    if config.arize.space_id:
        kwargs["space_id"] = config.arize.space_id
    if config.arize.api_key:
        kwargs["api_key"] = config.arize.api_key
    if config.arize.project_name:
        kwargs["project_name"] = config.arize.project_name
    if config.arize.endpoint:
        kwargs["endpoint"] = config.arize.endpoint

    provider: TracerProvider = register(**kwargs)

    logger.debug(
        "TracerProvider configured via arize.otel with endpoint: %s",
        config.arize.endpoint,
    )

    return provider


def _create_via_manual_otlp(config: LLMOpsConfig) -> TracerProvider:
    """Create TracerProvider with manual OTLP setup.

    Supports TLS certificate configuration for secure connections.

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

    # Configure authentication headers
    headers: dict[str, str] = {}
    if config.arize.api_key:
        headers["authorization"] = f"Bearer {config.arize.api_key}"
    if config.arize.space_id:
        headers["x-arize-space-id"] = config.arize.space_id
    if config.arize.project_name:
        headers["x-arize-project-name"] = config.arize.project_name

    # Create OTLP exporter with TLS certificate support
    exporter = OTLPSpanExporter(
        endpoint=config.arize.endpoint,
        headers=headers if headers else None,
        certificate_file=config.arize.certificate_file,
        client_key_file=config.arize.client_key_file,
        client_certificate_file=config.arize.client_certificate_file,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    logger.debug(
        "TracerProvider configured via manual OTLP with endpoint: %s",
        config.arize.endpoint,
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
