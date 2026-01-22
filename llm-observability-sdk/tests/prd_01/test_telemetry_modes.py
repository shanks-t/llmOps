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


class TestNewConfigOptions:
    """Tests for transport, batch_spans, and debug config options."""

    def test_transport_defaults_to_http(
        self,
        tmp_path: "Path",
    ) -> None:
        """
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

    def test_batch_spans_defaults_to_true(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN batch_spans is NOT specified in config
        WHEN config is loaded
        THEN batch_spans defaults to True
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
        assert config.arize.batch_spans is True

    def test_batch_spans_false_parsed(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN batch_spans is false in config
        WHEN config is loaded
        THEN batch_spans is False
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  batch_spans: false
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.batch_spans is False

    def test_debug_defaults_to_false(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN debug is NOT specified in config
        WHEN config is loaded
        THEN debug defaults to False
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
        assert config.arize.debug is False

    def test_debug_true_parsed(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN debug is true in config
        WHEN config is loaded
        THEN debug is True
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  debug: true
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)
        assert config.arize.debug is True

    def test_arize_otel_receives_new_options(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN transport, batch_spans, and debug are specified in config
        WHEN _create_via_arize_otel is called
        THEN arize.otel.register receives these options
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  space_id: test-space
  api_key: test-key
  transport: http
  batch_spans: false
  debug: true
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)

        # Mock arize.otel.register and Transport
        mock_provider = MagicMock()
        mock_register = MagicMock(return_value=mock_provider)
        mock_transport = MagicMock()
        mock_transport.HTTP = "HTTP"
        mock_transport.GRPC = "GRPC"
        mock_arize_otel = MagicMock()
        mock_arize_otel.register = mock_register
        mock_arize_otel.Transport = mock_transport

        with patch.dict("sys.modules", {"arize.otel": mock_arize_otel}):
            import importlib

            import llmops._internal.telemetry as telemetry_module

            importlib.reload(telemetry_module)

            telemetry_module._create_via_arize_otel(config)

            mock_register.assert_called_once()
            call_kwargs = mock_register.call_args[1]
            assert call_kwargs["transport"] == "HTTP"  # HTTP from Transport enum
            assert call_kwargs["batch"] is False
            assert call_kwargs["log_to_console"] is True


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

    def test_relative_path_resolved_from_config_dir(
        self,
        tmp_path: "Path",
    ) -> None:
        """
        GIVEN certificate_file is a relative path
        WHEN config is loaded
        THEN the path is resolved relative to the config file's directory
        """
        # Create a subdirectory structure
        config_dir = tmp_path / "config"
        certs_dir = config_dir / "certs"
        config_dir.mkdir()
        certs_dir.mkdir()

        cert_file = certs_dir / "ca.pem"
        cert_file.write_text("ca cert")

        # Use relative path in config
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
        # Should be resolved to absolute path from config file's directory
        assert config.arize.certificate_file == str(cert_file)

    def test_absolute_path_not_modified(
        self,
        tmp_path: "Path",
    ) -> None:
        """
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


class TestTLSBridgeToEnvVars:
    """Tests for _bridge_tls_config_to_env() function.

    This function bridges TLS certificate configuration from llmops config
    to standard OTEL environment variables, enabling seamless TLS support
    when using arize.otel.register().
    """

    def test_bridge_sets_certificate_env_var(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        GIVEN certificate_file is specified in config
        AND OTEL_EXPORTER_OTLP_CERTIFICATE env var is NOT set
        WHEN _bridge_tls_config_to_env is called
        THEN the env var is set to the certificate path
        """
        # Ensure env var is not set
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

        # Should keep existing value, not override
        assert os.environ.get("OTEL_EXPORTER_OTLP_CERTIFICATE") == existing_cert

    def test_bridge_skips_none_values(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        GIVEN no TLS fields are specified in config
        WHEN _bridge_tls_config_to_env is called
        THEN no env vars are set (no errors, no side effects)
        """
        # Clear env var
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

    def test_arize_otel_path_calls_bridge(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        GIVEN certificate_file is specified in config
        AND arize-otel is available
        WHEN _create_via_arize_otel is called
        THEN _bridge_tls_config_to_env is called (env var is set)
        """
        # Clear env var
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_CERTIFICATE", raising=False)

        cert_file = tmp_path / "ca-bundle.pem"
        cert_file.write_text("dummy cert")

        config_content = f"""service:
  name: test-service

arize:
  endpoint: https://otlp.internal/v1/traces
  certificate_file: {cert_file}
  space_id: test-space
  api_key: test-key
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config

        config = load_config(config_path)

        # Mock arize.otel.register and Transport
        mock_provider = MagicMock()
        mock_register = MagicMock(return_value=mock_provider)
        mock_transport = MagicMock()
        mock_transport.HTTP = "HTTP"
        mock_transport.GRPC = "GRPC"
        mock_arize_otel = MagicMock()
        mock_arize_otel.register = mock_register
        mock_arize_otel.Transport = mock_transport

        with patch.dict("sys.modules", {"arize.otel": mock_arize_otel}):
            import importlib

            import llmops._internal.telemetry as telemetry_module

            importlib.reload(telemetry_module)

            telemetry_module._create_via_arize_otel(config)

            # Verify env var was set by the bridge
            import os

            assert os.environ.get("OTEL_EXPORTER_OTLP_CERTIFICATE") == str(cert_file)


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
