# Auto-Instrumentation Analysis & Simplified Architecture

**Version:** 1.0
**Date:** 2026-01-13
**Status:** Draft

---

## 1. Executive Summary

This document analyzes whether we can achieve our observability goals by **leveraging existing auto-instrumentation** from MLflow and Phoenix rather than building custom span creation logic.

**Key Finding:** Both MLflow and Phoenix provide mature auto-instrumentation for our target frameworks (Google ADK, Gemini, FastAPI). Our SDK can act as a **thin orchestration layer** that:

1. Provides unified configuration
2. Enables the appropriate backend's auto-instrumentation
3. Adds minimal enrichment APIs for edge cases

This approach dramatically simplifies the SDK while delivering better framework coverage.

---

## 2. Auto-Instrumentation Capabilities

### 2.1 MLflow Tracing

**Activation:**
```python
import mlflow
mlflow.openai.autolog()      # OpenAI
mlflow.anthropic.autolog()   # Anthropic
mlflow.langchain.autolog()   # LangChain
mlflow.gemini.autolog()      # Google Gemini (if available)
```

**What's Automatically Captured:**

| Category | Captured | Notes |
|----------|----------|-------|
| LLM calls | ✅ | Model, provider, operation type |
| Input messages | ✅ | Full prompt/message content |
| Output messages | ✅ | Full response content |
| Token usage | ✅ | Input, output, total tokens |
| Latency | ✅ | Per-span timing |
| Streaming | ✅ | Token-by-token capture |
| Tool calls | ✅ | Function name, arguments, results |
| Agent workflows | ✅ | Via LangChain/LangGraph autolog |
| Span hierarchy | ✅ | Automatic parent-child nesting |
| Async support | ✅ | Full async/await support |
| Error capture | ✅ | Exception type, message, trace |

**Supported Frameworks:**
- OpenAI, Anthropic, Google Gemini
- LangChain, LangGraph, LlamaIndex
- DSPy, CrewAI, AutoGen, Haystack
- Pydantic AI, Instructor

**Gaps:**
- Google ADK: Not explicitly listed (may work via Gemini integration)
- Custom enrichment: Limited to tags/attributes

---

### 2.2 Phoenix (OpenInference)

**Activation:**
```python
from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

OpenAIInstrumentor().instrument(tracer_provider=provider)
GoogleGenAIInstrumentor().instrument(tracer_provider=provider)
GoogleADKInstrumentor().instrument(tracer_provider=provider)
```

**What's Automatically Captured:**

| Category | Captured | Notes |
|----------|----------|-------|
| LLM calls | ✅ | Full OpenInference semantics |
| Input messages | ✅ | Structured message format |
| Output messages | ✅ | Structured message format |
| Token usage | ✅ | Prompt, completion, total |
| Latency | ✅ | Per-span timing |
| Streaming | ✅ | Chunk-level capture |
| Tool calls | ✅ | Name, arguments, results |
| Agent workflows | ✅ | Native Google ADK support |
| Span hierarchy | ✅ | Automatic nesting |
| Async support | ✅ | Full async support |
| Error capture | ✅ | Exception attributes |
| Retrieval (RAG) | ✅ | Document scores, content |
| Embeddings | ✅ | Vector operations |

**Supported Frameworks:**
- OpenAI, Anthropic, Google GenAI, Groq, MistralAI
- **Google ADK** ✅ (native support)
- LangChain, LlamaIndex, LangGraph
- CrewAI, AutoGen, DSPy, Haystack

**Gaps:**
- Tool definitions: Partially supported
- Cost tracking: Available but requires configuration

---

### 2.3 Feature Comparison

| Feature | MLflow | Phoenix | Our Requirement |
|---------|--------|---------|-----------------|
| Google ADK support | ⚠️ Indirect | ✅ Native | **Required** |
| Google Gemini support | ✅ | ✅ | **Required** |
| FastAPI compatibility | ✅ | ✅ | **Required** |
| Token usage | ✅ | ✅ | **Required** |
| Streaming | ✅ | ✅ | **Required** |
| Agent hierarchies | ✅ | ✅ | **Required** |
| Tool calls | ✅ | ✅ | **Required** |
| Privacy controls | ⚠️ Manual | ⚠️ Manual | Should have |
| Session tracking | ⚠️ Via tags | ⚠️ Via attributes | Should have |
| Custom enrichment | ✅ Tags | ✅ Attributes | Should have |

**Conclusion:** Both backends provide ~90% of what we need out of the box. Phoenix has better Google ADK support. MLflow has broader ecosystem integration.

---

## 3. Proposed Simplified Architecture

### 3.1 New Vision

Instead of building custom span creation, our SDK becomes a **configuration and orchestration layer**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION CODE                                   │
│                                                                             │
│   # One-line setup - that's it!                                             │
│   llmops.configure(backend="phoenix")  # or "mlflow"                        │
│                                                                             │
│   # Application code unchanged - uses Google ADK normally                   │
│   agent = Agent(model="gemini-2.0-flash", tools=[...])                     │
│   response = await agent.run("Query")                                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                    ┌─────────────────────────┐                              │
│                    │      LLM OPS SDK        │                              │
│                    │  (Orchestration Layer)  │                              │
│                    └───────────┬─────────────┘                              │
│                                │                                            │
│              ┌─────────────────┼─────────────────┐                          │
│              │                 │                 │                          │
│              ▼                 ▼                 ▼                          │
│   ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐           │
│   │ Phoenix Backend  │ │ MLflow Backend   │ │ OTLP Backend     │           │
│   │                  │ │                  │ │                  │           │
│   │ Enables:         │ │ Enables:         │ │ Enables:         │           │
│   │ • GoogleADK      │ │ • gemini.autolog │ │ • OTel exporters │           │
│   │   Instrumentor   │ │ • openai.autolog │ │                  │           │
│   │ • GoogleGenAI    │ │ • langchain...   │ │                  │           │
│   │   Instrumentor   │ │                  │ │                  │           │
│   └──────────────────┘ └──────────────────┘ └──────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Simplified Public API

```python
import llmops

# OPTION 1: Minimal configuration (recommended)
llmops.configure(
    backend="phoenix",                    # or "mlflow"
    endpoint="http://localhost:6006",     # Backend endpoint
)

# OPTION 2: Multi-backend
llmops.configure(
    backends=[
        {"type": "phoenix", "endpoint": "http://localhost:6006"},
        {"type": "mlflow", "endpoint": "http://localhost:5001"},
    ]
)

# OPTION 3: With privacy controls
llmops.configure(
    backend="phoenix",
    endpoint="http://localhost:6006",
    capture_content=False,  # Disable prompt/response capture
)
```

**That's it.** No decorators needed for basic instrumentation.

### 3.3 Optional Enrichment API

For cases where auto-instrumentation doesn't capture everything:

```python
# Add session/user context
with llmops.context(session_id="sess-123", user_id="user-456"):
    response = await agent.run("Query")

# Add custom metadata to current span
llmops.set_metadata(request_type="summarization", priority=1)

# Manual span for non-instrumented code
with llmops.span("custom-operation"):
    result = custom_processing()
```

### 3.4 What the SDK Does Internally

```python
def configure(backend: str, endpoint: str, **kwargs):
    """Configure and enable auto-instrumentation."""

    if backend == "phoenix":
        # Set up Phoenix with OpenInference instrumentors
        from phoenix.otel import register
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        tracer_provider = register(endpoint=endpoint)
        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)

    elif backend == "mlflow":
        # Set up MLflow tracing
        import mlflow
        mlflow.set_tracking_uri(endpoint)
        mlflow.gemini.autolog()
        mlflow.langchain.autolog()
        # ... other autologs as needed

    elif backend == "otlp":
        # Generic OTLP setup
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        # ... standard OTel setup
```

---

## 4. Developer Experience Comparison

### 4.1 Current Design (Custom Instrumentation)

```python
import llmops
from google.adk import Agent

llmops.configure(...)

@llmops.agent(name="research")
async def research(query: str):
    llmops.set_input(query)

    agent = Agent(model="gemini-2.0-flash")

    @llmops.llm(model="gemini-2.0-flash")  # Decorator on internal call?
    async def call_llm():
        llmops.set_input(...)
        response = await agent.generate(...)
        llmops.set_output(response)
        llmops.set_tokens(...)
        return response

    result = await call_llm()
    llmops.set_output(result)
    return result
```

**Problems:**
- Verbose: 10+ lines of instrumentation code
- Intrusive: Must wrap every LLM call
- Redundant: Re-implementing what backends already do
- Fragile: Tightly coupled to application structure

### 4.2 Proposed Design (Auto-Instrumentation)

```python
import llmops
from google.adk import Agent

llmops.configure(backend="phoenix", endpoint="http://localhost:6006")

async def research(query: str):
    agent = Agent(model="gemini-2.0-flash")
    response = await agent.run(query)
    return response
```

**Benefits:**
- Minimal: 1 line of setup
- Non-intrusive: Zero changes to application code
- Complete: Full trace hierarchy captured automatically
- Robust: Leverages battle-tested instrumentation

---

## 5. Gap Analysis

### 5.1 What Auto-Instrumentation Handles

| Requirement (from PRD) | Auto-Instrumented? |
|------------------------|-------------------|
| F1: Semantic boundaries | ✅ Automatic |
| F2: Input/output/tokens | ✅ Automatic |
| F3: OTel GenAI spans | ✅ Automatic |
| F4: YAML configuration | ⚠️ We add this |
| F5: Multiple backends | ⚠️ We add this |
| F6: Custom attributes | ⚠️ Via enrichment API |
| F7: Streaming chunks | ✅ Automatic |
| F8: Session tracking | ⚠️ Via enrichment API |

### 5.2 What We Still Need to Build

| Component | Purpose | Complexity |
|-----------|---------|------------|
| **Configuration loader** | YAML + env vars | Low |
| **Backend orchestrator** | Enable right instrumentors | Low |
| **Context manager** | Session/user tracking | Low |
| **Metadata enrichment** | Custom attributes | Low |
| **Privacy filter** | Content redaction | Medium |
| **Multi-backend router** | Fan-out to multiple backends | Medium |

### 5.3 Privacy Considerations

Auto-instrumentation captures **everything** by default. We need to add:

```python
llmops.configure(
    backend="phoenix",
    privacy={
        "capture_content": False,      # Redact prompts/responses
        "capture_tokens": True,        # Keep token counts
        "redact_patterns": [r"\b\d{3}-\d{2}-\d{4}\b"],  # SSN pattern
    }
)
```

This would require a **SpanProcessor** that filters attributes before export.

---

## 6. Implementation Roadmap

### Phase 1: Core Orchestration (POC)

```
llmops/
├── __init__.py           # Public API
├── config.py             # YAML + env configuration
├── backends/
│   ├── phoenix.py        # Enable Phoenix instrumentors
│   ├── mlflow.py         # Enable MLflow autolog
│   └── otlp.py           # Generic OTLP setup
└── context.py            # Session/metadata enrichment
```

**Deliverables:**
- `llmops.configure(backend=..., endpoint=...)`
- Automatic instrumentor activation
- YAML configuration support

### Phase 2: Enrichment & Privacy

```
llmops/
├── enrichment.py         # set_metadata(), context()
├── privacy/
│   ├── processor.py      # SpanProcessor for filtering
│   └── patterns.py       # PII detection patterns
```

**Deliverables:**
- `llmops.set_metadata()`
- `llmops.context()` for session tracking
- Privacy filtering SpanProcessor

### Phase 3: Multi-Backend & Advanced

```
llmops/
├── router.py             # Multi-backend span routing
├── validation.py         # Strict mode for CI
```

**Deliverables:**
- Multiple simultaneous backends
- Validation mode for development

---

## 7. Decision Matrix

| Approach | Dev Experience | Coverage | Maintenance | Risk |
|----------|---------------|----------|-------------|------|
| **Custom instrumentation** | Medium | Partial | High | Medium |
| **Auto-instrumentation wrapper** | Excellent | Full | Low | Low |
| **Hybrid (auto + decorators)** | Good | Full | Medium | Low |

**Recommendation:** Auto-instrumentation wrapper with optional enrichment APIs.

---

## 8. Open Questions

| # | Question | Recommendation |
|---|----------|----------------|
| 1 | Should we support both Phoenix AND MLflow simultaneously? | Yes, for migration flexibility |
| 2 | How do we handle privacy when using auto-instrumentation? | SpanProcessor that redacts before export |
| 3 | Do we need decorators at all? | Only for non-instrumented code paths |
| 4 | What about frameworks without auto-instrumentation? | Provide manual span API as fallback |

---

## 9. Next Steps

1. **Validate Google ADK coverage** — Test Phoenix's GoogleADKInstrumentor with real agent code
2. **Prototype configuration layer** — Build minimal `llmops.configure()`
3. **Test multi-backend** — Verify spans can be sent to both Phoenix and MLflow
4. **Design privacy processor** — Spec out content filtering approach
5. **Update PRD** — Reflect simplified architecture

---

## 10. Related Documents

| Document | Purpose |
|----------|---------|
| [PRD](./PRD.md) | Requirements (needs update) |
| [Reference Architecture](./REFERENCE_ARCHITECTURE.md) | Technical patterns (needs revision) |
| [API Specification](./API_SPECIFICATION.md) | Public API (needs simplification) |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-13
