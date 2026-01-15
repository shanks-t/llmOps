# LLM Observability SDK — Reference Architecture

**Version:** 2.0
**Date:** 2026-01-15
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

## 2. How to Read This Document

This reference architecture distinguishes between **normative** and **illustrative** content:

| Type | Meaning | Reader Action |
|------|---------|---------------|
| **Normative** | Architectural constraints that MUST be followed | Implement exactly as specified |
| **Illustrative** | Example strategies demonstrating one valid approach | Use as guidance; other implementations are valid |

### Section Classifications

| Section | Classification | Rationale |
|---------|---------------|-----------|
| §3 SDK Layering | **Normative** | Defines system structure and dependency rules |
| §4 Core Invariants | **Normative** | Safety properties that must hold |
| §5 Async and Concurrency | **Normative (contract)** / Illustrative (code) | Callable types must be supported; implementation may vary |
| §6 Streaming Patterns | **Normative (behavior)** / Illustrative (code) | Streaming must work; exact mechanism may vary |
| §7 Error Handling | **Normative** | Error isolation is a safety requirement |
| §8 Span Nesting | **Normative** | Context propagation rules must hold |
| §9 Backend Adapter Contract | **Normative (interface)** / Illustrative (examples) | Contract is required; adapter internals may vary |
| §10 Semantic Mapping Pipeline | **Normative (flow)** / Illustrative (code) | Data flow must follow pattern; translation details may vary |
| §11 Configuration | **Normative (schema)** / Illustrative (examples) | Schema is required; load mechanics may vary |
| §12 Validation Modes | **Normative** | Both modes must be supported |
| §13 Performance | **Illustrative** | Guidelines, not requirements |
| §14 Testing & CI | **Illustrative** | Recommended patterns, not required |

### Marking Convention

Throughout this document:

> **Normative:** Text in this format represents architectural requirements.

```
# Illustrative Example (Non-Normative)
# Code in blocks marked this way demonstrates one possible implementation.
# Other implementations are valid as long as invariants hold.
```

---

## 3. SDK Layering

> **Normative:** The layer structure and dependency rules in this section are architectural requirements.

### 3.1 Layer Definitions

| Layer | Responsibility | Stability | Dependencies |
|-------|---------------|-----------|--------------|
| **L5: Public API** | Developer-facing init(), decorators, enrichment | Stable | L4, L3 |
| **L4: Auto-instrumentation** | Backend instrumentor orchestration | Stable | L1, L0 |
| **L3: Semantic Model** | SemanticKind, span lifecycle, context | Stable contract | L2 |
| **L2: OTel Mapping** | Translate to gen_ai.* attributes | Internal | L1 |
| **L1: Adapters** | Backend-specific translation | Maintained | L0 |
| **L0: OpenTelemetry** | Tracing foundation | External | None |

### 3.2 Dependency Rule

> **Normative:** These dependency constraints must be enforced.

**Strict downward-only dependencies:**

```
L5 → L4 → L3 → L2 → L1 → L0
     ↓              ↑
     └──────────────┘ (L4 also depends on L1 for backend config)
```

- Higher layers may depend on lower layers
- Lower layers MUST NOT depend on higher layers
- No circular dependencies

### 3.3 API vs SDK Separation

> **Normative:** This separation must be maintained.

Inspired by [OpenTelemetry's design](https://opentelemetry.io/docs/specs/otel/library-guidelines/):

| Component | Contains | Depends On |
|-----------|----------|------------|
| **API Package** | Decorators, enrichment functions, SemanticKind enum | Nothing (self-sufficient) |
| **SDK Package** | Span processors, adapters, configuration | API + OpenTelemetry |

**Key property:** Application code depends only on API package. SDK package can be swapped or omitted (no-op mode).

### 3.4 Auto-instrumentation Layer (L4)

The auto-instrumentation layer orchestrates backend-provided instrumentors based on configuration.

#### 3.4.1 Supported Backends and Instrumentors

> **Normative:** These backends must be supported with their respective instrumentor sources.

| Backend | Instrumentor Source | Libraries Supported |
|---------|--------------------|--------------------|
| **Arize Phoenix** | OpenInference | OpenAI, Anthropic, LangChain, LlamaIndex, Google GenAI, Bedrock, Mistral, Groq, VertexAI |
| **MLflow** | MLflow native | OpenAI, Anthropic, LangChain, LlamaIndex, AutoGen, DSPy, Google GenAI |

#### 3.4.2 init() Function Interface

> **Normative:** This interface must be provided.

```python
def init(
    config_path: str | None = None,
    *,
    backend: Literal["phoenix", "mlflow"] | None = None,
    auto_instrument: bool = True,
    **backend_kwargs,
) -> None:
    """
    Initialize the SDK with auto-instrumentation.

    Args:
        config_path: Path to YAML config file. Defaults to ./llmops.yaml
        backend: Override backend from config (phoenix or mlflow)
        auto_instrument: Enable auto-instrumentation (default True)
        **backend_kwargs: Backend-specific configuration overrides

    Raises:
        ConfigurationError: If config is invalid (at startup, not runtime)
    """
```

#### 3.4.3 Auto-instrumentation Invariants

> **Normative:** These invariants must hold for all implementations.

```
INVARIANT A1: Auto-instrumentation never modifies application behavior
```

**Rules:**
- Instrumentors MUST NOT change function return values
- Instrumentors MUST NOT change exception propagation
- Library patching happens at init() time, not at call time

```
INVARIANT A2: Auto-instrumentation failures are non-fatal
```

**Rules:**
- Missing instrumentor packages log warning, continue without
- Individual instrumentor failures don't prevent others from loading
- Application starts successfully even if no instrumentors load

```
INVARIANT A3: Manual instrumentation takes precedence
```

**Rules:**
- Decorated functions create their own spans
- Auto-instrumentation spans nest under manual spans when applicable
- Duplicate instrumentation avoided via context propagation

---

## 4. Core Invariants

> **Normative:** These invariants MUST hold for all implementations. Violations are bugs.

### 4.1 Telemetry Safety

```
INVARIANT 1: Telemetry never breaks business logic
```

**Rules:**
- Decorators MUST NOT raise exceptions to user code
- Enrichment calls MUST NOT raise exceptions
- All telemetry failures are caught and logged internally
- Function return values MUST NOT be modified
- Function signatures MUST be preserved exactly

### 4.2 Signature Preservation

```
INVARIANT 2: Decorators preserve function signatures
```

**Rules:**
- `functools.wraps` is mandatory
- `__name__`, `__doc__`, `__annotations__` must be preserved
- `__wrapped__` must point to original function
- No argument reordering or mutation
- FastAPI dependency injection must work unchanged

**Verification (normative test):**
```python
@llmops.llm(model="gpt-4o")
async def generate(prompt: str, temperature: float = 0.7) -> str:
    ...

# These must all work:
assert generate.__name__ == "generate"
assert generate.__annotations__ == {"prompt": str, "temperature": float, "return": str}
assert hasattr(generate, "__wrapped__")
```

### 4.3 Explicit Enrichment

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

### 4.4 Privacy by Default

```
INVARIANT 4: Content is not captured unless explicitly enabled
```

**Rules:**
- `set_input()` and `set_output()` record metadata only by default
- Actual content requires `capture_content: true` in config
- Per-call override available via `capture=True` parameter
- Content stored as OTel events, not span attributes

---

## 5. Async and Concurrency

### 5.1 Supported Callable Types

> **Normative:** All callable types in this table must be supported.

| Type | Detection | Span Lifecycle |
|------|-----------|----------------|
| Sync function | `not asyncio.iscoroutinefunction(f)` | Start → call → end |
| Async function | `asyncio.iscoroutinefunction(f)` | Start → await → end |
| Sync generator | `inspect.isgeneratorfunction(f)` | Start → iterate → end |
| Async generator | `inspect.isasyncgenfunction(f)` | Start → async iterate → end |

### 5.2 Context Propagation

> **Normative:** Context must propagate correctly across async boundaries.

**Required properties:**
- Works across `await` boundaries
- Isolated between concurrent tasks
- No thread-local storage (async-safe)

```python
# Illustrative Example (Non-Normative)
# This demonstrates one possible implementation using contextvars.
# Other mechanisms that provide the same properties are valid.

_current_span: ContextVar[Optional[Span]] = ContextVar("current_span", default=None)

def set_input(value: Any) -> None:
    span = _current_span.get()
    if span is not None:
        span.set_input(value)
    # No-op if no span (safe by design)
```

### 5.3 Generator Span Lifecycle

> **Normative:** Generator spans must follow this lifecycle contract.

**Sync generators:**
- Span starts at first iteration or function entry
- Span ends on exhaustion, exception, or early termination

**Async generators:**
- Same lifecycle as sync generators, but async-aware

**Edge cases (all must be handled):**
- Early termination (break): Span ends with partial data
- Exception during iteration: Span ends with error status
- Generator garbage collected: Span ends cleanly

---

## 6. Streaming Patterns

### 6.1 Chunk Emission

> **Normative:** Streaming responses must support chunk emission as span events.

**Required behavior:**
- Chunks emitted during iteration appear as span events
- Each chunk event includes index and optional content
- Time-to-first-token automatically captured

**Event structure (normative schema):**
```python
{
    "name": "gen_ai.content.chunk",
    "timestamp": ...,
    "attributes": {
        "chunk.index": int,          # Required
        "chunk.content": str | None, # If capture enabled
    }
}
```

### 6.2 Time-to-First-Token

> **Normative:** TTFT must be captured for streaming spans.

**Required attribute:** `gen_ai.time_to_first_token_ms`
- Measured from span start to first chunk emission
- Set automatically on first `emit_chunk()` call

### 6.3 Token Accumulation

> **Normative:** Token counts may be set at any point, including after stream completion.

This allows streaming implementations to set final token counts when usage information becomes available (typically in the final chunk).

---

## 7. Error Handling

> **Normative:** Error handling rules in this section are safety requirements.

### 7.1 Error Categories

| Category | Source | SDK Behavior |
|----------|--------|--------------|
| **Telemetry error** | SDK internal failure | Log internally, continue execution |
| **Application error** | User code exception | Propagate unchanged, mark span as error |
| **Configuration error** | Invalid config | Fail at startup (not runtime) |

### 7.2 Application Error Handling

> **Normative:** Application errors must propagate unchanged.

**Required behavior:**
- Exceptions from user code are re-raised exactly
- Span is marked with error status
- Exception type and message captured as span attributes

**Automatic capture (normative attributes):**
- `error.type`: Exception class name
- `error.message`: Exception message
- Span status: `ERROR`

### 7.3 Telemetry Error Isolation

> **Normative:** Telemetry errors must never propagate to user code.

All SDK operations must catch and handle exceptions internally. Failed operations result in degraded telemetry (e.g., missing attributes), never application failures.

---

## 8. Span Nesting

> **Normative:** Automatic parent-child relationships must work via context propagation.

### 8.1 Automatic Parent-Child

Spans automatically nest via context propagation. When a decorated function calls another decorated function, the inner span becomes a child of the outer span.

### 8.2 Context Inheritance

> **Normative:** Child spans must inherit from parent:

- Trace ID
- Custom attributes set via context manager
- Session ID if set

---

## 9. Backend Adapter Contract

### 9.1 Adapter Interface

> **Normative:** All adapters must implement this interface.

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

### 9.2 Adapter Invariants

> **Normative:** These properties must hold for all adapter implementations.

1. **Never raise to SDK core** — All exceptions caught internally
2. **Handle missing attributes** — Graceful degradation for incomplete spans
3. **Preserve custom attributes** — Pass through unchanged
4. **Support batching** — Buffer and batch export for efficiency

### 9.3 Translation Responsibility

> **Normative:** Translation responsibility by backend type.

| Backend | Translation |
|---------|-------------|
| OTLP (Tempo, Jaeger) | None — pass-through |
| MLflow | None — native gen_ai.* support |
| Arize Phoenix | Translate gen_ai.* → OpenInference |
| Datadog | None — native gen_ai.* support (v1.37+) |

### 9.4 Adapter Translation Contract

> **Normative:** Adapters requiring translation must implement these mappings.

**Phoenix (OpenInference) required mappings:**

| OTel GenAI Attribute | OpenInference Attribute |
|---------------------|------------------------|
| `gen_ai.operation.name` | `openinference.span.kind` |
| `gen_ai.request.model` | `llm.model_name` |
| `gen_ai.usage.input_tokens` | `llm.token_count.prompt` |
| `gen_ai.usage.output_tokens` | `llm.token_count.completion` |

**Operation to span kind mapping:**

| `gen_ai.operation.name` | `openinference.span.kind` |
|------------------------|--------------------------|
| `chat` | `LLM` |
| `text_completion` | `LLM` |
| `embeddings` | `EMBEDDING` |
| `execute_tool` | `TOOL` |
| `agent` | `AGENT` |
| `retrieve` | `RETRIEVER` |
| (other) | `CHAIN` |

```python
# Illustrative Example (Non-Normative)
# This pseudocode demonstrates the translation pattern.
# Actual implementation may differ.

def translate_to_openinference(span):
    for attr in gen_ai_attributes:
        map_to_openinference(attr)
    for event in content_events:
        flatten_to_indexed_attributes(event)
    preserve_custom_attributes()
```

---

## 10. Semantic Mapping Pipeline

> **Normative:** The pipeline stages and data flow in this section are architectural requirements. Implementation details are illustrative.

For complete attribute mapping tables, see [SEMANTICS.md](./SEMANTICS.md).

### 10.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 5: Public API                                                        │
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
│      kind: SemanticKind,                                                    │
│      name: str,                                                             │
│      model: str | None,                                                     │
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
│      name: "{operation} {model|name}",                                      │
│      kind: SpanKind.CLIENT | SpanKind.INTERNAL,                            │
│      attributes: {                                                          │
│          "gen_ai.operation.name": str,                                      │
│          "gen_ai.request.model": str | None,                               │
│          "gen_ai.usage.input_tokens": int | None,                          │
│          "gen_ai.usage.output_tokens": int | None,                         │
│      },                                                                     │
│      events: [Event("gen_ai.content.*", {...})],  # If capture enabled     │
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
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
    Tempo/Jaeger              MLflow                 Phoenix
```

### 10.2 SemanticKind to OTel GenAI Mapping

> **Normative:** These mappings must be implemented.

| SemanticKind | `gen_ai.operation.name` | OTel SpanKind | Span Name Format |
|--------------|-------------------------|---------------|------------------|
| `LLM_GENERATE` | `chat` | `CLIENT` | `chat {model}` |
| `TOOL_CALL` | `execute_tool` | `INTERNAL` | `execute_tool {name}` |
| `AGENT_RUN` | `agent` | `INTERNAL` | `agent {name}` |
| `RETRIEVE` | `retrieve` | `INTERNAL` | `retrieve {name}` |
| `EMBED` | `embeddings` | `CLIENT` | `embeddings {model}` |
| `TASK` | `task` | `INTERNAL` | `task {name}` |

### 10.3 Content Capture and Privacy

> **Normative:** Privacy configuration must follow this precedence.

**Capture resolution order (highest to lowest priority):**
1. Per-call override (`capture=True/False` parameter)
2. Per-span override (decorator parameter)
3. Global configuration (`privacy.capture_content`)

**Content storage:** Content must be stored as OTel events, not span attributes, to support backends that distinguish between metadata and content.

---

## 11. Configuration

### 11.1 Load Order

> **Normative:** Configuration must be loaded in this order.

```
1. Default values (in code)
2. YAML config file (~/.llmops/config.yaml or ./llmops.yaml)
3. Environment variables (LLMOPS_*)
4. Programmatic override (init(**kwargs))
```

Later sources override earlier sources.

### 11.2 Validation

> **Normative:** Configuration must be validated at startup, not runtime.

Invalid configuration must raise `ConfigurationError` at `init()` time. Runtime operations must never fail due to configuration issues.

### 11.3 Required vs Optional

> **Normative:** This schema must be supported.

| Field | Required | Default |
|-------|----------|---------|
| `service.name` | Yes | — |
| `backend` | Yes | — |
| `privacy.capture_content` | No | `false` |
| `auto_instrumentation.enabled` | No | `true` |
| `auto_instrumentation.disabled` | No | `[]` |

### 11.4 Environment Variable Overrides

> **Normative:** These environment variables must be supported.

| Environment Variable | Config Path | Example |
|---------------------|-------------|---------|
| `LLMOPS_BACKEND` | `backend` | `phoenix` |
| `LLMOPS_PHOENIX_ENDPOINT` | `phoenix.endpoint` | `http://localhost:6006` |
| `LLMOPS_MLFLOW_TRACKING_URI` | `mlflow.tracking_uri` | `http://localhost:5000` |
| `LLMOPS_AUTO_INSTRUMENT` | `auto_instrumentation.enabled` | `true` |
| `LLMOPS_CAPTURE_CONTENT` | `privacy.capture_content` | `false` |

---

## 12. Validation Modes

> **Normative:** Both validation modes must be supported.

### 12.1 Permissive Mode (Production)

- Unknown SemanticKind → warning + custom span
- Missing enrichment → silent (metadata-only span)
- Invalid attribute value → log warning, skip attribute

### 12.2 Strict Mode (Development/CI)

- Unknown SemanticKind → error at decoration time
- LLM span without `set_model()` → warning
- Tool span without name → warning
- Warnings can be configured to fail CI

---

## 13. Performance Guidelines

> **Illustrative:** This section provides implementation guidance. Specific values and strategies may be adjusted based on deployment requirements.

### 13.1 Overhead Budget

Target: <1ms overhead per span for hot path operations.

### 13.2 Batching

Recommended batching parameters:
- Batch size: 512 spans
- Flush interval: 5 seconds
- Flush on shutdown

### 13.3 Sampling

Future consideration:
- Head-based sampling at trace start
- Tail-based sampling for errors/slow traces

---

## 14. Testing Patterns

> **Illustrative:** This section provides recommended testing approaches. Teams may adapt these patterns to their testing frameworks and requirements.

### 14.1 Mocking Enrichment

Enrichment functions should be mockable for unit testing:

```python
# Illustrative Example (Non-Normative)
from unittest.mock import patch

def test_llm_call():
    with patch("llmops.set_input") as mock_input:
        with patch("llmops.set_output") as mock_output:
            result = await generate("test prompt")

            mock_input.assert_called_once_with("test prompt")
            mock_output.assert_called_once()
```

### 14.2 Test Mode

A test mode should be available that:
- Collects spans in memory instead of exporting
- Provides access to collected spans for assertions
- Does not require backend connectivity

### 14.3 CI Integration

Strict validation mode can be enabled in CI to catch missing instrumentation during development.

---

## 15. Related Documents

| Document | Purpose |
|----------|---------|
| [PRD](./PRD.md) | Requirements and success criteria |
| [Conceptual Architecture](./CONCEPTUAL_ARCHITECTURE.md) | Visual system overview |
| [API Specification](./API_SPECIFICATION.md) | Public API contracts and signatures |
| [Semantic Conventions](./SEMANTICS.md) | Attribute mapping tables across backends |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-15
