"""Unit tests for span filtering and processing utilities.

Tests derived from PRD_02.

Requirements covered:
- F5: Only OpenInference spans sent to Arize by default
- F6: filter_to_genai_spans=False sends all spans
- Arize project name injection for instrument_existing_tracer()
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from llmops._internal.span_filter import (
    ARIZE_PROJECT_NAME_ATTR,
    ArizeProjectNameInjector,
    OpenInferenceSpanFilter,
)


@pytest.mark.unit
class TestOpenInferenceSpanFilter:
    """Tests for the OpenInferenceSpanFilter class.

    PRD: PRD_02, Requirements: F5, F6
    """

    def test_filter_forwards_openinference_spans(self) -> None:
        """
        PRD: PRD_02, Requirement: F5

        GIVEN a span with openinference.span.kind attribute
        WHEN the span passes through OpenInferenceSpanFilter
        THEN the span is forwarded to the delegate processor
        """
        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        # Create a fake span with OpenInference attribute
        span = MagicMock()
        span.attributes = {"openinference.span.kind": "LLM"}

        filter_processor.on_end(span)

        delegate.on_end.assert_called_once_with(span)

    def test_filter_blocks_non_openinference_spans(self) -> None:
        """
        PRD: PRD_02, Requirement: F5

        GIVEN a span WITHOUT openinference.span.kind attribute
        WHEN the span passes through OpenInferenceSpanFilter
        THEN the span is NOT forwarded to the delegate processor
        """
        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        # Create a fake span without OpenInference attribute
        span = MagicMock()
        span.attributes = {"http.method": "GET", "http.url": "https://api.example.com"}

        filter_processor.on_end(span)

        delegate.on_end.assert_not_called()

    def test_filter_handles_empty_attributes(self) -> None:
        """
        PRD: PRD_02, Requirement: F5

        GIVEN a span with no attributes
        WHEN the span passes through OpenInferenceSpanFilter
        THEN the span is NOT forwarded (no error raised)
        """
        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        span = MagicMock()
        span.attributes = {}

        # Should not raise
        filter_processor.on_end(span)

        delegate.on_end.assert_not_called()

    def test_filter_handles_none_attributes(self) -> None:
        """
        PRD: PRD_02, Requirement: F5

        GIVEN a span with None attributes
        WHEN the span passes through OpenInferenceSpanFilter
        THEN the span is NOT forwarded (no error raised)
        """
        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        span = MagicMock()
        span.attributes = None

        # Should not raise
        filter_processor.on_end(span)

        delegate.on_end.assert_not_called()

    def test_filter_forwards_on_start_to_delegate(self) -> None:
        """
        PRD: PRD_02, Requirement: F5

        GIVEN an OpenInferenceSpanFilter wrapping a delegate
        WHEN on_start() is called on the filter
        THEN on_start() is forwarded to the delegate

        This is important so wrapped processors (like ArizeProjectNameInjector)
        can set attributes on span start.
        """
        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        span = MagicMock()
        parent_context = MagicMock()

        filter_processor.on_start(span, parent_context)

        delegate.on_start.assert_called_once_with(span, parent_context)

    def test_filter_delegates_shutdown(self) -> None:
        """
        PRD: PRD_02, Requirement: F5

        GIVEN an OpenInferenceSpanFilter wrapping a delegate
        WHEN shutdown() is called on the filter
        THEN shutdown() is called on the delegate
        """
        delegate = MagicMock()
        filter_processor = OpenInferenceSpanFilter(delegate)

        filter_processor.shutdown()

        delegate.shutdown.assert_called_once()

    def test_filter_delegates_force_flush(self) -> None:
        """
        PRD: PRD_02, Requirement: F5

        GIVEN an OpenInferenceSpanFilter wrapping a delegate
        WHEN force_flush() is called on the filter
        THEN force_flush() is called on the delegate
        """
        delegate = MagicMock()
        delegate.force_flush.return_value = True
        filter_processor = OpenInferenceSpanFilter(delegate)

        result = filter_processor.force_flush(timeout_millis=5000)

        delegate.force_flush.assert_called_once_with(5000)
        assert result is True


@pytest.mark.unit
class TestArizeProjectNameInjector:
    """Tests for the ArizeProjectNameInjector class.

    This processor injects arize.project.name span attribute for
    instrument_existing_tracer() where we can't set Resource attributes.
    """

    def test_injector_sets_project_name_on_start(self) -> None:
        """
        GIVEN an ArizeProjectNameInjector with project_name "my-project"
        WHEN on_start() is called with a span
        THEN the span has arize.project.name attribute set to "my-project"
        """
        delegate = MagicMock()
        injector = ArizeProjectNameInjector(delegate, "my-project")

        span = MagicMock()
        parent_context = MagicMock()

        injector.on_start(span, parent_context)

        span.set_attribute.assert_called_once_with(
            ARIZE_PROJECT_NAME_ATTR, "my-project"
        )
        delegate.on_start.assert_called_once_with(span, parent_context)

    def test_injector_forwards_on_end(self) -> None:
        """
        GIVEN an ArizeProjectNameInjector
        WHEN on_end() is called
        THEN it forwards to the delegate
        """
        delegate = MagicMock()
        injector = ArizeProjectNameInjector(delegate, "my-project")

        span = MagicMock()
        injector.on_end(span)

        delegate.on_end.assert_called_once_with(span)

    def test_injector_forwards_shutdown(self) -> None:
        """
        GIVEN an ArizeProjectNameInjector
        WHEN shutdown() is called
        THEN it forwards to the delegate
        """
        delegate = MagicMock()
        injector = ArizeProjectNameInjector(delegate, "my-project")

        injector.shutdown()

        delegate.shutdown.assert_called_once()

    def test_injector_forwards_force_flush(self) -> None:
        """
        GIVEN an ArizeProjectNameInjector
        WHEN force_flush() is called
        THEN it forwards to the delegate and returns the result
        """
        delegate = MagicMock()
        delegate.force_flush.return_value = True
        injector = ArizeProjectNameInjector(delegate, "my-project")

        result = injector.force_flush(timeout_millis=5000)

        delegate.force_flush.assert_called_once_with(5000)
        assert result is True

    def test_injector_and_filter_chain_order(self) -> None:
        """
        GIVEN ArizeProjectNameInjector wrapping OpenInferenceSpanFilter
        WHEN a span goes through on_start and on_end
        THEN the project name is set and filter logic works correctly

        This tests the correct wrapper order for instrument_existing_tracer().
        """
        # Innermost: mock exporter processor
        exporter = MagicMock()

        # Middle: filter (only forwards GenAI spans)
        filter_processor = OpenInferenceSpanFilter(exporter)

        # Outermost: injector (sets arize.project.name)
        injector = ArizeProjectNameInjector(filter_processor, "test-project")

        # Create a span that looks like a GenAI span
        span = MagicMock()
        span.attributes = {"openinference.span.kind": "LLM"}

        # on_start chain
        injector.on_start(span, None)
        span.set_attribute.assert_called_once_with(
            ARIZE_PROJECT_NAME_ATTR, "test-project"
        )

        # on_end chain - should forward because it's a GenAI span
        injector.on_end(span)
        exporter.on_end.assert_called_once_with(span)

    def test_injector_and_filter_blocks_non_genai(self) -> None:
        """
        GIVEN ArizeProjectNameInjector wrapping OpenInferenceSpanFilter
        WHEN a non-GenAI span goes through the chain
        THEN the project name is still set but the span is not forwarded to exporter
        """
        exporter = MagicMock()
        filter_processor = OpenInferenceSpanFilter(exporter)
        injector = ArizeProjectNameInjector(filter_processor, "test-project")

        # Create a non-GenAI span (HTTP request)
        span = MagicMock()
        span.attributes = {"http.method": "GET"}

        injector.on_start(span, None)
        span.set_attribute.assert_called_once()  # Still sets attribute

        injector.on_end(span)
        exporter.on_end.assert_not_called()  # But filter blocks it
