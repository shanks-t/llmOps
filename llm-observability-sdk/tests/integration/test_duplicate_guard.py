"""Integration tests for duplicate instrumentation prevention.

Tests derived from PRD_02.

Requirements covered:
- F7: Duplicate calls log warning and skip
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.integration
class TestDuplicateInstrumentationGuard:
    """Tests for preventing duplicate instrumentation.

    PRD: PRD_02, Requirement: F7
    """

    def test_warns_on_duplicate_call(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F7

        GIVEN instrument_existing_tracer() was already called on a provider
        WHEN it is called again on the same provider
        THEN a warning is logged
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

        # First call
        llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Second call - should warn
        with caplog.at_level(logging.WARNING):
            llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        assert "already added" in caplog.text.lower()

    def test_no_duplicate_processor_added(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F7

        GIVEN instrument_existing_tracer() was already called on a provider
        WHEN it is called again on the same provider
        THEN no additional span processor is added
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

        # First call
        llmops_arize_module.instrument_existing_tracer(config_path=config_path)
        processor_count_after_first = len(
            existing_provider._active_span_processor._span_processors
        )

        # Second call
        llmops_arize_module.instrument_existing_tracer(config_path=config_path)
        processor_count_after_second = len(
            existing_provider._active_span_processor._span_processors
        )

        # Processor count should remain the same
        assert processor_count_after_second == processor_count_after_first


@pytest.mark.integration
class TestIdempotency:
    """Tests for idempotent behavior.

    PRD: PRD_02, Requirement: F7
    """

    def test_multiple_calls_are_safe(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F7

        GIVEN instrument_existing_tracer() is called multiple times
        WHEN the application runs
        THEN no errors occur and behavior is consistent
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

        # Call multiple times - should not raise
        for _ in range(5):
            llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Application should still work
        tracer = trace.get_tracer("test-tracer")
        with tracer.start_as_current_span("test-span") as span:
            span.set_attribute("test", "value")

        # No assertion needed - test passes if no exception raised
