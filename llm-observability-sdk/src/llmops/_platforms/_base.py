"""Platform Protocol definition."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from opentelemetry.sdk.trace import TracerProvider

from llmops.config import LLMOpsConfig


class Platform(Protocol):
    """Protocol that all platform implementations must satisfy."""

    @property
    def name(self) -> str:
        """Platform identifier (e.g., 'arize', 'mlflow')."""
        ...

    @property
    def config_section(self) -> str:
        """Config file section name (e.g., 'arize', 'mlflow')."""
        ...

    @property
    def install_extra(self) -> str:
        """pip extra name (e.g., 'arize' for pip install llmops[arize])."""
        ...

    def check_dependencies(self) -> None:
        """Raise ImportError with helpful message if deps missing."""
        ...

    def create_tracer_provider(self, config: LLMOpsConfig) -> TracerProvider:
        """Create platform-specific TracerProvider."""
        ...

    def get_instrumentor_registry(self) -> list[tuple[str, str, str]]:
        """Return list of (config_key, module_path, class_name) tuples."""
        ...

    def instrument(self, config_path: str | Path | None = None) -> TracerProvider:
        """Initialize telemetry and auto-instrumentation for the platform."""
        ...
