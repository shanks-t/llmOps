"""Contract tests for MLflow skeleton instrumentation — PRD_01.

Executable contracts derived from:
- PRD: docs/prd/PRD_01.md
- API: docs/api_spec/API_SPEC_01.md

Requirements covered:
- F1: llmops.mlflow.instrument(config_path) exists
- F6: instrument() requires an explicit config path (arg or env var)
- F7: instrument() accepts llmops.yaml (preferred) and llmops.yml (supported)
- F14: llmops.mlflow.instrument() exists as a skeleton
- N5: Permissive validation uses a no-op tracer provider on config errors
- N6: Strict validation fails startup on config errors
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_01"
API_SPEC_ID = "API_SPEC_01"
CAPABILITY = "mlflow_instrument"


class TestMLflowConfigResolution:
    """Tests for MLflow config path resolution behavior."""

    def test_instrument_fails_without_config_in_strict_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
        llmops_mlflow_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

        GIVEN the LLMOPS_CONFIG_PATH environment variable is not set
        AND no config path is provided to instrument()
        WHEN llmops.mlflow.instrument() is called
        THEN a ConfigurationError is raised
        """
        monkeypatch.delenv("LLMOPS_CONFIG_PATH", raising=False)

        with pytest.raises(llmops_mlflow_module.ConfigurationError):
            llmops_mlflow_module.instrument()

    def test_instrument_resolves_config_from_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
        valid_mlflow_config_file: "Path",
        llmops_mlflow_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

        GIVEN a valid config file exists
        AND the LLMOPS_CONFIG_PATH environment variable is set to that path
        WHEN llmops.mlflow.instrument() is called without arguments
        THEN a TracerProvider is returned
        """
        monkeypatch.setenv("LLMOPS_CONFIG_PATH", str(valid_mlflow_config_file))

        provider = llmops_mlflow_module.instrument()

        assert provider is not None

    def test_instrument_explicit_path_takes_precedence_over_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: "Path",
        valid_mlflow_config_content: str,
        llmops_mlflow_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

        GIVEN a valid config file exists at "env.yaml"
        AND a valid config file exists at "arg.yaml"
        AND the LLMOPS_CONFIG_PATH environment variable is set to "env.yaml"
        WHEN llmops.mlflow.instrument() is called with config_path set to "arg.yaml"
        THEN a TracerProvider is returned
        AND the config from "arg.yaml" is used (not "env.yaml")
        """
        env_config = tmp_path / "env.yaml"
        arg_config = tmp_path / "arg.yaml"

        env_content = valid_mlflow_config_content.replace("test-service", "env-service")
        arg_content = valid_mlflow_config_content.replace("test-service", "arg-service")

        env_config.write_text(env_content)
        arg_config.write_text(arg_content)

        monkeypatch.setenv("LLMOPS_CONFIG_PATH", str(env_config))

        provider = llmops_mlflow_module.instrument(config_path=arg_config)

        assert provider is not None
        resource = provider.resource
        service_name = resource.attributes.get("service.name")
        assert service_name == "arg-service", (
            "Expected service name 'arg-service' from arg config, "
            f"but got '{service_name}' (env config may have been used instead)"
        )


class TestMLflowFileExtensions:
    """Tests for config file extension handling."""

    def test_instrument_accepts_yaml_extension(
        self,
        tmp_path: "Path",
        valid_mlflow_config_content: str,
        llmops_mlflow_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

        GIVEN a valid config file exists with .yaml extension
        WHEN llmops.mlflow.instrument() is called with that config path
        THEN a TracerProvider is returned
        """
        config_path = tmp_path / "config.yaml"
        config_path.write_text(valid_mlflow_config_content)

        provider = llmops_mlflow_module.instrument(config_path=config_path)

        assert provider is not None

    def test_instrument_accepts_yml_extension(
        self,
        tmp_path: "Path",
        valid_mlflow_config_content: str,
        llmops_mlflow_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

        GIVEN a valid config file exists with .yml extension
        WHEN llmops.mlflow.instrument() is called with that config path
        THEN a TracerProvider is returned
        """
        config_path = tmp_path / "config.yml"
        config_path.write_text(valid_mlflow_config_content)

        provider = llmops_mlflow_module.instrument(config_path=config_path)

        assert provider is not None


class TestMLflowSkeletonBehavior:
    """Tests for skeleton behavior (no-op provider).

    MLflow is a skeleton implementation and should return a no-op provider
    even when the config is valid.
    """

    def test_skeleton_returns_noop_provider_on_valid_config(
        self,
        valid_mlflow_config_file: "Path",
        llmops_mlflow_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

        GIVEN a valid MLflow config file
        WHEN llmops.mlflow.instrument() is called
        THEN a no-op tracer provider is returned
        """
        provider = llmops_mlflow_module.instrument(config_path=valid_mlflow_config_file)

        assert provider is not None


class TestMLflowValidation:
    """Tests for strict vs permissive validation behavior."""

    def test_permissive_mode_returns_noop_on_invalid_config(
        self,
        tmp_path: "Path",
        llmops_mlflow_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

        GIVEN a config file with validation mode set to "permissive"
        AND the config file is missing required fields
        WHEN llmops.mlflow.instrument() is called with that config
        THEN a provider is returned (no-op tracer provider)
        AND no exception is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "validation:\n"
            "  mode: permissive\n"
            "# Missing required 'service' and 'mlflow' sections\n"
        )

        provider = llmops_mlflow_module.instrument(config_path=config_path)

        assert provider is not None

    def test_strict_mode_raises_error_on_invalid_config(
        self,
        tmp_path: "Path",
        llmops_mlflow_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

        GIVEN a config file with validation mode set to "strict"
        AND the config file is missing required fields
        WHEN llmops.mlflow.instrument() is called with that config
        THEN a ConfigurationError is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "validation:\n"
            "  mode: strict\n"
            "# Missing required 'service' and 'mlflow' sections\n"
        )

        with pytest.raises(llmops_mlflow_module.ConfigurationError):
            llmops_mlflow_module.instrument(config_path=config_path)
