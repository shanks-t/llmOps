"""Integration tests for Phoenix backend configuration.

These tests verify the complete Phoenix setup including:
- TracerProvider configuration
- OTLP exporter setup
- OpenInference instrumentor enablement
"""

import pytest
from unittest.mock import patch, Mock
from importlib import import_module


class TestPhoenixConfiguration:
    """Tests for Phoenix backend configuration via llmops.configure()."""

    def test_phoenix_creates_otlp_exporter(self):
        """GIVEN phoenix backend
        WHEN llmops.configure() is called
        THEN OTLPSpanExporter is created with correct endpoint.
        """
        configure_module = import_module("llmops.configure")

        with patch.object(configure_module, "_enable_openinference_instrumentors"):
            with patch(
                "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter"
            ) as mock_exporter:
                import llmops

                llmops.configure(
                    backend="phoenix",
                    endpoint="http://phoenix.example.com:6006/v1/traces",
                    service_name="test",
                )

                mock_exporter.assert_called_once_with(
                    endpoint="http://phoenix.example.com:6006/v1/traces"
                )

    def test_phoenix_uses_batch_span_processor(self):
        """GIVEN phoenix backend
        WHEN llmops.configure() is called
        THEN BatchSpanProcessor wraps the OTLP exporter.
        """
        configure_module = import_module("llmops.configure")

        with patch.object(configure_module, "_enable_openinference_instrumentors"):
            with patch(
                "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter"
            ):
                with patch(
                    "opentelemetry.sdk.trace.export.BatchSpanProcessor"
                ) as mock_batch:
                    import llmops

                    llmops.configure(
                        backend="phoenix",
                        endpoint="http://localhost:6006/v1/traces",
                        service_name="test",
                    )

                    mock_batch.assert_called_once()

    def test_phoenix_sets_service_name_resource(self):
        """GIVEN phoenix backend with service_name
        WHEN llmops.configure() is called
        THEN Resource.create() is called with SERVICE_NAME.
        """
        from opentelemetry.sdk.resources import SERVICE_NAME

        configure_module = import_module("llmops.configure")

        captured_attrs = {}

        def capture_create(attrs):
            nonlocal captured_attrs
            captured_attrs = dict(attrs)
            from opentelemetry.sdk.resources import Resource

            return Resource(attrs)

        with patch.object(configure_module, "_enable_openinference_instrumentors"):
            with patch(
                "opentelemetry.sdk.resources.Resource.create", side_effect=capture_create
            ):
                import llmops

                llmops.configure(
                    backend="phoenix",
                    endpoint="http://localhost:6006/v1/traces",
                    service_name="my-test-service",
                )

        assert captured_attrs.get(SERVICE_NAME) == "my-test-service"

    def test_phoenix_sets_global_tracer_provider(self):
        """GIVEN phoenix backend
        WHEN llmops.configure() is called
        THEN global TracerProvider is set (not NoOpTracerProvider).
        """
        import llmops
        from opentelemetry import trace

        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test",
        )

        provider = trace.get_tracer_provider()
        assert provider is not None
        assert type(provider).__name__ == "TracerProvider"


class TestPhoenixWithInit:
    """Tests for Phoenix configuration via llmops.init() with YAML."""

    def test_init_loads_phoenix_from_yaml(self, phoenix_config_yaml):
        """GIVEN llmops.yaml with phoenix backend
        WHEN llmops.init() is called
        THEN Phoenix is configured correctly.
        """
        import llmops

        llmops.init(config_path=phoenix_config_yaml)

        assert llmops.is_configured()
        assert llmops.get_backend() == "phoenix"

    def test_init_phoenix_sets_service_name(self, phoenix_config_yaml):
        """GIVEN llmops.yaml with phoenix and service.name
        WHEN llmops.init() is called
        THEN Resource.create() is called with correct SERVICE_NAME.
        """
        from opentelemetry.sdk.resources import SERVICE_NAME

        configure_module = import_module("llmops.configure")

        captured_attrs = {}

        def capture_create(attrs):
            nonlocal captured_attrs
            captured_attrs = dict(attrs)
            from opentelemetry.sdk.resources import Resource

            return Resource(attrs)

        with patch(
            "opentelemetry.sdk.resources.Resource.create", side_effect=capture_create
        ):
            import llmops

            llmops.init(config_path=phoenix_config_yaml)

        assert captured_attrs.get(SERVICE_NAME) == "integration-test-service"

    def test_init_phoenix_enables_instrumentors(self, phoenix_config_yaml):
        """GIVEN llmops.yaml with phoenix backend
        WHEN llmops.init() is called with auto_instrument=True (default)
        THEN OpenInference instrumentors are enabled.
        """
        configure_module = import_module("llmops.configure")

        with patch.object(
            configure_module, "_enable_openinference_instrumentors"
        ) as mock_enable:
            import llmops

            llmops.init(config_path=phoenix_config_yaml)
            mock_enable.assert_called_once()

    def test_init_phoenix_auto_instrument_false_skips_instrumentors(
        self, phoenix_config_yaml
    ):
        """GIVEN llmops.yaml with phoenix backend
        WHEN llmops.init(auto_instrument=False) is called
        THEN OpenInference instrumentors are NOT enabled.
        """
        configure_module = import_module("llmops.configure")

        with patch.object(
            configure_module, "_enable_openinference_instrumentors"
        ) as mock_enable:
            import llmops

            llmops.init(config_path=phoenix_config_yaml, auto_instrument=False)
            mock_enable.assert_not_called()


class TestPhoenixConsoleOutput:
    """Tests for Phoenix console exporter functionality."""

    def test_phoenix_console_mode_prints_message(self, capsys):
        """GIVEN phoenix backend with console=True
        WHEN llmops.configure() is called
        THEN console exporter enabled message is printed.
        """
        import llmops

        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test",
            console=True,
        )

        captured = capsys.readouterr()
        assert "Console exporter enabled" in captured.out


class TestPhoenixSpanExport:
    """Tests for span export behavior with Phoenix."""

    def test_spans_created_after_configure(self):
        """GIVEN phoenix backend configured
        WHEN spans are created
        THEN they should be associated with the TracerProvider.
        """
        import llmops
        from opentelemetry import trace

        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test",
        )

        tracer = trace.get_tracer("test-tracer")
        with tracer.start_as_current_span("test-span") as span:
            assert span is not None
            assert span.is_recording()

    def test_shutdown_flushes_spans(self):
        """GIVEN phoenix backend with pending spans
        WHEN llmops.shutdown() is called
        THEN provider.force_flush() is called.
        """
        configure_module = import_module("llmops.configure")

        mock_provider = Mock()

        with patch.object(configure_module, "_enable_openinference_instrumentors"):
            with patch(
                "opentelemetry.sdk.trace.TracerProvider", return_value=mock_provider
            ):
                import llmops

                llmops.configure(
                    backend="phoenix",
                    endpoint="http://localhost:6006/v1/traces",
                    service_name="test",
                )

        llmops.shutdown()
        mock_provider.force_flush.assert_called_once()
        mock_provider.shutdown.assert_called_once()
