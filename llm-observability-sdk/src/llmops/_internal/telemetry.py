"""Telemetry setup and TracerProvider creation."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

# gRPC exporter is optional - only available with opentelemetry-exporter-otlp-proto-grpc
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter as GRPCSpanExporter,
    )

    GRPC_AVAILABLE = True
except ImportError:
    GRPCSpanExporter = None  # type: ignore[misc, assignment]
    GRPC_AVAILABLE = False

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


def _bridge_tls_config_to_env(config: LLMOpsConfig) -> None:
    """Bridge TLS certificate configuration to OTEL environment variables.

    arize.otel.register reads TLS settings from standard OTEL environment
    variables, not from function arguments. This bridges our config to those
    env vars so TLS works seamlessly with arize.otel.

    Uses setdefault to avoid overriding user-set environment variables.

    Args:
        config: Validated SDK configuration.
    """
    if config.arize.certificate_file:
        os.environ.setdefault(
            "OTEL_EXPORTER_OTLP_CERTIFICATE", config.arize.certificate_file
        )
        logger.debug(
            "Set OTEL_EXPORTER_OTLP_CERTIFICATE=%s", config.arize.certificate_file
        )
    if config.arize.client_key_file:
        os.environ.setdefault(
            "OTEL_EXPORTER_OTLP_CLIENT_KEY", config.arize.client_key_file
        )
        logger.debug(
            "Set OTEL_EXPORTER_OTLP_CLIENT_KEY=%s", config.arize.client_key_file
        )
    if config.arize.client_certificate_file:
        os.environ.setdefault(
            "OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE",
            config.arize.client_certificate_file,
        )
        logger.debug(
            "Set OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE=%s",
            config.arize.client_certificate_file,
        )


def _create_via_arize_otel(config: LLMOpsConfig) -> TracerProvider:
    """Create TracerProvider using arize.otel.register.

    Bridges TLS certificate configuration to OTEL environment variables
    before calling register, since arize.otel reads TLS settings from env vars.

    Args:
        config: Validated SDK configuration.

    Returns:
        TracerProvider created by arize.otel.register.

    Raises:
        ImportError: If arize-otel package is not installed.
    """
    from arize.otel import Transport, register  # type: ignore[import-not-found]

    logger.debug("Using arize.otel.register for TracerProvider creation")

    # Bridge TLS config to OTEL environment variables
    _bridge_tls_config_to_env(config)

    # Map transport config to arize.otel Transport enum
    transport = Transport.HTTP if config.arize.transport == "http" else Transport.GRPC

    # Build kwargs, only passing non-None values
    kwargs: dict[str, str | bool | None] = {
        "transport": transport,
        "batch": config.arize.batch_spans,
        "log_to_console": config.arize.debug,
        "verbose": False,  # SDK handles its own logging
    }
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
        "TracerProvider configured via arize.otel with endpoint: %s (transport=%s)",
        config.arize.endpoint,
        config.arize.transport,
    )

    return provider


def _create_via_manual_otlp(config: LLMOpsConfig) -> TracerProvider:
    """Create TracerProvider with manual OTLP setup.

    Supports TLS certificate configuration for secure connections,
    transport selection (HTTP/gRPC), and batch/simple span processing.

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

    # Create OTLP exporter based on transport configuration
    if config.arize.transport == "grpc":
        if not GRPC_AVAILABLE:
            logger.warning(
                "gRPC transport requested but opentelemetry-exporter-otlp-proto-grpc "
                "is not installed. Falling back to HTTP transport. "
                "Install with: pip install opentelemetry-exporter-otlp-proto-grpc"
            )
            exporter = _create_http_exporter(config, headers)
        else:
            exporter = _create_grpc_exporter(config, headers)
    else:
        exporter = _create_http_exporter(config, headers)

    # Choose span processor based on configuration
    processor: BatchSpanProcessor | SimpleSpanProcessor
    if config.arize.batch_spans:
        processor = BatchSpanProcessor(exporter)
    else:
        processor = SimpleSpanProcessor(exporter)

    provider.add_span_processor(processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    logger.debug(
        "TracerProvider configured via manual OTLP with endpoint: %s "
        "(transport=%s, batch=%s)",
        config.arize.endpoint,
        config.arize.transport,
        config.arize.batch_spans,
    )

    return provider


def _create_http_exporter(
    config: LLMOpsConfig, headers: dict[str, str]
) -> HTTPSpanExporter:
    """Create HTTP OTLP span exporter with TLS support.

    Args:
        config: Validated SDK configuration.
        headers: Authentication headers.

    Returns:
        Configured HTTPSpanExporter.
    """
    return HTTPSpanExporter(
        endpoint=config.arize.endpoint,
        headers=headers if headers else None,
        certificate_file=config.arize.certificate_file,
        client_key_file=config.arize.client_key_file,
        client_certificate_file=config.arize.client_certificate_file,
    )


def _create_grpc_exporter(
    config: LLMOpsConfig, headers: dict[str, str]
) -> Any:  # Returns GRPCSpanExporter when available
    """Create gRPC OTLP span exporter with TLS support.

    For gRPC, TLS certificates are handled via the credentials parameter
    or environment variables. We bridge config to env vars for consistency.

    Args:
        config: Validated SDK configuration.
        headers: Authentication headers.

    Returns:
        Configured GRPCSpanExporter.
    """
    # Bridge TLS config to environment variables for gRPC
    # gRPC exporter reads OTEL_EXPORTER_OTLP_CERTIFICATE from env
    _bridge_tls_config_to_env(config)

    # Convert headers dict to tuple format for gRPC
    headers_tuple = tuple(headers.items()) if headers else None

    # GRPCSpanExporter is conditionally imported and checked via GRPC_AVAILABLE
    return GRPCSpanExporter(  # type: ignore[misc]
        endpoint=config.arize.endpoint,
        headers=headers_tuple,
    )


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
