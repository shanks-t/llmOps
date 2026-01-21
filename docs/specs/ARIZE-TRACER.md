# Arize/Phoenix Tracer Integration with Existing OpenTelemetry

This document explains how Arize Phoenix's auto-instrumentation interacts with existing OpenTelemetry configurations, and provides guidance for dual-backend architectures where GenAI traces need to be routed separately from infrastructure traces.

## Table of Contents

- [The Problem: Dual-Backend Architecture](#the-problem-dual-backend-architecture)
- [How Phoenix register() Works](#how-phoenix-register-works)
- [OpenTelemetry Global Provider Behavior](#opentelemetry-global-provider-behavior)
- [How OpenInference Instrumentors Work](#how-openinference-instrumentors-work)
- [The Real Interaction](#the-real-interaction)
- [Recommended Approach: Dual-Backend with Filtering](#recommended-approach-dual-backend-with-filtering)
- [References](#references)

---

## The Problem: Dual-Backend Architecture

Many production applications have a common requirement:

```
Infrastructure traces  →  Backend A (Google Cloud Trace, Dynatrace, Datadog, Jaeger)
GenAI/LLM traces      →  Backend B (Arize Phoenix, Arize AX)
```

This creates a challenge: How do you add Arize's GenAI tracing to an application that already has OpenTelemetry configured for a different backend?

### Why This Matters

- **Cost optimization**: GenAI traces can be verbose; you may not want them in your primary APM tool
- **Specialized analysis**: Phoenix/Arize provide GenAI-specific analysis (hallucination detection, retrieval evaluation) that general APM tools don't offer
- **Separation of concerns**: Infrastructure teams and ML teams often use different observability platforms

---

## How Phoenix register() Works

Phoenix provides a convenience function `register()` in the `arize-phoenix-otel` package for quick setup.

### Source Code Reference

From [`phoenix/otel/otel.py`](https://github.com/Arize-ai/phoenix/blob/main/packages/phoenix-otel/src/phoenix/otel/otel.py):

```python
def register(
    endpoint: str = None,
    project_name: str = None,
    batch: bool = True,
    set_global_tracer_provider: bool = True,  # <-- KEY PARAMETER
    auto_instrument: bool = False,
    ...
) -> TracerProvider:
    # Creates a new TracerProvider
    tracer_provider = TracerProvider(resource=resource)

    # Adds span processor with OTLP exporter
    tracer_provider.add_span_processor(span_processor)

    # If set_global_tracer_provider=True (DEFAULT), sets it globally
    if set_global_tracer_provider:
        trace.set_tracer_provider(tracer_provider)

    # Optionally auto-instruments installed OpenInference libraries
    if auto_instrument:
        _auto_instrument_installed_openinference_libraries()

    return tracer_provider
```

### Key Behaviors

| Parameter | Default | Effect |
|-----------|---------|--------|
| `set_global_tracer_provider` | `True` | Calls `trace.set_tracer_provider()` to set as global |
| `auto_instrument` | `False` | Auto-instruments OpenAI, LangChain, etc. if their OpenInference packages are installed |
| `batch` | `True` | Uses `BatchSpanProcessor` for production-ready batching |

---

## OpenTelemetry Global Provider Behavior

OpenTelemetry enforces a **single global tracer provider** rule.

### From the [OpenTelemetry Python Documentation](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html):

> "This can only be done once, a warning will be logged if any further attempt is made."

### What Happens on Multiple Calls

```python
# First call - SUCCEEDS
trace.set_tracer_provider(provider_a)  # ✓ Global provider set

# Second call - FAILS SILENTLY (with warning)
trace.set_tracer_provider(provider_b)  # ⚠️ Warning logged, provider_b IGNORED
```

The second provider is **not set**. The first provider remains active.

---

## How OpenInference Instrumentors Work

OpenInference instrumentors (GoogleADKInstrumentor, GoogleGenAIInstrumentor, LangChainInstrumentor, etc.) can receive a tracer provider in two ways:

### Option 1: Explicit Provider (Recommended for Dual-Backend)

```python
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

# Pass provider explicitly
GoogleADKInstrumentor().instrument(tracer_provider=my_provider)
GoogleGenAIInstrumentor().instrument(tracer_provider=my_provider)
```

### Option 2: Global Provider (Default Behavior)

```python
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

# Uses trace.get_tracer_provider() internally
GoogleADKInstrumentor().instrument()
```

### Source References

- [OpenInference Google ADK Instrumentation](https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-adk)
- [OpenInference Google GenAI Instrumentation](https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-genai)
- [OpenInference Instrumentation PyPI](https://pypi.org/project/openinference-instrumentation/)

---

## The Real Interaction

### Scenario: App with Existing Provider + Phoenix register()

```
Timeline:
─────────────────────────────────────────────────────────────────────────────
1. App startup    │  trace.set_tracer_provider(cloud_trace_provider)
                  │  ✓ Global provider set to Cloud Trace
─────────────────────────────────────────────────────────────────────────────
2. Phoenix init   │  register(endpoint="phoenix:6006")
                  │  → Creates new TracerProvider
                  │  → Calls trace.set_tracer_provider(phoenix_provider)
                  │  ⚠️ WARNING: "Overriding of current TracerProvider is not allowed"
                  │  ✗ Phoenix provider is IGNORED
─────────────────────────────────────────────────────────────────────────────
3. Result         │  Global provider = cloud_trace_provider (unchanged)
                  │  Infrastructure traces → Cloud Trace ✓
                  │  GenAI traces → Cloud Trace (NOT Phoenix!) ✗
─────────────────────────────────────────────────────────────────────────────
```

### Failure Modes

| Expectation | Reality |
|-------------|---------|
| Phoenix breaks existing tracing | Existing tracing continues fine |
| Phoenix captures GenAI traces | Phoenix provider is ignored; GenAI traces go to existing backend |
| One-line setup works | Silent failure with warning in logs |

---

## Recommended Approach: Dual-Backend with Filtering

For applications with existing OpenTelemetry configuration, use the **Span Processor Injection** pattern.

### Architecture

```
                                    ┌─────────────────────────┐
                                    │   BatchSpanProcessor    │
                              ┌────►│   (OTLP → Jaeger)       │──► All Spans
                              │     └─────────────────────────┘
┌──────────────┐              │
│ TracerProvider│─────────────┤
│   (Single)    │              │     ┌─────────────────────────┐
└──────────────┘              │     │ OpenInferenceFilter     │
                              └────►│   └─► BatchSpanProcessor │──► GenAI Spans Only
                                    │       (OTLP → Phoenix)   │
                                    └─────────────────────────┘
```

### Implementation

#### Step 1: Create a Filtering Span Processor

```python
from opentelemetry.sdk.trace import SpanProcessor

class OpenInferenceOnlySpanProcessor(SpanProcessor):
    """
    Filters spans so that ONLY OpenInference (GenAI) spans
    are forwarded to the delegate processor.

    Uses the openinference.span.kind attribute as the filter criterion.
    """

    def __init__(self, delegate_processor: SpanProcessor):
        self._delegate = delegate_processor

    def on_start(self, span, parent_context=None) -> None:
        # Don't filter on start - let all spans begin normally
        pass

    def on_end(self, span) -> None:
        attributes = span.attributes or {}

        # Only forward spans with OpenInference semantic attribute
        if "openinference.span.kind" in attributes:
            self._delegate.on_end(span)

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int | None = None) -> bool:
        if timeout_millis is None:
            return self._delegate.force_flush()
        return self._delegate.force_flush(timeout_millis)
```

#### Step 2: Configure Dual-Backend Setup

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# ------------------------------------
# Single TracerProvider for the app
# ------------------------------------
resource = Resource.create({
    "service.name": "my-service",
    "deployment.environment": "production",
})
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# ------------------------------------
# Backend 1: Infrastructure traces → Jaeger/Cloud Trace
# (ALL spans go here)
# ------------------------------------
infra_exporter = OTLPSpanExporter(
    endpoint="http://jaeger:4318/v1/traces"
)
infra_processor = BatchSpanProcessor(infra_exporter)
tracer_provider.add_span_processor(infra_processor)

# ------------------------------------
# Backend 2: GenAI traces → Phoenix
# (ONLY OpenInference spans go here)
# ------------------------------------
phoenix_exporter = OTLPSpanExporter(
    endpoint="http://phoenix:6006/v1/traces"
)
phoenix_batch_processor = BatchSpanProcessor(phoenix_exporter)
phoenix_filtered_processor = OpenInferenceOnlySpanProcessor(phoenix_batch_processor)
tracer_provider.add_span_processor(phoenix_filtered_processor)

# ------------------------------------
# Instrument GenAI libraries (Google ADK & Gemini)
# ------------------------------------
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

# Pass the shared tracer_provider explicitly
# GoogleADKInstrumentor: Instruments Google Agent Development Kit (ADK)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)

# GoogleGenAIInstrumentor: Instruments google-generativeai SDK (Gemini API)
GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
```

#### Step 3: For Arize AX (Enterprise)

```python
from arize.otel import HTTPSpanExporter

ax_exporter = HTTPSpanExporter(
    endpoint="https://otlp.arize.com/v1/traces",
    api_key="YOUR_API_KEY",
    space_id="YOUR_SPACE_ID",
)
ax_batch_processor = BatchSpanProcessor(ax_exporter)
ax_filtered_processor = OpenInferenceOnlySpanProcessor(ax_batch_processor)
tracer_provider.add_span_processor(ax_filtered_processor)
```

### OpenInference Span Attributes

The filter relies on the `openinference.span.kind` attribute, which OpenInference instrumentors automatically set on GenAI-related spans:

| Span Kind | Description |
|-----------|-------------|
| `LLM` | Language model inference calls |
| `CHAIN` | LangChain/LlamaIndex chain executions |
| `AGENT` | Agent orchestration spans |
| `TOOL` | Tool/function calls |
| `RETRIEVER` | RAG retrieval operations |
| `EMBEDDING` | Embedding generation |
| `RERANKER` | Reranking operations |

See: [OpenInference Semantic Conventions](https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md)

---

## SDK Implications

### Why One-Line Auto-Instrumentation Isn't Possible

For dual-backend scenarios, a one-line SDK call cannot work because:

1. **No access to existing provider**: The SDK can't know what provider the app already configured
2. **Filtering requires custom processor**: The `OpenInferenceOnlySpanProcessor` must wrap the exporter
3. **Provider must be shared**: Instrumentors need the same provider that has both processors

### What Would Be Needed

A hypothetical SDK feature would need:

```python
# Hypothetical API (does not exist today)
llmops.add_genai_backend(
    existing_provider=trace.get_tracer_provider(),  # Use existing
    backend="phoenix",
    endpoint="http://phoenix:6006/v1/traces",
    filter_genai_only=True  # Apply OpenInference filter
)
```

Or a processor factory:

```python
# Returns a pre-configured, filtered processor
processor = llmops.create_phoenix_processor(
    endpoint="http://phoenix:6006/v1/traces",
    filter_genai_only=True
)
existing_provider.add_span_processor(processor)
```

---

## References

### Phoenix/Arize Documentation

- [arize-phoenix-otel PyPI](https://pypi.org/project/arize-phoenix-otel/)
- [Phoenix OTEL Reference Documentation](https://arize-phoenix.readthedocs.io/projects/otel/en/latest/)
- [Arize AX OpenTelemetry Integration](https://arize.com/docs/ax/integrations/opentelemetry/opentelemetry-arize-otel)
- [Phoenix register() Source Code](https://github.com/Arize-ai/phoenix/blob/main/packages/phoenix-otel/src/phoenix/otel/otel.py)

### OpenTelemetry Documentation

- [OpenTelemetry Python Trace API](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html)
- [OpenTelemetry Tracing SDK Specification](https://opentelemetry.io/docs/specs/otel/trace/sdk/)
- [set_tracer_provider() Race Condition Issue](https://github.com/open-telemetry/opentelemetry-python/issues/2181)

### OpenInference

- [OpenInference GitHub Repository](https://github.com/Arize-ai/openinference)
- [OpenInference Google ADK Instrumentation](https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-adk)
- [OpenInference Google GenAI Instrumentation](https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-genai)
- [OpenInference Semantic Conventions](https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md)

### Example Implementation

See [`llm-observability-sdk/examples/genai_service/observability.py`](../llm-observability-sdk/examples/genai_service/observability.py) for a complete working example of the dual-backend pattern with filtering.
