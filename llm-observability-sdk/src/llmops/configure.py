"""Main configuration entry point"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Sequence

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.sdk.trace.export import SpanExportResult

import yaml
from opentelemetry.sdk.trace.export import SpanExporter


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


# Global state
_tracer_provider = None
_configured = False
_backend_type = None


# =============================================================================
# Configuration Loading
# =============================================================================

def _load_yaml_config(config_path: str | Path) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        ConfigurationError: If file doesn't exist or YAML is invalid.
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    try:
        with open(path) as f:
            config = yaml.safe_load(f)
            return config if config else {}
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}")


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to configuration.

    Environment variables follow the pattern LLMOPS_<SECTION>_<KEY>.
    For example:
    - LLMOPS_BACKEND -> config['backend']
    - LLMOPS_SERVICE_NAME -> config['service']['name']
    - LLMOPS_PHOENIX_ENDPOINT -> config['phoenix']['endpoint']

    Args:
        config: Base configuration dictionary.

    Returns:
        Configuration with environment overrides applied.
    """
    # Simple top-level overrides
    if backend := os.environ.get("LLMOPS_BACKEND"):
        config["backend"] = backend

    if service_name := os.environ.get("LLMOPS_SERVICE_NAME"):
        if "service" not in config:
            config["service"] = {}
        config["service"]["name"] = service_name

    # Phoenix overrides
    if phoenix_endpoint := os.environ.get("LLMOPS_PHOENIX_ENDPOINT"):
        if "phoenix" not in config:
            config["phoenix"] = {}
        config["phoenix"]["endpoint"] = phoenix_endpoint

    # MLflow overrides
    if mlflow_uri := os.environ.get("LLMOPS_MLFLOW_TRACKING_URI"):
        if "mlflow" not in config:
            config["mlflow"] = {}
        config["mlflow"]["tracking_uri"] = mlflow_uri

    return config


def _validate_config(config: dict[str, Any]) -> None:
    """Validate required configuration values.

    Args:
        config: Configuration dictionary to validate.

    Raises:
        ConfigurationError: If required values are missing.
    """
    # Check for service name
    service_name = config.get("service", {}).get("name")
    if not service_name:
        raise ConfigurationError(
            "service.name is required in configuration. "
            "Add 'service: name: my-service' to your llmops.yaml"
        )

    # Check for backend
    backend = config.get("backend")
    if not backend:
        raise ConfigurationError(
            "backend is required in configuration. "
            "Add 'backend: phoenix' or 'backend: mlflow' to your llmops.yaml"
        )

    if backend not in ("phoenix", "mlflow"):
        raise ConfigurationError(
            f"Unknown backend: {backend}. Use 'phoenix' or 'mlflow'."
        )


# =============================================================================
# Phoenix Backend (OpenInference)
# =============================================================================

def _setup_phoenix(
    endpoint: str,
    service_name: str,
    console: bool = False,
    auto_instrument: bool = True,
):
    """Setup Phoenix with OpenInference instrumentation."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    # Add console exporter if requested
    if console:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        print("llmops: Console exporter enabled")

    # Add OTLP exporter for Phoenix
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    print(f"llmops: Phoenix endpoint: {endpoint}")

    trace.set_tracer_provider(provider)

    # Enable OpenInference instrumentors (if auto_instrument is True)
    if auto_instrument:
        _enable_openinference_instrumentors(provider)

    return provider


def _enable_openinference_instrumentors(provider) -> None:
    """Enable OpenInference instrumentors for LLM frameworks."""
    instrumentors = [
        ("openinference.instrumentation.google_adk", "GoogleADKInstrumentor"),
        ("openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor"),
    ]

    for module_path, class_name in instrumentors:
        try:
            module = __import__(module_path, fromlist=[class_name])
            instrumentor_class = getattr(module, class_name)
            instrumentor = instrumentor_class()
            instrumentor.instrument(tracer_provider=provider)
            print(f"llmops: Enabled {class_name}")
        except ImportError:
            print(f"llmops: {class_name} not available, skipping")
        except Exception as e:
            print(f"llmops: Failed to enable {class_name}: {e}")


# =============================================================================
# MLflow Backend (OTLP-based tracing for Google ADK)
# =============================================================================


class RootSpanEnrichingExporter(SpanExporter):
    """SpanExporter wrapper that enriches root spans with child span inputs/outputs.

    MLflow's Traces UI shows Request/Response columns from the root span's
    mlflow.spanInputs and mlflow.spanOutputs attributes. Google ADK traces
    only set these on leaf spans (call_llm), leaving root spans empty.

    This exporter buffers spans by trace_id and propagates the first
    mlflow.spanInputs/spanOutputs found in children to the root span
    before forwarding to the underlying exporter.

    Implements the SpanExporter protocol for compatibility with SpanProcessors.
    """

    def __init__(
        self, wrapped_exporter: SpanExporter, timeout_seconds: float = 30.0
    ) -> None:
        """Initialize the enriching exporter.

        Args:
            wrapped_exporter: The underlying SpanExporter to forward spans to.
            timeout_seconds: Max time to buffer spans before force-exporting.
        """
        import threading
        import time

        self._wrapped = wrapped_exporter
        self._timeout = timeout_seconds
        self._lock = threading.Lock()
        # trace_id -> {"spans": [...], "timestamp": float}
        self._buffer: dict[str, dict[str, Any]] = {}
        self._time = time

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Buffer spans and export complete traces with enriched root spans."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        for span in spans:
            trace_id = format(span.context.trace_id, "032x")

            with self._lock:
                if trace_id not in self._buffer:
                    self._buffer[trace_id] = {
                        "spans": [],
                        "timestamp": self._time.time(),
                    }
                self._buffer[trace_id]["spans"].append(span)

                # Check if this is the root span (no parent)
                if span.parent is None:
                    # Root span arrived - enrich and export entire trace
                    trace_data = self._buffer.pop(trace_id)
                    self._export_enriched_trace(trace_data["spans"])

        # Clean up stale traces (timeout protection)
        self._cleanup_stale_traces()

        return SpanExportResult.SUCCESS

    def _export_enriched_trace(self, spans: list) -> None:
        """Enrich root span with child inputs/outputs and export."""
        # Find root span and collect inputs/outputs from children
        # Google ADK uses gcp.vertex.agent.llm_request/llm_response
        # MLflow transforms these to mlflow.spanInputs/spanOutputs on ingestion
        # We need to look for the source attributes and add the mlflow ones
        root_span = None
        first_inputs = None
        first_outputs = None

        # Attribute names to check (in priority order)
        input_attrs = ["mlflow.spanInputs", "gcp.vertex.agent.llm_request"]
        output_attrs = ["mlflow.spanOutputs", "gcp.vertex.agent.llm_response"]

        for span in spans:
            if span.parent is None:
                root_span = span
            else:
                attrs = span.attributes or {}
                # Find first available input attribute
                if first_inputs is None:
                    for attr_name in input_attrs:
                        if attr_name in attrs:
                            first_inputs = attrs[attr_name]
                            break
                # Find first available output attribute
                if first_outputs is None:
                    for attr_name in output_attrs:
                        if attr_name in attrs:
                            first_outputs = attrs[attr_name]
                            break

        # Enrich root span if we found inputs/outputs
        if root_span is not None and (first_inputs or first_outputs):
            # ReadableSpan attributes are immutable, so we create enriched copy
            enriched_spans = []
            for span in spans:
                if span.parent is None:
                    # Create enriched root span
                    enriched_span = self._enrich_span(
                        span, first_inputs, first_outputs
                    )
                    enriched_spans.append(enriched_span)
                else:
                    enriched_spans.append(span)
            self._wrapped.export(enriched_spans)
        else:
            # No enrichment needed
            self._wrapped.export(spans)

    def _enrich_span(self, span, inputs: str | None, outputs: str | None):
        """Create a copy of span with added mlflow attributes."""
        # Build new attributes dict
        new_attrs = dict(span.attributes) if span.attributes else {}
        if inputs and "mlflow.spanInputs" not in new_attrs:
            new_attrs["mlflow.spanInputs"] = inputs
        if outputs and "mlflow.spanOutputs" not in new_attrs:
            new_attrs["mlflow.spanOutputs"] = outputs

        # Create new ReadableSpan with enriched attributes
        # We use the internal _ReadableSpan constructor approach
        enriched = _EnrichedReadableSpan(span, new_attrs)
        return enriched

    def _cleanup_stale_traces(self) -> None:
        """Remove traces that have been buffered too long."""
        now = self._time.time()
        stale_traces = []

        with self._lock:
            for trace_id, data in self._buffer.items():
                if now - data["timestamp"] > self._timeout:
                    stale_traces.append(trace_id)

            for trace_id in stale_traces:
                trace_data = self._buffer.pop(trace_id)
                # Export without enrichment (root span never arrived)
                self._wrapped.export(trace_data["spans"])

    def shutdown(self) -> None:
        """Flush remaining spans and shutdown."""
        with self._lock:
            for trace_data in self._buffer.values():
                self._wrapped.export(trace_data["spans"])
            self._buffer.clear()
        self._wrapped.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush all buffered spans."""
        with self._lock:
            for trace_data in self._buffer.values():
                self._wrapped.export(trace_data["spans"])
            self._buffer.clear()
        result = self._wrapped.force_flush(timeout_millis)
        return bool(result)


class _EnrichedReadableSpan:
    """Wrapper that presents a ReadableSpan with modified attributes.

    OpenTelemetry's ReadableSpan is immutable, so we wrap it to override
    the attributes property while delegating everything else.
    """

    def __init__(self, original_span, new_attributes: dict):
        self._original = original_span
        self._attributes = new_attributes

    @property
    def attributes(self):
        return self._attributes

    @property
    def name(self):
        return self._original.name

    @property
    def context(self):
        return self._original.context

    @property
    def parent(self):
        return self._original.parent

    @property
    def start_time(self):
        return self._original.start_time

    @property
    def end_time(self):
        return self._original.end_time

    @property
    def status(self):
        return self._original.status

    @property
    def kind(self):
        return self._original.kind

    @property
    def events(self):
        return self._original.events

    @property
    def links(self):
        return self._original.links

    @property
    def resource(self):
        return self._original.resource

    @property
    def instrumentation_scope(self):
        return self._original.instrumentation_scope

    @property
    def dropped_attributes(self):
        return self._original.dropped_attributes

    @property
    def dropped_events(self):
        return self._original.dropped_events

    @property
    def dropped_links(self):
        return self._original.dropped_links

    def get_span_context(self):
        return self._original.get_span_context()

    def to_json(self, indent=4):
        return self._original.to_json(indent)


def _setup_mlflow(endpoint: str, service_name: str, console: bool = False):
    """Setup MLflow with OTLP for Google ADK tracing.

    Per MLflow docs (https://mlflow.org/docs/latest/genai/tracing/integrations/listing/google-adk/):
    - Initialize OpenTelemetry TracerProvider with OTLP exporter
    - OTLP exporter sends traces to MLflow's /v1/traces endpoint
    - Requires x-mlflow-experiment-id header for trace association
    - Google ADK generates traces natively once TracerProvider is set

    Note: No instrumentors needed - ADK has native OpenTelemetry tracing.
    """
    try:
        import mlflow
    except ImportError:
        raise ImportError(
            "mlflow is required for MLflow backend. "
            "Install with: pip install llmops[mlflow]"
        )

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource

    # Set tracking URI
    mlflow.set_tracking_uri(endpoint)
    print(f"llmops: MLflow tracking URI: {endpoint}")

    # Set experiment (creates if doesn't exist) and get experiment ID
    experiment = mlflow.set_experiment(service_name)
    experiment_id = experiment.experiment_id
    print(f"llmops: MLflow experiment: {service_name} (id: {experiment_id})")

    # Setup OTLP exporter for ADK tracing to MLflow
    # MLflow 3.6.0+ supports OTLP ingestion at /v1/traces
    otlp_endpoint = f"{endpoint.rstrip('/')}/v1/traces"
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    # Console exporter first (to see if spans are being created)
    if console:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        print("llmops: Console exporter enabled")

    # OTLP exporter to MLflow, wrapped to enrich root spans
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        headers={"x-mlflow-experiment-id": experiment_id},
    )
    enriching_exporter = RootSpanEnrichingExporter(otlp_exporter)
    provider.add_span_processor(SimpleSpanProcessor(enriching_exporter))
    print(f"llmops: OTLP endpoint for ADK tracing: {otlp_endpoint}")
    print("llmops: Root span enrichment enabled for MLflow UI")

    trace.set_tracer_provider(provider)

    return provider


# =============================================================================
# Public API
# =============================================================================

def configure(
    *,
    backend: Literal["phoenix", "mlflow"],
    endpoint: str,
    service_name: str = "llmops-app",
    console: bool = False,
) -> None:
    """
    Configure auto-instrumentation for a single backend.

    Each backend uses its native instrumentation:
    - Phoenix: OpenInference semantic conventions
    - MLflow: MLflow native autolog

    Args:
        backend: Backend type - "phoenix" or "mlflow"
        endpoint: Backend endpoint URL
        service_name: Service/experiment name for traces
        console: If True, also print traces to console for debugging

    Raises:
        ConfigurationError: If configuration is invalid

    Examples:
        # Phoenix (OpenInference)
        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="my-agent",
        )

        # MLflow (native autolog)
        llmops.configure(
            backend="mlflow",
            endpoint="http://localhost:5001",
            service_name="my-agent",
        )

        # With console output for debugging
        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            console=True,
        )
    """
    global _tracer_provider, _configured, _backend_type

    if _configured:
        raise ConfigurationError(
            "llmops is already configured. Call shutdown() first to reconfigure."
        )

    if backend not in ("phoenix", "mlflow"):
        raise ConfigurationError(
            f"Unknown backend: {backend}. Use 'phoenix' or 'mlflow'."
        )

    if not endpoint:
        raise ConfigurationError("endpoint is required")

    # Setup the appropriate backend
    if backend == "phoenix":
        _tracer_provider = _setup_phoenix(endpoint, service_name, console)
    elif backend == "mlflow":
        _tracer_provider = _setup_mlflow(endpoint, service_name, console)

    _backend_type = backend
    _configured = True
    print(f"llmops: Configuration complete ({backend})")


def shutdown(timeout_ms: int = 5000) -> None:
    """
    Flush pending traces and shutdown.

    Call this before application exit to ensure all telemetry is exported.

    Args:
        timeout_ms: Maximum time to wait for flush (default: 5000ms)
    """
    global _tracer_provider, _configured, _backend_type

    # Flush and shutdown TracerProvider (used by both Phoenix and MLflow)
    if _tracer_provider is not None:
        _tracer_provider.force_flush(timeout_millis=timeout_ms)
        _tracer_provider.shutdown()
        _tracer_provider = None

    _configured = False
    _backend_type = None
    print("llmops: Shutdown complete")


def get_backend() -> str | None:
    """Return the currently configured backend type."""
    return _backend_type


def is_configured() -> bool:
    """Return True if llmops is configured."""
    return _configured


def init(
    config_path: str | Path | None = None,
    *,
    backend: Literal["phoenix", "mlflow"] | None = None,
    auto_instrument: bool = True,
    capture_content: bool | None = None,
    **backend_kwargs,
) -> None:
    """
    Initialize the SDK with auto-instrumentation.

    This single call:
    1. Loads configuration from YAML file
    2. Initializes OpenTelemetry TracerProvider
    3. Sets up backend-specific exporter
    4. Enables auto-instrumentation for all supported libraries

    Args:
        config_path: Path to YAML config file.
                     Defaults to ./llmops.yaml in current directory.
        backend: Override backend from config ("phoenix" or "mlflow").
        auto_instrument: Enable auto-instrumentation (default True).
                        Set to False for manual-only instrumentation.
        capture_content: Override content capture setting.
        **backend_kwargs: Backend-specific configuration overrides
                         (e.g., endpoint, project_name for Phoenix).

    Raises:
        ConfigurationError: If configuration is invalid.
                           Only raised at startup, never during operation.

    Examples:
        # Minimal setup (uses ./llmops.yaml)
        llmops.init()

        # Override backend programmatically
        llmops.init(backend="phoenix", endpoint="http://localhost:6006")

        # Disable auto-instrumentation (manual only)
        llmops.init(auto_instrument=False)
    """
    global _tracer_provider, _configured, _backend_type

    if _configured:
        raise ConfigurationError(
            "llmops is already configured. Call shutdown() first to reconfigure."
        )

    # Determine config path
    if config_path is None:
        config_path = Path.cwd() / "llmops.yaml"
    else:
        config_path = Path(config_path)

    # Load and merge configuration
    config = _load_yaml_config(config_path)
    config = _apply_env_overrides(config)

    # Apply kwarg overrides (highest priority)
    if backend:
        config["backend"] = backend

    # Apply endpoint override from kwargs
    if "endpoint" in backend_kwargs:
        effective_backend = config.get("backend", "phoenix")
        if effective_backend == "phoenix":
            if "phoenix" not in config:
                config["phoenix"] = {}
            config["phoenix"]["endpoint"] = backend_kwargs["endpoint"]
        elif effective_backend == "mlflow":
            if "mlflow" not in config:
                config["mlflow"] = {}
            config["mlflow"]["tracking_uri"] = backend_kwargs["endpoint"]

    # Validate configuration
    _validate_config(config)

    # Extract values
    effective_backend = config["backend"]
    service_name = config["service"]["name"]
    # Console can be set in YAML (debug.console) or via kwargs
    console_enabled = config.get("debug", {}).get("console", False) or backend_kwargs.get("console", False)

    # Setup the appropriate backend
    if effective_backend == "phoenix":
        phoenix_config = config.get("phoenix", {})
        endpoint = phoenix_config.get("endpoint")
        if not endpoint:
            raise ConfigurationError(
                "phoenix.endpoint is required when using Phoenix backend"
            )
        _tracer_provider = _setup_phoenix(
            endpoint=endpoint,
            service_name=service_name,
            console=console_enabled,
            auto_instrument=auto_instrument,
        )

    elif effective_backend == "mlflow":
        mlflow_config = config.get("mlflow", {})
        tracking_uri = mlflow_config.get("tracking_uri")
        if not tracking_uri:
            raise ConfigurationError(
                "mlflow.tracking_uri is required when using MLflow backend"
            )
        experiment_name = mlflow_config.get("experiment_name", service_name)
        _tracer_provider = _setup_mlflow(
            endpoint=tracking_uri,
            service_name=experiment_name,
            console=console_enabled,
        )

    _backend_type = effective_backend
    _configured = True
    print(f"llmops: Configuration complete ({effective_backend})")
