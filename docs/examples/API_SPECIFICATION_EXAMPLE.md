# LLM Observability SDK — API Specification

**Version:** 1.0
**Date:** 2026-01-13
**Status:** Draft

---

## 1. Overview

This document defines the **public API contracts** for the LLM Observability SDK. It serves as the authoritative reference for:

- Decorator signatures and behavior
- Enrichment function contracts
- Type definitions and enums
- Configuration API
- Error handling semantics

**Design Principle:** If the API feels awkward in examples, the API is wrong.

---

## 2. Package Structure

```
llmops/
├── __init__.py          # Public API exports
├── init.py              # instrument() for auto-instrumentation
├── decorators.py        # @llm, @tool, @agent, @retrieve
├── enrichment.py        # set_input, set_output, set_tokens, emit_chunk
├── types.py             # SemanticKind, TokenUsage, etc.
├── config.py            # Configuration dataclasses
└── _internal/           # Not part of public API
    ├── context.py       # Context propagation
    ├── spans.py         # Span management
    ├── auto_instrument/ # Backend-specific instrumentor setup
    │   ├── phoenix.py   # OpenInference instrumentors
    │   └── mlflow.py    # MLflow tracing setup
    └── adapters/        # Backend adapters
```

**Import Convention:**
```python
import llmops

# Auto-instrumentation (quick start)
llmops.instrument()  # Uses config from llmops.yaml

# Manual instrumentation (fine-grained control)
@llmops.llm(model="gpt-4o")
async def generate(prompt: str) -> str:
    llmops.set_input(prompt)
    ...
```

---

## 3. Semantic Decorators

### 3.1 Overview

Decorators mark **semantic boundaries** — they declare what kind of operation a function represents. They do NOT extract data; that's the job of enrichment functions.

| Decorator | Purpose | Required Parameters |
|-----------|---------|---------------------|
| `@llmops.llm()` | LLM generation call | `model` |
| `@llmops.tool()` | Tool/function execution | `name` (optional, defaults to function name) |
| `@llmops.agent()` | Agent workflow | `name` (optional, defaults to function name) |
| `@llmops.retrieve()` | Retrieval operation | `name` (optional, defaults to function name) |
| `@llmops.task()` | Generic task/step | `name` (optional, defaults to function name) |

### 3.2 `@llmops.llm()`

Marks a function as an LLM generation operation.

**Signature:**
```python
def llm(
    *,
    model: str,
    name: str | None = None,
    capture: bool | None = None,
) -> Callable[[F], F]:
    """
    Mark a function as an LLM generation operation.

    Args:
        model: The model identifier (e.g., "gpt-4o", "claude-3-opus").
               Required. Used for gen_ai.request.model attribute.
        name: Span name. Defaults to function name if not provided.
        capture: Override content capture setting for this span.
                 None = use global config, True = capture, False = don't capture.

    Returns:
        Decorated function with preserved signature.
    """
```

**Example:**
```python
@llmops.llm(model="gpt-4o")
async def generate_summary(text: str) -> str:
    llmops.set_input(text)
    response = await openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarize: {text}"}]
    )
    result = response.choices[0].message.content
    llmops.set_output(result)
    llmops.set_tokens(
        input=response.usage.prompt_tokens,
        output=response.usage.completion_tokens
    )
    return result
```

**Resulting Span Attributes:**
```
gen_ai.operation.name: "chat"
gen_ai.request.model: "gpt-4o"
gen_ai.usage.input_tokens: <from set_tokens>
gen_ai.usage.output_tokens: <from set_tokens>
```

### 3.3 `@llmops.tool()`

Marks a function as a tool/function call.

**Signature:**
```python
def tool(
    *,
    name: str | None = None,
    capture: bool | None = None,
) -> Callable[[F], F]:
    """
    Mark a function as a tool execution.

    Args:
        name: Tool name for the span. Defaults to function name.
        capture: Override content capture setting for this span.

    Returns:
        Decorated function with preserved signature.
    """
```

**Example:**
```python
@llmops.tool()
async def search_database(query: str) -> list[dict]:
    llmops.set_input(query)
    results = await db.search(query)
    llmops.set_output(results)
    return results
```

### 3.4 `@llmops.agent()`

Marks a function as an agent workflow (typically a parent span).

**Signature:**
```python
def agent(
    *,
    name: str | None = None,
    capture: bool | None = None,
) -> Callable[[F], F]:
    """
    Mark a function as an agent workflow.

    Args:
        name: Agent name for the span. Defaults to function name.
        capture: Override content capture setting for this span.

    Returns:
        Decorated function with preserved signature.
    """
```

**Example:**
```python
@llmops.agent(name="research-agent")
async def research(query: str) -> str:
    llmops.set_input(query)

    # Child spans nest automatically
    docs = await search_documents(query)
    analysis = await analyze_documents(docs)

    llmops.set_output(analysis)
    return analysis
```

### 3.5 `@llmops.retrieve()`

Marks a function as a retrieval operation (RAG, vector search, etc.).

**Signature:**
```python
def retrieve(
    *,
    name: str | None = None,
    capture: bool | None = None,
) -> Callable[[F], F]:
    """
    Mark a function as a retrieval operation.

    Args:
        name: Retrieval operation name. Defaults to function name.
        capture: Override content capture setting for this span.

    Returns:
        Decorated function with preserved signature.
    """
```

**Example:**
```python
@llmops.retrieve(name="vector-search")
async def search_knowledge_base(query: str, top_k: int = 5) -> list[Document]:
    llmops.set_input(query)
    embedding = await get_embedding(query)
    results = await vector_db.search(embedding, limit=top_k)
    llmops.set_output({"count": len(results), "ids": [r.id for r in results]})
    return results
```

### 3.6 `@llmops.task()`

Marks a function as a generic task or step.

**Signature:**
```python
def task(
    *,
    name: str | None = None,
    capture: bool | None = None,
) -> Callable[[F], F]:
    """
    Mark a function as a generic task.

    Use for operations that don't fit other semantic categories.

    Args:
        name: Task name for the span. Defaults to function name.
        capture: Override content capture setting for this span.

    Returns:
        Decorated function with preserved signature.
    """
```

### 3.7 Decorator Invariants

All decorators MUST:

1. **Preserve function signature** — `functools.wraps` applied, `__name__`, `__doc__`, `__annotations__` preserved
2. **Never raise exceptions** — All telemetry failures caught and logged internally
3. **Support all callable types** — sync, async, sync generator, async generator
4. **Not modify return values** — Function output passed through unchanged
5. **Enable automatic nesting** — Child spans inherit parent context

**Verification Test:**
```python
@llmops.llm(model="gpt-4o")
async def my_func(prompt: str, temperature: float = 0.7) -> str:
    """Generate text."""
    ...

# All must pass:
assert my_func.__name__ == "my_func"
assert my_func.__doc__ == "Generate text."
assert my_func.__annotations__ == {"prompt": str, "temperature": float, "return": str}
assert hasattr(my_func, "__wrapped__")
```

---

## 4. Enrichment Functions

Enrichment functions add data to the current span. They are the "what data to capture" part of the two-part contract.

### 4.1 Overview

| Function | Purpose | When to Call |
|----------|---------|--------------|
| `set_input()` | Record input data | After receiving input |
| `set_output()` | Record output data | Before returning |
| `set_tokens()` | Record token usage | When usage is known |
| `emit_chunk()` | Record streaming chunk | During iteration |
| `set_error()` | Record error context | In exception handler |
| `set_metadata()` | Add custom attributes | Anytime |

### 4.2 `set_input()`

Record the input to an operation.

**Signature:**
```python
def set_input(
    value: Any,
    *,
    capture: bool | None = None,
) -> None:
    """
    Record input data for the current span.

    Args:
        value: The input value. Will be serialized to string/JSON.
        capture: Override content capture for this specific call.
                 None = use span/global setting.

    Behavior:
        - If capture enabled: Content stored as span event
        - If capture disabled: Only metadata recorded (type, length)
        - No-op if no active span (safe to call anywhere)

    Raises:
        Never raises. Failures logged internally.
    """
```

**Example:**
```python
@llmops.llm(model="gpt-4o")
async def generate(prompt: str) -> str:
    llmops.set_input(prompt)  # Records input
    ...
```

### 4.3 `set_output()`

Record the output of an operation.

**Signature:**
```python
def set_output(
    value: Any,
    *,
    capture: bool | None = None,
) -> None:
    """
    Record output data for the current span.

    Args:
        value: The output value. Will be serialized to string/JSON.
        capture: Override content capture for this specific call.

    Behavior:
        - If capture enabled: Content stored as span event
        - If capture disabled: Only metadata recorded (type, length)
        - No-op if no active span

    Raises:
        Never raises. Failures logged internally.
    """
```

### 4.4 `set_tokens()`

Record token usage for LLM operations.

**Signature:**
```python
def set_tokens(
    *,
    input: int | None = None,
    output: int | None = None,
    total: int | None = None,
) -> None:
    """
    Record token usage for the current span.

    Args:
        input: Number of input/prompt tokens.
        output: Number of output/completion tokens.
        total: Total tokens (if input/output not available separately).

    Behavior:
        - Sets gen_ai.usage.input_tokens if input provided
        - Sets gen_ai.usage.output_tokens if output provided
        - Computes total if not provided but input+output are
        - No-op if no active span

    Raises:
        Never raises. Failures logged internally.
    """
```

**Example:**
```python
llmops.set_tokens(
    input=response.usage.prompt_tokens,
    output=response.usage.completion_tokens
)
```

### 4.5 `emit_chunk()`

Record a streaming chunk during iteration.

**Signature:**
```python
def emit_chunk(
    content: str | Any,
    *,
    index: int | None = None,
    capture: bool | None = None,
) -> None:
    """
    Record a streaming chunk as a span event.

    Args:
        content: The chunk content.
        index: Optional chunk index. Auto-incremented if not provided.
        capture: Override content capture for this chunk.

    Behavior:
        - Creates span event with chunk data
        - First call records time-to-first-token
        - No-op if no active span

    Raises:
        Never raises. Failures logged internally.
    """
```

**Example:**
```python
@llmops.llm(model="gpt-4o")
async def stream_generate(prompt: str):
    llmops.set_input(prompt)
    accumulated = []

    async for chunk in openai_stream:
        content = chunk.choices[0].delta.content or ""
        llmops.emit_chunk(content)
        accumulated.append(content)
        yield content

    llmops.set_output("".join(accumulated))
```

### 4.6 `set_error()`

Record error context for the current span.

**Signature:**
```python
def set_error(
    error: BaseException,
    *,
    message: str | None = None,
) -> None:
    """
    Record error information for the current span.

    Args:
        error: The exception that occurred.
        message: Optional additional context message.

    Behavior:
        - Sets span status to ERROR
        - Records error.type and error.message attributes
        - Records stack trace if available
        - Does NOT suppress the exception (caller must re-raise)

    Raises:
        Never raises. Failures logged internally.
    """
```

**Example:**
```python
@llmops.tool(name="database-query")
async def query_db(sql: str):
    llmops.set_input(sql)
    try:
        result = await db.execute(sql)
        llmops.set_output(result)
        return result
    except DatabaseError as e:
        llmops.set_error(e, message="Query execution failed")
        raise  # Must re-raise
```

### 4.7 `set_metadata()`

Add custom attributes to the current span.

**Signature:**
```python
def set_metadata(
    **kwargs: str | int | float | bool,
) -> None:
    """
    Add custom attributes to the current span.

    Args:
        **kwargs: Key-value pairs to add as span attributes.
                  Keys will be prefixed with configured namespace.
                  Values must be primitive types.

    Behavior:
        - Attributes namespaced under custom.* by default
        - No-op if no active span

    Raises:
        Never raises. Failures logged internally.
    """
```

**Example:**
```python
llmops.set_metadata(
    user_id="user-123",
    request_type="summarization",
    priority=1
)
# Results in: custom.user_id, custom.request_type, custom.priority
```

### 4.8 Enrichment Invariants

All enrichment functions MUST:

1. **Never raise exceptions** — Failures logged internally, no-op on error
2. **Be safe to call without active span** — No-op behavior, no error
3. **Support any serializable value** — Automatic JSON serialization
4. **Respect privacy settings** — Honor capture configuration

---

## 5. Types and Enums

### 5.1 `SemanticKind`

Enumeration of operation types.

```python
from enum import Enum

class SemanticKind(Enum):
    """
    Semantic classification of operations.

    Used internally by decorators. Not typically used directly by application code.
    """

    LLM_GENERATE = "llm.generate"
    """LLM text generation operation."""

    TOOL_CALL = "tool.call"
    """Tool or function execution."""

    AGENT_RUN = "agent.run"
    """Agent workflow execution."""

    RETRIEVE = "retrieve"
    """Retrieval operation (RAG, vector search)."""

    TASK = "task"
    """Generic task or step."""

    EMBED = "embed"
    """Embedding generation."""
```

### 5.2 `TokenUsage`

Token usage data structure.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class TokenUsage:
    """
    Token usage information.

    Attributes:
        input_tokens: Number of input/prompt tokens.
        output_tokens: Number of output/completion tokens.
        total_tokens: Total tokens used.
    """
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def __post_init__(self):
        # Compute total if not provided
        if self.total_tokens is None and self.input_tokens and self.output_tokens:
            object.__setattr__(self, 'total_tokens', self.input_tokens + self.output_tokens)
```

### 5.3 `Configuration`

Configuration data structures.

```python
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class PhoenixConfig:
    """Configuration for Arize Phoenix backend."""
    endpoint: str
    project_name: str | None = None

@dataclass
class MLflowConfig:
    """Configuration for MLflow backend."""
    tracking_uri: str
    experiment_name: str | None = None

@dataclass
class AutoInstrumentationConfig:
    """Auto-instrumentation settings."""
    enabled: bool = True
    disabled: list[str] = field(default_factory=list)  # Instrumentors to skip

@dataclass
class BackendConfig:
    """Configuration for a single backend (used with configure())."""
    type: str  # "otlp", "mlflow", "phoenix"
    endpoint: str
    headers: dict[str, str] = field(default_factory=dict)

@dataclass
class PrivacyConfig:
    """Privacy-related configuration."""
    capture_content: bool = False

@dataclass
class ValidationConfig:
    """Validation mode configuration."""
    mode: str = "permissive"  # "permissive" or "strict"
    fail_on_warnings: bool = False

@dataclass
class Configuration:
    """
    SDK configuration.

    Attributes:
        service_name: Name of the service (required).
        service_version: Version of the service.
        backend: Primary backend for auto-instrumentation ("phoenix" or "mlflow").
        phoenix: Phoenix-specific configuration.
        mlflow: MLflow-specific configuration.
        auto_instrumentation: Auto-instrumentation settings.
        backends: List of backend configurations (for configure() multi-backend).
        privacy: Privacy settings.
        validation: Validation mode settings.
        custom_namespace: Namespace for custom attributes.
    """
    service_name: str
    service_version: str | None = None

    # For instrument() - single backend with auto-instrumentation
    backend: Literal["phoenix", "mlflow"] | None = None
    phoenix: PhoenixConfig | None = None
    mlflow: MLflowConfig | None = None
    auto_instrumentation: AutoInstrumentationConfig = field(
        default_factory=AutoInstrumentationConfig
    )

    # For configure() - multiple backends
    backends: list[BackendConfig] = field(default_factory=list)

    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    custom_namespace: str = "custom"
```

---

## 6. Initialization & Configuration API

### 6.1 `instrument()` — Auto-Instrumentation Entry Point

Initialize the SDK with auto-instrumentation enabled. This is the **recommended quick-start** for most applications.

**Signature:**
```python
def instrument(
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

    Supported Backends and Tracing:

        Phoenix (OpenInference):
            Auto-instruments: OpenAI, Anthropic, LangChain, LlamaIndex,
            Google GenAI, Google ADK, Bedrock, Mistral, Groq, VertexAI

        MLflow (OTLP for Google ADK):
            Google ADK traces via OTLP exporter to MLflow's /v1/traces endpoint.
            Per MLflow docs, ADK tracing uses OTLP export with x-mlflow-experiment-id
            header, NOT mlflow.autolog() or mlflow.tracing.enable().

    Examples:
        # Minimal setup (uses ./llmops.yaml)
        llmops.instrument()

        # Override backend programmatically
        llmops.instrument(backend="phoenix", endpoint="http://localhost:6006")

        # Disable auto-instrumentation (manual only)
        llmops.instrument(auto_instrument=False)
    """
```

**Quick Start Example:**
```python
# llmops.yaml
# backend: phoenix
# phoenix:
#   endpoint: http://localhost:6006

import llmops
llmops.instrument()  # That's it!

# All LLM library calls are now automatically traced
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
# ^ Automatically creates a span with model, tokens, input/output
```

### 6.2 `configure()` — Manual Configuration

Initialize the SDK with explicit configuration. Use this for advanced setups or when you need fine-grained control.

**Signature:**
```python
def configure(
    *,
    config_path: str | Path | None = None,
    service_name: str | None = None,
    service_version: str | None = None,
    backends: list[dict] | None = None,
    capture_content: bool | None = None,
    validation_mode: str | None = None,
    test_mode: bool = False,
    **kwargs,
) -> None:
    """
    Initialize the LLM Observability SDK with manual configuration.

    Note: For most use cases, prefer instrument() which provides auto-instrumentation.
    Use configure() when you need:
    - Multiple backends simultaneously
    - Test mode for unit testing
    - Fine-grained validation settings

    Configuration is loaded in order (later overrides earlier):
    1. Default values
    2. YAML config file
    3. Environment variables (LLMOPS_*)
    4. Keyword arguments to this function

    Args:
        config_path: Path to YAML config file.
                     Defaults to ./llmops.yaml or ~/.llmops/config.yaml
        service_name: Name of the service.
        service_version: Version of the service.
        backends: List of backend configurations.
        capture_content: Global content capture setting.
        validation_mode: "permissive" or "strict".
        test_mode: If True, spans collected in memory instead of exported.
        **kwargs: Additional configuration options.

    Raises:
        ConfigurationError: If configuration is invalid.
                           Only raised at startup, never during operation.

    Example:
        llmops.configure(
            service_name="my-agent",
            backends=[
                {"type": "phoenix", "endpoint": "http://localhost:6006"}
            ]
        )
    """
```

### 6.3 YAML Configuration Schema

The configuration format differs slightly depending on whether you use `instrument()` (auto-instrumentation) or `configure()` (manual setup).

#### For `instrument()` (Auto-Instrumentation)

```yaml
# llmops.yaml - Phoenix backend
service:
  name: "my-agent-service"
  version: "1.0.0"

# Required: Single backend for auto-instrumentation
backend: phoenix  # or "mlflow"

# Backend-specific configuration
phoenix:
  endpoint: http://localhost:6006
  project_name: my-project  # Optional

# Optional: Auto-instrumentation settings
auto_instrumentation:
  enabled: true  # Default: true
  disabled: []   # List of instrumentors to skip, e.g., ["langchain"]

# Optional: Privacy settings
privacy:
  capture_content: false  # Default: false
```

```yaml
# llmops.yaml - MLflow backend
service:
  name: "my-agent-service"
  version: "1.0.0"

backend: mlflow

mlflow:
  tracking_uri: http://localhost:5000
  experiment_name: my-experiment  # Optional

auto_instrumentation:
  enabled: true
  disabled: []

privacy:
  capture_content: false
```

#### For `configure()` (Manual Setup / Multiple Backends)

```yaml
# llmops.yaml - Multiple backends
service:
  name: "my-agent-service"
  version: "1.0.0"

# Multiple backends supported
backends:
  - type: phoenix
    endpoint: http://localhost:6006/v1/traces

  - type: mlflow
    endpoint: http://localhost:5001/v1/traces

  - type: otlp
    endpoint: http://localhost:4318/v1/traces
    headers:
      Authorization: "Bearer ${OTLP_TOKEN}"  # Env var substitution

privacy:
  capture_content: false

validation:
  mode: permissive  # "permissive" or "strict"
  fail_on_warnings: false

custom:
  namespace: "custom"  # Prefix for set_metadata() attributes
```

### 6.4 Environment Variables

| Variable | Overrides | Example |
|----------|-----------|---------|
| `LLMOPS_BACKEND` | `backend` | `phoenix` |
| `LLMOPS_PHOENIX_ENDPOINT` | `phoenix.endpoint` | `http://localhost:6006` |
| `LLMOPS_MLFLOW_TRACKING_URI` | `mlflow.tracking_uri` | `http://localhost:5000` |
| `LLMOPS_AUTO_INSTRUMENT` | `auto_instrumentation.enabled` | `true` |
| `LLMOPS_SERVICE_NAME` | `service.name` | `my-agent` |
| `LLMOPS_SERVICE_VERSION` | `service.version` | `1.0.0` |
| `LLMOPS_CAPTURE_CONTENT` | `privacy.capture_content` | `true` |
| `LLMOPS_VALIDATION_MODE` | `validation.mode` | `strict` |
| `LLMOPS_CONFIG_PATH` | Config file path | `./config/llmops.yaml` |

### 6.5 `get_test_spans()`

Retrieve spans captured in test mode.

**Signature:**
```python
def get_test_spans() -> list[TestSpan]:
    """
    Get spans captured during test mode.

    Returns:
        List of TestSpan objects with captured data.

    Raises:
        RuntimeError: If not in test mode.

    Example:
        llmops.configure(test_mode=True)

        await my_llm_function("test input")

        spans = llmops.get_test_spans()
        assert len(spans) == 1
        assert spans[0].attributes["gen_ai.request.model"] == "gpt-4o"
    """
```

### 6.6 `clear_test_spans()`

Clear captured test spans.

**Signature:**
```python
def clear_test_spans() -> None:
    """
    Clear all spans captured in test mode.

    Raises:
        RuntimeError: If not in test mode.
    """
```

---

## 7. Context Managers

### 7.1 `attributes()`

Add attributes to all spans within a context.

**Signature:**
```python
@contextmanager
def attributes(**kwargs: str | int | float | bool):
    """
    Add attributes to all spans created within this context.

    Args:
        **kwargs: Attributes to add to all child spans.

    Example:
        async with llmops.attributes(session_id="sess-123", user_id="user-456"):
            # All spans in this block will have session_id and user_id
            await generate_response(prompt)
            await execute_tool(tool_name)
    """
```

### 7.2 `session()`

Track a conversation/session.

**Signature:**
```python
@contextmanager
def session(session_id: str):
    """
    Track spans as part of a session/conversation.

    Args:
        session_id: Unique identifier for the session.

    Example:
        async with llmops.session("conversation-123"):
            await process_message(msg1)
            await process_message(msg2)
            # All spans tagged with session_id
    """
```

---

## 8. Error Handling

### 8.1 Error Categories

| Category | Source | SDK Behavior |
|----------|--------|--------------|
| **Configuration Error** | Invalid config | Raised at `instrument()` or `configure()` |
| **Telemetry Error** | SDK internal failure | Logged, operation continues |
| **Application Error** | User code exception | Propagated unchanged |

### 8.2 `ConfigurationError`

Raised when configuration is invalid.

```python
class ConfigurationError(Exception):
    """
    Raised when SDK configuration is invalid.

    Only raised during instrument() or configure(), never during normal operation.
    """
    pass
```

**Examples of configuration errors:**
- Missing required `service.name`
- No backend configured (for `instrument()`)
- Invalid backend type
- Malformed YAML
- Invalid instrumentor name in `disabled` list

### 8.3 Telemetry Error Isolation

Telemetry errors NEVER propagate to application code:

```python
# Internal implementation pattern
def set_input(value: Any) -> None:
    try:
        span = _current_span.get()
        if span is not None:
            span.set_input(value)
    except Exception as e:
        _log_internal_error("set_input", e)
        # Continue without raising
```

---

## 9. Complete Examples

### 9.1 Auto-Instrumentation Quick Start (Phoenix)

```yaml
# llmops.yaml
service:
  name: my-service

backend: phoenix

phoenix:
  endpoint: http://localhost:6006
```

```python
import llmops
from openai import OpenAI

# Initialize auto-instrumentation
llmops.instrument()

# That's it! All OpenAI calls are now automatically traced
client = OpenAI()

def chat(message: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content

# This call is automatically traced with:
# - Model name
# - Input/output tokens
# - Latency
# - Input/output content (if capture_content enabled)
result = chat("What is the capital of France?")
```

### 9.2 Auto-Instrumentation Quick Start (MLflow)

```yaml
# llmops.yaml
service:
  name: my-service

backend: mlflow

mlflow:
  tracking_uri: http://localhost:5000
  experiment_name: my-experiment
```

```python
import llmops
from anthropic import Anthropic

llmops.instrument()

# Anthropic calls are also auto-traced
client = Anthropic()

def ask_claude(question: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": question}]
    )
    return response.content[0].text

result = ask_claude("Explain quantum computing")
```

### 9.3 Auto + Manual Instrumentation Combined

```python
import llmops
from openai import AsyncOpenAI

# Enable auto-instrumentation
llmops.instrument()

client = AsyncOpenAI()

# Manual span for custom business logic
@llmops.agent(name="research-agent")
async def research(query: str) -> str:
    llmops.set_input(query)
    llmops.set_metadata(query_type="research", priority="high")

    # These OpenAI calls are auto-traced AND nested under research-agent
    plan = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Create research plan for: {query}"}]
    )

    results = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Execute plan: {plan.choices[0].message.content}"}]
    )

    output = results.choices[0].message.content
    llmops.set_output(output)
    return output
```

### 9.4 Basic LLM Call (Manual Instrumentation)

```python
import llmops
from openai import AsyncOpenAI

llmops.configure(
    service_name="my-service",
    backends=[{"type": "phoenix", "endpoint": "http://localhost:6006/v1/traces"}]
)

client = AsyncOpenAI()

@llmops.llm(model="gpt-4o")
async def summarize(text: str) -> str:
    llmops.set_input(text)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarize: {text}"}]
    )

    result = response.choices[0].message.content
    llmops.set_output(result)
    llmops.set_tokens(
        input=response.usage.prompt_tokens,
        output=response.usage.completion_tokens
    )

    return result
```

### 9.5 Streaming Response

```python
@llmops.llm(model="gpt-4o")
async def stream_response(prompt: str):
    llmops.set_input(prompt)
    chunks = []

    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.content or ""
        if content:
            llmops.emit_chunk(content)
            chunks.append(content)
            yield content

    llmops.set_output("".join(chunks))
```

### 9.6 Agent Workflow

```python
@llmops.agent(name="research-agent")
async def research(query: str) -> str:
    llmops.set_input(query)

    # Search for relevant documents (child span)
    docs = await search_documents(query)

    # Analyze with LLM (child span)
    analysis = await analyze(docs)

    llmops.set_output(analysis)
    return analysis

@llmops.retrieve(name="document-search")
async def search_documents(query: str) -> list[Document]:
    llmops.set_input(query)
    results = await vector_db.search(query, limit=5)
    llmops.set_output({"count": len(results)})
    return results

@llmops.llm(model="gpt-4o")
async def analyze(docs: list[Document]) -> str:
    llmops.set_input({"doc_count": len(docs)})
    # ... LLM call ...
    llmops.set_output(result)
    return result
```

### 9.7 Tool Execution with Error Handling

```python
@llmops.tool(name="database-query")
async def query_database(sql: str) -> list[dict]:
    llmops.set_input(sql)

    try:
        results = await db.execute(sql)
        llmops.set_output({"row_count": len(results)})
        return results
    except DatabaseError as e:
        llmops.set_error(e)
        raise  # Always re-raise application errors
```

### 9.8 FastAPI Integration

```python
from fastapi import FastAPI, Depends
import llmops

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Auto-instrumentation: all LLM calls traced automatically
    llmops.instrument()

@app.post("/chat")
async def chat(message: str):
    # OpenAI calls here are auto-traced
    response = await openai_client.chat.completions.create(...)
    return {"response": response.choices[0].message.content}

# Manual instrumentation still works with FastAPI DI
@llmops.llm(model="gpt-4o")
async def generate_response(prompt: str, db: Database = Depends(get_db)) -> str:
    # FastAPI DI still works - signature preserved
    llmops.set_input(prompt)
    ...
```

### 9.9 Testing

```python
import pytest
import llmops

@pytest.fixture(autouse=True)
def setup_test_mode():
    llmops.configure(test_mode=True, service_name="test")
    yield
    llmops.clear_test_spans()

async def test_llm_captures_tokens():
    result = await summarize("Hello world")

    spans = llmops.get_test_spans()
    assert len(spans) == 1
    assert spans[0].attributes["gen_ai.request.model"] == "gpt-4o"
    assert spans[0].attributes["gen_ai.usage.input_tokens"] > 0
```

---

## 10. Anti-Examples

### 10.1 DON'T: Infer from Argument Names

```python
# WRONG: SDK does not auto-extract "prompt" argument
@llmops.llm(model="gpt-4o")
async def generate(prompt: str) -> str:
    # Missing set_input()! Input not captured.
    response = await client.chat.completions.create(...)
    return response.choices[0].message.content

# CORRECT: Explicitly capture input
@llmops.llm(model="gpt-4o")
async def generate(prompt: str) -> str:
    llmops.set_input(prompt)  # Explicit capture
    response = await client.chat.completions.create(...)
    result = response.choices[0].message.content
    llmops.set_output(result)
    return result
```

### 10.2 DON'T: Catch and Suppress Application Errors

```python
# WRONG: Suppresses application errors
@llmops.tool()
async def query(sql: str):
    try:
        return await db.execute(sql)
    except DatabaseError as e:
        llmops.set_error(e)
        return None  # Wrong! Caller doesn't know about error

# CORRECT: Always re-raise
@llmops.tool()
async def query(sql: str):
    try:
        return await db.execute(sql)
    except DatabaseError as e:
        llmops.set_error(e)
        raise  # Correct! Propagate to caller
```

### 10.3 DON'T: Use Outside Decorated Function

```python
# WRONG: set_input() outside decorated context
async def process(data):
    llmops.set_input(data)  # No-op! No active span
    await some_other_function()

# CORRECT: Only call within decorated function
@llmops.task()
async def process(data):
    llmops.set_input(data)  # Correct! Active span exists
    await some_other_function()
```

### 10.4 DON'T: Forget Streaming Enrichment

```python
# WRONG: No chunk emission or final output
@llmops.llm(model="gpt-4o")
async def stream(prompt: str):
    async for chunk in llm_stream:
        yield chunk  # Chunks not captured!

# CORRECT: Emit chunks and set final output
@llmops.llm(model="gpt-4o")
async def stream(prompt: str):
    llmops.set_input(prompt)
    accumulated = []
    async for chunk in llm_stream:
        llmops.emit_chunk(chunk)
        accumulated.append(chunk)
        yield chunk
    llmops.set_output("".join(accumulated))
```

---

## 11. Public API Summary

### Initialization (Auto-Instrumentation)
- `llmops.instrument(config_path?, backend?, auto_instrument?, capture_content?, **backend_kwargs)` — **Recommended entry point**

### Decorators (Manual Instrumentation)
- `@llmops.llm(model, name?, capture?)`
- `@llmops.tool(name?, capture?)`
- `@llmops.agent(name?, capture?)`
- `@llmops.retrieve(name?, capture?)`
- `@llmops.task(name?, capture?)`

### Enrichment Functions
- `llmops.set_input(value, capture?)`
- `llmops.set_output(value, capture?)`
- `llmops.set_tokens(input?, output?, total?)`
- `llmops.emit_chunk(content, index?, capture?)`
- `llmops.set_error(error, message?)`
- `llmops.set_metadata(**kwargs)`

### Configuration (Advanced)
- `llmops.configure(...)` — For multi-backend or test mode setups
- `llmops.get_test_spans()`
- `llmops.clear_test_spans()`

### Context Managers
- `llmops.attributes(**kwargs)`
- `llmops.session(session_id)`

### Types
- `llmops.SemanticKind`
- `llmops.TokenUsage`
- `llmops.Configuration`
- `llmops.PhoenixConfig`
- `llmops.MLflowConfig`
- `llmops.AutoInstrumentationConfig`
- `llmops.ConfigurationError`

---

## 12. Related Documents

| Document | Purpose |
|----------|---------|
| [PRD](./PRD.md) | Requirements and success criteria |
| [Conceptual Architecture](./CONCEPTUAL_ARCHITECTURE.md) | Visual system overview |
| [Reference Architecture](./REFERENCE_ARCHITECTURE.md) | Technical patterns and invariants |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-13
