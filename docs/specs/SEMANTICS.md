# LLM Observability SDK — Semantic Conventions

**Version:** 1.0
**Date:** 2026-01-13
**Status:** Draft

---

## 1. Purpose

This document defines the **semantic mapping** between:

1. **SDK Public API** — Our decorator semantic kinds
2. **OTel GenAI** — OpenTelemetry Generative AI semantic conventions
3. **OpenInference** — Arize Phoenix semantic conventions
4. **MLflow** — MLflow tracing span types

This serves as the authoritative reference for how our abstraction layer translates to each backend.

---

## 2. Semantic Kind Mapping

### 2.1 SDK → OTel GenAI → Backend

| SDK SemanticKind | OTel GenAI `gen_ai.operation.name` | OTel SpanKind | OpenInference `openinference.span.kind` | MLflow `SpanType` |
|------------------|-------------------------------------|---------------|------------------------------------------|-------------------|
| `LLM_GENERATE` | `chat` or `text_completion` | `CLIENT` | `LLM` | `LLM` |
| `TOOL_CALL` | `execute_tool` | `INTERNAL` | `TOOL` | `TOOL` |
| `AGENT_RUN` | (custom) | `INTERNAL` | `AGENT` | `AGENT` |
| `RETRIEVE` | (custom) | `INTERNAL` | `RETRIEVER` | `RETRIEVER` |
| `EMBED` | `embeddings` | `CLIENT` | `EMBEDDING` | `EMBEDDING` |
| `TASK` | (custom) | `INTERNAL` | `CHAIN` | `CHAIN` |

### 2.2 Notes on Mapping

**OTel GenAI:**
- Uses `gen_ai.operation.name` to classify operations
- Standard values: `chat`, `text_completion`, `embeddings`, `execute_tool`
- Custom operations use descriptive names

**OpenInference:**
- Uses `openinference.span.kind` attribute with 9 defined kinds
- More granular than OTel (includes `RERANKER`, `GUARDRAIL`, `EVALUATOR`)
- Requires translation from OTel GenAI attributes

**MLflow:**
- Uses `SpanType` enum in Python SDK
- Values: `LLM`, `CHAIN`, `TOOL`, `AGENT`, `RETRIEVER`, `EMBEDDING`, `PARSER`, `RERANKER`

---

## 3. Attribute Mapping Tables

### 3.1 Core Span Attributes

| SDK Concept | OTel GenAI Attribute | OpenInference Attribute | MLflow Attribute |
|-------------|---------------------|-------------------------|------------------|
| Model name | `gen_ai.request.model` | `llm.model_name` | `model` (tag) |
| Model provider | `gen_ai.provider.name` | `llm.provider` | (derived from model) |
| Operation name | `gen_ai.operation.name` | `openinference.span.kind` | `span_type` |
| Response model | `gen_ai.response.model` | `llm.model_name` | — |
| Response ID | `gen_ai.response.id` | — | — |
| Finish reason | `gen_ai.response.finish_reasons` | — | — |

### 3.2 Token Usage Attributes

| SDK Concept | OTel GenAI Attribute | OpenInference Attribute | MLflow Attribute |
|-------------|---------------------|-------------------------|------------------|
| Input tokens | `gen_ai.usage.input_tokens` | `llm.token_count.prompt` | `prompt_tokens` |
| Output tokens | `gen_ai.usage.output_tokens` | `llm.token_count.completion` | `completion_tokens` |
| Total tokens | (computed) | `llm.token_count.total` | `total_tokens` |
| Cached read tokens | — | `llm.token_count.cache_read` | — |
| Cached write tokens | — | `llm.token_count.cache_write` | — |

### 3.3 Input/Output Content

| SDK Concept | OTel GenAI Attribute | OpenInference Attribute | MLflow Attribute |
|-------------|---------------------|-------------------------|------------------|
| Input messages | `gen_ai.input.messages` (event) | `llm.input_messages.<i>.*` | `inputs` (JSON) |
| Output messages | `gen_ai.output.messages` (event) | `llm.output_messages.<i>.*` | `outputs` (JSON) |
| System prompt | `gen_ai.system_instructions` (event) | `llm.input_messages.0.*` (role=system) | (in inputs) |
| Raw input | — | `input.value` | `inputs` |
| Raw output | — | `output.value` | `outputs` |
| Input MIME type | — | `input.mime_type` | — |
| Output MIME type | — | `output.mime_type` | — |

### 3.4 Request Parameters

| SDK Concept | OTel GenAI Attribute | OpenInference Attribute | MLflow Attribute |
|-------------|---------------------|-------------------------|------------------|
| Temperature | `gen_ai.request.temperature` | (in `llm.invocation_parameters`) | (in parameters) |
| Max tokens | `gen_ai.request.max_tokens` | (in `llm.invocation_parameters`) | (in parameters) |
| Top P | `gen_ai.request.top_p` | (in `llm.invocation_parameters`) | (in parameters) |
| Top K | `gen_ai.request.top_k` | (in `llm.invocation_parameters`) | (in parameters) |
| Frequency penalty | `gen_ai.request.frequency_penalty` | (in `llm.invocation_parameters`) | (in parameters) |
| Presence penalty | `gen_ai.request.presence_penalty` | (in `llm.invocation_parameters`) | (in parameters) |
| Invocation params (JSON) | — | `llm.invocation_parameters` | `params` |

### 3.5 Tool/Function Call Attributes

| SDK Concept | OTel GenAI Attribute | OpenInference Attribute | MLflow Attribute |
|-------------|---------------------|-------------------------|------------------|
| Tool name | `gen_ai.tool.name` | `tool.name` | `name` |
| Tool description | `gen_ai.tool.description` | `tool.description` | — |
| Tool call ID | `gen_ai.tool.call.id` | `tool_call.id` | — |
| Tool arguments | `gen_ai.tool.call.arguments` | `tool_call.function.arguments` | `inputs` |
| Tool result | `gen_ai.tool.call.result` | `output.value` | `outputs` |
| Tool definitions | `gen_ai.tool.definitions` | `llm.tools.<i>.*` | — |

### 3.6 Retrieval Attributes

| SDK Concept | OTel GenAI Attribute | OpenInference Attribute | MLflow Attribute |
|-------------|---------------------|-------------------------|------------------|
| Query | — | `input.value` | `inputs` |
| Documents | — | `retrieval.documents.<i>.*` | `outputs` |
| Document ID | — | `document.id` | — |
| Document content | — | `document.content` | — |
| Document score | — | `document.score` | — |
| Document metadata | — | `document.metadata` | — |

### 3.7 Embedding Attributes

| SDK Concept | OTel GenAI Attribute | OpenInference Attribute | MLflow Attribute |
|-------------|---------------------|-------------------------|------------------|
| Model name | `gen_ai.request.model` | `embedding.model_name` | `model` |
| Input text | — | `embedding.text` | `inputs` |
| Vector | — | `embedding.vector` | `outputs` |
| Dimensions | `gen_ai.embeddings.dimension.count` | (vector length) | — |
| Encoding format | `gen_ai.request.encoding_formats` | — | — |

### 3.8 Session/Context Attributes

| SDK Concept | OTel GenAI Attribute | OpenInference Attribute | MLflow Attribute |
|-------------|---------------------|-------------------------|------------------|
| Session ID | `gen_ai.conversation.id` | `session.id` | (tag) |
| User ID | — | `user.id` | (tag) |
| Tags | — | `tag.tags` | `tags` |
| Metadata | (custom attributes) | `metadata` (JSON) | `attributes` |

### 3.9 Error Attributes

| SDK Concept | OTel GenAI Attribute | OpenInference Attribute | MLflow Attribute |
|-------------|---------------------|-------------------------|------------------|
| Error type | `error.type` | `exception.type` | (status) |
| Error message | (span status) | `exception.message` | (status message) |
| Stack trace | (span event) | `exception.stacktrace` | (event) |

---

## 4. Event Mapping

### 4.1 OTel GenAI Events

OTel GenAI captures content as **span events** rather than span attributes:

| Event Name | Purpose | Body Attributes |
|------------|---------|-----------------|
| `gen_ai.client.inference.operation.details` | Request details | `gen_ai.input.messages`, `gen_ai.system_instructions` |
| `gen_ai.content.chunk` | Streaming chunk | `chunk.index`, `chunk.content` |
| `gen_ai.evaluation.result` | Quality metrics | `gen_ai.evaluation.name`, `gen_ai.evaluation.score.value` |

### 4.2 SDK Event Emission

| SDK Call | OTel Event | OpenInference | MLflow |
|----------|------------|---------------|--------|
| `set_input(value)` | Event with `gen_ai.input.messages` | `input.value` attribute | `inputs` |
| `set_output(value)` | Event with `gen_ai.output.messages` | `output.value` attribute | `outputs` |
| `emit_chunk(content)` | `gen_ai.content.chunk` event | — | (event) |
| `set_error(e)` | Exception event | `exception.*` attributes | Error status |

---

## 5. Span Naming Conventions

### 5.1 OTel GenAI Span Names

Format: `{operation.name} {model}` or `{operation.name} {tool.name}`

Examples:
- `chat gpt-4o`
- `text_completion claude-3-opus`
- `execute_tool search_database`
- `embeddings text-embedding-3-small`

### 5.2 SDK Span Naming

| SDK Decorator | Default Span Name | With Explicit Name |
|---------------|-------------------|-------------------|
| `@llmops.llm(model="gpt-4o")` | `chat gpt-4o` | `chat gpt-4o` (name param ignored) |
| `@llmops.tool()` | `execute_tool {func_name}` | `execute_tool {name}` |
| `@llmops.agent()` | `agent {func_name}` | `agent {name}` |
| `@llmops.retrieve()` | `retrieve {func_name}` | `retrieve {name}` |
| `@llmops.task()` | `task {func_name}` | `task {name}` |

---

## 6. Backend-Specific Translation

### 6.1 OTLP/Tempo/Jaeger (Pass-Through)

No translation required. OTel GenAI attributes passed directly.

```
SDK Span → OTel GenAI Span → OTLP Export → Backend
```

### 6.2 MLflow (Pass-Through with Mapping)

MLflow natively supports OTel GenAI conventions via `/v1/traces` endpoint.

```
SDK Span → OTel GenAI Span → OTLP Export → MLflow
```

MLflow extracts:
- `gen_ai.request.model` → displayed as model
- `gen_ai.usage.*` → token metrics
- Inputs/outputs from events

### 6.3 Arize Phoenix (Translation Required)

Phoenix uses OpenInference conventions. Adapter must translate:

```
SDK Span → OTel GenAI Span → OpenInference Translation → Phoenix
```

**Translation Rules:**

| OTel GenAI | OpenInference |
|------------|---------------|
| `gen_ai.operation.name: "chat"` | `openinference.span.kind: "LLM"` |
| `gen_ai.request.model` | `llm.model_name` |
| `gen_ai.usage.input_tokens` | `llm.token_count.prompt` |
| `gen_ai.usage.output_tokens` | `llm.token_count.completion` |
| `gen_ai.input.messages` (event) | `llm.input_messages.<i>.*` |
| `gen_ai.output.messages` (event) | `llm.output_messages.<i>.*` |

**Message Flattening:**

OpenInference uses indexed attribute prefixes instead of arrays:

```python
# OTel GenAI (event body)
{
  "gen_ai.input.messages": [
    {"role": "user", "content": "Hello"}
  ]
}

# OpenInference (span attributes)
{
  "llm.input_messages.0.message.role": "user",
  "llm.input_messages.0.message.content": "Hello"
}
```

---

## 7. Custom Attributes

### 7.1 Namespace Convention

SDK custom attributes use configurable namespace (default: `custom`):

```python
llmops.set_metadata(user_id="u-123", request_type="summary")

# Results in:
custom.user_id: "u-123"
custom.request_type: "summary"
```

### 7.2 Backend Handling

| Backend | Custom Attribute Handling |
|---------|---------------------------|
| OTLP | Preserved as-is |
| MLflow | Stored in trace tags |
| Phoenix | Preserved as span attributes |

---

## 8. Streaming Semantics

### 8.1 Time-to-First-Token

Captured automatically on first `emit_chunk()` call:

```
gen_ai.time_to_first_token_ms: 245
```

### 8.2 Chunk Events

Each `emit_chunk()` creates a span event:

```python
# OTel Event
{
  "name": "gen_ai.content.chunk",
  "timestamp": 1705123456789,
  "attributes": {
    "chunk.index": 0,
    "chunk.content": "The"  # If capture enabled
  }
}
```

---

## 9. Reference Links

### OpenTelemetry GenAI Semantic Conventions
- Spans: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
- Events: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-events/
- Status: Development (experimental)

### OpenInference (Arize Phoenix)
- Specification: https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md
- Python SDK: https://github.com/Arize-ai/openinference/tree/main/python

### MLflow Tracing
- Manual Tracing: https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/manual-tracing/
- Trace Concepts: https://mlflow.org/docs/latest/genai/concepts/trace/
- Automatic Tracing: https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic/

---

## 11. Related Documents

| Document | Purpose |
|----------|---------|
| [Reference Architecture](./REFERENCE_ARCHITECTURE.md) | Mapping flow and adapter patterns |
| [API Specification](./API_SPECIFICATION.md) | Public API contracts |
| [PRD](./PRD.md) | Requirements |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-13
