# LLM Observability SDK — Conceptual Architecture

**Version:** 1.0
**Date:** 2026-01-13
**Status:** Draft

---

## 1. Overview

This document provides a visual understanding of the LLM Observability SDK architecture. It describes **what the system looks like** and **how pieces relate**, not implementation details.

---

## 2. Core Concept: The Abstraction Layer

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION CODE                                  │
│                                                                         │
│   @llmops.llm(model="gpt-4o")                                          │
│   async def generate(prompt):                                           │
│       llmops.set_input(prompt)                                         │
│       ...                                                               │
│       llmops.set_output(result)                                        │
│       return result                                                     │
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
│         ┌─────────────────────┼─────────────────────┐                  │
│         │                     │                     │                  │
│         ▼                     ▼                     ▼                  │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐              │
│   │  MLflow  │         │  Arize   │         │   OTLP   │              │
│   │          │         │  Phoenix │         │  (Tempo) │              │
│   └──────────┘         └──────────┘         └──────────┘              │
│                                                                         │
│                        OBSERVABILITY BACKENDS                           │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Insight:** The SDK sits between application code and backends, providing a stable interface that absorbs ecosystem churn.

---

## 3. SDK Layer Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: Public API                                                    │
│  ─────────────────────────────────────────────────────────────────────  │
│  • Decorators: @llmops.llm(), @llmops.tool(), @llmops.agent()          │
│  • Enrichment: set_input(), set_output(), set_tokens()                 │
│  • Configuration: configure(), YAML loading                             │
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

### 4.1 Instrumentation Flow

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

### 4.2 Configuration Flow

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

### Why Decorators?

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
