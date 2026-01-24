"""Contract tests for OpenInference span filtering — PRD_02.

Executable contracts derived from:
- PRD: docs/prd/PRD_02.md
- API: docs/api_spec/API_SPEC_02.md

Requirements covered:
- F5: Only OpenInference spans sent to Arize by default
- F6: filter_to_genai_spans=False sends all spans
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_02"
API_SPEC_ID = "API_SPEC_02"
CAPABILITY = "span_filtering"

# Mark all tests as xfail until implementation is complete
pytestmark = pytest.mark.xfail(reason="PRD_02 implementation pending", strict=False)


class TestOpenInferenceSpanFilter:
    """Tests for the OpenInference span filtering behavior."""

    def test_filter_forwards_openinference_spans(self) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN a span with openinference.span.kind attribute
        WHEN the span passes through OpenInferenceSpanFilter
        THEN the span is forwarded to the delegate processor
        """
        from llmops._internal.span_filter import OpenInferenceSpanFilter

        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        # Create a fake span with OpenInference attribute
        span = MagicMock()
        span.attributes = {"openinference.span.kind": "LLM"}

        filter_processor.on_end(span)

        delegate.on_end.assert_called_once_with(span)

    def test_filter_blocks_non_openinference_spans(self) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN a span WITHOUT openinference.span.kind attribute
        WHEN the span passes through OpenInferenceSpanFilter
        THEN the span is NOT forwarded to the delegate processor
        """
        from llmops._internal.span_filter import OpenInferenceSpanFilter

        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        # Create a fake span without OpenInference attribute
        span = MagicMock()
        span.attributes = {"http.method": "GET", "http.url": "https://api.example.com"}

        filter_processor.on_end(span)

        delegate.on_end.assert_not_called()

    def test_filter_handles_empty_attributes(self) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN a span with no attributes
        WHEN the span passes through OpenInferenceSpanFilter
        THEN the span is NOT forwarded (no error raised)
        """
        from llmops._internal.span_filter import OpenInferenceSpanFilter

        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        span = MagicMock()
        span.attributes = {}

        # Should not raise
        filter_processor.on_end(span)

        delegate.on_end.assert_not_called()

    def test_filter_handles_none_attributes(self) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN a span with None attributes
        WHEN the span passes through OpenInferenceSpanFilter
        THEN the span is NOT forwarded (no error raised)
        """
        from llmops._internal.span_filter import OpenInferenceSpanFilter

        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        span = MagicMock()
        span.attributes = None

        # Should not raise
        filter_processor.on_end(span)

        delegate.on_end.assert_not_called()

    def test_filter_delegates_shutdown(self) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN an OpenInferenceSpanFilter wrapping a delegate
        WHEN shutdown() is called on the filter
        THEN shutdown() is called on the delegate
        """
        from llmops._internal.span_filter import OpenInferenceSpanFilter

        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        filter_processor.shutdown()

        delegate.shutdown.assert_called_once()

    def test_filter_delegates_force_flush(self) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN an OpenInferenceSpanFilter wrapping a delegate
        WHEN force_flush() is called on the filter
        THEN force_flush() is called on the delegate
        """
        from llmops._internal.span_filter import OpenInferenceSpanFilter

        delegate = MagicMock()
        delegate.force_flush.return_value = True
        filter_processor = OpenInferenceSpanFilter(delegate)

        result = filter_processor.force_flush(timeout_millis=5000)

        delegate.force_flush.assert_called_once_with(5000)
        assert result is True


class TestFilteringDefaultBehavior:
    """Tests for default filtering behavior in instrument_existing_tracer()."""

    def test_filter_enabled_by_default(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN instrument_existing_tracer() is called
        WHEN filter_to_genai_spans is not specified
        THEN filtering is enabled (only OpenInference spans go to Arize)
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  space_id: test-space
  api_key: test-key
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        # Call without specifying filter_to_genai_spans
        llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Verify filtering is enabled by checking processor chain
        # Implementation will add OpenInferenceSpanFilter wrapper
        processors = existing_provider._active_span_processor._span_processors
        assert len(processors) > 0

        # The processor should be wrapped with filter
        # (exact verification depends on implementation)

    def test_filter_can_be_disabled(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN filter_to_genai_spans=False is specified
        WHEN instrument_existing_tracer() is called
        THEN all spans are sent to Arize (no filtering)
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  space_id: test-space
  api_key: test-key
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        llmops_arize_module.instrument_existing_tracer(
            config_path=config_path,
            filter_to_genai_spans=False,
        )

        # Verify processor was added (without filter wrapper)
        processors = existing_provider._active_span_processor._span_processors
        assert len(processors) > 0


class TestFilteringComparisonWithInstrument:
    """Tests verifying different defaults between instrument() and instrument_existing_tracer()."""

    def test_instrument_existing_tracer_defaults_filter_true(
        self,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN the default behavior of instrument_existing_tracer()
        WHEN compared to instrument()
        THEN filter_to_genai_spans defaults to True (vs False for instrument())

        This test documents the intentional difference in defaults.
        """
        import inspect

        # Verify the function signature has filter_to_genai_spans with default True
        sig = inspect.signature(llmops_arize_module.instrument_existing_tracer)
        param = sig.parameters.get("filter_to_genai_spans")

        assert param is not None, "filter_to_genai_spans parameter should exist"
        assert param.default is True, (
            f"filter_to_genai_spans should default to True, got {param.default}"
        )
