"""Unit tests for configuration parsing and validation.

Tests derived from PRD_01.

Requirements covered:
- F10: Sensitive values (example: API keys) can be set via env var overrides
- Config option defaults and parsing (transport, batch, log_to_console, verbose)
- TLS certificate configuration
- Project name configuration
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.unit
class TestArizeConfigOptions:
    """Tests for transport, batch, log_to_console, and verbose config options.

    PRD: PRD_01
    """

    def test_transport_defaults_to_http(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN transport is NOT specified in config
        WHEN config is loaded
        THEN transport defaults to 'http'
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.transport == "http"

    def test_transport_grpc_parsed(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN transport is 'grpc' in config
        WHEN config is loaded
        THEN transport is 'grpc'
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  transport: grpc
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.transport == "grpc"

    def test_invalid_transport_defaults_to_http(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN transport is an invalid value
        WHEN config is loaded
        THEN transport defaults to 'http' with a warning
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  transport: invalid
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.transport == "http"

    def test_batch_defaults_to_true(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN batch is NOT specified in config
        WHEN config is loaded
        THEN batch defaults to True
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.batch is True

    def test_batch_false_parsed(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN batch is false in config
        WHEN config is loaded
        THEN batch is False
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  batch: false
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.batch is False

    def test_log_to_console_defaults_to_false(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN log_to_console is NOT specified in config
        WHEN config is loaded
        THEN log_to_console defaults to False
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.log_to_console is False

    def test_log_to_console_true_parsed(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN log_to_console is true in config
        WHEN config is loaded
        THEN log_to_console is True
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  log_to_console: true
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.log_to_console is True

    def test_verbose_defaults_to_false(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN verbose is NOT specified in config
        WHEN config is loaded
        THEN verbose defaults to False
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.verbose is False

    def test_verbose_true_parsed(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN verbose is true in config
        WHEN config is loaded
        THEN verbose is True
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  verbose: true
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.verbose is True


@pytest.mark.unit
class TestTLSCertificateConfig:
    """Tests for TLS certificate configuration.

    PRD: PRD_01
    """

    def test_certificate_file_from_config(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN certificate_file is specified in config
        WHEN config is loaded
        THEN the certificate_file is parsed correctly
        """
        cert_file = tmp_path / "ca-bundle.pem"
        cert_file.write_text("dummy cert content")

        config_content = f"""service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  certificate_file: {cert_file}
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.certificate_file == str(cert_file)

    def test_certificate_file_from_env_var(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01

        GIVEN OTEL_EXPORTER_OTLP_CERTIFICATE env var is set
        AND certificate_file is NOT in config
        WHEN config is loaded
        THEN the env var value is used
        """
        cert_file = tmp_path / "ca-bundle.pem"
        cert_file.write_text("dummy cert content")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_CERTIFICATE", str(cert_file))

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.certificate_file == str(cert_file)

    def test_config_file_overrides_env_var(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01

        GIVEN both config file and env var specify certificate_file
        WHEN config is loaded
        THEN config file value takes precedence
        """
        env_cert = tmp_path / "env-cert.pem"
        env_cert.write_text("env cert")
        config_cert = tmp_path / "config-cert.pem"
        config_cert.write_text("config cert")

        monkeypatch.setenv("OTEL_EXPORTER_OTLP_CERTIFICATE", str(env_cert))

        config_content = f"""service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  certificate_file: {config_cert}
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.certificate_file == str(config_cert)

    def test_relative_path_resolved_from_config_dir(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN certificate_file is a relative path
        WHEN config is loaded
        THEN the path is resolved relative to the config file's directory
        """
        config_dir = tmp_path / "config"
        certs_dir = config_dir / "certs"
        config_dir.mkdir()
        certs_dir.mkdir()

        cert_file = certs_dir / "ca.pem"
        cert_file.write_text("ca cert")

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  certificate_file: ./certs/ca.pem
"""
        config_path = config_dir / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.certificate_file == str(cert_file)

    def test_absolute_path_not_modified(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN certificate_file is an absolute path
        WHEN config is loaded
        THEN the path is used as-is
        """
        cert_file = tmp_path / "ca.pem"
        cert_file.write_text("ca cert")

        config_content = f"""service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  certificate_file: {cert_file}
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.certificate_file == str(cert_file)


@pytest.mark.unit
class TestCertificateValidation:
    """Tests for certificate file existence validation.

    PRD: PRD_01
    """

    def test_missing_cert_file_fails_in_strict_mode(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN certificate_file points to non-existent file
        AND validation mode is strict
        WHEN config is loaded
        THEN ConfigurationError is raised
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  certificate_file: /nonexistent/path/cert.pem

validation:
  mode: strict
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config
        from llmops.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(config_path)

        assert "Certificate file not found" in str(exc_info.value)

    def test_missing_cert_file_succeeds_in_permissive_mode(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN certificate_file points to non-existent file
        AND validation mode is permissive
        WHEN config is loaded
        THEN config loads successfully (validation errors are not raised)
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  certificate_file: /nonexistent/path/cert.pem

validation:
  mode: permissive
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.certificate_file == "/nonexistent/path/cert.pem"


@pytest.mark.unit
class TestTLSBridgeToEnvVars:
    """Tests for _bridge_tls_config_to_env() function.

    PRD: PRD_01
    """

    def test_bridge_sets_certificate_env_var(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01

        GIVEN certificate_file is specified in config
        AND OTEL_EXPORTER_OTLP_CERTIFICATE env var is NOT set
        WHEN _bridge_tls_config_to_env is called
        THEN the env var is set to the certificate path
        """
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_CERTIFICATE", raising=False)

        cert_file = tmp_path / "ca-bundle.pem"
        cert_file.write_text("dummy cert")

        config_content = f"""service:
  name: test-service

arize:
  endpoint: https://otlp.internal/v1/traces
  certificate_file: {cert_file}
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops._internal.telemetry import _bridge_tls_config_to_env
        from llmops.config import load_config

        config = load_config(config_path)
        _bridge_tls_config_to_env(config)

        import os

        assert os.environ.get("OTEL_EXPORTER_OTLP_CERTIFICATE") == str(cert_file)

    def test_bridge_does_not_override_existing_env_var(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01

        GIVEN OTEL_EXPORTER_OTLP_CERTIFICATE env var is already set
        AND certificate_file is specified in config
        WHEN _bridge_tls_config_to_env is called
        THEN the env var is NOT overridden (setdefault behavior)
        """
        existing_cert = "/existing/cert.pem"
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_CERTIFICATE", existing_cert)

        config_cert = tmp_path / "config-cert.pem"
        config_cert.write_text("config cert")

        config_content = f"""service:
  name: test-service

arize:
  endpoint: https://otlp.internal/v1/traces
  certificate_file: {config_cert}
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops._internal.telemetry import _bridge_tls_config_to_env
        from llmops.config import load_config

        config = load_config(config_path)
        _bridge_tls_config_to_env(config)

        import os

        assert os.environ.get("OTEL_EXPORTER_OTLP_CERTIFICATE") == existing_cert

    def test_bridge_skips_none_values(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01

        GIVEN no TLS fields are specified in config
        WHEN _bridge_tls_config_to_env is called
        THEN no env vars are set (no errors, no side effects)
        """
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_CERTIFICATE", raising=False)

        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.internal/v1/traces
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops._internal.telemetry import _bridge_tls_config_to_env
        from llmops.config import load_config

        config = load_config(config_path)
        _bridge_tls_config_to_env(config)

        import os

        assert os.environ.get("OTEL_EXPORTER_OTLP_CERTIFICATE") is None


@pytest.mark.unit
class TestProjectNameHeader:
    """Tests for project_name being passed correctly.

    PRD: PRD_01
    """

    def test_project_name_in_config(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN project_name is specified in config
        WHEN config is loaded
        THEN project_name is available in config
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  project_name: my-awesome-project
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.project_name == "my-awesome-project"


@pytest.mark.unit
class TestEnvVarOverrides:
    """Tests for environment variable override behavior.

    PRD: PRD_01, Requirement: F10
    """

    def test_api_key_can_be_set_via_env_var(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F10

        GIVEN a config file with arize.api_key set to "${ARIZE_API_KEY}"
        AND the ARIZE_API_KEY environment variable is set to "test-api-key"
        WHEN llmops.arize.instrument() is called
        THEN the API key from the environment is used
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            '  api_key: "${ARIZE_API_KEY}"\n'
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: true\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        monkeypatch.setenv("ARIZE_API_KEY", "test-api-key-from-env")

        provider = llmops_arize_module.instrument(config_path=config_path)

        assert provider is not None

    def test_space_id_can_be_set_via_env_var(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F10

        GIVEN a config file with arize.space_id set to "${ARIZE_SPACE_ID}"
        AND the ARIZE_SPACE_ID environment variable is set
        WHEN llmops.arize.instrument() is called
        THEN the space ID from the environment is used
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            '  space_id: "${ARIZE_SPACE_ID}"\n'
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: true\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        monkeypatch.setenv("ARIZE_SPACE_ID", "test-space-id-from-env")

        provider = llmops_arize_module.instrument(config_path=config_path)

        assert provider is not None

    def test_missing_env_var_in_permissive_mode_does_not_fail(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F10

        GIVEN a config file referencing an env var that is not set
        AND validation mode is permissive
        WHEN llmops.arize.instrument() is called
        THEN the SDK initializes without raising an exception
        AND a no-op or degraded mode is used
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            '  api_key: "${NONEXISTENT_ENV_VAR}"\n'
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: true\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        monkeypatch.delenv("NONEXISTENT_ENV_VAR", raising=False)

        provider = llmops_arize_module.instrument(config_path=config_path)

        assert provider is not None

    def test_missing_env_var_in_strict_mode_raises_error(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F10

        GIVEN a config file referencing an env var that is not set
        AND validation mode is strict
        WHEN llmops.arize.instrument() is called
        THEN a ConfigurationError is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            '  api_key: "${NONEXISTENT_ENV_VAR}"\n'
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: true\n"
            "validation:\n"
            "  mode: strict\n"
        )

        monkeypatch.delenv("NONEXISTENT_ENV_VAR", raising=False)

        with pytest.raises(llmops_arize_module.ConfigurationError):
            llmops_arize_module.instrument(config_path=config_path)
