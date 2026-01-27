"""Main SDK entry points: init(), shutdown(), is_configured().

This module provides the primary public interface for the SDK.
"""

from __future__ import annotations

import atexit
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from llmops.exceptions import ConfigurationError
from llmops.sdk.config.load import load_config
from llmops.sdk.lifecycle import (
    is_configured as _is_configured,
    set_configured,
    shutdown as _shutdown,
)
from llmops.sdk.pipeline import apply_instrumentation, create_provider

if TYPE_CHECKING:
    from llmops.api.types import Config

logger = logging.getLogger(__name__)

# Environment variable for config path fallback
LLMOPS_CONFIG_PATH_ENV = "LLMOPS_CONFIG_PATH"


def _resolve_config_path(config_path: str | Path | None) -> Path:
    """Resolve configuration file path from argument or environment.

    Args:
        config_path: Explicit path, or None to use environment variable.

    Returns:
        Resolved Path to configuration file.

    Raises:
        ConfigurationError: If no config path is provided and
                           LLMOPS_CONFIG_PATH env var is not set.
    """
    if config_path is not None:
        return Path(config_path)

    env_path = os.environ.get(LLMOPS_CONFIG_PATH_ENV)
    if env_path:
        return Path(env_path)

    raise ConfigurationError(
        f"No configuration path provided. Either pass a config path to init() "
        f"or set the {LLMOPS_CONFIG_PATH_ENV} environment variable."
    )


def init(config: str | Path | Config | None = None) -> None:
    """Initialize LLMOPS SDK with the given configuration.

    This is the single entry point for SDK initialization. Configuration
    can be provided as:
    - A path to a YAML config file (str or Path)
    - A Config object for programmatic configuration
    - None to use LLMOPS_CONFIG_PATH environment variable

    After initialization:
    - Auto-instrumentation is applied based on config
    - An atexit handler is registered for automatic shutdown
    - is_configured() returns True

    Args:
        config: Configuration source. Can be:
            - str/Path: Path to YAML configuration file
            - Config: Programmatic configuration object
            - None: Use LLMOPS_CONFIG_PATH environment variable

    Raises:
        ConfigurationError: If configuration is invalid or missing
                           (in strict validation mode).
    """
    # Import Config here to avoid circular import at module level
    from llmops.api.types import Config as ConfigType

    # Handle programmatic config vs file path
    if isinstance(config, ConfigType):
        resolved_config = config
    else:
        config_path = _resolve_config_path(config)
        resolved_config = load_config(config_path)

    try:
        provider = create_provider(resolved_config)
        apply_instrumentation(resolved_config, provider)
        set_configured(provider)
        atexit.register(_shutdown)
        logger.debug(
            "SDK initialized for platform '%s' with service '%s'",
            resolved_config.platform,
            resolved_config.service.name,
        )
    except ImportError as e:
        # Platform dependencies not installed
        raise ConfigurationError(str(e)) from e
    except Exception as e:
        if resolved_config.is_strict:
            raise ConfigurationError(f"SDK initialization failed: {e}") from e
        logger.warning("SDK initialization failed, using no-op mode: %s", e)
        # In permissive mode, create a no-op provider
        _create_noop_provider()


def _create_noop_provider() -> None:
    """Create and configure a no-op TracerProvider for permissive mode fallback."""
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    from llmops.sdk.lifecycle import set_configured

    resource = Resource.create({"service.name": "llmops-noop"})
    provider = TracerProvider(resource=resource)
    set_configured(provider)
    atexit.register(_shutdown)


def shutdown() -> None:
    """Shutdown the SDK and flush pending telemetry.

    This function:
    - Flushes any pending spans to the backend
    - Releases resources held by the TracerProvider
    - Resets is_configured() to return False

    It is idempotent and safe to call multiple times.
    """
    _shutdown()


def is_configured() -> bool:
    """Check if the SDK has been initialized.

    Returns:
        True if init() has been called successfully, False otherwise.
    """
    return _is_configured()
