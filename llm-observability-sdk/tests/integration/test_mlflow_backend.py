"""Integration tests for MLflow backend configuration.

These tests verify the complete MLflow setup per MLflow ADK docs:
https://mlflow.org/docs/latest/genai/tracing/integrations/listing/google-adk/

Key behaviors:
- Tracking URI configuration
- Experiment setup
- OTLP exporter for ADK tracing (not mlflow.autolog or mlflow.tracing.enable)
"""

import pytest
from unittest.mock import patch


@pytest.fixture
def mock_mlflow():
    """Mock mlflow module for tests."""
    mlflow = pytest.importorskip("mlflow")
    return mlflow


class TestMlflowConfiguration:
    """Tests for MLflow backend configuration via llmops.configure()."""

    def test_mlflow_sets_tracking_uri(self, mock_mlflow):
        """GIVEN mlflow backend
        WHEN llmops.configure() is called
        THEN mlflow.set_tracking_uri() is called with endpoint.
        """
        with patch.object(mock_mlflow, "set_tracking_uri") as mock_set_uri:
            with patch.object(mock_mlflow, "set_experiment"):
                import llmops

                llmops.configure(
                    backend="mlflow",
                    endpoint="http://mlflow.example.com:5001",
                    service_name="test",
                )

                mock_set_uri.assert_called_once_with(
                    "http://mlflow.example.com:5001"
                )

    def test_mlflow_sets_experiment_to_service_name(self, mock_mlflow):
        """GIVEN mlflow backend
        WHEN llmops.configure() is called
        THEN mlflow.set_experiment() is called with service_name.
        """
        with patch.object(mock_mlflow, "set_tracking_uri"):
            with patch.object(mock_mlflow, "set_experiment") as mock_set_exp:
                import llmops

                llmops.configure(
                    backend="mlflow",
                    endpoint="http://localhost:5001",
                    service_name="my-experiment-name",
                )

                mock_set_exp.assert_called_once_with("my-experiment-name")

    def test_mlflow_creates_otlp_exporter_for_adk(self, mock_mlflow):
        """GIVEN mlflow backend
        WHEN llmops.configure() is called
        THEN OTLP exporter is created for ADK tracing to /v1/traces.

        Per MLflow ADK docs, ADK tracing uses OTLP exporter, not mlflow.autolog().
        """
        with patch(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter"
        ) as mock_exporter:
            with patch.object(mock_mlflow, "set_tracking_uri"):
                with patch.object(mock_mlflow, "set_experiment"):
                    import llmops

                    llmops.configure(
                        backend="mlflow",
                        endpoint="http://localhost:5001",
                        service_name="test",
                    )

                    mock_exporter.assert_called_once()
                    call_kwargs = mock_exporter.call_args.kwargs
                    assert "/v1/traces" in call_kwargs.get("endpoint", "")

    def test_mlflow_otlp_exporter_has_experiment_id_header(self, mock_mlflow):
        """GIVEN mlflow backend
        WHEN llmops.configure() is called
        THEN OTLP exporter has x-mlflow-experiment-id header.
        """
        with patch(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter"
        ) as mock_exporter:
            with patch.object(mock_mlflow, "set_tracking_uri"):
                with patch.object(mock_mlflow, "set_experiment"):
                    import llmops

                    llmops.configure(
                        backend="mlflow",
                        endpoint="http://localhost:5001",
                        service_name="test",
                    )

                    call_kwargs = mock_exporter.call_args.kwargs
                    headers = call_kwargs.get("headers", {})
                    assert "x-mlflow-experiment-id" in headers

    def test_mlflow_sets_global_tracer_provider(self, mock_mlflow):
        """GIVEN mlflow backend
        WHEN llmops.configure() is called
        THEN global TracerProvider is set (not NoOpTracerProvider).
        """
        from opentelemetry import trace

        with patch.object(mock_mlflow, "set_tracking_uri"):
            with patch.object(mock_mlflow, "set_experiment"):
                import llmops

                llmops.configure(
                    backend="mlflow",
                    endpoint="http://localhost:5001",
                    service_name="test",
                )

                provider = trace.get_tracer_provider()
                assert provider is not None
                assert type(provider).__name__ == "TracerProvider"

    def test_mlflow_uses_simple_span_processor(self, mock_mlflow):
        """GIVEN mlflow backend
        WHEN llmops.configure() is called
        THEN SimpleSpanProcessor is used (per MLflow ADK docs).
        """
        with patch(
            "opentelemetry.sdk.trace.export.SimpleSpanProcessor"
        ) as mock_processor:
            with patch.object(mock_mlflow, "set_tracking_uri"):
                with patch.object(mock_mlflow, "set_experiment"):
                    import llmops

                    llmops.configure(
                        backend="mlflow",
                        endpoint="http://localhost:5001",
                        service_name="test",
                    )

                    mock_processor.assert_called()


class TestMlflowWithInit:
    """Tests for MLflow configuration via llmops.init() with YAML."""

    def test_init_loads_mlflow_from_yaml(self, mlflow_config_yaml, mock_mlflow):
        """GIVEN llmops.yaml with mlflow backend
        WHEN llmops.init() is called
        THEN MLflow is configured correctly.
        """
        with patch.object(mock_mlflow, "set_tracking_uri"):
            with patch.object(mock_mlflow, "set_experiment"):
                import llmops

                llmops.init(config_path=mlflow_config_yaml)

                assert llmops.is_configured()
                assert llmops.get_backend() == "mlflow"

    def test_init_mlflow_uses_service_name_as_experiment(
        self, mlflow_config_yaml, mock_mlflow
    ):
        """GIVEN llmops.yaml with mlflow and service.name
        WHEN llmops.init() is called
        THEN experiment name matches service name.
        """
        with patch.object(mock_mlflow, "set_tracking_uri"):
            with patch.object(mock_mlflow, "set_experiment") as mock_set_exp:
                import llmops

                llmops.init(config_path=mlflow_config_yaml)

                mock_set_exp.assert_called_once_with("integration-test-service")


class TestMlflowConsoleOutput:
    """Tests for MLflow console output functionality."""

    def test_mlflow_console_adds_console_exporter(self, mock_mlflow, capsys):
        """GIVEN mlflow backend with console=True
        WHEN llmops.configure() is called
        THEN ConsoleSpanExporter is added.
        """
        with patch.object(mock_mlflow, "set_tracking_uri"):
            with patch.object(mock_mlflow, "set_experiment"):
                import llmops

                llmops.configure(
                    backend="mlflow",
                    endpoint="http://localhost:5001",
                    service_name="test",
                    console=True,
                )

                captured = capsys.readouterr()
                assert "Console exporter enabled" in captured.out


class TestMlflowShutdown:
    """Tests for MLflow shutdown behavior."""

    def test_mlflow_shutdown_flushes_provider(self, mock_mlflow):
        """GIVEN mlflow backend configured
        WHEN llmops.shutdown() is called
        THEN TracerProvider is flushed and shutdown.

        Note: Per MLflow ADK docs, we don't use mlflow.tracing.disable()
        since we use OTLP-based tracing, not MLflow native tracing.
        """
        from unittest.mock import Mock

        with patch.object(mock_mlflow, "set_tracking_uri"):
            with patch.object(mock_mlflow, "set_experiment"):
                with patch(
                    "opentelemetry.sdk.trace.TracerProvider"
                ) as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider_class.return_value = mock_provider

                    import llmops

                    llmops.configure(
                        backend="mlflow",
                        endpoint="http://localhost:5001",
                        service_name="test",
                    )

        import llmops

        llmops.shutdown()
        mock_provider.force_flush.assert_called_once()
        mock_provider.shutdown.assert_called_once()


class TestMlflowNotInstalled:
    """Tests for behavior when MLflow is not installed."""

    def test_mlflow_raises_if_not_installed(self):
        """GIVEN mlflow not installed
        WHEN llmops.configure(backend='mlflow') is called
        THEN ImportError is raised with helpful message.
        """
        import sys

        # Temporarily remove mlflow from sys.modules
        mlflow_modules = {k: v for k, v in sys.modules.items() if "mlflow" in k}
        for key in mlflow_modules:
            del sys.modules[key]

        try:
            with patch.dict("sys.modules", {"mlflow": None}):

                def raise_import(*args, **kwargs):
                    if args[0] == "mlflow" or "mlflow" in str(args):
                        raise ImportError("No module named 'mlflow'")
                    return __builtins__.__dict__["__import__"](*args, **kwargs)

                with patch("builtins.__import__", side_effect=raise_import):
                    with pytest.raises(ImportError, match="mlflow"):
                        import llmops

                        llmops.configure(
                            backend="mlflow",
                            endpoint="http://localhost:5001",
                            service_name="test",
                        )
        finally:
            # Restore mlflow modules
            sys.modules.update(mlflow_modules)
