"""Public MLflow platform module for llmops (skeleton)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from llmops._platforms.mlflow import MLflowPlatform
from llmops.exceptions import ConfigurationError

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

ConfigurationError = ConfigurationError

_platform = MLflowPlatform()


def instrument(config_path: str | Path | None = None) -> "TracerProvider":
    """Initialize MLflow telemetry and auto-instrumentation (skeleton)."""
    return _platform.instrument(config_path=config_path)
