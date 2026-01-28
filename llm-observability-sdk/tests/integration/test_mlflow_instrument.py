"""Integration tests for MLflow platform initialization.

Tests derived from PRD_01.

Requirements covered:
- F1: llmops.instrument(config) initializes the SDK
- F6: instrument() requires an explicit config path (arg or env var)
- F7: instrument() accepts llmops.yaml (preferred) and llmops.yml (supported)
- F14: llmops platform: mlflow exists as a skeleton
- N5: Permissive validation uses a no-op tracer provider on config errors
- N6: Strict validation fails startup on config errors
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.integration
class TestMLflowConfigResolution:
    """Tests for MLflow config path resolution behavior.

    PRD: PRD_01, Requirements: F1, F6, F14
    """

    def test_instrument_fails_without_config(
        self,
        monkeypatch: pytest.MonkeyPatch,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F6

        GIVEN the LLMOPS_CONFIG_PATH environment variable is not set
        AND no config path is provided to instrument()
        WHEN llmops.instrument() is called
        THEN a ConfigurationError is raised
        """
        monkeypatch.delenv("LLMOPS_CONFIG_PATH", raising=False)

        with pytest.raises(llmops_module.ConfigurationError):
            llmops_module.instrument()

    def test_instrument_resolves_config_from_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
        valid_mlflow_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F1

        GIVEN a valid config file exists
        AND the LLMOPS_CONFIG_PATH environment variable is set to that path
        WHEN llmops.instrument() is called without arguments
        THEN the SDK initializes successfully
        """
        monkeypatch.setenv("LLMOPS_CONFIG_PATH", str(valid_mlflow_config_file))

        llmops_module.instrument()

        assert llmops_module.is_configured()

    def test_instrument_explicit_path_takes_precedence_over_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: "Path",
        valid_mlflow_config_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F6

        GIVEN a valid config file exists at "env.yaml"
        AND a valid config file exists at "arg.yaml"
        AND the LLMOPS_CONFIG_PATH environment variable is set to "env.yaml"
        WHEN llmops.instrument() is called with config set to "arg.yaml"
        THEN the SDK initializes successfully
        AND the config from "arg.yaml" is used (not "env.yaml")
        """
        env_config = tmp_path / "env.yaml"
        arg_config = tmp_path / "arg.yaml"

        env_content = valid_mlflow_config_content.replace("test-service", "env-service")
        arg_content = valid_mlflow_config_content.replace("test-service", "arg-service")

        env_config.write_text(env_content)
        arg_config.write_text(arg_content)

        monkeypatch.setenv("LLMOPS_CONFIG_PATH", str(env_config))

        llmops_module.instrument(config=arg_config)

        assert llmops_module.is_configured()

        # Verify the correct config was used by checking service name
        from llmops.sdk.lifecycle import get_provider

        provider = get_provider()
        assert provider is not None
        resource = provider.resource
        service_name = resource.attributes.get("service.name")
        assert service_name == "arg-service", (
            "Expected service name 'arg-service' from arg config, "
            f"but got '{service_name}' (env config may have been used instead)"
        )


@pytest.mark.integration
class TestMLflowFileExtensions:
    """Tests for config file extension handling.

    PRD: PRD_01, Requirement: F7
    """

    def test_instrument_accepts_yaml_extension(
        self,
        tmp_path: "Path",
        valid_mlflow_config_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F7

        GIVEN a valid config file exists with .yaml extension
        WHEN llmops.instrument() is called with that config path
        THEN the SDK initializes successfully
        """
        config_path = tmp_path / "config.yaml"
        config_path.write_text(valid_mlflow_config_content)

        llmops_module.instrument(config=config_path)

        assert llmops_module.is_configured()

    def test_instrument_accepts_yml_extension(
        self,
        tmp_path: "Path",
        valid_mlflow_config_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F7

        GIVEN a valid config file exists with .yml extension
        WHEN llmops.instrument() is called with that config path
        THEN the SDK initializes successfully
        """
        config_path = tmp_path / "config.yml"
        config_path.write_text(valid_mlflow_config_content)

        llmops_module.instrument(config=config_path)

        assert llmops_module.is_configured()


@pytest.mark.integration
class TestMLflowSkeletonBehavior:
    """Tests for skeleton behavior (basic provider).

    MLflow is a skeleton implementation that creates a basic TracerProvider.

    PRD: PRD_01, Requirement: F14
    """

    def test_skeleton_returns_provider_on_valid_config(
        self,
        valid_mlflow_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F14

        GIVEN a valid MLflow config file
        WHEN llmops.instrument() is called
        THEN the SDK initializes successfully
        """
        llmops_module.instrument(config=valid_mlflow_config_file)

        assert llmops_module.is_configured()


@pytest.mark.integration
class TestMLflowValidation:
    """Tests for strict vs permissive validation behavior.

    PRD: PRD_01, Requirements: N5, N6
    """

    def test_permissive_mode_succeeds_on_invalid_config(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: N5

        GIVEN a config file with validation mode set to "permissive"
        AND the config file is missing required fields (but has platform)
        WHEN llmops.instrument() is called with that config
        THEN the SDK initializes successfully (no-op mode)
        AND no exception is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "platform: mlflow\n"
            "validation:\n"
            "  mode: permissive\n"
            "# Missing required 'service' section\n"
            "mlflow:\n"
            "  tracking_uri: http://localhost:5001\n"
        )

        llmops_module.instrument(config=config_path)

        assert llmops_module.is_configured()

    def test_strict_mode_raises_error_on_invalid_config(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: N6

        GIVEN a config file with validation mode set to "strict"
        AND the config file is missing required fields
        WHEN llmops.instrument() is called with that config
        THEN a ConfigurationError is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "platform: mlflow\n"
            "validation:\n"
            "  mode: strict\n"
            "# Missing required 'service' and 'mlflow' sections\n"
        )

        with pytest.raises(llmops_module.ConfigurationError):
            llmops_module.instrument(config=config_path)
