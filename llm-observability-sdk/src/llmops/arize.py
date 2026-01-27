"""Public Arize platform module for llmops.

Usage:
    import llmops
    llmops.arize.instrument(config_path="/path/to/llmops.yaml")
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from llmops._platforms.arize import ArizePlatform
from llmops.exceptions import ConfigurationError

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

ConfigurationError = ConfigurationError

_platform = ArizePlatform()


def instrument(config_path: str | Path | None = None) -> "TracerProvider":
    """Initialize Arize telemetry and auto-instrumentation.

    Creates a new TracerProvider configured for Arize and sets it as the
    global tracer provider. Use this for greenfield applications without
    existing OpenTelemetry setup.

    Args:
        config_path: Path to llmops.yaml configuration file.

    Returns:
        The configured TracerProvider.
    """
    return _platform.instrument(config_path=config_path)
