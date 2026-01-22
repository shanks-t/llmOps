"""Main instrument() entry point for the llmops SDK."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from llmops._internal.instrumentation import apply_instrumentation
from llmops._internal.telemetry import (
    create_noop_tracer_provider,
    create_tracer_provider,
)
from llmops.config import load_config
from llmops.exceptions import ConfigurationError

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

logger = logging.getLogger(__name__)

# Environment variable for config path
LLMOPS_CONFIG_PATH_ENV = "LLMOPS_CONFIG_PATH"


def instrument(config_path: str | Path | None = None) -> TracerProvider:
    """Initialize Arize telemetry and auto-instrumentation.

    This single call:
    1. Resolves config path (arg > env var)
    2. Loads and validates configuration
    3. Creates TracerProvider with OTLP exporter
    4. Applies auto-instrumentation for enabled frameworks
    5. Returns the configured provider

    Args:
        config_path: Optional path to llmops.yaml (preferred) or llmops.yml.
                     If omitted, LLMOPS_CONFIG_PATH must be set.

    Returns:
        The configured OpenTelemetry TracerProvider.

    Raises:
        ConfigurationError: If config is missing or invalid (strict mode only).
                           In permissive mode, returns a no-op tracer provider.

    Examples:
        # Using environment variable
        import os
        os.environ["LLMOPS_CONFIG_PATH"] = "/path/to/llmops.yaml"
        import llmops
        llmops.instrument()

        # Using explicit path
        import llmops
        llmops.instrument(config_path="/path/to/llmops.yaml")
    """
    # Step 1: Resolve config path
    resolved_path = _resolve_config_path(config_path)

    # Step 2: Load and validate configuration
    try:
        config = load_config(resolved_path)
    except ConfigurationError:
        # Re-raise configuration errors (they already respect strict/permissive)
        raise
    except Exception as e:
        # Unexpected errors during config loading
        logger.warning("Unexpected error loading config: %s", e)
        raise ConfigurationError(f"Failed to load configuration: {e}")

    # Step 3: Create TracerProvider
    try:
        provider = create_tracer_provider(config)
    except Exception as e:
        if config.is_strict:
            raise ConfigurationError(f"Failed to create tracer provider: {e}")
        logger.warning("Failed to create tracer provider, using no-op: %s", e)
        return create_noop_tracer_provider()

    # Step 4: Apply auto-instrumentation
    # Instrumentation failures are always swallowed (logged internally)
    try:
        apply_instrumentation(config.instrumentation, provider)
    except Exception as e:
        # Should not happen (apply_instrumentation swallows errors),
        # but be defensive
        logger.warning("Unexpected error during instrumentation: %s", e)

    # Step 5: Return the provider
    logger.debug("llmops initialized successfully")
    return provider


def _resolve_config_path(config_path: str | Path | None) -> Path:
    """Resolve the configuration file path.

    Resolution order:
    1. Explicit config_path argument (highest priority)
    2. LLMOPS_CONFIG_PATH environment variable
    3. Raise ConfigurationError (no default/auto-discovery)

    Args:
        config_path: Explicit path from instrument() argument.

    Returns:
        Resolved Path to configuration file.

    Raises:
        ConfigurationError: If no config path can be resolved.
    """
    # Priority 1: Explicit argument
    if config_path is not None:
        return Path(config_path)

    # Priority 2: Environment variable
    env_path = os.environ.get(LLMOPS_CONFIG_PATH_ENV)
    if env_path:
        return Path(env_path)

    # No config path available
    raise ConfigurationError(
        f"No configuration path provided. Either pass config_path to instrument() "
        f"or set the {LLMOPS_CONFIG_PATH_ENV} environment variable."
    )
