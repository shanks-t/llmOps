# LLM Observability SDK - Reference Architecture

**Version:** 1.0
**Date:** 2026-01-10
**Status:** Design / Pre-Implementation

---

## Executive Summary

This document defines the reference architecture for an **LLM Observability SDK** - an organizational abstraction layer that protects engineering teams from LLM observability ecosystem churn while providing excellent developer experience.

### The Problem We're Solving

**The LLM observability ecosystem is fragmented and rapidly evolving:**
- Backends: Arize, MLflow, LangSmith, Datadog, custom tools
- Conventions: OpenInference, OTel GenAI (experimental), vendor-specific formats
- Maturity: Everything is still changing, vendors come and go
- Developer Impact: Rewriting instrumentation, vendor lock-in, maintenance burden

**Without an SDK:** Teams rewrite instrumentation every time backends change.
**With this SDK:** Platform team maintains adapters, developers never change code.

### What This SDK Provides

1. **Stable developer API** - Decorators and patterns that won't change
2. **Backend flexibility** - Switch from Arize → MLflow → custom without touching app code
3. **Standards-based implementation** - Uses OTel GenAI conventions internally for maximum compatibility
4. **Organizational isolation** - Ecosystem volatility doesn't impact developers
5. **Migration tooling** - CLI tools for configuration, validation, and backend switching

### The Core Insight: Dual-Layer Architecture

> **We build a stable abstraction ON TOP OF standards, not INSTEAD OF them.**
>
> **Developer-Facing Layer** (Public API - optimized for DX):
> - `@observe.llm()`, `@observe.agent()`, `@observe.retriever()` - intuitive decorators
> - Domain-specific abstractions for common LLM patterns
> - This API is **stable** - changes require major version bump
>
> **Implementation Layer** (Internal - standards-based):
> - Uses OTel GenAI semantic conventions (`gen_ai.*` attributes)
> - Emits standard spans, events, and metrics
> - Backends that support OTel work with minimal/no adaptation

This approach gives us **developer stability + backend compatibility + organizational agility**.

---

## Design Principles

### 1. **Standards-Based Implementation, Custom Developer API**

- **Internally:** Use OTel GenAI semantic conventions (`gen_ai.*` attributes)
- **Externally:** Provide intuitive, domain-specific decorators optimized for DX
- **Why:** Maximum backend compatibility without sacrificing developer experience
- **Exit strategy:** Built on standards, not proprietary formats

### 2. **Organizational Stability Over Ecosystem Volatility**

- **Developer API is sacred** - breaking changes require major version bumps
- **Internal implementation can evolve** - upgrade OTel conventions without API changes
- **Backend adapters absorb complexity** - isolate teams from ecosystem churn
- **Cost of SDK maintenance << Cost of rewriting 50+ services**

### 3. **Developer Experience First**

- Decorators and context managers, not raw span objects
- Hard to misuse, easy to onboard
- Automatic nesting and context propagation
- Domain-specific abstractions (agents, RAG, workflows)
- Minimal boilerplate

### 4. **Privacy and Compliance by Default**

- **Opt-in for sensitive data** - prompts/completions not captured by default
- **Event-based content storage** - separate retention for PII vs. operational metadata
- **External storage pattern** - reference IDs instead of inline content
- **Sanitization helpers** - tools for PII removal when capture is enabled

### 5. **Backend Adapters Are Mission-Critical**

- Adapters are **the entire point** - they absorb ecosystem complexity
- Each adapter translates `gen_ai.*` → backend-specific conventions
- Support multiple backends simultaneously (migration, A/B testing)
- Adapters can be complex - that's better than 50+ services being complex

### 6. **What We Won't Do** (Hard-Earned Lessons)

- ❌ Don't invent competing semantic standards - use OTel GenAI internally
- ❌ Don't expose raw spans to users - decorators only
- ❌ Don't capture content by default - privacy first
- ❌ Don't tie developers to specific backends - adapters handle variation
- ❌ Don't create our own trace context system - use OTel

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 4: CLI Tooling (configuration, migration, validation)        │
│  $ observe-cli configure | validate | migrate | export-traces       │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 3: Backend Adapters (multi-backend support)                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │
│  │ Arize/Phoenix│ │   MLflow     │ │   Datadog    │  (simultaneous) │
│  │   Adapter    │ │   Adapter    │ │   Adapter    │                │
│  └──────────────┘ └──────────────┘ └──────────────┘                │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 2: Developer-Facing API (STABLE - public contract)           │
│  @observe.llm() | @observe.agent() | @observe.retriever()          │
│  Domain-specific abstractions optimized for DX                      │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 1: Standards Implementation (OTel GenAI conventions)         │
│  gen_ai.* attributes | Events for content | SpanKind.CLIENT         │
│  Uses official semantic conventions for maximum compatibility       │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 0: OpenTelemetry Foundation (unchanged)                      │
│  TracerProvider | Spans | Events | Context | Exporters             │
└─────────────────────────────────────────────────────────────────────┘

STABILITY BOUNDARIES:
═══════════════════════════════════════════════════════════════════════
Layer 2 (Public API)  → STABLE: Breaking changes require MAJOR version
Layer 1 (Internal)    → EVOLVES: Can upgrade OTel conventions anytime
Layer 3 (Adapters)    → MAINTAINED: Platform team updates as needed
Layer 4 (CLI)         → ENHANCED: Additive changes, backward compatible
```

### Layer 0: OpenTelemetry Foundation

**Responsibilities:**
- Trace context propagation
- Span lifecycle management
- Resource attributes
- Export pipeline (processors, exporters)

**Components Used:**
- `opentelemetry-api` - Tracer, Span, Context APIs
- `opentelemetry-sdk` - TracerProvider, SpanProcessor
- `opentelemetry-exporter-otlp-proto-grpc` - OTLP export

**Rule:** Our SDK never replaces these, only configures and uses them.

---

### Layer 1: Standards Implementation (OTel GenAI Conventions)

This layer implements **official OpenTelemetry GenAI semantic conventions** internally, ensuring maximum backend compatibility while remaining invisible to developers.

#### Why OTel GenAI Conventions?

**Standards-based approach gives us:**
- ✅ **Backend compatibility** - Backends adopting `gen_ai.*` work with zero mapping
- ✅ **Future-proof** - As OTel evolves, we upgrade internally without API changes
- ✅ **Exit strategy** - Built on standards, not proprietary formats
- ✅ **Community** - Benefit from OTel ecosystem tools and best practices

**Official OTel GenAI specification:** https://opentelemetry.io/docs/specs/semconv/gen-ai/

#### OTel Span Types (What Backends See)

Our SDK creates these standard OTel span types internally:

| OTel Span Type | gen_ai.operation.name | SpanKind | Description |
|----------------|----------------------|----------|-------------|
| **Inference** | `"chat"` or `"text_completion"` | CLIENT | LLM API calls for completions |
| **Embeddings** | `"embeddings"` | CLIENT | Embedding/vectorization requests |
| **Execute Tool** | (tool-specific) | CLIENT/INTERNAL | Function/tool executions |

**Span Naming Convention (OTel Standard):**
```
{gen_ai.operation.name} {gen_ai.request.model}
Examples: "chat gpt-4o", "embeddings text-embedding-ada-002"
```

#### OTel GenAI Attributes (Internal Representation)

These are the **actual attributes** written to spans:

##### Core Attributes (Required - All Spans)

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.operation.name` | string | Operation type | `"chat"`, `"embeddings"`, `"text_completion"` |
| `gen_ai.system` | string | GenAI system identifier | `"openai"`, `"anthropic"`, `"llama_cpp"` |
| `gen_ai.request.model` | string | Model identifier | `"gpt-4o"`, `"llama-3.2-3b-instruct"` |

##### Inference Request Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.request.temperature` | float | Sampling temperature | `0.7` |
| `gen_ai.request.max_tokens` | int | Max completion tokens | `1024` |
| `gen_ai.request.top_p` | float | Nucleus sampling | `0.9` |
| `gen_ai.request.top_k` | int | Top-K sampling | `40` |
| `gen_ai.request.frequency_penalty` | float | Frequency penalty | `0.5` |
| `gen_ai.request.presence_penalty` | float | Presence penalty | `0.0` |

##### Inference Response Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.response.id` | string | Response identifier | `"chatcmpl-abc123"` |
| `gen_ai.response.model` | string | Actual model used | `"gpt-4o-2024-05-13"` |
| `gen_ai.response.finish_reasons` | string[] | Completion reasons | `["stop"]` |
| `gen_ai.usage.input_tokens` | int | Input tokens consumed | `150` |
| `gen_ai.usage.output_tokens` | int | Output tokens generated | `75` |

##### Tool/Function Calling Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.tool.name` | string | Tool identifier | `"web_search"`, `"calculator"` |

##### Embeddings Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.request.embedding_format` | string | Encoding format | `"float"`, `"base64"` |
| `gen_ai.embeddings.dimension.count` | int | Vector dimensions | `1536` |

##### Custom Extensions (Our Organization-Specific Attributes)

We extend OTel with our own namespace for domain-specific needs:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `company.llm.session_id` | string | Session/conversation ID | UUID or user-defined |
| `company.llm.workflow_type` | string | Workflow category | `"agent"`, `"rag"`, `"chain"` |
| `company.llm.cost_center` | string | Billing/chargeback code | `"eng-platform"` |
| `company.llm.prompt.template_id` | string | Prompt template ID | `"k8s_log_analysis_v1"` |
| `company.llm.prompt.template_hash` | string | Template content hash | `"a3f8d92c"` |
| `company.retriever.source` | string | Data source (for RAG) | `"pinecone"`, `"loki"` |
| `company.retriever.type` | string | Retrieval method | `"vector"`, `"keyword"` |

**Namespace Rule:** All custom attributes use `company.*` prefix to avoid conflicts with OTel standards.

#### Event-Based Content Capture (Privacy-First)

**Prompts and completions are captured as EVENTS, not span attributes:**

```python
# Event name: "gen_ai.content.prompt"
# Attributes:
{
    "gen_ai.prompt.id": "prompt-123",
    "gen_ai.prompt.text": "[User prompt content]"  # Opt-in only
}

# Event name: "gen_ai.content.completion"
# Attributes:
{
    "gen_ai.completion.id": "completion-456",
    "gen_ai.completion.text": "[LLM response]"  # Opt-in only
}
```

**Benefits:**
- ✅ Separate retention policies (1 day for events, 30 days for traces)
- ✅ Independent sampling (sample 1% of content, 100% of operational metadata)
- ✅ Privacy-first (opt-in required via `capture_content=True` or env var)

#### Span Lifecycle & SpanKind

**SpanKind Selection:**
```python
# For remote LLM API calls (OpenAI, Anthropic, etc.)
SpanKind.CLIENT

# For local model execution (llama.cpp running in-process)
SpanKind.INTERNAL
```

**Span Naming:**
```python
# Format: "{operation} {model}"
span_name = f"{operation_name} {model}"
# Examples: "chat gpt-4o", "embeddings text-embedding-ada-002"
```

---

### Layer 2: Developer-Facing API (STABLE Public Contract)

This is the **stable interface** that developers use. Changes here require major version bumps.

#### Design Goals

- **Stability** - This API is sacred, versioned strictly with SemVer
- **Intuitive** - Domain-specific decorators that match LLM patterns
- **Declarative** - Describe intent, SDK handles implementation
- **Automatic** - Context propagation, nesting, cleanup all invisible

#### The Dual-Layer Promise

```
Developer writes:         @observe.llm(name="analyze", model="gpt-4o")
                                     ↓
SDK internally creates:   Span with gen_ai.operation.name="chat"
                         Span name: "chat gpt-4o"
                         SpanKind: CLIENT
                         Attributes: gen_ai.request.model="gpt-4o", etc.
                                     ↓
Backend receives:        Standard OTel GenAI span (works everywhere)
```

**Key Insight:** Developers never see `gen_ai.*` attributes. They use friendly decorators.

#### API Surface

##### 1. Decorators (Primary Pattern)

```python
from llm_observability import observe

# ═══════════════════════════════════════════════════════════════════
# Decorator: @observe.llm() - For LLM inference calls
# ═══════════════════════════════════════════════════════════════════
@observe.llm(
    name="analyze_logs",           # User-friendly label (company.llm.operation_label)
    model="gpt-4o",                # → gen_ai.request.model
    provider="openai",             # → gen_ai.system
    temperature=0.7,               # → gen_ai.request.temperature
    capture_content=False          # Privacy: opt-in for prompts/completions
)
def call_llm(prompt: str) -> str:
    response = openai.chat.completions.create(...)

    # SDK automatically:
    # 1. Creates span: "chat gpt-4o" (SpanKind.CLIENT)
    # 2. Sets gen_ai.operation.name="chat"
    # 3. Captures token usage (gen_ai.usage.input_tokens, output_tokens)
    # 4. If capture_content=True, emits events for prompt/completion

    return response.choices[0].message.content


# ═══════════════════════════════════════════════════════════════════
# Decorator: @observe.agent() - For agent workflows
# ═══════════════════════════════════════════════════════════════════
@observe.agent(
    name="support_agent",          # User-friendly label
    agent_type="react",            # → company.llm.agent_type (custom extension)
    tools=["search", "calculator"] # → company.llm.agent_tools (custom extension)
)
def run_agent(query: str) -> dict:
    # SDK creates:
    # - Regular OTel span (SpanKind.INTERNAL, name="support_agent")
    # - Custom attributes for agent metadata
    # - Child spans (llm, tool calls) nest automatically

    results = search_web(query)    # ← Nested tool span
    answer = call_llm(results)     # ← Nested LLM span
    return answer


# ═══════════════════════════════════════════════════════════════════
# Decorator: @observe.tool() - For tool/function calls
# ═══════════════════════════════════════════════════════════════════
@observe.tool(name="web_search")
def search_web(query: str) -> list[dict]:
    results = search_api.query(query)

    # SDK creates:
    # - Execute tool span (gen_ai.tool.name="web_search")
    # - Captures input/output (optional, privacy-controlled)

    return results


# ═══════════════════════════════════════════════════════════════════
# Decorator: @observe.retriever() - For RAG retrieval operations
# ═══════════════════════════════════════════════════════════════════
@observe.retriever(
    name="log_search",
    retriever_type="keyword",      # → company.retriever.type (custom)
    source="loki"                  # → company.retriever.source (custom)
)
def search_logs(query: str, limit: int = 10) -> list[dict]:
    # SDK creates:
    # - Regular span for the retrieval operation
    # - If embedding is involved, creates gen_ai.operation.name="embeddings" span
    # - Database operations use db.* semantic conventions

    return loki.query(query, limit=limit)


# ═══════════════════════════════════════════════════════════════════
# Decorator: @observe.embeddings() - For embedding generation
# ═══════════════════════════════════════════════════════════════════
@observe.embeddings(
    model="text-embedding-ada-002",  # → gen_ai.request.model
    provider="openai"                 # → gen_ai.system
)
def generate_embedding(text: str) -> list[float]:
    response = openai.embeddings.create(model="text-embedding-ada-002", input=text)

    # SDK creates:
    # - Span: "embeddings text-embedding-ada-002" (SpanKind.CLIENT)
    # - gen_ai.operation.name="embeddings"
    # - gen_ai.embeddings.dimension.count (auto-detected)

    return response.data[0].embedding
```

**Decorator Mapping Summary:**

| Decorator | Internal OTel Span Type | gen_ai.operation.name | SpanKind |
|-----------|------------------------|-----------------------|----------|
| `@observe.llm()` | Inference | `"chat"` or `"text_completion"` | CLIENT |
| `@observe.embeddings()` | Embeddings | `"embeddings"` | CLIENT |
| `@observe.tool()` | Execute Tool | (tool-specific) | CLIENT/INTERNAL |
| `@observe.agent()` | Regular span | N/A (not a GenAI operation) | INTERNAL |
| `@observe.retriever()` | Regular span + maybe embeddings | Mixed | varies |

##### 2. Context Managers (Explicit Spans)

```python
# For operations that don't fit decorator pattern
with observe.span(
    "llm.workflow",
    name="multi_step_analysis"
) as span:
    # Step 1
    logs = retrieve_logs()
    span.set_attribute("workflow.step", "retrieve")

    # Step 2
    analysis = analyze(logs)
    span.set_attribute("workflow.step", "analyze")

    # Step 3
    report = generate_report(analysis)
    span.set_attribute("workflow.step", "report")

# Prompt registry pattern
with observe.prompt_render(
    template_id="k8s_log_analysis_v1",
    variables={"logs": logs, "namespace": "default"}
) as prompt:
    rendered = prompt.render()
    # Hash tracking happens automatically
```

##### 3. Manual Instrumentation (Escape Hatch)

```python
# For fine-grained control
span = observe.start_span(
    "llm.call",
    name="streaming_llm_call",
    attributes={
        "llm.model": "gpt-4o",
        "llm.streaming": True
    }
)

try:
    for chunk in stream_llm():
        process(chunk)
    span.set_attribute("llm.usage.completion_tokens", token_count)
finally:
    span.end()
```

##### 4. Async Support

```python
@observe.llm(name="async_call", model="gpt-4o")
async def async_llm_call(prompt: str) -> str:
    response = await openai_async.chat.completions.create(...)
    return response.choices[0].message.content

# Context managers
async with observe.span("llm.agent", name="async_agent") as span:
    result = await agent.run(query)
```

#### Internal Behavior

When a decorator/context manager is invoked:

1. **Create OTel span** with appropriate name and kind
2. **Apply semantic contract** - set required attributes
3. **Capture function signature** - parameters as attributes (if safe)
4. **Handle context propagation** - nested spans work automatically
5. **Capture result/error** - output or exception details
6. **Never expose span objects** to user code (except escape hatch)

---

### Layer 3: Backend Adapters (Complexity Absorbers)

Backend adapters are **the entire point** of this SDK - they isolate developers from ecosystem volatility.

#### The Value of Adapters

**Without SDK:**
- 50 services all directly use Arize SDK
- Organization decides to switch to MLflow
- Result: 50 services need code changes

**With SDK:**
- 50 services use our stable decorator API
- Platform team updates ONE adapter
- Result: Zero service-level changes

**Cost:** Platform team maintains 3-5 adapters < Cost of rewriting 50+ services

#### Multi-Backend Support (Migration & Redundancy)

**Critical feature:** SDK can export to multiple backends simultaneously:

```python
from llm_observability import observe
from llm_observability.adapters import OTLPAdapter, ArizeAdapter

observe.configure(
    adapters=[
        OTLPAdapter(
            endpoint="http://tempo:4317",
            is_primary=True  # Current production backend
        ),
        ArizeAdapter(
            endpoint="https://phoenix.arize.com:4317",
            api_key=os.getenv("ARIZE_API_KEY"),
            is_primary=False  # Testing/migration
        ),
    ],
    export_policy="all",  # Options: "all", "primary_only", "sample_secondary"
    secondary_sample_rate=0.1  # Send 10% of traffic to secondary
)
```

**Use cases:**
- ✅ **Gradual migration** - Run both backends in parallel, validate, cutover
- ✅ **A/B testing** - Compare backend capabilities side-by-side
- ✅ **Backup/redundancy** - If primary fails, secondary captures data
- ✅ **Data export** - Send subset to expensive backend, full data to cheap storage

#### Adapter Responsibilities

Because we use `gen_ai.*` attributes internally, adapters are much simpler:

1. **Endpoint configuration** - Set OTLP endpoint URL
2. **Authentication** - Headers, API keys, tokens
3. **Minimal attribute mapping** - Only for backends that don't support `gen_ai.*` yet
4. **Resource attributes** - Add backend-specific metadata

#### MLflow Adapter (Simplest - Full OTel Support)

**Target:** MLflow Tracking
**Protocol:** OTLP (HTTP)
**Conventions:** OTel GenAI (native support)

```python
from llm_observability.adapters import MLflowAdapter

adapter = MLflowAdapter(
    tracking_uri="http://mlflow:5000",
    experiment_name="log-analyzer-dev"
)

observe.configure(adapter=adapter)
```

**Attribute Mapping:**

| Internal (gen_ai.*) | MLflow (gen_ai.*) | Mapping Needed? |
|---------------------|-------------------|-----------------|
| `gen_ai.request.model` | `gen_ai.request.model` | ❌ Pass-through |
| `gen_ai.usage.input_tokens` | `gen_ai.usage.input_tokens` | ❌ Pass-through |
| `gen_ai.operation.name` | `gen_ai.operation.name` | ❌ Pass-through |

**Implementation (~50 lines):**
- Almost pure pass-through - MLflow speaks `gen_ai.*` natively!
- Configure experiment/run context
- Add MLflow resource attributes

#### Custom OTLP Adapter (Default - Zero Mapping)

**Target:** Any OTLP-compatible backend (Tempo, Jaeger, Honeycomb, etc.)
**Protocol:** OTLP (gRPC or HTTP)
**Conventions:** OTel GenAI (unchanged)

```python
from llm_observability.adapters import OTLPAdapter

adapter = OTLPAdapter(
    endpoint="http://tempo.logging.svc.cluster.local:4317",
    protocol="grpc",
    headers={"x-custom-header": "value"}
)

observe.configure(adapter=adapter)
```

**Implementation (~40 lines):**
- **100% pass-through** - no attribute mapping needed
- Configurable endpoint, protocol, headers
- This is the "reference implementation"

#### Arize Phoenix Adapter (Moderate Complexity)

**Target:** Arize Phoenix / Arize Platform
**Protocol:** OTLP (gRPC or HTTP)
**Conventions:** OpenInference (partial `gen_ai.*` support in 2024)

```python
from llm_observability.adapters import ArizeAdapter

adapter = ArizeAdapter(
    endpoint="https://phoenix.arize.com:4317",
    api_key="your-api-key",
    project_name="log-analyzer"
)

observe.configure(adapter=adapter)
```

**Attribute Mapping:**

Phoenix supports some `gen_ai.*` attributes natively, others need translation to OpenInference:

| Internal (gen_ai.*) | Phoenix (OpenInference) | Mapping Needed? |
|---------------------|-------------------------|-----------------|
| `gen_ai.request.model` | `llm.model_name` | ✅ Simple rename |
| `gen_ai.usage.input_tokens` | `llm.token_count.prompt` | ✅ Simple rename |
| `gen_ai.operation.name` | (inferred from span) | ❌ Structural |
| `gen_ai.tool.name` | `tool.name` | ✅ Prefix change |

**Implementation (~100 lines):**
- Map `gen_ai.*` → OpenInference where needed
- Pass-through for attributes Phoenix already supports
- Add Arize-specific resource attributes (project_name, etc.)

**Note:** As Arize adopts more `gen_ai.*` standards, this adapter gets simpler over time!

---

### Layer 4: CLI Tooling (Developer & Platform Experience)

The CLI is the **secret weapon** for making backend migrations seamless.

#### Why CLI Tooling Matters

**Problem:** Backend configuration requires:
- API keys/endpoints in code or environment variables
- Manual testing of connections
- Complex migration procedures
- No visibility into what's configured

**Solution:** Centralized CLI tool for all observability configuration.

#### Core CLI Commands

##### 1. Initialize Configuration

```bash
# Interactive setup (first-time user)
$ observe-cli init
? Which observability backend?
  ❯ MLflow
    Arize Phoenix
    Custom OTLP
    Multiple backends

? MLflow tracking URI: http://mlflow.company.internal:5000
? Experiment name: my-service-dev
? Capture prompt/completion content? (No - privacy-first default)
✓ Configuration saved to ~/.observe/config.yaml

# Generated config file:
# ~/.observe/config.yaml
backends:
  primary:
    type: mlflow
    tracking_uri: http://mlflow.company.internal:5000
    experiment_name: my-service-dev
privacy:
  capture_content: false
```

##### 2. Validate Configuration

```bash
# Test connection to configured backends
$ observe-cli validate
✓ Connecting to MLflow at http://mlflow.company.internal:5000
✓ Testing OTLP export...
✓ Creating test span...
✓ Verifying span received...
✓ All checks passed!

# Validate with specific backend
$ observe-cli validate --backend arize
✗ Connection failed: Invalid API key
  Check ARIZE_API_KEY environment variable
```

##### 3. Switch Backends (Zero Code Changes!)

```bash
# Current backend
$ observe-cli status
Primary backend: MLflow (http://mlflow.company.internal:5000)
Status: Connected ✓

# Switch to different backend
$ observe-cli configure --backend arize
? Arize endpoint: https://phoenix.arize.com:4317
? API key: [from env: ARIZE_API_KEY]
? Project name: log-analyzer
✓ Configuration updated
✓ Validating connection...
✓ Backend switched to Arize Phoenix

# Restart your service - it now uses Arize (no code changes!)
```

##### 4. Multi-Backend Setup (Migration Mode)

```bash
# Enable dual export for gradual migration
$ observe-cli configure --multi-backend
Primary backend (current production): MLflow
Secondary backend (migration target):
  ❯ Arize Phoenix
    Datadog
    Custom OTLP

? Sample rate for secondary (0.0-1.0): 0.1  # Send 10% to new backend
? Export policy:
  ❯ all              # Send all data to both
    primary_only     # Only primary for now
    sample_secondary # Sample to secondary

✓ Multi-backend export enabled
  Primary: MLflow (100% of traffic)
  Secondary: Arize (10% sampled)

# Generated config:
backends:
  adapters:
    - type: mlflow
      is_primary: true
      tracking_uri: http://mlflow:5000
    - type: arize
      is_primary: false
      endpoint: https://phoenix.arize.com:4317
      api_key: ${ARIZE_API_KEY}
  export_policy: sample_secondary
  secondary_sample_rate: 0.1
```

##### 5. Export & Migrate Data

```bash
# Export traces from current backend
$ observe-cli export-traces \
    --backend mlflow \
    --start-date 2026-01-01 \
    --end-date 2026-01-07 \
    --output traces_backup.json
✓ Exported 12,543 traces

# Import to new backend
$ observe-cli import-traces \
    --backend arize \
    --input traces_backup.json
✓ Imported 12,543 traces to Arize
```

##### 6. List Supported Backends

```bash
$ observe-cli backends
Supported backends:
  mlflow          - MLflow Tracking (native gen_ai.* support)
  arize           - Arize Phoenix (OpenInference + partial gen_ai.*)
  otlp            - Generic OTLP endpoint (Tempo, Jaeger, etc.)
  datadog         - Datadog APM
  custom          - Custom adapter (bring your own)

Install additional adapters:
  $ pip install observe-sdk-backend-langsmith
```

#### Environment Variable Support

CLI respects environment variables for automation:

```bash
# Configuration via env vars (CI/CD, containers)
export OBSERVE_BACKEND_TYPE=mlflow
export OBSERVE_MLFLOW_URI=http://mlflow:5000
export OBSERVE_EXPERIMENT_NAME=ci-tests
export OBSERVE_CAPTURE_CONTENT=false

# CLI commands use these automatically
$ observe-cli validate  # Uses env var config
✓ MLflow connection validated
```

#### SDK Auto-Configuration

SDK reads from CLI-generated config:

```python
# In your application code - NO HARDCODED BACKENDS!
from llm_observability import observe

# Reads ~/.observe/config.yaml (generated by CLI)
observe.auto_configure()

# Or explicit file path
observe.configure_from_file("~/.observe/config.yaml")

# Application code never mentions backends directly!
@observe.llm(name="analyze", model="gpt-4o")
def my_function():
    ...
```

#### Benefits Summary

✅ **Zero code changes** for backend migrations
✅ **Centralized configuration** - one file, one source of truth
✅ **Interactive setup** - friendly UX for new developers
✅ **Validation tooling** - catch config errors before deploy
✅ **Migration support** - export/import, dual backends, sampling
✅ **Automation-friendly** - environment variable support for CI/CD

---

## Package Structure

```
llm-observability-sdk/
├── pyproject.toml
├── README.md
├── SEMANTICS.md                    # Semantic contract specification (OTel GenAI)
├── LICENSE
├── src/
│   └── llm_observability/
│       ├── __init__.py             # Public API exports
│       ├── version.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── observer.py         # Main observe object
│       │   ├── decorators.py       # @observe.llm, @observe.agent, etc.
│       │   ├── context.py          # Context managers
│       │   ├── span_builder.py     # Span creation (gen_ai.* attributes)
│       │   ├── events.py           # Event emission (prompts/completions)
│       │   └── attributes.py       # Attribute management
│       │
│       ├── semantic/
│       │   ├── __init__.py
│       │   ├── contract.py         # OTel GenAI attribute constants
│       │   ├── extensions.py       # company.* custom attributes
│       │   ├── span_kinds.py       # SpanKind mappings
│       │   └── validation.py       # Contract validation
│       │
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py             # BackendAdapter base class
│       │   ├── otlp.py             # OTLPAdapter (default, zero mapping)
│       │   ├── mlflow.py           # MLflowAdapter (minimal mapping)
│       │   ├── arize.py            # ArizeAdapter (gen_ai → OpenInference)
│       │   └── multi.py            # MultiBackendAdapter (parallel export)
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py         # Configuration management
│       │   ├── loader.py           # Load from ~/.observe/config.yaml
│       │   └── env.py              # Environment variable handling
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py             # CLI entry point (observe-cli)
│       │   ├── commands/
│       │   │   ├── init.py         # observe-cli init
│       │   │   ├── configure.py    # observe-cli configure
│       │   │   ├── validate.py     # observe-cli validate
│       │   │   ├── status.py       # observe-cli status
│       │   │   ├── export.py       # observe-cli export-traces
│       │   │   └── backends.py     # observe-cli backends
│       │   └── interactive.py      # Interactive prompts
│       │
│       └── utils/
│           ├── __init__.py
│           ├── serialization.py    # JSON serialization, truncation
│           ├── hashing.py          # Content hashing
│           └── sanitization.py     # PII removal helpers
│
├── tests/
│   ├── unit/
│   │   ├── test_decorators.py
│   │   ├── test_span_builder.py
│   │   ├── test_attributes.py
│   │   ├── test_adapters.py
│   │   └── test_cli.py
│   ├── integration/
│   │   ├── test_mlflow_integration.py   # Full OTel support test
│   │   ├── test_arize_integration.py    # Attribute mapping test
│   │   ├── test_otlp_export.py
│   │   └── test_multi_backend.py
│   └── fixtures/
│       └── mock_backends.py
│
└── examples/
    ├── basic_usage.py
    ├── agent_instrumentation.py
    ├── async_example.py
    ├── multi_backend_migration.py    # Gradual migration example
    └── backends/
        ├── mlflow_example.py
        └── arize_example.py
```

### Key Files

#### `src/llm_observability/__init__.py`

```python
"""LLM Observability SDK - OpenTelemetry-based LLM telemetry."""

from llm_observability.core.observer import observe
from llm_observability.adapters import (
    OTLPAdapter,
    ArizeAdapter,
    MLflowAdapter,
    BackendAdapter
)
from llm_observability.version import __version__

__all__ = [
    "observe",
    "OTLPAdapter",
    "ArizeAdapter",
    "MLflowAdapter",
    "BackendAdapter",
    "__version__",
]
```

#### `src/llm_observability/semantic/contract.py`

```python
"""OTel GenAI semantic conventions - our internal representation."""

from enum import Enum
from opentelemetry.trace import SpanKind

class GenAIOperation(str, Enum):
    """OTel GenAI operation types."""
    CHAT = "chat"
    TEXT_COMPLETION = "text_completion"
    EMBEDDINGS = "embeddings"

class OTelGenAIAttributes:
    """Official OpenTelemetry GenAI semantic conventions.

    Spec: https://opentelemetry.io/docs/specs/semconv/gen-ai/
    """

    # Core attributes (required)
    OPERATION_NAME = "gen_ai.operation.name"      # "chat", "embeddings", etc.
    SYSTEM = "gen_ai.system"                      # "openai", "anthropic", etc.
    REQUEST_MODEL = "gen_ai.request.model"        # Model identifier

    # Request parameters
    REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    REQUEST_TOP_P = "gen_ai.request.top_p"
    REQUEST_TOP_K = "gen_ai.request.top_k"
    REQUEST_FREQUENCY_PENALTY = "gen_ai.request.frequency_penalty"
    REQUEST_PRESENCE_PENALTY = "gen_ai.request.presence_penalty"

    # Response attributes
    RESPONSE_ID = "gen_ai.response.id"
    RESPONSE_MODEL = "gen_ai.response.model"
    RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"

    # Token usage
    USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"

    # Tool calling
    TOOL_NAME = "gen_ai.tool.name"

    # Embeddings
    EMBEDDINGS_DIMENSION = "gen_ai.embeddings.dimension.count"
    REQUEST_EMBEDDING_FORMAT = "gen_ai.request.embedding_format"


class CompanyExtensions:
    """Organization-specific custom attributes.

    These extend OTel with domain-specific needs, using company.* namespace
    to avoid conflicts with standards.
    """

    # Session/conversation tracking
    SESSION_ID = "company.llm.session_id"

    # Workflow categorization
    WORKFLOW_TYPE = "company.llm.workflow_type"  # "agent", "rag", "chain"
    OPERATION_LABEL = "company.llm.operation_label"  # User-friendly name

    # Agent-specific
    AGENT_TYPE = "company.llm.agent_type"  # "react", "plan-execute", etc.
    AGENT_ITERATIONS = "company.llm.agent_iterations"
    AGENT_TOOLS = "company.llm.agent_tools"  # JSON array

    # RAG/Retriever
    RETRIEVER_TYPE = "company.retriever.type"  # "vector", "keyword", "hybrid"
    RETRIEVER_SOURCE = "company.retriever.source"  # "pinecone", "loki", etc.
    RETRIEVER_TOP_K = "company.retriever.top_k"
    RETRIEVER_RESULTS_COUNT = "company.retriever.results_count"

    # Prompt management
    PROMPT_TEMPLATE_ID = "company.llm.prompt.template_id"
    PROMPT_TEMPLATE_VERSION = "company.llm.prompt.template_version"
    PROMPT_TEMPLATE_HASH = "company.llm.prompt.template_hash"

    # Billing/chargeback
    COST_CENTER = "company.llm.cost_center"


# Event names for content capture (opt-in)
class GenAIEvents:
    """Event types for capturing prompts/completions."""
    PROMPT = "gen_ai.content.prompt"
    COMPLETION = "gen_ai.content.completion"
```

---

## Integration Patterns

### Pattern 1: Full Decorator-Based Instrumentation

```python
from llm_observability import observe

@observe.agent(name="log_analyzer_agent", agent_type="sequential")
def analyze_logs_workflow(time_range: dict, filters: dict):

    @observe.retriever(
        name="query_loki",
        retriever_type="keyword",
        source="loki"
    )
    def query_logs(logql: str, limit: int):
        return loki_client.query(logql, limit=limit)

    @observe.llm(
        name="analyze_with_llm",
        model="gpt-4o",
        provider="openai"
    )
    def call_llm(prompt: str):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    # Workflow logic
    logs = query_logs(build_logql(filters), limit=50)
    analysis = call_llm(render_prompt(logs))
    return analysis
```

**Result:** Automatic nested span hierarchy:
```
span: llm.agent (log_analyzer_agent)
├─ span: llm.retriever (query_loki)
└─ span: llm.call (analyze_with_llm)
```

### Pattern 2: Mixed Decorator + Context Manager

```python
@observe.agent(name="support_agent")
def run_support_agent(user_query: str):

    # Explicit workflow tracking
    with observe.span("llm.workflow", name="multi_step_support") as workflow:
        workflow.set_attribute("workflow.user_query", user_query)

        # Step 1: Retrieval
        @observe.retriever(name="knowledge_search", source="pinecone")
        def search_kb(query: str):
            return pinecone.query(query, top_k=5)

        docs = search_kb(user_query)
        workflow.set_attribute("workflow.docs_retrieved", len(docs))

        # Step 2: LLM analysis
        @observe.llm(name="generate_response", model="gpt-4o")
        def generate_answer(context: list, question: str):
            prompt = f"Context: {context}\n\nQuestion: {question}"
            return openai.call(prompt)

        answer = generate_answer(docs, user_query)
        return answer
```

### Pattern 3: Prompt Registry Integration

```python
from llm_observability import observe
from llm_observability.utils import hash_content

@observe.llm(name="templated_analysis", model="gpt-4o")
def analyze_with_template(logs: list, namespace: str):

    # Explicit prompt rendering tracking
    with observe.span(
        "llm.prompt_registry",
        name="render_analysis_prompt"
    ) as prompt_span:
        template = load_template("k8s_log_analysis_v1")
        variables = {"logs": logs, "namespace": namespace}

        # Track hashes
        prompt_span.set_attribute("llm.prompt.id", template.id)
        prompt_span.set_attribute("llm.prompt.version", template.version)
        prompt_span.set_attribute("llm.prompt.template_hash",
                                   hash_content(template.content)[:8])
        prompt_span.set_attribute("llm.prompt.variables_hash",
                                   hash_content(str(variables))[:8])

        rendered = template.render(**variables)

        prompt_span.set_attribute("llm.prompt.rendered_hash",
                                   hash_content(rendered)[:8])

    # LLM call (already decorated)
    response = openai.call(rendered)
    return response
```

---

## Migration Path: log-analyzer Refactoring

### Current State

The `log-analyzer` service currently uses **manual OpenTelemetry span creation**:

```python
# Current approach (pipeline.py, main.py)
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("analyze_logs") as span:
    span.set_attribute("namespace", namespace)
    span.set_attribute("log_limit", limit)

    with tracer.start_as_current_span("query_loki") as query_span:
        query_span.set_attribute("logql.query", logql)
        results = loki.query(logql)
        query_span.set_attribute("loki.results_count", len(results))

    with tracer.start_as_current_span("call_llm") as llm_span:
        llm_span.set_attribute("llm.model", model)
        llm_span.set_attribute("llm.streaming", True)
        response = llm_client.call(prompt)
        llm_span.set_attribute("llm.tokens_prompt", tokens)
```

### Target State (After Migration)

```python
# New approach with SDK
from llm_observability import observe

@observe.workflow(name="analyze_logs")
def analyze_logs(time_range: dict, filters: dict, limit: int = 15):

    @observe.retriever(
        name="query_loki",
        retriever_type="keyword",
        source="loki"
    )
    def query_loki_logs(logql: str, limit: int):
        results = loki.query_range(logql, limit=limit)
        # Token usage automatically captured by decorator
        return results

    @observe.llm(
        name="analyze_with_llm",
        model=config.llm_model,
        provider="llama-cpp",
        streaming=True
    )
    def call_llm(prompt: str, temperature: float):
        response = llm_client.call(
            prompt=prompt,
            temperature=temperature,
            stream=True
        )
        # Decorator handles token tracking
        return response

    # Business logic (unchanged)
    logql = build_logql_query(time_range, filters)
    logs = query_loki_logs(logql, limit=limit)

    flattened = flatten_logs(logs)
    normalized = normalize_logs(flattened)

    prompt = render_prompt(template_id="k8s_log_analysis_v1",
                           logs=normalized,
                           namespace=filters.get("namespace"))

    analysis = call_llm(prompt, temperature=0.3)
    return analysis
```

### Migration Steps

1. **Install SDK as dependency** in `log-analyzer/pyproject.toml`
2. **Configure adapter** in `log-analyzer/src/log_analyzer/observability/__init__.py`
3. **Refactor pipeline.py** - replace manual spans with decorators
4. **Refactor main.py** - decorate HTTP endpoint handlers
5. **Update tests** - verify span structure with SDK
6. **Deploy to dev** - validate against Tempo backend
7. **(Optional) Add Arize adapter** - dual-export for comparison

### Configuration (Backend Selection)

```python
# log-analyzer/src/log_analyzer/observability/__init__.py

from llm_observability import observe
from llm_observability.adapters import OTLPAdapter, ArizeAdapter
import os

# Default: OTLP to Tempo (existing setup)
if os.getenv("OBSERVABILITY_BACKEND") == "arize":
    adapter = ArizeAdapter(
        endpoint=os.getenv("ARIZE_ENDPOINT"),
        api_key=os.getenv("ARIZE_API_KEY"),
        project_name="log-analyzer"
    )
else:
    adapter = OTLPAdapter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT",
                           "http://tempo.logging.svc.cluster.local:4317"),
        protocol="grpc"
    )

observe.configure(
    adapter=adapter,
    service_name=os.getenv("LOG_ANALYZER_SERVICE_NAME", "log-analyzer"),
    service_version=os.getenv("LOG_ANALYZER_SERVICE_VERSION", "unknown"),
    deployment_environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "dev")
)
```

**Deployment Change:**
```yaml
# deployment.yaml - add optional backend config
env:
  - name: OBSERVABILITY_BACKEND
    value: "otlp"  # or "arize", "mlflow"
  # - name: ARIZE_ENDPOINT
  #   value: "https://phoenix.arize.com:4317"
  # - name: ARIZE_API_KEY
  #   valueFrom:
  #     secretKeyRef:
  #       name: arize-credentials
  #       key: api-key
```

---

## MVP Implementation Roadmap

### Phase 1: Core SDK Foundation (Week 1)

**Goal:** Minimal working SDK with OTLP export

**Deliverables:**
1. ✅ Package structure (`llm-observability-sdk/`)
2. ✅ Semantic contract definition (`semantic/contract.py`)
3. ✅ Core observer implementation (`core/observer.py`)
4. ✅ Basic decorators: `@observe.llm()`, `@observe.agent()`
5. ✅ OTLP adapter (default backend)
6. ✅ Unit tests for decorators and span creation
7. ✅ `SEMANTICS.md` documentation

**Success Criteria:**
- Can decorate a function and see spans in Tempo
- Attributes match semantic contract
- Tests pass

**Files to Create:**
```
llm-observability-sdk/
├── pyproject.toml
├── SEMANTICS.md
└── src/llm_observability/
    ├── __init__.py
    ├── core/
    │   ├── observer.py
    │   ├── decorators.py
    │   └── span_builder.py
    ├── semantic/
    │   ├── contract.py
    │   └── span_kinds.py
    ├── adapters/
    │   ├── base.py
    │   └── otlp.py
    └── utils/
        └── serialization.py
```

### Phase 2: Remaining Decorators + Context Managers (Week 1-2)

**Goal:** Complete instrumentation API surface

**Deliverables:**
1. ✅ `@observe.tool()` decorator
2. ✅ `@observe.retriever()` decorator
3. ✅ `observe.span()` context manager
4. ✅ `observe.prompt_render()` context manager
5. ✅ Async support for all decorators
6. ✅ Integration tests with mock backends

**Success Criteria:**
- All decorator types work
- Nested spans propagate context correctly
- Async/await works seamlessly

### Phase 3: Backend Adapters (Week 2)

**Goal:** Support Arize and MLflow backends

**Deliverables:**
1. ✅ Arize adapter with OpenInference mapping
2. ✅ MLflow adapter with GenAI conventions
3. ✅ Adapter configuration API
4. ✅ Integration tests against Arize Phoenix (local)
5. ✅ Integration tests against MLflow (local)

**Success Criteria:**
- Same instrumented code exports to all 3 backends
- Attributes map correctly per backend conventions
- Zero user code changes when switching backends

### Phase 4: log-analyzer Migration (Week 2-3)

**Goal:** Refactor log-analyzer to use SDK

**Deliverables:**
1. ✅ Add SDK dependency to `log-analyzer`
2. ✅ Configure OTLP adapter for Tempo
3. ✅ Refactor `pipeline.py` with decorators
4. ✅ Refactor `main.py` HTTP handlers
5. ✅ Update tests
6. ✅ Deploy to dev cluster
7. ✅ Validate spans in Grafana/Tempo

**Success Criteria:**
- Existing Grafana dashboards still work
- Span structure improved (cleaner, more semantic)
- No performance degradation
- All tests pass

### Phase 5: Documentation + Examples (Week 3)

**Goal:** Enable external adoption

**Deliverables:**
1. ✅ README with quickstart
2. ✅ `SEMANTICS.md` (semantic contract spec)
3. ✅ API documentation (docstrings + Sphinx)
4. ✅ Example: Basic LLM instrumentation
5. ✅ Example: Agent with tools
6. ✅ Example: Arize backend configuration
7. ✅ Example: MLflow backend configuration

**Success Criteria:**
- A new developer can instrument an LLM app in <10 minutes
- Backend switching is clear and documented
- Semantic contract is well-understood

---

## Open Questions & Decisions Needed

### 1. **Automatic Input/Output Capture**

**Question:** Should decorators automatically capture function inputs/outputs as span attributes?

**Options:**
- **A)** Auto-capture by default, provide `@observe.llm(capture_io=False)` opt-out
- **B)** Manual capture only, user calls `span.set_input()` / `span.set_output()`
- **C)** Smart capture based on type hints (capture primitives, skip complex objects)

**Recommendation:** Option C with opt-out flag.

**Rationale:**
- Most LLM calls have simple string/dict inputs
- Auto-capture improves DX significantly
- Type-based filtering prevents accidentally logging huge objects
- Opt-out provides safety valve

---

### 2. **PII Sanitization Strategy**

**Question:** How aggressively should we sanitize inputs/outputs for PII?

**Options:**
- **A)** No sanitization (user responsibility)
- **B)** Opt-in sanitization via `@observe.llm(sanitize=True)`
- **C)** Always sanitize, provide raw capture escape hatch

**Recommendation:** Option B.

**Rationale:**
- PII rules vary by domain (healthcare vs. logs vs. chat)
- Default-off prevents surprising behavior
- Provide `llm_observability.utils.sanitize()` helper for common patterns
- Document PII risks clearly in README

---

### 3. **Token Usage Extraction**

**Question:** How do we extract token usage from LLM responses (varies by provider)?

**Options:**
- **A)** User manually calls `observe.record_tokens(prompt=X, completion=Y)`
- **B)** SDK auto-extracts from common response shapes (OpenAI, Anthropic, etc.)
- **C)** Provider-specific extractors (pluggable)

**Recommendation:** Option B with fallback to A.

**Rationale:**
- Auto-extraction for 80% case (OpenAI, Anthropic, Llama.cpp have standard fields)
- Manual recording for custom providers or streaming edge cases
- Keep extractors simple (no provider-specific clients)

**Implementation:**
```python
# In decorator post-processing
def extract_token_usage(response: Any) -> dict[str, int] | None:
    """Extract tokens from common response shapes."""
    if hasattr(response, 'usage'):  # OpenAI-like
        return {
            'prompt': response.usage.prompt_tokens,
            'completion': response.usage.completion_tokens,
            'total': response.usage.total_tokens
        }
    elif hasattr(response, 'metadata') and 'usage' in response.metadata:  # Anthropic
        return {
            'prompt': response.metadata.usage.input_tokens,
            'completion': response.metadata.usage.output_tokens,
            'total': response.metadata.usage.input_tokens + response.metadata.usage.output_tokens
        }
    return None
```

---

### 4. **Streaming LLM Calls**

**Question:** How do we instrument streaming responses where tokens arrive incrementally?

**Options:**
- **A)** User wraps generator, manually updates span at the end
- **B)** SDK provides `observe.stream()` wrapper that auto-updates
- **C)** Decorator detects generator return type, wraps automatically

**Recommendation:** Option B (explicit wrapper).

**Rationale:**
- Streaming has different semantics (can't capture output until done)
- Explicit wrapper makes streaming behavior clear
- Allows tracking metrics like time-to-first-token

**API:**
```python
@observe.llm(name="streaming_call", model="gpt-4o")
def call_llm_streaming(prompt: str):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )

    # Wrap generator to track output
    return observe.stream(
        response,
        accumulator=lambda chunks: ''.join(c.choices[0].delta.content for c in chunks)
    )

# Usage
for chunk in call_llm_streaming("Hello"):
    print(chunk)
# Span auto-closes after iteration completes, with full output captured
```

---

### 5. **Error Handling & Failed Spans**

**Question:** How do we mark spans when LLM calls fail (rate limits, timeouts, errors)?

**Options:**
- **A)** Let exception propagate, OTel marks span as error automatically
- **B)** Catch exception, add semantic error attributes, re-raise
- **C)** Provide error categorization (rate_limit, timeout, invalid_input)

**Recommendation:** Option B + C.

**Rationale:**
- OTel's default error tracking is generic (just stack trace)
- LLM-specific error categories enable better observability (dashboards, alerts)
- Re-raising preserves normal exception flow

**Implementation:**
```python
# In decorator error handler
try:
    result = func(*args, **kwargs)
except RateLimitError as e:
    span.set_attribute("llm.error.type", "rate_limit")
    span.set_attribute("llm.error.code", str(e.status_code))
    span.set_attribute("llm.error.message", str(e))
    span.set_status(StatusCode.ERROR, "Rate limit exceeded")
    raise
except TimeoutError as e:
    span.set_attribute("llm.error.type", "timeout")
    span.set_attribute("llm.error.message", str(e))
    span.set_status(StatusCode.ERROR, "Request timeout")
    raise
```

---

## Success Metrics (Post-MVP)

### Developer Experience
- **Onboarding time:** <10 minutes from install to first trace
- **Lines of code:** <5 lines to instrument a basic LLM call
- **Decorator types:** 5-7 total (llm, agent, tool, retriever, embedding, workflow, prompt)

### Stability
- **Semantic contract churn:** <2 breaking changes per year
- **Backend adapter size:** <200 lines per adapter
- **Test coverage:** >85% for core, >70% for adapters

### Adoption (Internal)
- **log-analyzer migration:** Complete in Phase 4
- **Additional services instrumented:** 2+ by end of Q1 2026

---

## Appendix A: Semantic Contract Comparison

### Our Contract vs. OpenInference

| Concept | Our Attribute | OpenInference | Notes |
|---------|---------------|---------------|-------|
| Model name | `llm.model` | `llm.model_name` | Slight naming difference |
| Prompt tokens | `llm.usage.prompt_tokens` | `llm.token_count.prompt` | Hierarchical vs. flat |
| Input messages | `llm.input.messages` | `llm.input_messages` | Identical |
| Tool name | `llm.tool.name` | `tool.name` | Different prefix |

**Adapter Complexity:** ~20 attribute mappings in Arize adapter.

### Our Contract vs. OTel GenAI Conventions

| Concept | Our Attribute | OTel GenAI | Notes |
|---------|---------------|------------|-------|
| Model | `llm.model` | `gen_ai.request.model` | Different prefix |
| Temperature | `llm.temperature` | `gen_ai.request.temperature` | Different prefix |
| Prompt tokens | `llm.usage.prompt_tokens` | `gen_ai.usage.prompt_tokens` | Similar structure |

**Adapter Complexity:** ~15 attribute mappings in MLflow adapter.

---

## Appendix B: Technology Choices

### Why OpenTelemetry?

- ✅ Industry standard for distributed tracing
- ✅ Vendor-neutral, CNCF project
- ✅ Excellent Python SDK with auto-instrumentation
- ✅ Already deployed in our infrastructure (Tempo, Alloy)
- ✅ Future-proof (won't be deprecated)

### Why Not Build on Langchain/LlamaIndex Observability?

- ❌ Tied to specific frameworks (Langchain, LlamaIndex)
- ❌ Custom formats, not OTel-native
- ❌ Backend lock-in (LangSmith, Arize integrations are proprietary)
- ❌ We want framework-agnostic SDK

### Why Python First?

- ✅ Dominant language for LLM/ML workloads
- ✅ log-analyzer is Python
- ✅ Fast iteration for MVP
- 🔮 Future: TypeScript/JavaScript version for Node.js agents

---

## Appendix C: References

### Standards & Specifications
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [OTel GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenInference Specification](https://github.com/Arize-ai/openinference)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)

### Backend Documentation
- [Arize Phoenix OTLP Ingestion](https://docs.arize.com/phoenix/tracing/integrations/opentelemetry)
- [MLflow Tracing](https://mlflow.org/docs/latest/llms/tracing/index.html)
- [Grafana Tempo](https://grafana.com/docs/tempo/latest/)

### Inspirations
- [OpenLLMetry](https://github.com/traceloop/openllmetry) - OTel-based LLM instrumentation
- [LangSmith SDK](https://docs.smith.langchain.com/) - Proprietary but good DX patterns
- [Helicone](https://docs.helicone.ai/) - Proxy-based observability (different approach)

---

## Next Steps

1. **Review this architecture** - Gather feedback from team
2. **Make decisions** on open questions (input capture, PII, streaming)
3. **Set up SDK repository** - `llm-observability-sdk/` monorepo
4. **Start Phase 1** - Core SDK foundation (Week 1 goal)
5. **Create SEMANTICS.md** - Detailed semantic contract specification

---

**Document Owner:** Log Analyzer Team
**Last Updated:** 2026-01-10
**Status:** ✅ Ready for Implementation
