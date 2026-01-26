# PRD_02 — API Specification

**Version:** 0.1
**Date:** 2026-01-24
**Status:** Draft
**Implements:** PRD_02

---

## 1. Overview

This document defines the public API for PRD_02: Add-On Instrumentation for Existing OpenTelemetry Users. The API extends `llmops.arize` with a new function that adds Arize telemetry to an existing TracerProvider without replacing it.

**Design Principle:** Non-disruptive integration. The existing observability stack remains untouched; Arize is added as an additional span processor.

---

## 2. Public API

### 2.1 `llmops.arize.instrument_existing_tracer()`

Add Arize telemetry to an existing global TracerProvider.

**Signature:**
```python
def instrument_existing_tracer(
    config_path: str | Path | None = None,
    *,
    endpoint: str | None = None,
    api_key: str | None = None,
    space_id: str | None = None,
    project_name: str | None = None,
    filter_to_genai_spans: bool = True,
) -> None:
    """
    Add Arize telemetry to an existing global TracerProvider.

    Use this when your application already has OpenTelemetry configured
    with a global TracerProvider. This function:

    1. Gets the existing global TracerProvider
    2. Creates an Arize SpanProcessor
    3. Optionally wraps it with OpenInference filtering
    4. Adds the processor to the existing provider
    5. Applies OpenInference auto-instrumentation (Google ADK, etc.)

    Unlike `instrument()`, this function does NOT:
    - Create a new TracerProvider
    - Set the global TracerProvider
    - Register an atexit handler (user owns the provider lifecycle)

    Args:
        config_path: Optional path to `llmops.yaml`. Not required if all
                     credentials are provided via kwargs.
        endpoint: Arize OTLP endpoint. Overrides config file value.
        api_key: Arize API key. Overrides config file value.
        space_id: Arize space ID. Overrides config file value.
        project_name: Arize project name. Overrides config file value.
        filter_to_genai_spans: If True (default), only spans with
                               `openinference.span.kind` attribute are
                               sent to Arize. Set to False to send all spans.

    Returns:
        None. The function modifies the existing provider in place.

    Raises:
        ConfigurationError: If configuration is invalid in strict mode.
        ImportError: If arize-otel package is not installed.

    Note:
        - Calling this function twice on the same provider logs a warning
          and does nothing (idempotent).
        - If no SDK TracerProvider exists, a warning is logged but the
          function continues (may not work correctly).

    Example:
        # Programmatic configuration (no config file needed)
        >>> import llmops
        >>> llmops.arize.instrument_existing_tracer(
        ...     endpoint="https://otlp.arize.com/v1",
        ...     api_key=os.environ["ARIZE_API_KEY"],
        ...     space_id=os.environ["ARIZE_SPACE_ID"],
        ... )

        # With config file
        >>> llmops.arize.instrument_existing_tracer(config_path="llmops.yaml")

        # Send all spans (not just GenAI)
        >>> llmops.arize.instrument_existing_tracer(
        ...     config_path="llmops.yaml",
        ...     filter_to_genai_spans=False,
        ... )
    """
```

---

## 3. Configuration

### 3.1 Programmatic Configuration

When all required credentials are provided as kwargs, no config file is needed:

```python
llmops.arize.instrument_existing_tracer(
    endpoint="https://otlp.arize.com/v1",
    api_key=os.environ["ARIZE_API_KEY"],
    space_id=os.environ["ARIZE_SPACE_ID"],
    project_name="my-genai-service",  # Optional
)
```

**Required kwargs (when no config file):**
- `endpoint`
- `api_key`
- `space_id`

### 3.2 Config File with Overrides

Config file values can be overridden by kwargs:

```python
# Config file provides defaults, kwargs override specific values
llmops.arize.instrument_existing_tracer(
    config_path="llmops.yaml",
    project_name="override-project",  # Overrides config file
)
```

**Override precedence:** kwargs > config file > defaults

### 3.3 YAML Schema Addition

The existing `arize:` section is reused. One new field is added:

```yaml
arize:
  endpoint: "https://otlp.arize.com/v1"
  api_key: "${ARIZE_API_KEY}"
  space_id: "${ARIZE_SPACE_ID}"
  project_name: "my-project"
  
  # New field for PRD_02
  filter_to_genai_spans: true  # Default: true for instrument_existing_tracer()
```

---

## 4. Filtering Behavior

### 4.1 OpenInference Span Filter

When `filter_to_genai_spans=True` (default), only spans with the `openinference.span.kind` attribute are forwarded to Arize. This attribute is set by OpenInference instrumentors (Google ADK, Google GenAI, etc.).

**Filtering logic:**
```python
# Span is forwarded to Arize if:
"openinference.span.kind" in span.attributes
```

**Effect:**
- GenAI spans (LLM calls, tool calls, agent runs) → Arize
- Infrastructure spans (HTTP requests, DB queries) → NOT sent to Arize

### 4.2 Disabling Filtering

Set `filter_to_genai_spans=False` to send all spans to Arize:

```python
llmops.arize.instrument_existing_tracer(
    endpoint="...",
    api_key="...",
    space_id="...",
    filter_to_genai_spans=False,  # All spans go to Arize
)
```

### 4.3 Default Behavior Comparison

| Function | `filter_to_genai_spans` Default |
|----------|--------------------------------|
| `instrument()` | `False` (send all spans) |
| `instrument_existing_tracer()` | `True` (GenAI only) |

**Rationale:** Users of `instrument_existing_tracer()` typically have existing infrastructure telemetry and only want GenAI-specific spans in Arize.

### 4.4 Trace Context and Orphaned Spans

**Important:** Filtering affects trace context preservation.

**When `filter_to_genai_spans=True`:**
- Parent spans (HTTP requests, middleware, etc.) are NOT sent to Arize
- GenAI spans lose their parent reference and become **orphaned spans**
- Orphaned spans appear in Arize's **Spans tab** but NOT in the **Traces tab**
- Spans are not visually connected in the trace waterfall view

**When `filter_to_genai_spans=False`:**
- ALL spans are sent to Arize (HTTP, DB, GenAI, etc.)
- Full trace context is preserved
- Traces appear correctly in Arize's **Traces tab** with parent-child relationships
- Higher data volume may impact Arize costs/quotas

### 4.5 Query-Time Filtering

To preserve trace context while focusing on GenAI spans, disable export-time filtering and filter in the Arize UI:

```python
# Send all spans to preserve trace context
llmops.arize.instrument_existing_tracer(
    config_path="llmops.yaml",
    filter_to_genai_spans=False,
)
```

Then in Arize UI, filter spans using:
```
openinference.span.kind EXISTS
```

Valid `openinference.span.kind` values (from OpenInference specification):

| Value | Description |
|-------|-------------|
| `LLM` | LLM inference calls |
| `CHAIN` | Chain/pipeline of operations |
| `AGENT` | Autonomous agent |
| `TOOL` | Tool execution |
| `EMBEDDING` | Embedding generation |
| `RETRIEVER` | Document retrieval |
| `RERANKER` | Re-ranking results |
| `GUARDRAIL` | Safety/guardrail checks |

### 4.6 Choosing a Filtering Strategy

| Priority | Recommended Setting | Rationale |
|----------|---------------------|-----------|
| Minimize Arize data volume | `filter_to_genai_spans=True` | Only GenAI spans exported; spans are orphaned |
| Preserve trace context | `filter_to_genai_spans=False` | Full traces visible; filter in Arize UI |
| Debug GenAI in request context | `filter_to_genai_spans=False` | See HTTP → GenAI call flow |

---

## 5. Duplicate Call Prevention

The function tracks instrumented providers to prevent duplicate processors:

```python
# First call: adds processor
llmops.arize.instrument_existing_tracer(endpoint="...", ...)

# Second call: logs warning, does nothing
llmops.arize.instrument_existing_tracer(endpoint="...", ...)
# WARNING: Arize instrumentation already added to this TracerProvider. Skipping.
```

**Implementation:** A module-level boolean flag tracks whether instrumentation has been applied.

**Note:** OpenTelemetry Python does not allow changing the global TracerProvider once set (`trace.set_tracer_provider()` can only be called once per process). Therefore, a simple boolean flag suffices for duplicate prevention within a single application lifecycle.

---

## 6. Error Handling

### 6.1 Non-SDK TracerProvider

If the global provider is not an SDK TracerProvider (e.g., ProxyTracerProvider):

```python
# Logs warning but continues
llmops.arize.instrument_existing_tracer(endpoint="...", ...)
# WARNING: Global TracerProvider is not an SDK TracerProvider (ProxyTracerProvider).
#          Arize instrumentation may not work correctly.
```

The function continues because:
- Some frameworks set up providers lazily
- Failing silently is safer than raising exceptions

### 6.2 Missing Credentials

**With config file:**
```python
# Config file missing required fields in strict mode
llmops.arize.instrument_existing_tracer(config_path="incomplete.yaml")
# ConfigurationError: arize.endpoint is required
```

**Without config file:**
```python
# Missing required kwargs
llmops.arize.instrument_existing_tracer(endpoint="...")
# ConfigurationError: api_key and space_id required when not using config file
```

### 6.3 Telemetry Isolation

All failures after initialization are swallowed and logged. Telemetry never breaks business logic.

---

## 7. Lifecycle Management

### 7.1 No Atexit Registration

Unlike `instrument()`, this function does NOT register an atexit handler:

| Function | Atexit Handler |
|----------|---------------|
| `instrument()` | Yes (calls `provider.shutdown()`) |
| `instrument_existing_tracer()` | No |

**Rationale:** The user owns the TracerProvider and its lifecycle. The SDK should not interfere.

### 7.2 Shutdown Responsibility

Users must ensure their existing provider shutdown includes flushing Arize spans:

```python
# User's existing shutdown code
provider = trace.get_tracer_provider()
provider.shutdown()  # Flushes all processors including Arize
```

---

## 8. Public API Summary

### New Function

| Function | Signature | Returns |
|----------|-----------|---------|
| `llmops.arize.instrument_existing_tracer` | `(config_path, *, endpoint, api_key, space_id, project_name, filter_to_genai_spans)` | `None` |

### Parameters

| Parameter | Type | Default | Required |
|-----------|------|---------|----------|
| `config_path` | `str \| Path \| None` | `None` | No* |
| `endpoint` | `str \| None` | `None` | Yes* |
| `api_key` | `str \| None` | `None` | Yes* |
| `space_id` | `str \| None` | `None` | Yes* |
| `project_name` | `str \| None` | `None` | No |
| `filter_to_genai_spans` | `bool` | `True` | No |

\* Either `config_path` OR all three of (`endpoint`, `api_key`, `space_id`) must be provided.

### Exceptions

| Exception | When Raised |
|-----------|-------------|
| `ConfigurationError` | Invalid config in strict mode |
| `ImportError` | Platform dependencies missing |

---

## 9. Internal Components

### 9.1 OpenInferenceSpanFilter

Internal span processor that filters to OpenInference spans only.

**Location:** `llmops._internal.span_filter.OpenInferenceSpanFilter`

```python
class OpenInferenceSpanFilter(SpanProcessor):
    """Filters spans to only forward OpenInference (GenAI) spans."""
    
    OPENINFERENCE_ATTRIBUTE = "openinference.span.kind"
    
    def __init__(self, delegate: SpanProcessor) -> None: ...
    def on_start(self, span, parent_context=None) -> None: ...
    def on_end(self, span) -> None: ...
    def shutdown(self) -> None: ...
    def force_flush(self, timeout_millis=None) -> bool: ...
```

### 9.2 Duplicate Tracking

**Location:** `llmops._platforms.arize._arize_instrumentation_applied`

Module-level boolean flag indicating whether Arize instrumentation has been applied. Since OpenTelemetry Python does not allow changing the global TracerProvider once set, a simple boolean suffices for duplicate prevention within a single application lifecycle.

### 9.3 ArizeProjectNameInjector

Internal span processor that injects the `arize.project.name` span attribute.

**Location:** `llmops._internal.span_filter.ArizeProjectNameInjector`

**Purpose:** When using `instrument_existing_tracer()`, we cannot modify the existing TracerProvider's Resource attributes. Arize requires either:
- `openinference.project.name` as a Resource attribute (set by `arize.otel.register()`), OR
- `arize.project.name` as a Span attribute

This processor injects the span attribute on every span during `on_start()`.

```python
class ArizeProjectNameInjector(SpanProcessor):
    """Injects arize.project.name span attribute for Arize routing."""
    
    def __init__(self, delegate: SpanProcessor, project_name: str) -> None: ...
    def on_start(self, span, parent_context=None) -> None: ...
    def on_end(self, span) -> None: ...
    def shutdown(self) -> None: ...
    def force_flush(self, timeout_millis=None) -> bool: ...
```

**Processor Chain Order:**

When both `project_name` and `filter_to_genai_spans=True` are configured, the processor chain is:

```
ArizeProjectNameInjector → OpenInferenceSpanFilter → BatchSpanProcessor
         (outer)                  (middle)                (inner)
```

The injector must be the outermost wrapper so `on_start()` is called first to set the attribute before the span is processed by inner processors.

---

## 10. Type Stubs

```python
# llmops/arize.pyi (additions)
from pathlib import Path

def instrument_existing_tracer(
    config_path: str | Path | None = None,
    *,
    endpoint: str | None = None,
    api_key: str | None = None,
    space_id: str | None = None,
    project_name: str | None = None,
    filter_to_genai_spans: bool = True,
) -> None: ...
```

---

## 11. Usage Examples

### 11.1 Basic Add-On (Programmatic)

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# User's existing setup
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint="http://dynatrace:4318/v1/traces"
)))
trace.set_tracer_provider(provider)

# Add Arize for GenAI traces
import llmops
llmops.arize.instrument_existing_tracer(
    endpoint="https://otlp.arize.com/v1",
    api_key=os.environ["ARIZE_API_KEY"],
    space_id=os.environ["ARIZE_SPACE_ID"],
)

# Now:
# - All spans go to Dynatrace
# - GenAI spans also go to Arize
```

### 11.2 With Config File

```python
# User's existing OTel setup
setup_existing_telemetry()

# Add Arize
import llmops
llmops.arize.instrument_existing_tracer(config_path="llmops.yaml")
```

### 11.3 FastAPI Application

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Existing telemetry setup
    provider = setup_existing_telemetry()
    
    # Add Arize
    import llmops
    llmops.arize.instrument_existing_tracer(
        endpoint=os.environ["ARIZE_ENDPOINT"],
        api_key=os.environ["ARIZE_API_KEY"],
        space_id=os.environ["ARIZE_SPACE_ID"],
    )
    
    yield
    
    # User handles shutdown
    provider.shutdown()

app = FastAPI(lifespan=lifespan)
```

---

## 12. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_02.md` | Requirements and success criteria |
| `docs/api_spec/API_SPEC_01.md` | API for `instrument()` (PRD_01) |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-24
