"""Arize platform implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from llmops._platforms._instrument import instrument_platform
from llmops._internal import telemetry as telemetry_module
from llmops.config import LLMOpsConfig

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider


class ArizePlatform:
    """Arize platform implementation."""

    name = "arize"
    config_section = "arize"
    install_extra = "arize"

    def check_dependencies(self) -> None:
        try:
            __import__("arize.otel")
        except ImportError:
            raise ImportError(
                "Arize platform requires 'arize-otel' package.\n"
                "Install with: pip install llmops[arize]"
            ) from None

    def create_tracer_provider(self, config: LLMOpsConfig) -> "TracerProvider":
        if not config.arize.endpoint:
            raise ValueError("arize.endpoint is required")
        return telemetry_module.create_tracer_provider(config)

    def get_instrumentor_registry(self) -> list[tuple[str, str, str]]:
        return [
            (
                "google_adk",
                "openinference.instrumentation.google_adk",
                "GoogleADKInstrumentor",
            ),
            (
                "google_genai",
                "openinference.instrumentation.google_genai",
                "GoogleGenAIInstrumentor",
            ),
        ]

    def instrument(self, config_path: str | Path | None = None) -> "TracerProvider":
        return instrument_platform(self, config_path=config_path)
