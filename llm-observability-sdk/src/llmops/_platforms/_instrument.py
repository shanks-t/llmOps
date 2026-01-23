"""Shared platform instrumentation flow."""

from __future__ import annotations

import atexit
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from llmops._platforms._registry import apply_instrumentation
from llmops._internal.telemetry import create_noop_tracer_provider
from llmops.config import load_config
from llmops.exceptions import ConfigurationError

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

    from llmops._platforms._base import Platform

logger = logging.getLogger(__name__)

LLMOPS_CONFIG_PATH_ENV = "LLMOPS_CONFIG_PATH"


def instrument_platform(
    platform: "Platform",
    config_path: str | Path | None = None,
) -> "TracerProvider":
    """Shared instrumentation workflow for all platforms."""
    platform.check_dependencies()
    resolved_path = _resolve_config_path(config_path)

    try:
        config = load_config(resolved_path)
    except ConfigurationError:
        raise
    except Exception as exc:
        logger.warning("Unexpected error loading config: %s", exc)
        raise ConfigurationError(f"Failed to load configuration: {exc}")

    try:
        provider = platform.create_tracer_provider(config)
        atexit.register(provider.shutdown)
    except Exception as exc:
        if config.is_strict:
            raise ConfigurationError(f"Failed to create tracer provider: {exc}")
        logger.warning("Failed to create tracer provider, using no-op: %s", exc)
        provider = create_noop_tracer_provider()
        atexit.register(provider.shutdown)
        return provider

    try:
        apply_instrumentation(
            config.instrumentation, platform.get_instrumentor_registry(), provider
        )
    except Exception as exc:
        logger.warning("Unexpected error during instrumentation: %s", exc)

    logger.debug("llmops %s initialized successfully", platform.name)
    return provider


def _resolve_config_path(config_path: str | Path | None) -> Path:
    if config_path is not None:
        return Path(config_path)

    env_path = os.environ.get(LLMOPS_CONFIG_PATH_ENV)
    if env_path:
        return Path(env_path)

    raise ConfigurationError(
        "No configuration path provided. Either pass config_path to instrument() "
        f"or set the {LLMOPS_CONFIG_PATH_ENV} environment variable."
    )
