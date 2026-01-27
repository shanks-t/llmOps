"""Arize platform implementation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from llmops._platforms._instrument import instrument_platform
from llmops._internal import telemetry as telemetry_module
from llmops.config import (
    ArizeConfig,
    LLMOpsConfig,
)

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace import SpanProcessor

logger = logging.getLogger(__name__)


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

    def _create_span_processor(self, config: ArizeConfig) -> "SpanProcessor":
        """Create a BatchSpanProcessor with Arize HTTPSpanExporter.

        Args:
            config: ArizeConfig with endpoint, api_key, space_id, etc.

        Returns:
            BatchSpanProcessor configured for Arize export.

        Raises:
            ValueError: If required configuration is missing.
        """
        if not config.endpoint:
            raise ValueError("arize.endpoint is required")
        if not config.api_key:
            raise ValueError("arize.api_key is required")
        if not config.space_id:
            raise ValueError("arize.space_id is required")

        from arize.otel import HTTPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter = HTTPSpanExporter(
            endpoint=config.endpoint,
            api_key=config.api_key,
            space_id=config.space_id,
        )

        return BatchSpanProcessor(exporter)

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

    # Keep for backward compatibility with tests that mock this method
    def create_arize_span_processor(self, config: ArizeConfig) -> "SpanProcessor":
        """Deprecated: Use _create_span_processor instead."""
        return self._create_span_processor(config)
