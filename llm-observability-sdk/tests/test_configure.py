"""Tests for llmops.configure() - BDD/TDD test suite.

These tests define the expected behavior and invariants for backend configuration.
Use red-green-refactor pattern: write failing tests first, then implement.
"""

import pytest
from unittest.mock import Mock, patch
import llmops
from llmops import ConfigurationError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def reset_llmops():
    """Reset llmops state before and after each test."""
    # Setup: ensure clean state
    if llmops.is_configured():
        llmops.shutdown()
    yield
    # Teardown: cleanup
    if llmops.is_configured():
        llmops.shutdown()


# =============================================================================
# CONFIGURATION VALIDATION TESTS
# =============================================================================

class TestConfigurationValidation:
    """Tests for configuration input validation."""

    def test_configure_requires_endpoint(self):
        """GIVEN no endpoint WHEN configure() THEN raise ConfigurationError."""
        with pytest.raises(ConfigurationError, match="endpoint is required"):
            llmops.configure(backend="phoenix", endpoint="")

    def test_configure_unknown_backend_raises(self):
        """GIVEN unknown backend WHEN configure() THEN raise ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Unknown backend"):
            llmops.configure(backend="unknown", endpoint="http://localhost:9999")

    def test_configure_already_configured_raises(self):
        """GIVEN already configured WHEN configure() again THEN raise ConfigurationError."""
        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test",
        )
        with pytest.raises(ConfigurationError, match="already configured"):
            llmops.configure(
                backend="phoenix",
                endpoint="http://localhost:6006/v1/traces",
                service_name="test2",
            )

    def test_configure_valid_backends(self):
        """GIVEN valid backend names WHEN configure() THEN succeed."""
        # Phoenix
        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test",
        )
        assert llmops.get_backend() == "phoenix"
        llmops.shutdown()

        # MLflow (skip if not installed)
        mlflow = pytest.importorskip("mlflow")
        with patch.object(mlflow, "set_tracking_uri"):
            with patch.object(mlflow, "set_experiment"):
                llmops.configure(
                    backend="mlflow",
                    endpoint="http://localhost:5001",
                    service_name="test",
                )
        assert llmops.get_backend() == "mlflow"


# =============================================================================
# STATE MANAGEMENT TESTS
# =============================================================================

class TestStateManagement:
    """Tests for configuration state management."""

    def test_is_configured_returns_false_initially(self):
        """GIVEN fresh state WHEN is_configured() THEN return False."""
        assert not llmops.is_configured()

    def test_get_backend_returns_none_when_not_configured(self):
        """GIVEN not configured WHEN get_backend() THEN return None."""
        assert llmops.get_backend() is None

    def test_shutdown_allows_reconfigure(self):
        """GIVEN configured WHEN shutdown() THEN allow reconfiguration."""
        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test1",
        )
        llmops.shutdown()
        assert not llmops.is_configured()

        # Should be able to reconfigure
        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test2",
        )
        assert llmops.is_configured()

    def test_shutdown_idempotent(self):
        """GIVEN not configured WHEN shutdown() THEN no error."""
        llmops.shutdown()  # Should not raise
        assert not llmops.is_configured()


# =============================================================================
# PHOENIX BACKEND TESTS
# =============================================================================

class TestPhoenixBackend:
    """Tests for Phoenix backend configuration.

    Invariants:
    - TracerProvider is set globally via trace.set_tracer_provider()
    - OTLP exporter configured with correct endpoint
    - BatchSpanProcessor used for OTLP exporter
    - OpenInference instrumentors enabled (ADK, GenAI)
    - Resource includes SERVICE_NAME
    """

    def test_phoenix_sets_tracer_provider(self):
        """GIVEN phoenix backend WHEN configure() THEN set global TracerProvider."""
        from opentelemetry import trace

        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test-service",
        )

        provider = trace.get_tracer_provider()
        assert provider is not None
        # Verify it's our TracerProvider (not NoOpTracerProvider)
        assert type(provider).__name__ == "TracerProvider"

    def test_phoenix_configures_otlp_exporter(self):
        """GIVEN phoenix backend WHEN configure() THEN OTLP exporter has correct endpoint."""
        from importlib import import_module
        configure_module = import_module("llmops.configure")

        with patch.object(configure_module, "_enable_openinference_instrumentors"):
            with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter") as mock_exporter_class:
                with patch("opentelemetry.sdk.trace.export.BatchSpanProcessor"):
                    llmops.configure(
                        backend="phoenix",
                        endpoint="http://localhost:6006/v1/traces",
                        service_name="test",
                    )
                    mock_exporter_class.assert_called_once_with(
                        endpoint="http://localhost:6006/v1/traces"
                    )

    def test_phoenix_uses_batch_span_processor(self):
        """GIVEN phoenix backend WHEN configure() THEN use BatchSpanProcessor for OTLP."""
        from importlib import import_module
        configure_module = import_module("llmops.configure")

        with patch.object(configure_module, "_enable_openinference_instrumentors"):
            with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter") as mock_exporter_class:
                with patch("opentelemetry.sdk.trace.export.BatchSpanProcessor") as mock_batch:
                    mock_exporter = Mock()
                    mock_exporter_class.return_value = mock_exporter

                    llmops.configure(
                        backend="phoenix",
                        endpoint="http://localhost:6006/v1/traces",
                        service_name="test",
                    )

                    mock_batch.assert_called_once_with(mock_exporter)

    def test_phoenix_sets_service_name_resource(self):
        """GIVEN phoenix backend with service_name WHEN configure() THEN resource has SERVICE_NAME."""
        from importlib import import_module
        from opentelemetry.sdk.resources import SERVICE_NAME
        configure_module = import_module("llmops.configure")

        # Track the arguments passed to Resource.create
        captured_attrs = {}

        def capture_create(attrs):
            nonlocal captured_attrs
            captured_attrs = dict(attrs)
            # Import here to avoid patching issues
            from opentelemetry.sdk.resources import Resource
            return Resource(attrs)

        with patch.object(configure_module, "_enable_openinference_instrumentors"):
            with patch("opentelemetry.sdk.resources.Resource.create", side_effect=capture_create):
                llmops.configure(
                    backend="phoenix",
                    endpoint="http://localhost:6006/v1/traces",
                    service_name="my-test-service",
                )

        # Verify service name was passed
        assert captured_attrs.get(SERVICE_NAME) == "my-test-service"

    def test_phoenix_enables_openinference_instrumentors(self):
        """GIVEN phoenix backend WHEN configure() THEN enable OpenInference instrumentors."""
        from importlib import import_module
        configure_module = import_module("llmops.configure")

        with patch.object(configure_module, "_enable_openinference_instrumentors") as mock_enable:
            llmops.configure(
                backend="phoenix",
                endpoint="http://localhost:6006/v1/traces",
                service_name="test",
            )
            mock_enable.assert_called_once()

    def test_phoenix_console_adds_console_exporter(self, capsys):
        """GIVEN phoenix backend with console=True WHEN configure() THEN add ConsoleSpanExporter."""
        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test",
            console=True,
        )

        captured = capsys.readouterr()
        assert "Console exporter enabled" in captured.out


class TestOpenInferenceInstrumentors:
    """Tests for OpenInference instrumentor enablement."""

    def test_enables_google_adk_instrumentor(self):
        """GIVEN OpenInference ADK installed WHEN _enable_openinference_instrumentors() THEN instrument ADK."""
        mock_provider = Mock()
        mock_instrumentor = Mock()
        mock_module = Mock()
        mock_module.GoogleADKInstrumentor = Mock(return_value=mock_instrumentor)

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "openinference.instrumentation.google_adk":
                return mock_module
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            from importlib import import_module
            configure_module = import_module("llmops.configure")
            configure_module._enable_openinference_instrumentors(mock_provider)
            mock_instrumentor.instrument.assert_called_with(tracer_provider=mock_provider)

    def test_enables_google_genai_instrumentor(self):
        """GIVEN OpenInference GenAI installed WHEN _enable_openinference_instrumentors() THEN instrument GenAI."""
        mock_provider = Mock()
        mock_instrumentor = Mock()
        mock_module = Mock()
        mock_module.GoogleGenAIInstrumentor = Mock(return_value=mock_instrumentor)

        with patch.dict("sys.modules", {
            "openinference.instrumentation.google_genai": mock_module
        }):
            from llmops.configure import _enable_openinference_instrumentors
            _enable_openinference_instrumentors(mock_provider)
            mock_instrumentor.instrument.assert_called_with(tracer_provider=mock_provider)

    def test_handles_missing_instrumentors_gracefully(self, capsys):
        """GIVEN instrumentor not installed WHEN _enable_openinference_instrumentors() THEN skip gracefully."""
        mock_provider = Mock()

        # Force ImportError by removing the module and making __import__ fail
        import sys
        original_modules = dict(sys.modules)

        # Remove any openinference modules
        for key in list(sys.modules.keys()):
            if "openinference" in key:
                del sys.modules[key]

        def fake_import(name, *args, **kwargs):
            if "openinference" in name:
                raise ImportError(f"No module named '{name}'")
            return original_modules.get(name) or __builtins__.__import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            from llmops.configure import _enable_openinference_instrumentors
            # Should not raise
            _enable_openinference_instrumentors(mock_provider)

        captured = capsys.readouterr()
        assert "not available" in captured.out


# =============================================================================
# MLFLOW BACKEND TESTS - OTLP-based tracing per MLflow ADK docs
# =============================================================================

class TestMlflowBackend:
    """Tests for MLflow backend configuration.

    Per MLflow ADK docs (https://mlflow.org/docs/latest/genai/tracing/integrations/listing/google-adk/):
    - TracerProvider is set globally (for ADK tracing via OTLP)
    - OTLP exporter configured to MLflow's /v1/traces endpoint
    - x-mlflow-experiment-id header set on OTLP exporter
    - mlflow.set_tracking_uri() called with endpoint
    - mlflow.set_experiment() called with service_name

    Note: mlflow.autolog() and mlflow.tracing.enable() are NOT used for ADK tracing.
    """

    def test_mlflow_sets_tracking_uri(self):
        """GIVEN mlflow backend WHEN configure() THEN set tracking URI."""
        mlflow = pytest.importorskip("mlflow")

        with patch.object(mlflow, "set_tracking_uri") as mock_set_uri:
            with patch.object(mlflow, "set_experiment"):
                llmops.configure(
                    backend="mlflow",
                    endpoint="http://localhost:5001",
                    service_name="test",
                )
                mock_set_uri.assert_called_once_with("http://localhost:5001")

    def test_mlflow_sets_experiment(self):
        """GIVEN mlflow backend WHEN configure() THEN set experiment to service_name."""
        mlflow = pytest.importorskip("mlflow")

        with patch.object(mlflow, "set_tracking_uri"):
            with patch.object(mlflow, "set_experiment") as mock_set_exp:
                llmops.configure(
                    backend="mlflow",
                    endpoint="http://localhost:5001",
                    service_name="my-experiment",
                )
                mock_set_exp.assert_called_once_with("my-experiment")

    def test_mlflow_sets_tracer_provider_for_adk(self):
        """GIVEN mlflow backend WHEN configure() THEN set TracerProvider for ADK tracing.

        Per MLflow ADK docs: OTLP exporter sends ADK traces to /v1/traces endpoint.
        """
        mlflow = pytest.importorskip("mlflow")
        from opentelemetry import trace

        with patch.object(mlflow, "set_tracking_uri"):
            with patch.object(mlflow, "set_experiment"):
                llmops.configure(
                    backend="mlflow",
                    endpoint="http://localhost:5001",
                    service_name="test",
                )

                # TracerProvider should be set (not NoOpTracerProvider)
                provider = trace.get_tracer_provider()
                assert type(provider).__name__ == "TracerProvider"

    def test_mlflow_otlp_endpoint_includes_traces_path(self):
        """GIVEN mlflow backend WHEN configure() THEN OTLP endpoint is /v1/traces."""
        mlflow = pytest.importorskip("mlflow")

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter") as mock_exporter:
            with patch.object(mlflow, "set_tracking_uri"):
                with patch.object(mlflow, "set_experiment"):
                    with patch("opentelemetry.trace.set_tracer_provider"):
                        llmops.configure(
                            backend="mlflow",
                            endpoint="http://localhost:5001",
                            service_name="test",
                        )

                        # OTLP exporter should be called with /v1/traces endpoint
                        mock_exporter.assert_called_once()
                        call_kwargs = mock_exporter.call_args.kwargs
                        endpoint = call_kwargs.get("endpoint", "")
                        assert "/v1/traces" in endpoint

    def test_mlflow_otlp_has_experiment_id_header(self):
        """GIVEN mlflow backend WHEN configure() THEN OTLP has experiment ID header."""
        mlflow = pytest.importorskip("mlflow")

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter") as mock_exporter:
            with patch.object(mlflow, "set_tracking_uri"):
                with patch.object(mlflow, "set_experiment"):
                    with patch("opentelemetry.trace.set_tracer_provider"):
                        llmops.configure(
                            backend="mlflow",
                            endpoint="http://localhost:5001",
                            service_name="test",
                        )

                        call_kwargs = mock_exporter.call_args.kwargs
                        headers = call_kwargs.get("headers", {})
                        assert "x-mlflow-experiment-id" in headers

    def test_mlflow_console_adds_console_exporter(self, capsys):
        """GIVEN mlflow backend with console=True WHEN configure() THEN add ConsoleSpanExporter."""
        mlflow = pytest.importorskip("mlflow")

        with patch.object(mlflow, "set_tracking_uri"):
            with patch.object(mlflow, "set_experiment"):
                llmops.configure(
                    backend="mlflow",
                    endpoint="http://localhost:5001",
                    service_name="test",
                    console=True,
                )

                captured = capsys.readouterr()
                assert "Console exporter enabled" in captured.out

    def test_mlflow_raises_if_not_installed(self):
        """GIVEN mlflow not installed WHEN configure() THEN raise ImportError."""
        import sys

        # Temporarily remove mlflow from sys.modules
        mlflow_modules = {k: v for k, v in sys.modules.items() if "mlflow" in k}
        for key in mlflow_modules:
            del sys.modules[key]

        try:
            with patch.dict("sys.modules", {"mlflow": None}):
                # Force re-import to trigger ImportError
                def raise_import(*args, **kwargs):
                    if args[0] == "mlflow" or "mlflow" in str(args):
                        raise ImportError("No module named 'mlflow'")
                    return __builtins__.__dict__["__import__"](*args, **kwargs)

                with patch("builtins.__import__", side_effect=raise_import):
                    with pytest.raises(ImportError, match="mlflow is required"):
                        llmops.configure(
                            backend="mlflow",
                            endpoint="http://localhost:5001",
                            service_name="test",
                        )
        finally:
            # Restore mlflow modules
            sys.modules.update(mlflow_modules)


# =============================================================================
# SHUTDOWN TESTS
# =============================================================================

class TestShutdown:
    """Tests for shutdown behavior."""

    def test_phoenix_shutdown_flushes_and_shuts_down_provider(self):
        """GIVEN phoenix configured WHEN shutdown() THEN flush and shutdown provider."""
        from importlib import import_module
        configure_module = import_module("llmops.configure")

        # Create a mock provider
        mock_provider = Mock()

        with patch.object(configure_module, "_enable_openinference_instrumentors"):
            with patch("opentelemetry.sdk.trace.TracerProvider", return_value=mock_provider):
                llmops.configure(
                    backend="phoenix",
                    endpoint="http://localhost:6006/v1/traces",
                    service_name="test",
                )

        llmops.shutdown()
        mock_provider.force_flush.assert_called_once()
        mock_provider.shutdown.assert_called_once()

    def test_mlflow_shutdown_flushes_and_shuts_down_provider(self):
        """GIVEN mlflow configured WHEN shutdown() THEN flush and shutdown provider.

        Note: Per MLflow ADK docs, we use OTLP-based tracing, so shutdown
        only needs to flush and shutdown the TracerProvider.
        """
        mlflow = pytest.importorskip("mlflow")

        mock_provider = Mock()

        with patch.object(mlflow, "set_tracking_uri"):
            with patch.object(mlflow, "set_experiment"):
                with patch("opentelemetry.sdk.trace.TracerProvider", return_value=mock_provider):
                    llmops.configure(
                        backend="mlflow",
                        endpoint="http://localhost:5001",
                        service_name="test",
                    )

        llmops.shutdown()
        mock_provider.force_flush.assert_called_once()
        mock_provider.shutdown.assert_called_once()


# =============================================================================
# INIT() AUTO-INSTRUMENTATION TESTS
# =============================================================================

class TestInit:
    """Tests for init() auto-instrumentation entry point.

    init() is the recommended quick-start API that:
    1. Loads configuration from YAML file
    2. Initializes OpenTelemetry TracerProvider
    3. Sets up backend-specific exporter
    4. Enables auto-instrumentation for all supported libraries

    Invariants:
    - Defaults to ./llmops.yaml if no config_path provided
    - Backend can be overridden via parameter
    - backend_kwargs override YAML values
    - Sets is_configured() to True on success
    - Raises ConfigurationError for invalid config
    """

    def test_init_exists_in_module(self):
        """GIVEN llmops module WHEN accessed THEN init function exists."""
        assert hasattr(llmops, "init")
        assert callable(llmops.init)

    def test_init_configures_sdk(self, tmp_path):
        """GIVEN valid YAML config WHEN init() THEN SDK is configured."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces
""")
        llmops.init(config_path=str(config_file))
        assert llmops.is_configured()
        assert llmops.get_backend() == "phoenix"

    def test_init_backend_override(self, tmp_path):
        """GIVEN YAML with phoenix WHEN init(backend='mlflow') THEN use mlflow."""
        mlflow = pytest.importorskip("mlflow")

        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces

mlflow:
  tracking_uri: http://localhost:5001
""")
        with patch.object(mlflow, "set_tracking_uri"):
            with patch.object(mlflow, "set_experiment"):
                llmops.init(config_path=str(config_file), backend="mlflow")

        assert llmops.get_backend() == "mlflow"

    def test_init_endpoint_override_via_kwargs(self, tmp_path):
        """GIVEN YAML config WHEN init(endpoint=...) THEN override endpoint."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: phoenix

phoenix:
  endpoint: http://yaml-endpoint:6006/v1/traces
""")
        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter") as mock_exporter:
            with patch("opentelemetry.sdk.trace.export.BatchSpanProcessor"):
                llmops.init(
                    config_path=str(config_file),
                    endpoint="http://override-endpoint:6006/v1/traces"
                )

        # Verify the override endpoint was used
        mock_exporter.assert_called_once()
        call_kwargs = mock_exporter.call_args.kwargs
        assert call_kwargs.get("endpoint") == "http://override-endpoint:6006/v1/traces"

    def test_init_service_name_from_yaml(self, tmp_path):
        """GIVEN YAML with service.name WHEN init() THEN use service name."""
        from opentelemetry.sdk.resources import SERVICE_NAME

        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: my-awesome-service

backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces
""")
        captured_attrs = {}

        def capture_create(attrs):
            nonlocal captured_attrs
            captured_attrs = dict(attrs)
            from opentelemetry.sdk.resources import Resource
            return Resource(attrs)

        with patch("opentelemetry.sdk.resources.Resource.create", side_effect=capture_create):
            llmops.init(config_path=str(config_file))

        assert captured_attrs.get(SERVICE_NAME) == "my-awesome-service"

    def test_init_raises_without_backend(self, tmp_path):
        """GIVEN YAML without backend WHEN init() THEN raise ConfigurationError."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service
# No backend specified!
""")
        with pytest.raises(ConfigurationError, match="backend"):
            llmops.init(config_path=str(config_file))

    def test_init_raises_without_service_name(self, tmp_path):
        """GIVEN YAML without service.name WHEN init() THEN raise ConfigurationError."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces
# No service.name!
""")
        with pytest.raises(ConfigurationError, match="service"):
            llmops.init(config_path=str(config_file))

    def test_init_raises_on_missing_config_file(self):
        """GIVEN non-existent config file WHEN init() THEN raise ConfigurationError."""
        with pytest.raises(ConfigurationError, match="not found|does not exist"):
            llmops.init(config_path="/nonexistent/path/llmops.yaml")

    def test_init_raises_on_invalid_yaml(self, tmp_path):
        """GIVEN malformed YAML WHEN init() THEN raise ConfigurationError."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
this is not: valid: yaml: syntax
  - broken
    indentation
""")
        with pytest.raises(ConfigurationError, match="YAML|parse|invalid"):
            llmops.init(config_path=str(config_file))

    def test_init_already_configured_raises(self, tmp_path):
        """GIVEN already configured WHEN init() again THEN raise ConfigurationError."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces
""")
        llmops.init(config_path=str(config_file))
        with pytest.raises(ConfigurationError, match="already configured"):
            llmops.init(config_path=str(config_file))


class TestInitEnvironmentVariables:
    """Tests for environment variable support in init().

    Environment variables override YAML config values.
    Format: LLMOPS_<SECTION>_<KEY> (e.g., LLMOPS_PHOENIX_ENDPOINT)
    """

    def test_init_env_var_backend_override(self, tmp_path, monkeypatch):
        """GIVEN LLMOPS_BACKEND env var WHEN init() THEN override YAML backend."""
        mlflow = pytest.importorskip("mlflow")

        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces

mlflow:
  tracking_uri: http://localhost:5001
""")
        monkeypatch.setenv("LLMOPS_BACKEND", "mlflow")

        with patch.object(mlflow, "set_tracking_uri"):
            with patch.object(mlflow, "set_experiment"):
                llmops.init(config_path=str(config_file))

        assert llmops.get_backend() == "mlflow"

    def test_init_env_var_phoenix_endpoint_override(self, tmp_path, monkeypatch):
        """GIVEN LLMOPS_PHOENIX_ENDPOINT env var WHEN init() THEN override YAML endpoint."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: phoenix

phoenix:
  endpoint: http://yaml-endpoint:6006/v1/traces
""")
        monkeypatch.setenv("LLMOPS_PHOENIX_ENDPOINT", "http://env-endpoint:6006/v1/traces")

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter") as mock_exporter:
            with patch("opentelemetry.sdk.trace.export.BatchSpanProcessor"):
                llmops.init(config_path=str(config_file))

        mock_exporter.assert_called_once()
        call_kwargs = mock_exporter.call_args.kwargs
        assert call_kwargs.get("endpoint") == "http://env-endpoint:6006/v1/traces"

    def test_init_env_var_service_name_override(self, tmp_path, monkeypatch):
        """GIVEN LLMOPS_SERVICE_NAME env var WHEN init() THEN override YAML service name."""
        from opentelemetry.sdk.resources import SERVICE_NAME

        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: yaml-service-name

backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces
""")
        monkeypatch.setenv("LLMOPS_SERVICE_NAME", "env-service-name")

        captured_attrs = {}

        def capture_create(attrs):
            nonlocal captured_attrs
            captured_attrs = dict(attrs)
            from opentelemetry.sdk.resources import Resource
            return Resource(attrs)

        with patch("opentelemetry.sdk.resources.Resource.create", side_effect=capture_create):
            llmops.init(config_path=str(config_file))

        assert captured_attrs.get(SERVICE_NAME) == "env-service-name"

    def test_init_kwarg_overrides_env_var(self, tmp_path, monkeypatch):
        """GIVEN both env var and kwarg WHEN init() THEN kwarg wins."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: phoenix

phoenix:
  endpoint: http://yaml-endpoint:6006/v1/traces
""")
        monkeypatch.setenv("LLMOPS_PHOENIX_ENDPOINT", "http://env-endpoint:6006/v1/traces")

        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter") as mock_exporter:
            with patch("opentelemetry.sdk.trace.export.BatchSpanProcessor"):
                llmops.init(
                    config_path=str(config_file),
                    endpoint="http://kwarg-endpoint:6006/v1/traces"
                )

        # Kwarg should win over env var
        mock_exporter.assert_called_once()
        call_kwargs = mock_exporter.call_args.kwargs
        assert call_kwargs.get("endpoint") == "http://kwarg-endpoint:6006/v1/traces"


class TestInitMlflow:
    """Tests for init() with MLflow backend."""

    def test_init_mlflow_from_yaml(self, tmp_path):
        """GIVEN YAML with mlflow backend WHEN init() THEN configure MLflow."""
        mlflow = pytest.importorskip("mlflow")

        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: mlflow

mlflow:
  tracking_uri: http://localhost:5001
  experiment_name: my-experiment
""")
        with patch.object(mlflow, "set_tracking_uri") as mock_set_uri:
            with patch.object(mlflow, "set_experiment"):
                llmops.init(config_path=str(config_file))

        mock_set_uri.assert_called_once_with("http://localhost:5001")
        assert llmops.get_backend() == "mlflow"

    def test_init_mlflow_uses_service_name_as_experiment(self, tmp_path):
        """GIVEN YAML without experiment_name WHEN init() THEN use service.name."""
        mlflow = pytest.importorskip("mlflow")

        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: my-service-name

backend: mlflow

mlflow:
  tracking_uri: http://localhost:5001
  # No experiment_name - should use service.name
""")
        with patch.object(mlflow, "set_tracking_uri"):
            with patch.object(mlflow, "set_experiment") as mock_set_exp:
                llmops.init(config_path=str(config_file))

        mock_set_exp.assert_called_once_with("my-service-name")


class TestInitAutoInstrument:
    """Tests for auto_instrument parameter in init()."""

    def test_init_auto_instrument_default_true(self, tmp_path):
        """GIVEN init() without auto_instrument WHEN called THEN auto-instrumentation enabled."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces
""")
        from importlib import import_module
        configure_module = import_module("llmops.configure")

        with patch.object(configure_module, "_enable_openinference_instrumentors") as mock_enable:
            llmops.init(config_path=str(config_file))
            mock_enable.assert_called_once()

    def test_init_auto_instrument_false_skips_instrumentors(self, tmp_path):
        """GIVEN init(auto_instrument=False) WHEN called THEN skip auto-instrumentation."""
        config_file = tmp_path / "llmops.yaml"
        config_file.write_text("""
service:
  name: test-service

backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces
""")
        from importlib import import_module
        configure_module = import_module("llmops.configure")

        with patch.object(configure_module, "_enable_openinference_instrumentors") as mock_enable:
            llmops.init(config_path=str(config_file), auto_instrument=False)
            mock_enable.assert_not_called()
