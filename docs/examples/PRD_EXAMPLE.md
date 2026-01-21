# LLM Observability SDK — Product Requirements Document

**Version:** 1.0
**Date:** 2026-01-13
**Status:** Draft

---

## 1. Problem Statement

The LLM observability ecosystem is fragmented:

- **Multiple backends** with incompatible conventions (Arize/OpenInference, MLflow, Datadog, custom OTLP)
- **Evolving standards** (OTel GenAI conventions are still in Development status)
- **Framework coupling** (instrumentation tied to LangChain, LlamaIndex, etc.)

**Without an SDK:** Teams rewrite instrumentation when backends change, standards evolve, or frameworks shift.

**With this SDK:** Developers use stable decorators and enrichment calls; platform team maintains backend adapters.

---

## 2. Product Vision

A **stable, developer-friendly SDK** for capturing telemetry from LLM-based applications that:

1. **Gets developers started in minutes** via auto-instrumentation
2. **Insulates developers** from backend and standards churn
3. **Never breaks** application correctness
4. **Works naturally** with async Python and streaming responses

The SDK provides **two instrumentation modes**:

| Mode | Use Case | Setup |
|------|----------|-------|
| **Auto-instrumentation** | Quick start, standard patterns | `llmops.init()` + config file |
| **Manual instrumentation** | Custom logic, fine-grained control | Decorators + enrichment calls |

---

## 3. Target Users

### Primary Users

| User | Need |
|------|------|
| **Application developers** | Instrument LLM calls with minimal friction |
| **Platform team** | Maintain backend adapters without touching app code |

### Primary Frameworks

- FastAPI async web services
- Google ADK agent applications

### Primary Backends (Auto-instrumentation Supported)

- **Arize Phoenix** — Full auto-instrumentation via OpenInference instrumentors
- **MLflow** — Full auto-instrumentation via native OTel GenAI support

### Secondary Backends (Manual Instrumentation Only)

- Generic OTLP (Tempo, Jaeger, Datadog)

---

## 4. Goals

1. **Stable API** — Breaking changes require major version; <2 per year
2. **Backend independence** — Switch backends via configuration only
3. **Telemetry safety** — SDK failures never break application logic
4. **Async-native** — First-class support for async functions and generators
5. **Explicit instrumentation** — No magic inference from function signatures

---

## 5. Non-Goals

- Replace OpenTelemetry
- Implement an agent framework
- Implement custom auto-instrumentors (we leverage backend-provided instrumentors)
- Infer semantic meaning from function signatures or argument names
- Enforce specific LLM providers

---

## 6. Constraints

| Constraint | Rationale |
|------------|-----------|
| Python ≥3.14 | Modern typing features, async improvements |
| FastAPI compatible | Must preserve function signatures for DI |
| OTel GenAI aligned | Internal representation uses emerging standard |

---

## 7. Requirements

### 7.1 Functional Requirements

#### Auto-Instrumentation

| ID | Requirement | Priority |
|----|-------------|----------|
| A1 | Single `init()` call enables auto-instrumentation based on config | Must |
| A2 | Auto-instrumentation supports Arize Phoenix (OpenInference) | Must |
| A3 | Auto-instrumentation supports MLflow | Must |
| A4 | Auto-instrumentors for all backend-supported libraries enabled by default | Must |
| A5 | Individual instrumentors can be disabled via config | Should |
| A6 | Auto-instrumentation and manual instrumentation can coexist | Must |

#### Manual Instrumentation

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | Developers can mark semantic boundaries via decorators | Must |
| F2 | Developers can enrich spans with input/output/tokens via SDK calls | Must |
| F3 | SDK emits OTel GenAI-compatible spans | Must |
| F4 | Configuration loaded from YAML files | Must |
| F5 | Multiple backends supported simultaneously | Should |
| F6 | Custom attributes preserved across all backends | Must |
| F7 | Streaming responses can emit chunks during iteration | Must |
| F8 | Session/conversation tracking supported | Should |

### 7.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| N1 | Telemetry failures never raise exceptions to user code | Must |
| N2 | Decorators preserve function signatures (FastAPI DI works) | Must |
| N3 | Async functions and generators fully supported | Must |
| N4 | Auto-instrumentation onboarding <5 minutes from install to first trace | Should |
| N5 | Manual instrumentation onboarding <30 minutes from install to first trace | Should |
| N6 | Auto-instrumentation requires ≤3 lines of code (import, config, init) | Should |
| N7 | <5 lines of code to manually instrument a simple LLM call | Should |

### 7.3 Privacy Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| P1 | Prompt/response content NOT captured by default | Must |
| P2 | Content capture opt-in via configuration | Must |
| P3 | Per-call override for content capture | Should |

---

## 8. Success Criteria

### Developer Experience

- **Auto-instrumentation onboarding:** <5 minutes from install to first trace
- **Manual instrumentation onboarding:** <30 minutes from install to first trace
- **Auto-instrumentation code:** 3 lines (import, config path, init call)
- **Manual instrumentation code:** Decorator + 2-3 SDK calls per function
- **Type safety:** Full IDE autocomplete via enums and type hints

### Stability

- **API churn:** avoid frequent breaking
- **Semver:** allow devs to opt-in to new features
- **Backend isolation:** Switch backends with config change only
- **Error isolation:** Telemetry failures never break application

### Testability

- **Mock-friendly:** SDK calls easily mocked/spied in tests
- **Validation:** Strict mode catches missing instrumentation in CI, permissie 

---

## 9. User Stories

### US0: Quick Start with Auto-Instrumentation

> As a developer, I want to get observability working with minimal setup so that I can see traces immediately without learning the SDK API.

**Acceptance:**
- Create config file pointing to backend (Arize or MLflow)
- Call `llmops.init()` at application startup
- All supported LLM library calls automatically traced
- Traces appear in configured backend without any decorators

**Example:**
```yaml
# llmops.yaml
backend: phoenix
phoenix:
  endpoint: http://localhost:6006
```

```python
import llmops
llmops.init()  # Auto-instruments all supported libraries

# No decorators needed - calls are automatically traced
response = openai.chat.completions.create(...)
```

### US1: Basic LLM Instrumentation (Manual)

> As a developer, I want to instrument an LLM call so that I can see it in my observability backend.

**Acceptance:**
- Decorator marks the function as an LLM operation
- SDK calls capture input, output, and token counts
- Span appears in configured backend with correct attributes

### US2: Streaming Response

> As a developer, I want to instrument a streaming LLM response so that I can track tokens as they arrive.

**Acceptance:**
- Async generator decorated with semantic kind
- Chunks emitted during iteration appear as span events
- Span closes when generator exhausts

### US3: Agent Workflow

> As a developer, I want to instrument a multi-step agent so that I can see the hierarchy of operations.

**Acceptance:**
- Parent span for agent run
- Child spans for tool calls and LLM calls nest automatically
- Full trace visible in backend

### US4: Backend Switch

> As a platform engineer, I want to switch from MLflow to Arize without changing application code.

**Acceptance:**
- Modify YAML configuration only (change `backend: mlflow` to `backend: phoenix`)
- Restart application
- Auto-instrumentation automatically uses new backend's instrumentors
- Traces appear in new backend with appropriate conventions

### US5: Privacy Control

> As a compliance officer, I want prompts and responses excluded by default so that we don't accidentally capture PII.

**Acceptance:**
- Default configuration does not capture content
- Opt-in required in config or per-call
- Metadata (model, tokens, timing) still captured

---

## 10. Out of Scope

Detailed in separate documents:

| Topic | Document |
|-------|----------|
| System layers and data flow | Conceptual Architecture |
| SDK internals, invariants, async patterns | Reference Architecture |
| Decorator signatures, enrichment API, examples | API Specification |

---

## 11. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | How do we handle library version compatibility for auto-instrumentors? | Needs design |
| 2 | How do we handle multi-backend routing (different spans to different backends)? | Needs design |
| 3 | Should strict validation mode be the default in CI? | Needs discussion |
| 4 | How should auto-instrumentation interact with manual spans for the same call? | Needs design |

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| **Auto-instrumentation** | Automatic tracing of library calls without code changes, enabled by backend-provided instrumentors |
| **Manual instrumentation** | Explicit tracing via decorators and SDK enrichment calls |
| **Instrumentor** | Component that patches a library to emit telemetry (e.g., OpenInference OpenAI instrumentor) |
| **Semantic Kind** | Type of operation (LLM call, tool call, agent run, etc.) |
| **Span** | Unit of work in a trace with start/end time and attributes |
| **Enrichment** | Adding data (input, output, tokens) to a span |
| **Backend** | Observability system that receives telemetry (MLflow, Arize, etc.) |
| **Adapter** | Component that translates OTel spans to backend-specific format |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-13
