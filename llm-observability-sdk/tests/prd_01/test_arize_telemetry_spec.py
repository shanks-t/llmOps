"""Tests for Arize telemetry setup and TLS configuration.

Requirements covered:
- TracerProvider creation via arize.otel.register
- TLS certificate configuration via config file
- TLS certificate configuration via environment variables
- Certificate file existence validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from opentelemetry.sdk.trace import TracerProvider

from tests.fakes import Transport

if TYPE_CHECKING:
    from pathlib import Path
    from tests.fakes import FakeArizeOtel

# Traceability metadata
PRD_ID = "PRD_01"
CAPABILITY = "arize_telemetry"


@pytest.mark.disable_mock_sdk_telemetry
class TestArizeOtelMode:
    """Tests for arize.otel.register integration.

    These tests verify that create_tracer_provider correctly passes
    config values to arize.otel.register() parameters using FakeArizeOtel.

    Note: This class is marked with @pytest.mark.disable_mock_sdk_telemetry
    to disable the autouse mock_sdk_telemetry fixture, allowing tests to
    verify actual arize.otel interactions.
    """

    def test_create_tracer_provider_passes_config_to_register(
        self,
        tmp_path: "Path",
        patched_arize_otel: "FakeArizeOtel",
    ) -> None:
        """
        GIVEN a valid config with arize credentials
        WHEN create_tracer_provider is called
        THEN arize.otel.register receives the config values
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
        import llmops._internal.telemetry as telemetry_module

        config = load_config(config_path)
        provider = telemetry_module.create_tracer_provider(config)

        # Verify config values are passed to arize.otel.register
        patched_arize_otel.assert_registered_once()
        patched_arize_otel.assert_registered_with(
            space_id="test-space",
            api_key="test-key",
            project_name="test-project",
            endpoint="https://otlp.arize.com/v1/traces",
        )

        # Verify we got a real TracerProvider
        assert isinstance(provider, TracerProvider)


class TestArizeConfigOptions:
    """Tests for transport, batch, log_to_console, and verbose config options."""

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

    def test_batch_defaults_to_true(
        self,
        tmp_path: "Path",
    ) -> None:
        """
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

    @pytest.mark.disable_mock_sdk_telemetry
    def test_arize_otel_receives_config_options(
        self,
        tmp_path: "Path",
        patched_arize_otel: "FakeArizeOtel",
    ) -> None:
        """
        GIVEN transport, batch, log_to_console, and verbose are specified in config
        WHEN create_tracer_provider is called
        THEN arize.otel.register receives these options
        """
        config_content = """service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  space_id: test-space
  api_key: test-key
  transport: http
  batch: false
  log_to_console: true
  verbose: true
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.config import load_config
        import llmops._internal.telemetry as telemetry_module

        config = load_config(config_path)
        telemetry_module.create_tracer_provider(config)

        # Verify config values are passed to arize.otel.register
        patched_arize_otel.assert_registered_once()
        patched_arize_otel.assert_registered_with(
            transport=Transport.HTTP,
            batch=False,
            log_to_console=True,
            verbose=True,
        )


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

        config = load_config(config_path)
        assert config.arize.certificate_file == "/nonexistent/path/cert.pem"


class TestTLSBridgeToEnvVars:
    """Tests for _bridge_tls_config_to_env() function."""

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

    @pytest.mark.disable_mock_sdk_telemetry
    def test_create_tracer_provider_calls_bridge(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        patched_arize_otel: "FakeArizeOtel",
    ) -> None:
        """
        GIVEN certificate_file is specified in config
        WHEN create_tracer_provider is called
        THEN _bridge_tls_config_to_env is called (env var is set)

        Note: This tests the side effect of TLS config bridging to env vars,
        which is the observable behavior we care about.
        """
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
        import llmops._internal.telemetry as telemetry_module

        config = load_config(config_path)
        telemetry_module.create_tracer_provider(config)

        # Verify the observable behavior: env var is set
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
