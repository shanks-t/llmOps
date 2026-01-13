"""Global state management for the SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

# Global state
_configured: bool = False
_tracer_provider: TracerProvider | None = None


def set_configured(configured: bool, provider: TracerProvider | None = None) -> None:
    """Set the SDK configuration state."""
    global _configured, _tracer_provider
    _configured = configured
    _tracer_provider = provider


def is_configured() -> bool:
    """Check if the SDK has been configured."""
    return _configured


def get_tracer_provider() -> TracerProvider | None:
    """Get the configured TracerProvider."""
    return _tracer_provider


def shutdown(timeout_ms: int = 5000) -> None:
    """
    Flush pending spans and shutdown the SDK.

    Call this before application exit to ensure all telemetry is exported.

    Args:
        timeout_ms: Maximum time to wait for flush (default: 5000ms)
    """
    global _configured, _tracer_provider

    if _tracer_provider is not None:
        _tracer_provider.force_flush(timeout_millis=timeout_ms)
        _tracer_provider.shutdown()
        _tracer_provider = None

    _configured = False
