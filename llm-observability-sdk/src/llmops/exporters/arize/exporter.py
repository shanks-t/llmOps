"""Arize exporter implementation.

This module provides TracerProvider creation for the Arize platform
using arize.otel.register().
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

    from llmops.api.types import Config

logger = logging.getLogger(__name__)


def check_dependencies() -> None:
    """Verify Arize dependencies are installed.

    Raises:
        ImportError: If arize-otel package is not installed.
    """
    try:
        __import__("arize.otel")
    except ImportError:
        raise ImportError(
            "Arize exporter requires 'arize-otel' package.\n"
            "Install with: pip install llmops[arize]"
        ) from None


def create_arize_provider(config: Config) -> TracerProvider:
    """Create TracerProvider configured for Arize.

    Args:
        config: SDK configuration with arize section.

    Returns:
        TracerProvider configured to export to Arize.

    Raises:
        ImportError: If arize-otel is not installed.
        ValueError: If arize config section is missing.
    """
    check_dependencies()

    if config.arize is None:
        raise ValueError("Arize config section required when platform is 'arize'")

    arize = config.arize

    # Bridge TLS config to environment variables
    _bridge_tls_config_to_env(arize.certificate_file)

    from arize.otel import Transport, register

    transport = Transport.HTTP if arize.transport == "http" else Transport.GRPC

    kwargs: dict[str, Any] = {
        "transport": transport,
        "batch": arize.batch,
        "set_global_tracer_provider": True,
        "headers": None,
        "verbose": arize.verbose,
        "log_to_console": arize.log_to_console,
    }

    if arize.space_id is not None:
        kwargs["space_id"] = arize.space_id
    if arize.api_key is not None:
        kwargs["api_key"] = arize.api_key
    if arize.project_name is not None:
        kwargs["project_name"] = arize.project_name
    else:
        # Fall back to service name if project_name not specified
        kwargs["project_name"] = config.service.name
    if arize.endpoint is not None:
        kwargs["endpoint"] = arize.endpoint

    provider = cast("TracerProvider", register(**kwargs))  # type: ignore[arg-type,call-arg]

    logger.debug(
        "TracerProvider configured via arize.otel with endpoint: %s (transport=%s)",
        arize.endpoint,
        arize.transport,
    )

    return provider


def _bridge_tls_config_to_env(certificate_file: str | None) -> None:
    """Bridge TLS certificate configuration to OTEL environment variables.

    arize.otel.register reads TLS settings from standard OTEL environment
    variables, not from function arguments. This bridges our config to those
    env vars so TLS works seamlessly with arize.otel.

    Uses setdefault to avoid overriding user-set environment variables.

    Args:
        certificate_file: Path to TLS certificate file, or None.
    """
    if certificate_file:
        os.environ.setdefault("OTEL_EXPORTER_OTLP_CERTIFICATE", certificate_file)
        logger.debug("Set OTEL_EXPORTER_OTLP_CERTIFICATE=%s", certificate_file)
