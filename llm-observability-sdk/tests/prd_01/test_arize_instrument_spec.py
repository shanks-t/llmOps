"""Contract tests for Arize SDK instrumentation — PRD_01.

Executable contracts derived from:
- PRD: docs/prd/PRD_01.md
- API: docs/api_spec/API_SPEC_01.md

Requirements covered:
- F1: llmops.arize.instrument(config_path) exists
- F2: llmops.arize.instrument() initializes Arize telemetry and returns a tracer provider
- F6: instrument() requires an explicit config path (arg or env var)
- F7: instrument() accepts llmops.yaml (preferred) and llmops.yml (supported)
- N4: All setup completes in a single synchronous call
- Lifecycle: instrument() registers atexit handler for automatic span flushing
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_01"
API_SPEC_ID = "API_SPEC_01"
CAPABILITY = "arize_instrument"


class TestArizeConfigResolution:
    """Tests for Arize config path resolution behavior."""

    def test_instrument_fails_without_config_in_strict_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN the LLMOPS_CONFIG_PATH environment variable is not set
        AND no config path is provided to instrument()
        WHEN llmops.arize.instrument() is called
        THEN a ConfigurationError is raised
        """
        monkeypatch.delenv("LLMOPS_CONFIG_PATH", raising=False)

        with pytest.raises(llmops_arize_module.ConfigurationError):
            llmops_arize_module.instrument()

    def test_instrument_resolves_config_from_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
        valid_arize_config_file: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a valid config file exists
        AND the LLMOPS_CONFIG_PATH environment variable is set to that path
        WHEN llmops.arize.instrument() is called without arguments
        THEN a TracerProvider is returned
        """
        monkeypatch.setenv("LLMOPS_CONFIG_PATH", str(valid_arize_config_file))

        provider = llmops_arize_module.instrument()

        assert provider is not None

    def test_instrument_explicit_path_takes_precedence_over_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: "Path",
        valid_arize_config_content: str,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a valid config file exists at "env.yaml"
        AND a valid config file exists at "arg.yaml"
        AND the LLMOPS_CONFIG_PATH environment variable is set to "env.yaml"
        WHEN llmops.arize.instrument() is called with config_path set to "arg.yaml"
        THEN a TracerProvider is returned
        AND the config from "arg.yaml" is used (not "env.yaml")
        """
        env_config = tmp_path / "env.yaml"
        arg_config = tmp_path / "arg.yaml"

        env_content = valid_arize_config_content.replace("test-service", "env-service")
        arg_content = valid_arize_config_content.replace("test-service", "arg-service")

        env_config.write_text(env_content)
        arg_config.write_text(arg_content)

        monkeypatch.setenv("LLMOPS_CONFIG_PATH", str(env_config))

        provider = llmops_arize_module.instrument(config_path=arg_config)

        assert provider is not None
        resource = provider.resource
        service_name = resource.attributes.get("service.name")
        assert service_name == "arg-service", (
            "Expected service name 'arg-service' from arg config, "
            f"but got '{service_name}' (env config may have been used instead)"
        )


class TestArizeFileExtensions:
    """Tests for config file extension handling."""

    def test_instrument_accepts_yaml_extension(
        self,
        tmp_path: "Path",
        valid_arize_config_content: str,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a valid config file exists with .yaml extension
        WHEN llmops.arize.instrument() is called with that config path
        THEN a TracerProvider is returned
        """
        config_path = tmp_path / "config.yaml"
        config_path.write_text(valid_arize_config_content)

        provider = llmops_arize_module.instrument(config_path=config_path)

        assert provider is not None

    def test_instrument_accepts_yml_extension(
        self,
        tmp_path: "Path",
        valid_arize_config_content: str,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a valid config file exists with .yml extension
        WHEN llmops.arize.instrument() is called with that config path
        THEN a TracerProvider is returned
        """
        config_path = tmp_path / "config.yml"
        config_path.write_text(valid_arize_config_content)

        provider = llmops_arize_module.instrument(config_path=config_path)

        assert provider is not None


class TestArizeLifecycle:
    """Tests for automatic lifecycle management."""

    def test_instrument_registers_atexit_handler(
        self,
        valid_arize_config_file: "Path",
        llmops_arize_module: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a valid config file exists
        WHEN llmops.arize.instrument() is called
        THEN an atexit handler is registered to shutdown the provider

        This ensures spans are flushed on process exit even if the caller
        doesn't explicitly call provider.shutdown().
        """
        import atexit

        registered_funcs: list[Any] = []
        original_register = atexit.register

        def mock_register(func: Any, *args: Any, **kwargs: Any) -> Any:
            registered_funcs.append(func)
            return original_register(func, *args, **kwargs)

        import llmops._platforms._instrument as instrument_module

        monkeypatch.setattr(instrument_module.atexit, "register", mock_register)

        provider = llmops_arize_module.instrument(config_path=valid_arize_config_file)

        assert len(registered_funcs) >= 1, (
            "Expected at least one atexit handler to be registered"
        )
        assert provider.shutdown in registered_funcs, (
            "atexit handler should include provider.shutdown"
        )
