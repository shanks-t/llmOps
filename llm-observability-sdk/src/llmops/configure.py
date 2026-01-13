"""Main configuration entry point."""

from __future__ import annotations

from typing import Literal, TypedDict


class BackendConfig(TypedDict, total=False):
    """Configuration for a single backend."""
    type: Literal["phoenix", "mlflow"]
    endpoint: str


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


# Global state
_tracer_provider = None
_configured = False


# =============================================================================
# Helper functions (defined first to ensure availability)
# =============================================================================

def _get_mlflow_experiment_id(tracking_uri: str, experiment_name: str) -> str:
    """Get or create MLflow experiment and return its ID."""
    try:
        import mlflow
        mlflow.set_tracking_uri(tracking_uri)
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment:
            return experiment.experiment_id
        else:
            return mlflow.create_experiment(experiment_name)
    except Exception as e:
        print(f"llmops: Warning - could not get MLflow experiment ID: {e}")
        return "0"  # Default experiment


def _setup_tracer_provider(otlp_configs: list[dict], service_name: str):
    """Setup TracerProvider with OTLP exporters for all endpoints."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    # Add an exporter for each endpoint config
    for config in otlp_configs:
        exporter = OTLPSpanExporter(
            endpoint=config["endpoint"],
            headers=config.get("headers", {}),
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    return provider


def _enable_instrumentors(provider) -> None:
    """Enable all available instrumentors."""
    # OpenInference instrumentors
    _try_instrument("openinference.instrumentation.google_adk", "GoogleADKInstrumentor", provider)
    _try_instrument("openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor", provider)

    # OpenTelemetry instrumentors
    _try_instrument_otel("opentelemetry.instrumentation.fastapi", "FastAPIInstrumentor")


def _try_instrument(module_path: str, class_name: str, provider) -> None:
    """Try to enable an OpenInference instrumentor."""
    try:
        module = __import__(module_path, fromlist=[class_name])
        instrumentor_class = getattr(module, class_name)
        instrumentor = instrumentor_class()
        instrumentor.instrument(tracer_provider=provider)
        print(f"llmops: Enabled {class_name}")
    except ImportError:
        print(f"llmops: {class_name} not installed, skipping")
    except Exception as e:
        print(f"llmops: Failed to enable {class_name}: {e}")


def _try_instrument_otel(module_path: str, class_name: str) -> None:
    """Try to enable an OpenTelemetry instrumentor."""
    try:
        module = __import__(module_path, fromlist=[class_name])
        instrumentor_class = getattr(module, class_name)
        instrumentor = instrumentor_class()
        instrumentor.instrument()
        print(f"llmops: Enabled {class_name}")
    except ImportError:
        print(f"llmops: {class_name} not installed, skipping")
    except Exception as e:
        print(f"llmops: Failed to enable {class_name}: {e}")


# =============================================================================
# Public API
# =============================================================================

def configure(
    *,
    backend: Literal["phoenix", "mlflow"] | None = None,
    backends: list[BackendConfig] | None = None,
    endpoint: str | None = None,
    service_name: str = "llmops-app",
) -> None:
    """
    Configure and enable auto-instrumentation.

    Supports single backend (legacy) or multiple backends.

    Args:
        backend: Single backend type ("phoenix" or "mlflow") - legacy API
        backends: List of backend configurations for multi-backend setup
        endpoint: Backend endpoint URL (used with single backend)
        service_name: Service name for traces

    Raises:
        ConfigurationError: If configuration is invalid

    Examples:
        # Single backend (legacy)
        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="my-agent",
        )

        # Multiple backends
        llmops.configure(
            backends=[
                {"type": "phoenix", "endpoint": "http://localhost:6006/v1/traces"},
                {"type": "mlflow", "endpoint": "http://localhost:5001"},
            ],
            service_name="my-agent",
        )
    """
    global _tracer_provider, _configured

    # Build list of backends to configure
    backend_list: list[BackendConfig] = []

    if backends:
        # Multi-backend API
        backend_list = backends
    elif backend and endpoint:
        # Legacy single-backend API
        backend_list = [{"type": backend, "endpoint": endpoint}]
    else:
        raise ConfigurationError(
            "Must provide either 'backends' list or both 'backend' and 'endpoint'"
        )

    # Validate backends
    for config in backend_list:
        backend_type = config.get("type")
        backend_endpoint = config.get("endpoint")

        if not backend_type:
            raise ConfigurationError("Each backend must have a 'type'")
        if not backend_endpoint:
            raise ConfigurationError(f"Backend '{backend_type}' requires an 'endpoint'")
        if backend_type not in ("phoenix", "mlflow"):
            raise ConfigurationError(
                f"Unknown backend: {backend_type}. Use 'phoenix' or 'mlflow'."
            )

    # Collect OTLP endpoint configs
    otlp_configs = []
    for config in backend_list:
        backend_type = config.get("type")
        backend_endpoint = config.get("endpoint")

        if backend_type == "phoenix":
            # Phoenix uses the endpoint directly for OTLP
            otlp_configs.append({
                "endpoint": backend_endpoint,
                "headers": {},
            })
            print(f"llmops: Adding Phoenix OTLP endpoint: {backend_endpoint}")
        elif backend_type == "mlflow":
            # MLflow OTLP endpoint requires experiment ID header
            mlflow_otlp = backend_endpoint.rstrip("/") + "/v1/traces"
            # Get or create experiment to get ID
            experiment_id = _get_mlflow_experiment_id(backend_endpoint, service_name)
            otlp_configs.append({
                "endpoint": mlflow_otlp,
                "headers": {"x-mlflow-experiment-id": experiment_id},
            })
            print(f"llmops: Adding MLflow OTLP endpoint: {mlflow_otlp} (experiment: {experiment_id})")

    # Setup TracerProvider with all OTLP exporters
    _tracer_provider = _setup_tracer_provider(otlp_configs, service_name)

    # Enable instrumentors
    _enable_instrumentors(_tracer_provider)

    _configured = True
    print(f"llmops: Configuration complete with {len(backend_list)} backend(s)")


def shutdown(timeout_ms: int = 5000) -> None:
    """
    Flush pending spans and shutdown all backends.

    Call this before application exit to ensure all telemetry is exported.

    Args:
        timeout_ms: Maximum time to wait for flush (default: 5000ms)
    """
    global _tracer_provider, _configured

    if _tracer_provider is not None:
        _tracer_provider.force_flush(timeout_millis=timeout_ms)
        _tracer_provider.shutdown()
        _tracer_provider = None

    _configured = False
    print("llmops: Shutdown complete")
