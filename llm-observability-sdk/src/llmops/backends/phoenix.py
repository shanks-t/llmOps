"""Phoenix/OpenInference backend implementation."""

from __future__ import annotations


def setup(endpoint: str, service_name: str):
    """
    Enable Phoenix/OpenInference auto-instrumentation.

    Args:
        endpoint: Phoenix OTLP endpoint (e.g., "http://localhost:6006/v1/traces")
        service_name: Service name for traces

    Returns:
        Configured TracerProvider
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource

    # Setup TracerProvider
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Enable instrumentors (fail silently if not installed)
    _try_instrument("openinference.instrumentation.google_adk", "GoogleADKInstrumentor", provider)
    _try_instrument("openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor", provider)
    _try_instrument_otel("opentelemetry.instrumentation.fastapi", "FastAPIInstrumentor", provider)

    return provider


def _try_instrument(module_path: str, class_name: str, provider) -> None:
    """Try to enable an OpenInference instrumentor, skip if not installed."""
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


def _try_instrument_otel(module_path: str, class_name: str, provider) -> None:
    """Try to enable an OpenTelemetry instrumentor, skip if not installed."""
    try:
        module = __import__(module_path, fromlist=[class_name])
        instrumentor_class = getattr(module, class_name)
        instrumentor = instrumentor_class()
        # OTel instrumentors use instrument() without tracer_provider arg
        instrumentor.instrument()
        print(f"llmops: Enabled {class_name}")
    except ImportError:
        print(f"llmops: {class_name} not installed, skipping")
    except Exception as e:
        print(f"llmops: Failed to enable {class_name}: {e}")
