# LLM Observability SDK — Reference Architecture

**Version:** 1.0
**Date:** 2026-01-13
**Status:** Draft

---

## 1. Purpose

This document encodes **architectural wisdom** for implementing the LLM Observability SDK. It defines:

- SDK layering and boundaries
- Invariants that must hold across all implementations
- Patterns for async, streaming, and error handling
- Technical constraints and their rationale

This is the "how systems like this should be built" document.

---

## 2. SDK Layering

### 2.1 Layer Definitions

| Layer | Responsibility | Stability | Dependencies |
|-------|---------------|-----------|--------------|
| **L4: Public API** | Developer-facing decorators and functions | Stable | L3 |
| **L3: Semantic Model** | SemanticKind, span lifecycle, context | Stable contract | L2 |
| **L2: OTel Mapping** | Translate to gen_ai.* attributes | Internal | L1 |
| **L1: Adapters** | Backend-specific translation | Maintained | L0 |
| **L0: OpenTelemetry** | Tracing foundation | External | None |

### 2.2 Dependency Rule

**Strict downward-only dependencies:**

```
L4 → L3 → L2 → L1 → L0
```

- Higher layers may depend on lower layers
- Lower layers MUST NOT depend on higher layers
- No circular dependencies

### 2.3 API vs SDK Separation

Inspired by [OpenTelemetry's design](https://opentelemetry.io/docs/specs/otel/library-guidelines/):

| Component | Contains | Depends On |
|-----------|----------|------------|
| **API Package** | Decorators, enrichment functions, SemanticKind enum | Nothing (self-sufficient) |
| **SDK Package** | Span processors, adapters, configuration | API + OpenTelemetry |

**Key property:** Application code depends only on API package. SDK package can be swapped or omitted (no-op mode).

---

## 3. Core Invariants

These MUST hold for all implementations. Violations are bugs.

### 3.1 Telemetry Safety

```
INVARIANT 1: Telemetry never breaks business logic
```

**Rules:**
- Decorators MUST NOT raise exceptions to user code
- Enrichment calls MUST NOT raise exceptions
- All telemetry failures are caught and logged internally
- Function return values MUST NOT be modified
- Function signatures MUST be preserved exactly

**Implementation:**
```python
def decorator(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            span = _start_span(...)
        except Exception:
            _log_internal_error(...)
            span = None  # Continue without telemetry

        try:
            return await func(*args, **kwargs)
        finally:
            if span:
                try:
                    _end_span(span)
                except Exception:
                    _log_internal_error(...)
    return wrapper
```

### 3.2 Signature Preservation

```
INVARIANT 2: Decorators preserve function signatures
```

**Rules:**
- `functools.wraps` is mandatory
- `__name__`, `__doc__`, `__annotations__` must be preserved
- `__wrapped__` must point to original function
- No argument reordering or mutation
- FastAPI dependency injection must work unchanged

**Verification:**
```python
@llmops.llm(model="gpt-4o")
async def generate(prompt: str, temperature: float = 0.7) -> str:
    ...

# These must all work:
assert generate.__name__ == "generate"
assert generate.__annotations__ == {"prompt": str, "temperature": float, "return": str}
assert hasattr(generate, "__wrapped__")
```

### 3.3 Explicit Enrichment

```
INVARIANT 3: Data capture requires explicit SDK calls
```

**Rules:**
- No inference from argument names
- No inference from return type
- No automatic extraction of "prompt" or "response" parameters
- All captured data comes from explicit `set_*()` calls

**Rationale:** Explicit calls are:
- Refactoring-safe (renaming args doesn't break instrumentation)
- Testable (calls can be mocked/asserted)
- Flexible (call at any point during execution)

### 3.4 Privacy by Default

```
INVARIANT 4: Content is not captured unless explicitly enabled
```

**Rules:**
- `set_input()` and `set_output()` record metadata only by default
- Actual content requires `capture_content: true` in config
- Per-call override available via `capture=True` parameter
- Content stored as OTel events, not span attributes

---

## 4. Async and Concurrency

### 4.1 Supported Callable Types

| Type | Detection | Span Lifecycle |
|------|-----------|----------------|
| Sync function | `not asyncio.iscoroutinefunction(f)` | Start → call → end |
| Async function | `asyncio.iscoroutinefunction(f)` | Start → await → end |
| Sync generator | `inspect.isgeneratorfunction(f)` | Start → iterate → end |
| Async generator | `inspect.isasyncgenfunction(f)` | Start → async iterate → end |

### 4.2 Context Propagation

**Mechanism:** Python `contextvars` for async-safe span context.

```python
_current_span: ContextVar[Optional[Span]] = ContextVar("current_span", default=None)

def set_input(value: Any) -> None:
    span = _current_span.get()
    if span is not None:
        span.set_input(value)
    # No-op if no span (safe by design)
```

**Properties:**
- Works across `await` boundaries
- Isolated between concurrent tasks
- No thread-local storage (async-safe)

### 4.3 Generator Span Lifecycle

**Sync generators:**
```python
@llmops.llm(model="gpt-4o")
def stream():
    # Span starts here (first iteration or function entry)
    for chunk in source:
        llmops.emit_chunk(chunk)
        yield chunk
    # Span ends here (exhaustion)
```

**Async generators:**
```python
@llmops.llm(model="gpt-4o")
async def stream():
    # Span starts here
    async for chunk in source:
        llmops.emit_chunk(chunk)
        yield chunk
    # Span ends here
```

**Edge cases:**
- Early termination (break): Span ends with partial data
- Exception during iteration: Span ends with error status
- Generator garbage collected: Span ends (cleanup via `__del__` or context manager)

### 4.4 Decorator Implementation Pattern

```python
import functools
import asyncio
import inspect
from contextlib import contextmanager, asynccontextmanager

def semantic(kind: SemanticKind, *, name: str = None, **kwargs):
    def decorator(func):
        is_async = asyncio.iscoroutinefunction(func)
        is_gen = inspect.isgeneratorfunction(func)
        is_async_gen = inspect.isasyncgenfunction(func)

        if is_async_gen:
            return _wrap_async_generator(func, kind, name, kwargs)
        elif is_gen:
            return _wrap_generator(func, kind, name, kwargs)
        elif is_async:
            return _wrap_async(func, kind, name, kwargs)
        else:
            return _wrap_sync(func, kind, name, kwargs)

    return decorator
```

---

## 5. Streaming Patterns

### 5.1 Chunk Emission

Streaming responses emit chunks as **span events**:

```python
async def stream_generate(prompt: str):
    llmops.set_input(prompt)

    async for chunk in llm_stream:
        llmops.emit_chunk(chunk)  # Creates span event
        yield chunk

    llmops.set_output(accumulated)  # Final output
```

**Event structure:**
```python
{
    "name": "gen_ai.content.chunk",
    "timestamp": ...,
    "attributes": {
        "chunk.index": 0,
        "chunk.content": "The",  # If capture enabled
    }
}
```

### 5.2 Time-to-First-Token

Automatically captured for streaming spans:

```python
# Internal tracking
span._first_chunk_time = None

def emit_chunk(chunk):
    span = _current_span.get()
    if span and span._first_chunk_time is None:
        span._first_chunk_time = time.time()
        span.set_attribute("gen_ai.time_to_first_token_ms",
                          (span._first_chunk_time - span._start_time) * 1000)
```

### 5.3 Token Accumulation

For streaming, tokens are typically known only at end:

```python
async def stream():
    llmops.set_input(prompt)
    chunks = []

    async for chunk in stream:
        chunks.append(chunk)
        llmops.emit_chunk(chunk)
        yield chunk

    # Set final values after stream completes
    llmops.set_output("".join(c.content for c in chunks))
    llmops.set_tokens(
        input=chunks[-1].usage.prompt_tokens,
        output=chunks[-1].usage.completion_tokens
    )
```

---

## 6. Error Handling

### 6.1 Error Categories

| Category | Source | SDK Behavior |
|----------|--------|--------------|
| **Telemetry error** | SDK internal failure | Log internally, continue execution |
| **Application error** | User code exception | Propagate unchanged, mark span as error |
| **Configuration error** | Invalid config | Fail at startup (not runtime) |

### 6.2 Application Error Handling

```python
@llmops.tool(name="query")
async def query_db(sql: str):
    llmops.set_input(sql)
    try:
        result = await db.execute(sql)
        llmops.set_output(result)
        return result
    except DatabaseError as e:
        llmops.set_error(e)  # Additional context
        raise  # MUST re-raise to user code
```

**Automatic capture:**
- Exception type: `error.type`
- Exception message: `error.message`
- Span status: `ERROR`

### 6.3 Telemetry Error Isolation

```python
# Internal pattern for all SDK operations
def _safe_operation(operation: Callable, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except Exception as e:
        _log_internal_error(e, operation.__name__)
        return None  # Safe default
```

---

## 7. Span Nesting

### 7.1 Automatic Parent-Child

Spans automatically nest via context propagation:

```python
@llmops.agent(name="research")
async def research(query):
    # Creates parent span

    result = await search(query)  # Child span
    analysis = await analyze(result)  # Child span
    return analysis

@llmops.retrieve(name="search")
async def search(query):
    # Automatically child of "research" span
    ...

@llmops.llm(model="gpt-4o")
async def analyze(data):
    # Automatically child of "research" span
    ...
```

### 7.2 Context Inheritance

Child spans inherit from parent:
- Trace ID
- Custom attributes set via `llmops.attributes()` context manager
- Session ID if set

---

## 8. Backend Adapter Contract

### 8.1 Adapter Interface

```python
class BackendAdapter(Protocol):
    def configure(self, config: dict) -> None:
        """Initialize adapter with config from YAML."""
        ...

    def export(self, span: OTelSpan) -> None:
        """Export span to backend. MUST NOT raise."""
        ...

    def flush(self) -> None:
        """Flush pending spans. Called on shutdown."""
        ...
```

### 8.2 Adapter Invariants

1. **Never raise to SDK core** — All exceptions caught internally
2. **Handle missing attributes** — Graceful degradation
3. **Preserve custom attributes** — Pass through unchanged
4. **Support batching** — Buffer and batch export for efficiency

### 8.3 Translation Responsibility

| Backend | Translation |
|---------|-------------|
| OTLP (Tempo, Jaeger) | None — pass-through |
| MLflow | None — native gen_ai.* support |
| Arize Phoenix | Translate gen_ai.* → OpenInference |
| Datadog | None — native gen_ai.* support (v1.37+) |

---

## 9. Semantic Mapping Pipeline

This section details how semantic information flows from the public API through to backend systems. For complete attribute mapping tables, see [SEMANTICS.md](./SEMANTICS.md).

### 9.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: Public API                                                        │
│  ────────────────────────────────────────────────────────────────────────── │
│  @llmops.llm(model="gpt-4o")      →  SemanticKind.LLM_GENERATE             │
│  @llmops.tool(name="search")      →  SemanticKind.TOOL_CALL                │
│  @llmops.agent(name="research")   →  SemanticKind.AGENT_RUN                │
│  @llmops.retrieve()               →  SemanticKind.RETRIEVE                  │
│                                                                             │
│  llmops.set_input(value)          →  InputEvent(value, capture_config)     │
│  llmops.set_output(value)         →  OutputEvent(value, capture_config)    │
│  llmops.set_tokens(in, out)       →  TokenUsage(input, output)             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: Semantic Model (Internal Representation)                          │
│  ────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  SemanticSpan {                                                             │
│      kind: SemanticKind.LLM_GENERATE,                                       │
│      name: "generate",                                                      │
│      model: "gpt-4o",                                                       │
│      input: InputEvent | None,                                              │
│      output: OutputEvent | None,                                            │
│      tokens: TokenUsage | None,                                             │
│      chunks: list[ChunkEvent],                                              │
│      error: ErrorInfo | None,                                               │
│      metadata: dict[str, Any],                                              │
│      parent: SemanticSpan | None,                                           │
│      children: list[SemanticSpan],                                          │
│  }                                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: OTel GenAI Mapping                                                │
│  ────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  OTelSpan {                                                                 │
│      name: "chat gpt-4o",                                                   │
│      kind: SpanKind.CLIENT,                                                 │
│      attributes: {                                                          │
│          "gen_ai.operation.name": "chat",                                   │
│          "gen_ai.request.model": "gpt-4o",                                  │
│          "gen_ai.usage.input_tokens": 150,                                  │
│          "gen_ai.usage.output_tokens": 42,                                  │
│      },                                                                     │
│      events: [                                                              │
│          Event("gen_ai.content.input", {...}),   # If capture enabled      │
│          Event("gen_ai.content.output", {...}),  # If capture enabled      │
│      ],                                                                     │
│  }                                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│  OTLP Adapter       │ │  MLflow Adapter     │ │  Phoenix Adapter    │
│  (Pass-through)     │ │  (Pass-through)     │ │  (Translation)      │
│                     │ │                     │ │                     │
│  No changes         │ │  No changes         │ │  gen_ai.* →         │
│  gen_ai.* intact    │ │  gen_ai.* intact    │ │  OpenInference      │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
    Tempo/Jaeger              MLflow                 Phoenix
```

### 9.2 SemanticKind to OTel GenAI Mapping

The SDK maps semantic kinds to OTel GenAI conventions:

| SemanticKind | `gen_ai.operation.name` | OTel SpanKind | Span Name Format |
|--------------|-------------------------|---------------|------------------|
| `LLM_GENERATE` | `chat` | `CLIENT` | `chat {model}` |
| `TOOL_CALL` | `execute_tool` | `INTERNAL` | `execute_tool {name}` |
| `AGENT_RUN` | `agent` | `INTERNAL` | `agent {name}` |
| `RETRIEVE` | `retrieve` | `INTERNAL` | `retrieve {name}` |
| `EMBED` | `embeddings` | `CLIENT` | `embeddings {model}` |
| `TASK` | `task` | `INTERNAL` | `task {name}` |

### 9.3 Span Creation Flow

```python
# Internal implementation (simplified)

def _create_span(kind: SemanticKind, **kwargs) -> SemanticSpan:
    """Create a semantic span from decorator parameters."""

    # 1. Create internal representation
    semantic_span = SemanticSpan(
        kind=kind,
        name=kwargs.get("name") or _get_function_name(),
        model=kwargs.get("model"),
        capture_override=kwargs.get("capture"),
    )

    # 2. Get parent from context (automatic nesting)
    parent = _current_span.get()
    if parent:
        semantic_span.parent = parent
        parent.children.append(semantic_span)

    # 3. Map to OTel GenAI
    otel_span = _map_to_otel(semantic_span)

    # 4. Set as current span in context
    _current_span.set(semantic_span)

    return semantic_span


def _map_to_otel(semantic_span: SemanticSpan) -> OTelSpan:
    """Map semantic span to OTel GenAI span."""

    # Determine OTel attributes based on semantic kind
    operation_name = _OPERATION_NAMES[semantic_span.kind]
    span_kind = _SPAN_KINDS[semantic_span.kind]

    # Build span name per OTel GenAI conventions
    if semantic_span.kind == SemanticKind.LLM_GENERATE:
        span_name = f"{operation_name} {semantic_span.model}"
    else:
        span_name = f"{operation_name} {semantic_span.name}"

    # Create OTel span
    otel_span = tracer.start_span(
        name=span_name,
        kind=span_kind,
        attributes={
            "gen_ai.operation.name": operation_name,
            "gen_ai.request.model": semantic_span.model,  # If applicable
        }
    )

    return otel_span
```

### 9.4 Enrichment to Attribute Mapping

When enrichment functions are called, they update both the semantic span and the OTel span:

```python
def set_tokens(*, input: int = None, output: int = None) -> None:
    """Map token counts to OTel GenAI attributes."""
    span = _current_span.get()
    if span is None:
        return  # No-op safety

    try:
        # Update semantic model
        span.tokens = TokenUsage(input=input, output=output)

        # Map to OTel GenAI attributes
        otel_span = span._otel_span
        if input is not None:
            otel_span.set_attribute("gen_ai.usage.input_tokens", input)
        if output is not None:
            otel_span.set_attribute("gen_ai.usage.output_tokens", output)

    except Exception as e:
        _log_internal_error("set_tokens", e)
```

### 9.5 Content Capture and Privacy

Content is captured as OTel events, respecting privacy configuration:

```python
def set_input(value: Any, *, capture: bool = None) -> None:
    """Capture input, respecting privacy settings."""
    span = _current_span.get()
    if span is None:
        return

    try:
        # Determine if content should be captured
        should_capture = _resolve_capture(
            global_config=_config.privacy.capture_content,
            span_override=span.capture_override,
            call_override=capture,
        )

        # Always record metadata
        span.input = InputEvent(
            value_type=type(value).__name__,
            value_length=_safe_length(value),
            timestamp=time.time(),
        )

        # Conditionally record content as OTel event
        if should_capture:
            serialized = _serialize_for_event(value)
            span._otel_span.add_event(
                name="gen_ai.content.input",
                attributes={"content": serialized}
            )

    except Exception as e:
        _log_internal_error("set_input", e)
```

### 9.6 Backend Adapter Translation

#### OTLP Adapter (Pass-Through)

```python
class OTLPAdapter:
    """Pass-through adapter for OTLP-compatible backends."""

    def export(self, span: OTelSpan) -> None:
        # No translation needed - OTel GenAI attributes passed directly
        self._exporter.export([span])
```

#### MLflow Adapter (Pass-Through)

```python
class MLflowAdapter:
    """Adapter for MLflow tracing endpoint."""

    def export(self, span: OTelSpan) -> None:
        # MLflow natively supports OTel GenAI conventions
        # via /v1/traces endpoint
        self._exporter.export([span])
```

#### Phoenix Adapter (Translation Required)

```python
class PhoenixAdapter:
    """Adapter for Arize Phoenix (OpenInference conventions)."""

    def export(self, span: OTelSpan) -> None:
        # Translate OTel GenAI → OpenInference
        translated = self._translate_to_openinference(span)
        self._exporter.export([translated])

    def _translate_to_openinference(self, span: OTelSpan) -> OTelSpan:
        """Translate gen_ai.* attributes to OpenInference."""
        new_attrs = {}

        # Map operation to span kind
        op_name = span.attributes.get("gen_ai.operation.name")
        new_attrs["openinference.span.kind"] = self._map_operation(op_name)

        # Map model
        if model := span.attributes.get("gen_ai.request.model"):
            new_attrs["llm.model_name"] = model

        # Map tokens
        if tokens := span.attributes.get("gen_ai.usage.input_tokens"):
            new_attrs["llm.token_count.prompt"] = tokens
        if tokens := span.attributes.get("gen_ai.usage.output_tokens"):
            new_attrs["llm.token_count.completion"] = tokens

        # Translate events to flattened attributes
        for event in span.events:
            if event.name == "gen_ai.content.input":
                self._flatten_messages(event, new_attrs, "llm.input_messages")
            elif event.name == "gen_ai.content.output":
                self._flatten_messages(event, new_attrs, "llm.output_messages")

        # Preserve custom attributes
        for key, value in span.attributes.items():
            if key.startswith("custom."):
                new_attrs[key] = value

        return span.with_attributes(new_attrs)

    def _map_operation(self, op_name: str) -> str:
        """Map OTel GenAI operation to OpenInference span kind."""
        return {
            "chat": "LLM",
            "text_completion": "LLM",
            "embeddings": "EMBEDDING",
            "execute_tool": "TOOL",
            "agent": "AGENT",
            "retrieve": "RETRIEVER",
        }.get(op_name, "CHAIN")

    def _flatten_messages(self, event, attrs: dict, prefix: str) -> None:
        """Flatten message array to OpenInference indexed format."""
        messages = event.attributes.get("content", [])
        for i, msg in enumerate(messages):
            attrs[f"{prefix}.{i}.message.role"] = msg.get("role")
            attrs[f"{prefix}.{i}.message.content"] = msg.get("content")
```

### 9.7 Multi-Backend Export

When multiple backends are configured, spans are exported to all:

```python
class SpanProcessor:
    """Process and export spans to configured backends."""

    def __init__(self, adapters: list[BackendAdapter]):
        self._adapters = adapters
        self._batch = []
        self._lock = threading.Lock()

    def on_span_end(self, span: OTelSpan) -> None:
        """Called when span ends. Buffer for batch export."""
        with self._lock:
            self._batch.append(span)

            if len(self._batch) >= self._batch_size:
                self._flush()

    def _flush(self) -> None:
        """Export buffered spans to all backends."""
        spans = self._batch
        self._batch = []

        for adapter in self._adapters:
            try:
                for span in spans:
                    adapter.export(span)
            except Exception as e:
                # Never fail - log and continue
                _log_internal_error(f"export to {adapter}", e)
```

---

## 10. Configuration

### 10.1 Load Order

```
1. Default values (in code)
2. YAML config file (~/.llmops/config.yaml or ./llmops.yaml)
3. Environment variables (LLMOPS_*)
4. Programmatic override (configure(**kwargs))
```

Later sources override earlier sources.

### 10.2 Validation

Configuration validated at startup, not runtime:

```python
def configure(config_path: str = None, **kwargs):
    config = _load_config(config_path)
    config = _apply_env_overrides(config)
    config = _apply_kwargs(config, kwargs)

    _validate_config(config)  # Raises on invalid config

    _initialize_adapters(config)
    _set_global_config(config)
```

### 10.3 Required vs Optional

| Field | Required | Default |
|-------|----------|---------|
| `service.name` | Yes | — |
| `backends` | Yes (at least one) | — |
| `privacy.capture_content` | No | `false` |
| `custom_attributes.namespace` | No | `"custom"` |
| `validation.mode` | No | `"permissive"` |

---

## 11. Validation Modes

### 11.1 Permissive Mode (Production)

- Unknown SemanticKind → warning + custom span
- Missing enrichment → silent (metadata-only span)
- Invalid attribute value → log warning, skip attribute

### 11.2 Strict Mode (Development/CI)

- Unknown SemanticKind → error at decoration time
- LLM span without `set_model()` → warning
- Tool span without name → warning
- Warnings can be configured to fail CI

---

## 12. Performance Considerations

### 12.1 Overhead Budget

Target: <1ms overhead per span for hot path operations.

### 12.2 Batching

Spans batched before export:
- Default batch size: 512 spans
- Default flush interval: 5 seconds
- Flush on shutdown

### 12.3 Sampling

Future consideration:
- Head-based sampling at trace start
- Tail-based sampling for errors/slow traces

---

## 13. Testing Patterns

### 13.1 Mocking Enrichment

```python
from unittest.mock import patch

def test_llm_call():
    with patch("llmops.set_input") as mock_input:
        with patch("llmops.set_output") as mock_output:
            result = await generate("test prompt")

            mock_input.assert_called_once_with("test prompt")
            mock_output.assert_called_once()
```

### 13.2 Test Mode

```python
llmops.configure(test_mode=True)
# Spans collected in memory, not exported
# Access via llmops.get_test_spans()
```

### 13.3 Validation in CI

```yaml
# CI config
validation:
  mode: "strict"
  fail_on_warnings: true
```

---

## 14. Related Documents

| Document | Purpose |
|----------|---------|
| [PRD](./PRD.md) | Requirements and success criteria |
| [Conceptual Architecture](./CONCEPTUAL_ARCHITECTURE.md) | Visual system overview |
| [API Specification](./API_SPECIFICATION.md) | Public API contracts and signatures |
| [Semantic Conventions](./SEMANTICS.md) | Attribute mapping tables across backends |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-13
