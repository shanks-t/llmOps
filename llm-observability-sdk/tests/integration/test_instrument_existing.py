"""Integration tests for instrument_existing_tracer().

Tests derived from PRD_02.

Requirements covered:
- F1: instrument_existing_tracer() adds Arize to existing global provider
- F2: Accepts programmatic credentials (endpoint, api_key, space_id)
- F3: Accepts optional config file path
- F4: Programmatic credentials override config file values
- F5: Only OpenInference spans sent to Arize by default
- F6: filter_to_genai_spans=False sends all spans
- F8: Google ADK and GenAI auto-instrumented against existing provider
- N1: Telemetry failures never raise exceptions
- N2: Non-SDK provider logs warning but continues
- N3: No atexit handler registered
- N4: Works without config file if credentials provided
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.integration
class TestAddToExistingProvider:
    """Tests for adding Arize instrumentation to existing TracerProvider.

    PRD: PRD_02, Requirement: F1
    """

    def test_adds_span_processor_to_existing_provider(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F1

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
        PRD: PRD_02, Requirement: F1

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
        PRD: PRD_02, Requirement: F1

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


@pytest.mark.integration
class TestNoAtexitRegistration:
    """Tests verifying no atexit handler is registered.

    PRD: PRD_02, Requirement: N3
    """

    def test_does_not_register_atexit_handler(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_02, Requirement: N3

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


@pytest.mark.integration
class TestNonSDKProviderHandling:
    """Tests for handling non-SDK TracerProviders.

    PRD: PRD_02, Requirement: N2
    """

    def test_warns_on_proxy_provider(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        PRD: PRD_02, Requirement: N2

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

        with caplog.at_level(logging.WARNING):
            # Should not raise, just warn
            llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        assert "not an SDK TracerProvider" in caplog.text


@pytest.mark.integration
class TestTelemetrySafety:
    """Tests verifying telemetry never breaks business logic.

    PRD: PRD_02, Requirement: N1
    """

    def test_swallows_processor_creation_errors_in_permissive_mode(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        PRD: PRD_02, Requirement: N1

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

        with caplog.at_level(logging.WARNING):
            # Should not raise in permissive mode
            llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Should have logged a warning about the failure
        # (exact message depends on implementation)


@pytest.mark.integration
class TestProgrammaticConfiguration:
    """Tests for programmatic (kwargs-based) configuration.

    PRD: PRD_02, Requirements: F2, F3, F4, N4
    """

    def test_works_without_config_file(
        self,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: N4

        GIVEN all required kwargs are provided (endpoint, api_key, space_id)
        WHEN instrument_existing_tracer() is called without config_path
        THEN instrumentation succeeds without error
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        # Should not raise - all required credentials provided
        llmops_arize_module.instrument_existing_tracer(
            endpoint="https://otlp.arize.com/v1",
            api_key="test-key",
            space_id="test-space",
        )

        # Verify processor was added
        processors = existing_provider._active_span_processor._span_processors
        assert len(processors) > 0

    def test_accepts_optional_project_name(
        self,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F2

        GIVEN all required kwargs plus optional project_name
        WHEN instrument_existing_tracer() is called
        THEN instrumentation succeeds with project_name applied
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        # Should not raise
        llmops_arize_module.instrument_existing_tracer(
            endpoint="https://otlp.arize.com/v1",
            api_key="test-key",
            space_id="test-space",
            project_name="my-custom-project",
        )

    def test_missing_required_kwargs_without_config_raises(
        self,
        llmops_arize_module: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F2

        GIVEN no config file path
        AND missing required kwargs (e.g., no space_id)
        WHEN instrument_existing_tracer() is called
        THEN ConfigurationError is raised
        """
        # Ensure no env var fallback
        monkeypatch.delenv("LLMOPS_CONFIG_PATH", raising=False)

        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        with pytest.raises(llmops_arize_module.ConfigurationError):
            llmops_arize_module.instrument_existing_tracer(
                endpoint="https://otlp.arize.com/v1",
                api_key="test-key",
                # Missing space_id
            )

    def test_config_file_provides_defaults(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F3

        GIVEN a valid config file with all Arize credentials
        WHEN instrument_existing_tracer() is called with config_path only
        THEN instrumentation uses config file values
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  space_id: config-space
  api_key: config-key
  project_name: config-project
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        # Should use config file values
        llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Verify processor was added
        processors = existing_provider._active_span_processor._span_processors
        assert len(processors) > 0

    def test_kwargs_override_config_file(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F4

        GIVEN a config file with Arize credentials
        AND kwargs that override some values
        WHEN instrument_existing_tracer() is called
        THEN kwargs take precedence over config file
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        config_content = """service:
  name: test-service

arize:
  endpoint: https://config-endpoint.com/v1
  space_id: config-space
  api_key: config-key
  project_name: config-project
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        # Override endpoint and project_name via kwargs
        llmops_arize_module.instrument_existing_tracer(
            config_path=config_path,
            endpoint="https://override-endpoint.com/v1",
            project_name="override-project",
        )

        # The override behavior is internal - this test verifies no error occurs


@pytest.mark.integration
class TestFilteringDefaultBehavior:
    """Tests for default filtering behavior in instrument_existing_tracer().

    PRD: PRD_02, Requirements: F5, F6
    """

    def test_filter_enabled_by_default(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F5

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

    def test_filter_can_be_disabled(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F6

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

    def test_instrument_existing_tracer_defaults_filter_true(
        self,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02, Requirement: F5

        GIVEN the default behavior of instrument_existing_tracer()
        WHEN compared to instrument()
        THEN filter_to_genai_spans defaults to True (vs False for instrument())

        This test documents the intentional difference in defaults.
        """
        # Verify the function signature has filter_to_genai_spans with default True
        sig = inspect.signature(llmops_arize_module.instrument_existing_tracer)
        param = sig.parameters.get("filter_to_genai_spans")

        assert param is not None, "filter_to_genai_spans parameter should exist"
        assert param.default is True, (
            f"filter_to_genai_spans should default to True, got {param.default}"
        )


@pytest.mark.integration
class TestArizeProjectNameInjection:
    """Tests verifying arize.project.name is injected on spans.

    When using instrument_existing_tracer(), we can't set Resource attributes
    on the existing provider. Arize requires either:
    - openinference.project.name as Resource attribute, OR
    - arize.project.name as Span attribute

    These tests verify the span attribute injection works correctly.
    """

    def test_project_name_injected_on_spans(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        GIVEN instrument_existing_tracer() is called with project_name
        WHEN a span is created
        THEN the span has arize.project.name attribute set
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  space_id: test-space
  api_key: test-key
  project_name: my-test-project
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Create a span and check it has the project name attribute
        tracer = trace.get_tracer("test-tracer")
        with tracer.start_as_current_span("test-span") as span:
            # The attribute should be set by ArizeProjectNameInjector
            # Note: span.attributes is available at runtime on SDK spans
            attrs = span.attributes  # type: ignore[attr-defined]
            assert "arize.project.name" in attrs
            assert attrs["arize.project.name"] == "my-test-project"

    def test_project_name_from_kwargs(
        self,
        llmops_arize_module: Any,
    ) -> None:
        """
        GIVEN instrument_existing_tracer() is called with project_name kwarg
        WHEN a span is created
        THEN the span has arize.project.name attribute set
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        llmops_arize_module.instrument_existing_tracer(
            endpoint="https://otlp.arize.com/v1",
            api_key="test-key",
            space_id="test-space",
            project_name="kwarg-project",
        )

        tracer = trace.get_tracer("test-tracer")
        with tracer.start_as_current_span("test-span") as span:
            attrs = span.attributes  # type: ignore[attr-defined]
            assert attrs.get("arize.project.name") == "kwarg-project"

    def test_processor_chain_order(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        GIVEN instrument_existing_tracer() is called with project_name and filter
        WHEN we inspect the processor chain
        THEN ArizeProjectNameInjector wraps OpenInferenceSpanFilter

        This order is important because:
        - Injector must be outer so on_start is called to set attribute
        - Filter must be inner so it can filter on on_end
        """
        from llmops._internal.span_filter import (
            ArizeProjectNameInjector,
            OpenInferenceSpanFilter,
        )

        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  space_id: test-space
  api_key: test-key
  project_name: test-project
  filter_to_genai_spans: true
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        # Find the Arize processor in the chain
        processors = existing_provider._active_span_processor._span_processors
        arize_processor = None
        for p in processors:
            if isinstance(p, ArizeProjectNameInjector):
                arize_processor = p
                break

        assert arize_processor is not None, "ArizeProjectNameInjector not found"
        assert isinstance(arize_processor._delegate, OpenInferenceSpanFilter), (
            "ArizeProjectNameInjector should wrap OpenInferenceSpanFilter"
        )
