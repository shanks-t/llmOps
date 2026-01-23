"""Telemetry setup and TracerProvider creation using arize.otel."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, cast

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from llmops.config import LLMOpsConfig

logger = logging.getLogger(__name__)


def create_tracer_provider(config: LLMOpsConfig) -> TracerProvider:
    """Create and configure a TracerProvider using arize.otel.register.

    Args:
        config: Validated SDK configuration.

    Returns:
        Configured TracerProvider set as the global provider.
    """
    logger.debug("Using arize.otel.register for TracerProvider creation")

    _bridge_tls_config_to_env(config)

    from arize.otel import Transport, register

    transport = Transport.HTTP if config.arize.transport == "http" else Transport.GRPC

    kwargs: dict[str, Any] = {
        "transport": transport,
        "batch": config.arize.batch_spans,
        "log_to_console": config.arize.debug,
        "verbose": False,
    }
    if config.arize.space_id is not None:
        kwargs["space_id"] = config.arize.space_id
    if config.arize.api_key is not None:
        kwargs["api_key"] = config.arize.api_key
    if config.arize.project_name is not None:
        kwargs["project_name"] = config.arize.project_name
    if config.arize.endpoint is not None:
        kwargs["endpoint"] = config.arize.endpoint

    provider = cast(TracerProvider, register(**kwargs))  # type: ignore[arg-type,call-arg]

    logger.debug(
        "TracerProvider configured via arize.otel with endpoint: %s (transport=%s)",
        config.arize.endpoint,
        config.arize.transport,
    )

    return provider


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
