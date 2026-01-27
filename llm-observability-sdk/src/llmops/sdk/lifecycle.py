"""Global SDK state management.

This module manages the singleton state of the SDK, including:
- Whether the SDK has been initialized
- The active TracerProvider
- Shutdown coordination
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

logger = logging.getLogger(__name__)

_configured: bool = False
_provider: TracerProvider | None = None


def set_configured(provider: TracerProvider) -> None:
    """Mark the SDK as configured with the given provider.

    Args:
        provider: The TracerProvider to use for telemetry.
    """
    global _configured, _provider
    if _configured:
        logger.warning(
            "SDK already configured. Call shutdown() before re-initializing."
        )
    _configured = True
    _provider = provider


def is_configured() -> bool:
    """Check if the SDK has been initialized.

    Returns:
        True if init() has been called successfully.
    """
    return _configured


def get_provider() -> TracerProvider | None:
    """Get the active TracerProvider.

    Returns:
        The TracerProvider if configured, None otherwise.
    """
    return _provider


def shutdown() -> None:
    """Shutdown the SDK and flush pending telemetry.

    This function is idempotent and safe to call multiple times.
    After shutdown, is_configured() returns False.
    """
    global _configured, _provider
    if _provider is not None:
        try:
            _provider.shutdown()
            logger.debug("TracerProvider shutdown complete")
        except Exception as e:
            logger.warning("Error during TracerProvider shutdown: %s", e)
    _configured = False
    _provider = None
