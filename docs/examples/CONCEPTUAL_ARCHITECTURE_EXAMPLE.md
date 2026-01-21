# LLM Observability SDK — Conceptual Architecture

**Version:** 1.0
**Date:** 2026-01-13
**Status:** Draft

---

## 1. Overview

This document provides a visual understanding of the LLM Observability SDK architecture. It describes **what the system looks like** and **how pieces relate**, not implementation details.

---

## 2. Core Concept: Two Paths to Observability

The SDK provides two instrumentation modes that can be used independently or together:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION CODE                                  │
│                                                                         │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────┐│
│  │   AUTO-INSTRUMENTATION      │    │   MANUAL INSTRUMENTATION        ││
│  │   (Quick Start)             │    │   (Fine-grained Control)        ││
│  │                             │    │                                 ││
│  │   import llmops             │    │   @llmops.llm(model="gpt-4o")  ││
│  │   llmops.init()             │    │   async def generate(prompt):  ││
│  │                             │    │       llmops.set_input(prompt) ││
│  │   # That's it! LLM calls    │    │       ...                      ││
│  │   # automatically traced    │    │       llmops.set_output(result)││
│  │                             │    │       return result            ││
│  └─────────────────────────────┘    └─────────────────────────────────┘│
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                    ┌─────────────────────┐                             │
│                    │   LLM OPS SDK       │  ← Stable API               │
│                    │   (This Project)    │                             │
│                    └──────────┬──────────┘                             │
│                               │                                         │
│              Translates to OTel GenAI conventions                       │
│                               │                                         │
│                    ┌──────────▼──────────┐                             │
│                    │   OpenTelemetry     │  ← Industry Standard        │
│                    │   (Unchanged)       │                             │
│                    └──────────┬──────────┘                             │
│                               │                                         │
├───────────────────────────────┼─────────────────────────────────────────┤
│                               │                                         │
│         ┌─────────────────────┴─────────────────────┐                  │
│         │                                           │                  │
│         ▼                                           ▼                  │
│   ┌──────────┐                               ┌──────────┐              │
│   │  Arize   │                               │  MLflow  │              │
│   │  Phoenix │                               │          │              │
│   └──────────┘                               └──────────┘              │
│                                                                         │
│              PRIMARY BACKENDS (Auto-instrumentation)                    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Insight:** The SDK provides a quick on-ramp via auto-instrumentation while preserving the option for fine-grained manual control.

---

## 3. SDK Layer Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 5: Public API                                                    │
│  ─────────────────────────────────────────────────────────────────────  │
│  • Initialization: init()                                               │
│  • Decorators: @llmops.llm(), @llmops.tool(), @llmops.agent()          │
│  • Enrichment: set_input(), set_output(), set_tokens()                 │
│                                                                         │
│  STABILITY: ████████████████████████████████████████  STABLE           │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 4: Auto-instrumentation                                          │
│  ─────────────────────────────────────────────────────────────────────  │
│  • Backend instrumentor orchestration                                   │
│  • Phoenix: OpenInference instrumentors                                 │
│  • MLflow: Native tracing instrumentors                                 │
│                                                                         │
│  STABILITY: ████████████████████████████████████████  STABLE           │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 3: Semantic Model                                                │
│  ─────────────────────────────────────────────────────────────────────  │
│  • SemanticKind enum (LLM_GENERATE, TOOL_CALL, etc.)                   │
│  • Span lifecycle management                                            │
│  • Context propagation                                                  │
│                                                                         │
│  STABILITY: ████████████████████████░░░░░░░░░░░░░░░░  STABLE (contract)│
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 2: OTel GenAI Mapping                                            │
│  ─────────────────────────────────────────────────────────────────────  │
│  • Translates SemanticKind → gen_ai.* attributes                       │
│  • Creates OTel spans and events                                        │
│  • Maps to OTel SpanKind (CLIENT, INTERNAL)                            │
│                                                                         │
│  STABILITY: ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  INTERNAL        │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 1: Backend Adapters                                              │
│  ─────────────────────────────────────────────────────────────────────  │
│  • OTLPAdapter (pass-through)                                           │
│  • MLflowAdapter (pass-through)                                         │
│  • ArizeAdapter (OpenInference translation)                             │
│                                                                         │
│  STABILITY: ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  MAINTAINED       │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 0: OpenTelemetry Foundation                                      │
│  ─────────────────────────────────────────────────────────────────────  │
│  • TracerProvider, Spans, Context                                       │
│  • Exporters (OTLP gRPC/HTTP)                                          │
│  • NOT modified by this SDK                                             │
│                                                                         │
│  STABILITY: ████████████████████████████████████████  EXTERNAL         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Flow

### 4.1 Auto-Instrumentation Flow (Quick Start)

```
    Application startup              SDK initializes            Backend receives
    ───────────────────              ──────────────            ─────────────────

    import llmops
    llmops.init()
            │
            ▼
    ┌───────────────────┐     ┌───────────────────┐
    │ Load config from  │────▶│ Detect backend    │
    │ llmops.yaml       │     │ (phoenix/mlflow)  │
    └───────────────────┘     └────────┬──────────┘
                                       │
                                       ▼
                              ┌───────────────────┐
                              │ Initialize OTel   │
                              │ TracerProvider    │
                              └────────┬──────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            │ Phoenix                                   MLflow   │
            ▼                                                    ▼
    ┌───────────────────┐                          ┌───────────────────┐
    │ OpenInference     │                          │ MLflow tracing    │
    │ instrumentors     │                          │ auto-instrument   │
    │ (OpenAI, etc.)    │                          │ (OpenAI, etc.)    │
    └────────┬──────────┘                          └────────┬──────────┘
             │                                              │
             └──────────────────────┬───────────────────────┘
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────────────┐
    │  APPLICATION CODE (no changes needed!)                                 │
    │                                                                        │
    │    response = openai.chat.completions.create(...)  ◀── Auto-traced   │
    │    result = anthropic.messages.create(...)         ◀── Auto-traced   │
    │    chain.invoke(...)                               ◀── Auto-traced   │
    │                                                                        │
    └───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │ Spans sent   │
                            │ to backend   │
                            └──────────────┘
```

### 4.2 Manual Instrumentation Flow (Fine-grained Control)

```
    Developer writes code          SDK processes              Backend receives
    ──────────────────────        ──────────────            ─────────────────

    @llmops.llm(model="gpt-4o")
    async def generate(prompt):
            │
            ▼
    ┌───────────────────┐
    │ Decorator creates │
    │ semantic span     │───────────────────────────────────────┐
    └───────────────────┘                                       │
            │                                                   │
            ▼                                                   │
    llmops.set_input(prompt)                                   │
            │                                                   │
            ▼                                                   │
    ┌───────────────────┐                                       │
    │ Enrichment call   │                                       │
    │ attaches to span  │───────────────────────────────────────┤
    └───────────────────┘                                       │
            │                                                   │
            ▼                                                   │
    response = await openai...                                  │
            │                                                   │
            ▼                                                   │
    llmops.set_output(result)                                  │
    llmops.set_tokens(...)                                     │
            │                                                   │
            ▼                                                   │
    ┌───────────────────┐     ┌───────────────────┐     ┌──────▼────────┐
    │ Function returns  │────▶│ Span closes       │────▶│ Span exported │
    │                   │     │ OTel attributes   │     │ to backend    │
    └───────────────────┘     └───────────────────┘     └───────────────┘
```

### 4.3 Configuration Flow

```
    ┌──────────────────┐
    │  YAML Config     │
    │  (llmops.yaml)   │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐     ┌──────────────────┐
    │  Environment     │────▶│  Configuration   │
    │  Variables       │     │  Loader          │
    └──────────────────┘     └────────┬─────────┘
                                      │
             ┌────────────────────────┼────────────────────────┐
             │                        │                        │
             ▼                        ▼                        ▼
    ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
    │  Service Info    │     │  Backend         │     │  Privacy         │
    │  (name, version) │     │  Adapters        │     │  Settings        │
    └──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## 5. Separation of Concerns

### 5.1 The Two-Part Contract

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│     DECORATOR                              SDK CALLS                    │
│     ─────────                              ─────────                    │
│                                                                         │
│     "What kind of                          "What data should            │
│      operation is this?"                    be captured?"               │
│                                                                         │
│     ┌─────────────────┐                    ┌─────────────────┐         │
│     │  @llmops.llm()  │                    │  set_input()    │         │
│     │  @llmops.tool() │                    │  set_output()   │         │
│     │  @llmops.agent()│                    │  set_tokens()   │         │
│     └─────────────────┘                    │  emit_chunk()   │         │
│                                            └─────────────────┘         │
│           │                                        │                   │
│           │                                        │                   │
│           ▼                                        ▼                   │
│     ┌─────────────────────────────────────────────────────────┐       │
│     │                      SPAN                                │       │
│     │                                                          │       │
│     │   kind: LLM_GENERATE                                    │       │
│     │   name: "generate"                                       │       │
│     │   model: "gpt-4o"          ◀── from decorator           │       │
│     │   ─────────────────────────────────────────────         │       │
│     │   input: "What is..."      ◀── from set_input()         │       │
│     │   output: "The answer..."  ◀── from set_output()        │       │
│     │   tokens.input: 15         ◀── from set_tokens()        │       │
│     │   tokens.output: 42                                      │       │
│     │                                                          │       │
│     └─────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Why This Separation?

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PROBLEM: All-in-decorator approach                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  @observe.llm(                                                          │
│      model="gpt-4o",                                                    │
│      input=lambda args, kwargs: kwargs["prompt"],    ◀── Complex       │
│      output=lambda r: r.choices[0].message.content,  ◀── Hard to test  │
│      tokens=lambda r: {...}                          ◀── Fixed timing  │
│  )                                                                      │
│  async def generate(prompt): ...                                        │
│                                                                         │
│  Issues:                                                                │
│  • Extraction happens at fixed points (before/after)                   │
│  • Streaming requires awkward workarounds                              │
│  • Lambda extractors hard to test in isolation                         │
│  • Decorator signature becomes complex                                  │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  SOLUTION: Decorator + explicit calls                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  @llmops.llm(model="gpt-4o")      ◀── Simple, static                   │
│  async def generate(prompt):                                            │
│      llmops.set_input(prompt)     ◀── Explicit, testable               │
│                                                                         │
│      async for chunk in stream:                                         │
│          llmops.emit_chunk(chunk) ◀── Works during iteration!          │
│          yield chunk                                                    │
│                                                                         │
│      llmops.set_output(full)      ◀── Call whenever ready              │
│                                                                         │
│  Benefits:                                                              │
│  • Enrichment at any point in execution                                │
│  • Streaming handled naturally                                          │
│  • SDK calls easily mocked in tests                                    │
│  • Decorators remain simple                                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Auto vs Manual: When to Use Which

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     INSTRUMENTATION DECISION TREE                        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  "I want traces with zero code changes"                         │   │
│  │                      │                                          │   │
│  │                      ▼                                          │   │
│  │            AUTO-INSTRUMENTATION                                 │   │
│  │            llmops.init() + config file                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  "I need custom business attributes on spans"                   │   │
│  │  "I need to trace functions that aren't LLM calls"             │   │
│  │  "I need fine-grained control over span boundaries"            │   │
│  │                      │                                          │   │
│  │                      ▼                                          │   │
│  │            MANUAL INSTRUMENTATION                               │   │
│  │            @llmops.* decorators + enrichment calls              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  "I want automatic traces PLUS custom spans for my logic"      │   │
│  │                      │                                          │   │
│  │                      ▼                                          │   │
│  │            BOTH (they coexist!)                                 │   │
│  │            llmops.init() + @llmops.* where needed               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Coexistence Example:**

```python
import llmops

# Enable auto-instrumentation for all LLM library calls
llmops.init()

# Add manual instrumentation for custom business logic
@llmops.agent(name="research-agent")
async def research(query: str):
    llmops.set_attribute("query.topic", extract_topic(query))

    # These OpenAI calls are auto-traced by init()
    # AND nested under the manual "research-agent" span
    plan = await openai.chat.completions.create(...)
    results = await openai.chat.completions.create(...)

    llmops.set_output(results)
    return results
```

---

## 6. Span Hierarchy

### 6.1 Automatic Nesting

```
    @llmops.agent(name="research")
    async def research(query):
        │
        │   @llmops.retrieve(name="search")
        ├──▶ async def search(q): ...
        │           │
        │           │   @llmops.llm(model="gpt-4o")
        │           └──▶ async def generate(prompt): ...
        │
        │   @llmops.tool(name="summarize")
        └──▶ async def summarize(docs): ...


    RESULTING TRACE:

    ┌─────────────────────────────────────────────────────────────────┐
    │  agent: research                                                │
    │  ┌────────────────────────────────────────────────────────────┐ │
    │  │  retrieve: search                                          │ │
    │  │  ┌───────────────────────────────────────────────────────┐ │ │
    │  │  │  llm: generate                                        │ │ │
    │  │  └───────────────────────────────────────────────────────┘ │ │
    │  └────────────────────────────────────────────────────────────┘ │
    │  ┌────────────────────────────────────────────────────────────┐ │
    │  │  tool: summarize                                           │ │
    │  └────────────────────────────────────────────────────────────┘ │
    └─────────────────────────────────────────────────────────────────┘
             time ───────────────────────────────────────────────▶
```

---

## 7. Backend Translation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SDK Internal                                  │
│                                                                         │
│   SemanticKind.LLM_GENERATE                                            │
│   ├── model: "gpt-4o"                                                  │
│   ├── input: "What is..."                                              │
│   ├── output: "The answer..."                                          │
│   └── tokens: {input: 15, output: 42}                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ OTel GenAI Mapping
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         OTel GenAI Span                                 │
│                                                                         │
│   gen_ai.operation.name: "chat"                                        │
│   gen_ai.request.model: "gpt-4o"                                       │
│   gen_ai.usage.input_tokens: 15                                        │
│   gen_ai.usage.output_tokens: 42                                       │
│   + events for input/output content                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
          │                         │                         │
          │ OTLP Adapter           │ MLflow Adapter          │ Arize Adapter
          │ (pass-through)         │ (pass-through)          │ (translate)
          ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     Tempo       │       │     MLflow      │       │  Arize Phoenix  │
│                 │       │                 │       │                 │
│  gen_ai.*       │       │  gen_ai.*       │       │  llm.model_name │
│  (unchanged)    │       │  (unchanged)    │       │  llm.token_count│
│                 │       │                 │       │  (OpenInference)│
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

---

## 8. Design Rationale

### Why Both Auto and Manual Instrumentation?

| User Need | Solution |
|-----------|----------|
| Quick start with zero code changes | Auto-instrumentation via `init()` |
| Fine-grained control and custom attributes | Manual instrumentation via decorators |
| Both baseline traces and custom business logic | Use both together |

**Key insight:** Different users have different needs. New teams want instant visibility. Mature teams want customization. The SDK supports both without forcing a choice.

### Why Leverage Backend Instrumentors?

| Alternative | Why Not |
|-------------|---------|
| Build custom instrumentors | Duplicates effort; falls behind library updates |
| Only manual instrumentation | High friction; adoption barrier |
| **Use backend instrumentors** | ✓ Battle-tested, maintained, comprehensive coverage |

### Why Decorators (for Manual)?

| Alternative | Why Not |
|-------------|---------|
| Context managers only | Requires `with` block everywhere; less ergonomic |
| Explicit span start/end | Easy to forget `end()`; error-prone |
| Monkey-patching | Magic behavior; hard to debug |
| **Decorators** | ✓ Clean syntax, explicit boundaries, Pythonic |

### Why Explicit Enrichment Calls?

| Alternative | Why Not |
|-------------|---------|
| Auto-extract from args | Requires inference; breaks on refactoring |
| Extraction lambdas in decorator | Hard to test; fixed execution points |
| **Explicit SDK calls** | ✓ Clear, testable, works with streaming |

### Why Enums for Semantic Kinds?

| Alternative | Why Not |
|-------------|---------|
| String literals | Typos at runtime; no autocomplete |
| Class constants | No exhaustiveness checking |
| **Enums** | ✓ Type-safe, discoverable, IDE autocomplete |

---

## 9. Related Documents

| Document | Purpose |
|----------|---------|
| [PRD](./PRD.md) | Requirements and success criteria |
| [Reference Architecture](./REFERENCE_ARCHITECTURE.md) | Technical patterns and invariants |
| API Specification | Detailed contracts and signatures |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-13
