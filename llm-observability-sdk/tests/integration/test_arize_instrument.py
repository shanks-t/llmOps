"""Integration tests for SDK initialization.

Tests derived from PRD_01.

Requirements covered:
- F1: llmops.instrument(config) initializes the SDK
- F2: llmops.instrument() initializes telemetry
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


@pytest.mark.integration
class TestConfigResolution:
    """Tests for config path resolution behavior.

    PRD: PRD_01, Requirements: F1, F6
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
        valid_arize_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F1, F2

        GIVEN a valid config file exists
        AND the LLMOPS_CONFIG_PATH environment variable is set to that path
        WHEN llmops.instrument() is called without arguments
        THEN the SDK initializes successfully
        """
        monkeypatch.setenv("LLMOPS_CONFIG_PATH", str(valid_arize_config_file))

        llmops_module.instrument()

        assert llmops_module.is_configured()

    def test_instrument_explicit_path_takes_precedence_over_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: "Path",
        valid_arize_config_content: str,
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

        env_content = valid_arize_config_content.replace("test-service", "env-service")
        arg_content = valid_arize_config_content.replace("test-service", "arg-service")

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
class TestFileExtensions:
    """Tests for config file extension handling.

    PRD: PRD_01, Requirement: F7
    """

    def test_instrument_accepts_yaml_extension(
        self,
        tmp_path: "Path",
        valid_arize_config_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F7

        GIVEN a valid config file exists with .yaml extension
        WHEN llmops.instrument() is called with that config path
        THEN the SDK initializes successfully
        """
        config_path = tmp_path / "config.yaml"
        config_path.write_text(valid_arize_config_content)

        llmops_module.instrument(config=config_path)

        assert llmops_module.is_configured()

    def test_instrument_accepts_yml_extension(
        self,
        tmp_path: "Path",
        valid_arize_config_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F7

        GIVEN a valid config file exists with .yml extension
        WHEN llmops.instrument() is called with that config path
        THEN the SDK initializes successfully
        """
        config_path = tmp_path / "config.yml"
        config_path.write_text(valid_arize_config_content)

        llmops_module.instrument(config=config_path)

        assert llmops_module.is_configured()


@pytest.mark.integration
class TestLifecycle:
    """Tests for automatic lifecycle management.

    PRD: PRD_01, Requirement: N4
    """

    def test_instrument_registers_atexit_handler(
        self,
        valid_arize_config_file: "Path",
        llmops_module: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01, Requirement: N4

        GIVEN a valid config file exists
        WHEN llmops.instrument() is called
        THEN an atexit handler is registered to shutdown the provider

        This ensures spans are flushed on process exit even if the caller
        doesn't explicitly call shutdown().
        """
        import atexit

        registered_funcs: list[Any] = []
        original_register = atexit.register

        def mock_register(func: Any, *args: Any, **kwargs: Any) -> Any:
            registered_funcs.append(func)
            return original_register(func, *args, **kwargs)

        import llmops.api._init as init_module

        monkeypatch.setattr(init_module.atexit, "register", mock_register)

        llmops_module.instrument(config=valid_arize_config_file)

        assert len(registered_funcs) >= 1, (
            "Expected at least one atexit handler to be registered"
        )

    def test_shutdown_resets_configured_state(
        self,
        valid_arize_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        GIVEN the SDK has been initialized
        WHEN shutdown() is called
        THEN is_configured() returns False
        """
        llmops_module.instrument(config=valid_arize_config_file)
        assert llmops_module.is_configured()

        llmops_module.shutdown()
        assert not llmops_module.is_configured()

    def test_shutdown_is_idempotent(
        self,
        valid_arize_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        GIVEN the SDK has been initialized
        WHEN shutdown() is called multiple times
        THEN no error is raised
        """
        llmops_module.instrument(config=valid_arize_config_file)

        # Multiple shutdowns should not raise
        llmops_module.shutdown()
        llmops_module.shutdown()
        llmops_module.shutdown()

        assert not llmops_module.is_configured()


@pytest.mark.integration
class TestProgrammaticConfig:
    """Tests for programmatic configuration via Config object."""

    def test_instrument_accepts_config_object(
        self,
        llmops_module: Any,
    ) -> None:
        """
        GIVEN a Config object is created programmatically
        WHEN llmops.instrument() is called with that Config
        THEN the SDK initializes successfully
        """
        config = llmops_module.Config(
            platform="arize",
            service=llmops_module.ServiceConfig(name="programmatic-service"),
            arize=llmops_module.ArizeConfig(endpoint="http://localhost:6006/v1/traces"),
        )

        llmops_module.instrument(config=config)

        assert llmops_module.is_configured()
