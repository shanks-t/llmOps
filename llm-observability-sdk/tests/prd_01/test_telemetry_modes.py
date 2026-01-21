"""Tests for telemetry dual-mode (arize.otel vs manual OTLP) and TLS configuration.

Requirements covered:
- Support for arize.otel.register when available
- Fallback to manual OTLP when arize-otel not installed
- TLS certificate configuration via config file
- TLS certificate configuration via environment variables
- Certificate file existence validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_01"
CAPABILITY = "telemetry_modes"


class TestArizeOtelMode:
    """Tests for arize.otel.register integration."""

    def test_create_via_arize_otel_calls_register(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN a valid config with arize credentials
        WHEN _create_via_arize_otel is called
        THEN arize.otel.register is called with correct arguments
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  space_id: test-space
  api_key: test-key
  project_name: test-project
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)

        # Create a mock for arize.otel.register
        mock_provider = MagicMock()
        mock_register = MagicMock(return_value=mock_provider)
        mock_arize_otel = MagicMock()
        mock_arize_otel.register = mock_register

        with patch.dict("sys.modules", {"arize.otel": mock_arize_otel}):
            # Import after patching sys.modules
            import importlib

            import llmops._internal.telemetry as telemetry_module

            importlib.reload(telemetry_module)

            provider = telemetry_module._create_via_arize_otel(config)

            mock_register.assert_called_once()
            call_kwargs = mock_register.call_args[1]
            assert call_kwargs["space_id"] == "test-space"
            assert call_kwargs["api_key"] == "test-key"
            assert call_kwargs["project_name"] == "test-project"
            assert call_kwargs["endpoint"] == "https://otlp.arize.com/v1/traces"
            assert provider == mock_provider

    def test_falls_back_to_manual_when_arize_otel_not_installed(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        mock_sdk_telemetry: Any,
    ) -> None:
        """
        GIVEN arize-otel is NOT installed
        AND use_arize_otel is True (default)
        WHEN create_tracer_provider is called
        THEN manual OTLP setup is used
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: http://localhost:6006/v1/traces
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        # The mock_sdk_telemetry fixture replaces create_tracer_provider
        # which uses manual OTLP. Since arize-otel is not installed,
        # the import will fail and it falls back to manual.
        import llmops

        provider = llmops.init(config_path=config_path)
        assert provider is not None

    def test_uses_manual_otlp_when_use_arize_otel_false(
        self,
        tmp_path: "Path",
        mock_sdk_telemetry: Any,
    ) -> None:
        """
        GIVEN use_arize_otel is False in config
        WHEN create_tracer_provider is called
        THEN manual OTLP setup is used (even if arize-otel would be available)
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: http://localhost:6006/v1/traces
  use_arize_otel: false
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        import llmops

        provider = llmops.init(config_path=config_path)
        assert provider is not None


class TestTLSCertificateConfig:
    """Tests for TLS certificate configuration."""

    def test_certificate_file_from_config(
        self,
        tmp_path: "Path",
    ) -> None:
        """
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

    def test_mtls_config_fields(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN client_key_file and client_certificate_file are specified
        WHEN config is loaded
        THEN mTLS fields are parsed correctly
        """
        ca_cert = tmp_path / "ca.pem"
        client_key = tmp_path / "client-key.pem"
        client_cert = tmp_path / "client-cert.pem"
        ca_cert.write_text("ca cert")
        client_key.write_text("client key")
        client_cert.write_text("client cert")

        config_content = f"""service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  certificate_file: {ca_cert}
  client_key_file: {client_key}
  client_certificate_file: {client_cert}
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.certificate_file == str(ca_cert)
        assert config.arize.client_key_file == str(client_key)
        assert config.arize.client_certificate_file == str(client_cert)


class TestCertificateValidation:
    """Tests for certificate file existence validation."""

    def test_missing_cert_file_fails_in_strict_mode(
        self,
        tmp_path: "Path",
    ) -> None:
        """
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

        # Should not raise - permissive mode
        config = load_config(config_path)
        assert config.arize.certificate_file == "/nonexistent/path/cert.pem"

    def test_missing_client_key_fails_in_strict_mode(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN client_key_file points to non-existent file
        AND validation mode is strict
        WHEN config is loaded
        THEN ConfigurationError is raised
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  client_key_file: /nonexistent/path/key.pem

validation:
  mode: strict
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config
        from llmops.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(config_path)

        assert "Client key file not found" in str(exc_info.value)

    def test_missing_client_cert_fails_in_strict_mode(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN client_certificate_file points to non-existent file
        AND validation mode is strict
        WHEN config is loaded
        THEN ConfigurationError is raised
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  client_certificate_file: /nonexistent/path/cert.pem

validation:
  mode: strict
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config
        from llmops.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(config_path)

        assert "Client certificate file not found" in str(exc_info.value)


class TestProjectNameHeader:
    """Tests for project_name being passed correctly."""

    def test_project_name_in_config(
        self,
        tmp_path: "Path",
    ) -> None:
        """
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
