"""Integration tests for Arize telemetry setup using FakeArizeOtel.

Tests derived from PRD_01.

Requirements covered:
- TracerProvider creation via arize.otel.register
- Config option passing to arize.otel.register
- TLS certificate bridging to environment variables
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from opentelemetry.sdk.trace import TracerProvider

from tests.fakes import Transport

if TYPE_CHECKING:
    from pathlib import Path

    from tests.fakes import FakeArizeOtel


@pytest.mark.integration
@pytest.mark.disable_mock_sdk_telemetry
class TestArizeOtelMode:
    """Tests for arize.otel.register integration.

    These tests verify that create_arize_provider correctly passes
    config values to arize.otel.register() parameters using FakeArizeOtel.

    PRD: PRD_01
    """

    def test_create_arize_provider_passes_config_to_register(
        self,
        tmp_path: "Path",
        patched_arize_otel: "FakeArizeOtel",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN a valid config with arize credentials
        WHEN create_arize_provider is called
        THEN arize.otel.register receives the config values
        """
        config_content = """platform: arize

service:
  name: test-service

arize:
  endpoint: https://otlp.arize.com/v1/traces
  space_id: test-space
  api_key: test-key
  project_name: test-project
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.exporters.arize.exporter import create_arize_provider
        from llmops.sdk.config.load import load_config

        config = load_config(config_path)
        provider = create_arize_provider(config)

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

    def test_arize_otel_receives_config_options(
        self,
        tmp_path: "Path",
        patched_arize_otel: "FakeArizeOtel",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN transport, batch, log_to_console, and verbose are specified in config
        WHEN create_arize_provider is called
        THEN arize.otel.register receives these options
        """
        config_content = """platform: arize

service:
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

        from llmops.exporters.arize.exporter import create_arize_provider
        from llmops.sdk.config.load import load_config

        config = load_config(config_path)
        create_arize_provider(config)

        # Verify config values are passed to arize.otel.register
        patched_arize_otel.assert_registered_once()
        patched_arize_otel.assert_registered_with(
            transport=Transport.HTTP,
            batch=False,
            log_to_console=True,
            verbose=True,
        )

    def test_create_arize_provider_calls_tls_bridge(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        patched_arize_otel: "FakeArizeOtel",
    ) -> None:
        """
        PRD: PRD_01

        GIVEN certificate_file is specified in config
        WHEN create_arize_provider is called
        THEN _bridge_tls_config_to_env is called (env var is set)

        Note: This tests the side effect of TLS config bridging to env vars,
        which is the observable behavior we care about.
        """
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_CERTIFICATE", raising=False)

        cert_file = tmp_path / "ca-bundle.pem"
        cert_file.write_text("dummy cert")

        config_content = f"""platform: arize

service:
  name: test-service

arize:
  endpoint: https://otlp.internal/v1/traces
  certificate_file: {cert_file}
  space_id: test-space
  api_key: test-key
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.exporters.arize.exporter import create_arize_provider
        from llmops.sdk.config.load import load_config

        config = load_config(config_path)
        create_arize_provider(config)

        # Verify the observable behavior: env var is set
        import os

        assert os.environ.get("OTEL_EXPORTER_OTLP_CERTIFICATE") == str(cert_file)

    def test_project_name_defaults_to_service_name(
        self,
        tmp_path: "Path",
        patched_arize_otel: "FakeArizeOtel",
    ) -> None:
        """
        GIVEN project_name is NOT specified in config
        WHEN create_arize_provider is called
        THEN project_name defaults to service.name
        """
        config_content = """platform: arize

service:
  name: my-service-name

arize:
  endpoint: https://otlp.arize.com/v1/traces
  space_id: test-space
  api_key: test-key
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        from llmops.exporters.arize.exporter import create_arize_provider
        from llmops.sdk.config.load import load_config

        config = load_config(config_path)
        create_arize_provider(config)

        patched_arize_otel.assert_registered_with(
            project_name="my-service-name",
        )
