"""Contract tests for SDK initialization — PRD_01.

Executable contracts derived from:
- PRD: docs/prd/PRD_01.md
- API: docs/api_spec/API_SPEC_01.md

Requirements covered:
- A1: init() initializes Arize telemetry and returns a tracer provider
- A4: init() requires an explicit config path (arg or env var)
- A5: init() accepts a config path parameter
- A6: init() supports config path override via env var
- A7: init() accepts llmops.yaml (preferred) and llmops.yml (supported)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_01"
API_SPEC_ID = "API_SPEC_01"
CAPABILITY = "init"


class TestInitConfigResolution:
    """Tests for config path resolution behavior."""

    def test_init_fails_without_config_in_strict_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN the LLMOPS_CONFIG_PATH environment variable is not set
        AND no config path is provided to init()
        WHEN llmops.init() is called
        THEN a ConfigurationError is raised
        """
        monkeypatch.delenv("LLMOPS_CONFIG_PATH", raising=False)

        with pytest.raises(llmops_module.ConfigurationError):
            llmops_module.init()

    def test_init_resolves_config_from_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
        valid_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a valid config file exists
        AND the LLMOPS_CONFIG_PATH environment variable is set to that path
        WHEN llmops.init() is called without arguments
        THEN a TracerProvider is returned
        """
        monkeypatch.setenv("LLMOPS_CONFIG_PATH", str(valid_config_file))

        provider = llmops_module.init()

        assert provider is not None

    def test_init_explicit_path_takes_precedence_over_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: "Path",
        valid_config_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a valid config file exists at "env.yaml"
        AND a valid config file exists at "arg.yaml"
        AND the LLMOPS_CONFIG_PATH environment variable is set to "env.yaml"
        WHEN llmops.init() is called with config_path set to "arg.yaml"
        THEN a TracerProvider is returned
        AND the config from "arg.yaml" is used (not "env.yaml")
        """
        env_config = tmp_path / "env.yaml"
        arg_config = tmp_path / "arg.yaml"

        # Create both config files with different service names
        env_content = valid_config_content.replace("test-service", "env-service")
        arg_content = valid_config_content.replace("test-service", "arg-service")

        env_config.write_text(env_content)
        arg_config.write_text(arg_content)

        monkeypatch.setenv("LLMOPS_CONFIG_PATH", str(env_config))

        provider = llmops_module.init(config_path=arg_config)

        assert provider is not None
        # Verify arg config was used by checking the resource attributes
        # The service name should be "arg-service", not "env-service"
        resource = provider.resource
        service_name = resource.attributes.get("service.name")
        assert service_name == "arg-service", (
            f"Expected service name 'arg-service' from arg config, "
            f"but got '{service_name}' (env config may have been used instead)"
        )


class TestInitFileExtensions:
    """Tests for config file extension handling."""

    def test_init_accepts_yaml_extension(
        self,
        tmp_path: "Path",
        valid_config_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a valid config file exists with .yaml extension
        WHEN llmops.init() is called with that config path
        THEN a TracerProvider is returned
        """
        config_path = tmp_path / "config.yaml"
        config_path.write_text(valid_config_content)

        provider = llmops_module.init(config_path=config_path)

        assert provider is not None

    def test_init_accepts_yml_extension(
        self,
        tmp_path: "Path",
        valid_config_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a valid config file exists with .yml extension
        WHEN llmops.init() is called with that config path
        THEN a TracerProvider is returned
        """
        config_path = tmp_path / "config.yml"
        config_path.write_text(valid_config_content)

        provider = llmops_module.init(config_path=config_path)

        assert provider is not None
