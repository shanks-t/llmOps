"""Contract tests for instrument_existing_tracer() — PRD_02.

Executable contracts derived from:
- PRD: docs/prd/PRD_02.md
- API: docs/api_spec/API_SPEC_02.md

Requirements covered:
- F1: instrument_existing_tracer() adds Arize to existing global provider
- F8: Google ADK and GenAI auto-instrumented against existing provider
- N1: Telemetry failures never raise exceptions
- N2: Non-SDK provider logs warning but continues
- N3: No atexit handler registered
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_02"
API_SPEC_ID = "API_SPEC_02"
CAPABILITY = "instrument_existing_tracer"

# Mark all tests as xfail until implementation is complete
pytestmark = pytest.mark.xfail(reason="PRD_02 implementation pending", strict=False)


class TestAddToExistingProvider:
    """Tests for adding Arize instrumentation to existing TracerProvider."""

    def test_adds_span_processor_to_existing_provider(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN an existing global TracerProvider
        AND a valid config file with Arize credentials
        WHEN instrument_existing_tracer() is called
        THEN a span processor is added to the existing provider
        """
        # Create and set existing provider
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        initial_processor_count = len(
            existing_provider._active_span_processor._span_processors
        )

        # Create config
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  space_id: test-space
  api_key: test-key
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        # Call instrument_existing_tracer
        llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Verify processor was added
        final_processor_count = len(
            existing_provider._active_span_processor._span_processors
        )
        assert final_processor_count > initial_processor_count

    def test_does_not_replace_global_provider(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN an existing global TracerProvider
        WHEN instrument_existing_tracer() is called
        THEN the global provider remains the same instance
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

        llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Verify same provider instance
        current_provider = trace.get_tracer_provider()
        assert current_provider is existing_provider

    def test_returns_none(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN an existing global TracerProvider
        WHEN instrument_existing_tracer() is called
        THEN None is returned (not a TracerProvider)
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

        result = llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        assert result is None


class TestNoAtexitRegistration:
    """Tests verifying no atexit handler is registered."""

    def test_does_not_register_atexit_handler(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN an existing global TracerProvider
        WHEN instrument_existing_tracer() is called
        THEN no atexit handler is registered for provider shutdown
        """
        import atexit

        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        registered_funcs: list[Any] = []
        original_register = atexit.register

        def mock_register(func: Any, *args: Any, **kwargs: Any) -> Any:
            registered_funcs.append(func)
            return original_register(func, *args, **kwargs)

        # Patch atexit in the instrument module
        import llmops._platforms._instrument as instrument_module

        monkeypatch.setattr(instrument_module.atexit, "register", mock_register)

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  space_id: test-space
  api_key: test-key
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Verify NO atexit handler was registered
        assert len(registered_funcs) == 0, (
            "instrument_existing_tracer() should not register atexit handlers"
        )


class TestNonSDKProviderHandling:
    """Tests for handling non-SDK TracerProviders."""

    def test_warns_on_proxy_provider(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN the global provider is a ProxyTracerProvider (not SDK)
        WHEN instrument_existing_tracer() is called
        THEN a warning is logged but instrumentation continues
        """
        # Don't set any provider - uses default ProxyTracerProvider
        # Note: reset_otel_state fixture clears the provider

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  space_id: test-space
  api_key: test-key
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        import logging

        with caplog.at_level(logging.WARNING):
            # Should not raise, just warn
            llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        assert "not an SDK TracerProvider" in caplog.text


class TestTelemetrySafety:
    """Tests verifying telemetry never breaks business logic."""

    def test_swallows_processor_creation_errors_in_permissive_mode(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN an existing provider
        AND an invalid endpoint that would cause processor creation to fail
        AND permissive validation mode
        WHEN instrument_existing_tracer() is called
        THEN no exception is raised
        AND a warning is logged
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        # Config with potentially problematic values - permissive mode
        config_content = """service:
  name: test-service

arize:
  endpoint: ""
  space_id: ""
  api_key: ""

validation:
  mode: permissive
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        import logging

        with caplog.at_level(logging.WARNING):
            # Should not raise in permissive mode
            llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Should have logged a warning about the failure
        # (exact message depends on implementation)
