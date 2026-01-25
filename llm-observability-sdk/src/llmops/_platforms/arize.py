"""Arize platform implementation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from opentelemetry import trace

from llmops._platforms._instrument import instrument_platform
from llmops._platforms._registry import apply_instrumentation
from llmops._internal import telemetry as telemetry_module
from llmops._internal.span_filter import (
    ArizeProjectNameInjector,
    OpenInferenceSpanFilter,
)
from llmops.config import (
    ArizeConfig,
    InstrumentationConfig,
    LLMOpsConfig,
    create_arize_config_from_kwargs,
    load_config,
    merge_arize_config_with_kwargs,
)

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace import SpanProcessor

logger = logging.getLogger(__name__)

# Simple flag to track if Arize instrumentation has been applied.
# OTel doesn't allow changing the global provider, so a bool suffices.
_arize_instrumentation_applied: bool = False


def reset_arize_instrumentation() -> None:
    """Reset Arize instrumentation state.

    This is primarily for testing purposes to allow re-instrumentation
    between tests.
    """
    global _arize_instrumentation_applied
    _arize_instrumentation_applied = False


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

    def instrument_existing_tracer(
        self,
        config_path: str | Path | None = None,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        space_id: str | None = None,
        project_name: str | None = None,
        filter_to_genai_spans: bool = True,
    ) -> None:
        """Add Arize instrumentation to an existing global TracerProvider.

        Use this when your application already has OpenTelemetry configured
        with a global TracerProvider. This function:

        1. Gets the existing global TracerProvider
        2. Creates an Arize SpanProcessor
        3. Optionally wraps it with OpenInference filtering
        4. Adds the processor to the existing provider
        5. Applies OpenInference auto-instrumentation (Google ADK, etc.)

        Unlike instrument(), this function does NOT:
        - Create a new TracerProvider
        - Set the global TracerProvider
        - Register an atexit handler (user owns the provider lifecycle)

        Args:
            config_path: Optional path to llmops.yaml. Not required if all
                         credentials are provided via kwargs.
            endpoint: Arize OTLP endpoint. Overrides config file value.
            api_key: Arize API key. Overrides config file value.
            space_id: Arize space ID. Overrides config file value.
            project_name: Arize project name. Overrides config file value.
            filter_to_genai_spans: If True (default), only spans with
                                   openinference.span.kind attribute are
                                   sent to Arize. Set to False to send all spans.

        Returns:
            None. The function modifies the existing provider in place.

        Raises:
            ConfigurationError: If configuration is invalid.
            ImportError: If arize-otel package is not installed.

        Note:
            - Calling this function twice logs a warning and does nothing
              (idempotent).
            - If no SDK TracerProvider exists, a warning is logged but the
              function continues (may not work correctly).
        """
        global _arize_instrumentation_applied

        self.check_dependencies()

        # Check for duplicate instrumentation
        if _arize_instrumentation_applied:
            logger.warning(
                "Arize instrumentation already added to this TracerProvider. Skipping."
            )
            return

        # Get and validate existing global provider
        provider = trace.get_tracer_provider()

        # Check for SDK TracerProvider
        from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider

        if not isinstance(provider, SDKTracerProvider):
            provider_type = type(provider).__name__
            logger.warning(
                "Global TracerProvider is not an SDK TracerProvider (%s). "
                "Arize instrumentation may not work correctly.",
                provider_type,
            )
            # Continue anyway - some frameworks set up providers lazily

        # Load or create configuration
        arize_config = self._resolve_config(
            config_path=config_path,
            endpoint=endpoint,
            api_key=api_key,
            space_id=space_id,
            project_name=project_name,
            filter_to_genai_spans=filter_to_genai_spans,
        )

        # Resolve filter setting: kwarg > config > default (True for existing tracer)
        should_filter = (
            filter_to_genai_spans
            if arize_config.filter_to_genai_spans is None
            else arize_config.filter_to_genai_spans
        )

        # Create span processor for Arize
        try:
            span_processor: SpanProcessor = self._create_span_processor(arize_config)
        except Exception as exc:
            logger.warning("Failed to create Arize span processor: %s", exc)
            return

        # Wrap with filter if enabled (must be inner wrapper)
        # Filter is applied on on_end when attributes are finalized
        if should_filter:
            span_processor = OpenInferenceSpanFilter(span_processor)

        # Wrap with project name injector if project_name is configured (outer wrapper)
        # This is required because Arize needs arize.project.name span attribute
        # when we can't set openinference.project.name on the Resource.
        # Must be outer wrapper so on_start is called to inject attribute.
        if arize_config.project_name:
            span_processor = ArizeProjectNameInjector(
                span_processor, arize_config.project_name
            )

        # Add processor to existing provider
        if isinstance(provider, SDKTracerProvider):
            provider.add_span_processor(span_processor)
        else:
            # Try anyway for duck-typed providers
            try:
                provider.add_span_processor(span_processor)  # type: ignore[attr-defined]
            except AttributeError:
                logger.error(
                    "Cannot add span processor to non-SDK TracerProvider (%s)",
                    type(provider).__name__,
                )
                return

        # Mark as instrumented
        _arize_instrumentation_applied = True

        # Apply auto-instrumentation
        try:
            instrumentation_config = InstrumentationConfig()
            apply_instrumentation(
                instrumentation_config,
                self.get_instrumentor_registry(),
                provider,  # type: ignore[arg-type]
            )
        except Exception as exc:
            logger.warning("Unexpected error during auto-instrumentation: %s", exc)

        logger.debug(
            "llmops arize added to existing TracerProvider (filter=%s)",
            should_filter,
        )

    def _resolve_config(
        self,
        config_path: str | Path | None,
        *,
        endpoint: str | None,
        api_key: str | None,
        space_id: str | None,
        project_name: str | None,
        filter_to_genai_spans: bool,
    ) -> ArizeConfig:
        """Resolve ArizeConfig from config file and/or kwargs."""
        if config_path is not None:
            config = load_config(Path(config_path))
            return merge_arize_config_with_kwargs(
                config.arize,
                endpoint=endpoint,
                api_key=api_key,
                space_id=space_id,
                project_name=project_name,
                filter_to_genai_spans=filter_to_genai_spans,
            )

        # No config file - must have all required kwargs
        return create_arize_config_from_kwargs(
            endpoint=endpoint,
            api_key=api_key,
            space_id=space_id,
            project_name=project_name,
            filter_to_genai_spans=filter_to_genai_spans,
        )

    # Keep for backward compatibility with tests that mock this method
    def create_arize_span_processor(self, config: ArizeConfig) -> "SpanProcessor":
        """Deprecated: Use _create_span_processor instead."""
        return self._create_span_processor(config)
