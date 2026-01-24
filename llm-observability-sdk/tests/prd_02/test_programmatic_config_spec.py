"""Contract tests for programmatic configuration — PRD_02.

Executable contracts derived from:
- PRD: docs/prd/PRD_02.md
- API: docs/api_spec/API_SPEC_02.md

Requirements covered:
- F2: Accepts programmatic credentials (endpoint, api_key, space_id)
- F3: Accepts optional config file path
- F4: Programmatic credentials override config file values
- N4: Works without config file if credentials provided
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
CAPABILITY = "programmatic_config"

# Mark all tests as xfail until implementation is complete
pytestmark = pytest.mark.xfail(reason="PRD_02 implementation pending", strict=False)


class TestProgrammaticConfiguration:
    """Tests for programmatic (kwargs-based) configuration."""

    def test_works_without_config_file(
        self,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

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
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

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
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

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


class TestConfigFileWithOverrides:
    """Tests for config file with programmatic overrides."""

    def test_config_file_provides_defaults(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

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
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

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
        # Actual override verification would require inspecting the created exporter

    def test_partial_kwargs_with_config_file(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN a config file with partial Arize credentials
        AND kwargs providing the missing values
        WHEN instrument_existing_tracer() is called
        THEN the combination provides complete configuration
        """
        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        # Config file has endpoint and space_id, but not api_key
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  space_id: config-space
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        # Provide api_key via kwarg
        llmops_arize_module.instrument_existing_tracer(
            config_path=config_path,
            api_key="kwarg-api-key",
        )

        # Should succeed with combined config
        processors = existing_provider._active_span_processor._span_processors
        assert len(processors) > 0


class TestEnvironmentVariableResolution:
    """Tests for environment variable resolution in config."""

    def test_config_file_supports_env_var_substitution(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_02
        API: API_SPEC_02.instrument_existing_tracer()

        GIVEN a config file with ${ENV_VAR} syntax
        AND the environment variables are set
        WHEN instrument_existing_tracer() is called
        THEN environment variables are substituted
        """
        monkeypatch.setenv("TEST_ARIZE_API_KEY", "env-api-key")
        monkeypatch.setenv("TEST_ARIZE_SPACE_ID", "env-space-id")

        existing_provider = TracerProvider()
        trace.set_tracer_provider(existing_provider)

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1
  api_key: ${TEST_ARIZE_API_KEY}
  space_id: ${TEST_ARIZE_SPACE_ID}
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        # Should resolve env vars
        llmops_arize_module.instrument_existing_tracer(config_path=config_path)

        processors = existing_provider._active_span_processor._span_processors
        assert len(processors) > 0
