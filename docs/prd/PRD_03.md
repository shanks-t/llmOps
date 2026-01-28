# PRD_03 — LLM-as-a-Judge Templates and AX Evaluation Runs

**Version:** 0.4
**Date:** 2026-01-28
**Status:** Draft
**Depends on:** PRD_01 (Config-Driven Auto-Instrumentation SDK)

---

## 1. Problem Statement

Teams need consistent, reusable evaluation templates and a reliable way to run them against telemetry already stored in Arize AX. Today:

1. **No standard template workflow** — Each team re-creates LLM-as-a-judge prompts and scoring logic.
2. **Boilerplate to operationalize evals** — Developers must stitch together template creation, backend storage, and execution.
3. **No SDK flow for telemetry subsets** — There is no simple SDK API to evaluate specific slices of AX telemetry.

We need an SDK feature that:
- Enables creation of LLM-as-a-judge evaluator templates
- Persists templates to Arize AX Evaluator Hub
- Retrieves templates for reuse
- Runs evaluations on **filtered subsets of AX telemetry**
- Supports both **online tasks** and **on-demand runs**

---

## 2. Product Vision

`llmops.eval` provides a platform-agnostic SDK surface that uses Arize AX under the hood to:

1. Create evaluator templates with minimal boilerplate
2. Save templates to the Arize AX Evaluator Hub
3. Retrieve and use templates across teams
4. Run evaluations on filtered telemetry subsets in AX
5. Support **online tasks** (continuous) and **on-demand runs** (one-time)

### API Design

```python
import llmops
from phoenix.evals.llm import LLM

llmops.eval.init(config="llmops.yaml")
llm = LLM(provider="openai", model="gpt-4o")

# Create and push a custom template
tone_eval = llmops.eval.create_classifier(
    name="professional_tone",
    prompt_template="Is the response professional? Response: {output}",
    llm=llm,
    choices={"professional": 1.0, "unprofessional": 0.0},
)
llmops.eval.push("professional_tone", tone_eval)

# Pull a template and use it locally
eval_ref = llmops.eval.pull("professional_tone", llm=llm)
scores = eval_ref.evaluate({"output": "Hello, how can I help?"})
```

### Telemetry Subset Filter

```python
telemetry_filter = {
    "space_id": "space_123",
    "model_id": "model_456",
    "environment": "TRACING",
    "time_range": {
        "start": "2026-01-01T00:00:00Z",
        "end": "2026-01-31T00:00:00Z",
    },
    "query": "span.kind == 'llm' and attributes.llm.provider == 'openai'",
}
```

### Online Task (Continuous Evaluation)

```python
task = llmops.eval.run_online(
    template="professional_tone",
    filter=telemetry_filter,
    llm=llm,
)
```

### On-Demand Run (Annotate Existing Telemetry)

```python
summary = llmops.eval.run(
    template="professional_tone",
    filter=telemetry_filter,
    llm=llm,
)

# summary includes counts and task_id
```

---

## 3. Target User Persona

### Primary Persona

**ML Engineer using Arize AX** who wants to:
- Create LLM-as-a-judge templates without low-level API work
- Persist templates for team reuse
- Evaluate subsets of telemetry in AX

### Non-Target Persona

- **Local-only or OSS evaluation users** — This PRD focuses on AX-backed workflows

---

## 4. Goals

| ID | Goal | Priority |
|----|------|----------|
| G1 | Create LLM-as-a-judge templates programmatically | Must |
| G2 | Persist templates in Arize AX Evaluator Hub | Must |
| G3 | Retrieve templates by name | Must |
| G4 | List available templates in AX | Should |
| G5 | Run online evaluation tasks on filtered telemetry | Must |
| G6 | Run on-demand evaluations that annotate existing telemetry | Must |
| G7 | Support filter object for selecting telemetry subsets | Must |
| G8 | Lazy-load eval module and deps | Must |
| G9 | Keep API in `llmops.eval` namespace | Should |

---

## 5. Non-Goals

- In-memory or local template registries
- Phoenix OSS or non-AX backends
- Telemetry collection or tracing (owned by PRD_01)
- Template versioning in this release
- Standalone local-only evaluation without AX export/logging

---

## 6. Constraints

| Constraint | Rationale |
|------------|-----------|
| Python >=3.13 | Matches repo baseline from PRD_01 |
| `arize-phoenix-evals>=2.0.0` dependency | Core evaluation functionality |
| AX backend required for persistence and runs | Scope is AX-only |
| LLM configuration is user-provided | Avoid SDK responsibility for API keys/models |
| Lazy loading required | Avoid import-time dependency errors |
| Uses reserved `llmops.eval` namespace | Aligns with Design Philosophy |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | `llmops.eval.init(config)` initializes eval auth for AX operations | Must |
| F2 | `llmops.eval.create_classifier(...)` creates a template evaluator | Must |
| F3 | `llmops.eval.push(name, evaluator)` saves template to AX Evaluator Hub | Must |
| F4 | `llmops.eval.pull(name, llm)` retrieves template from AX | Must |
| F5 | `llmops.eval.list_remote()` lists available AX templates | Should |
| F6 | `llmops.eval.run_online(...)` creates an online task in AX | Must |
| F7 | `llmops.eval.run(...)` runs an on-demand evaluation in AX | Must |
| F8 | On-demand runs annotate existing telemetry in AX | Must |
| F9 | On-demand runs return a minimal summary (counts, task_id) | Must |
| F10 | Filter object selects telemetry subset for run/task | Must |
| F11 | Missing deps raise `ImportError` with install guidance | Must |

**Filter object requirements (F10):**
- Includes `space_id`, `model_id`, `environment`
- Supports a `time_range` (start/end ISO-8601)
- Supports a `query` string for attribute filtering

### 7.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| N1 | `import llmops` succeeds without eval deps installed | Must |
| N2 | Error messages include installation instructions | Must |
| N3 | Backend operations timeout with clear errors | Should |
| N4 | Error handling is catchable (no hard crashes) | Should |

---

## 8. Architecture (High-Level)

### 8.1 Package Structure

```
llmops/
├── __init__.py              # Re-exports eval namespace
├── eval/                    # Evaluation module
│   ├── __init__.py          # Public API: create_classifier, push, pull, run
│   └── templates/           # Built-in templates (future)
└── ...
```

### 8.2 AX Integration (Conceptual)

- **Template storage:** Arize AX Evaluator Hub
- **Online tasks:** AX task API creates continuous evaluations over filtered telemetry
- **On-demand runs:** AX evaluation run API evaluates a filtered telemetry subset and writes results back as annotations

The SDK maps the filter object to the AX query filter for both run modes.

### 8.3 Auth and Init

- `llmops.init()` remains dedicated to telemetry and auto-instrumentation (PRD_01)
- `llmops.eval.init()` establishes auth and context required for AX evaluation operations
- Eval workflows do not require telemetry instrumentation

### 8.4 Local Evaluation Pipeline (Export → Evaluate → Log)

In addition to backend runs, the SDK supports a local evaluation workflow for offline analysis:

1. **Export telemetry to DataFrame** from AX
2. **Map columns** to the evaluator schema (`input`, `output`, `context`, `span_id`)
3. **Run evals locally** using Phoenix evals or `llmops.eval.create_classifier`
4. **Log results back** to AX/Phoenix for visualization

Local evaluation is distinct from backend annotation runs: it is client-side, uses exported data, and then writes results back.

---

## 9. Success Criteria

- Create + push a template in under 10 lines of code
- Create an online evaluation task with a filter in under 10 lines of code
- Run an on-demand evaluation that annotates telemetry and returns a summary
- Export telemetry, run local evals, and log results back in one script
- `import llmops` succeeds without eval dependencies installed

---

## 10. User Stories

### US1: Create and Push Template

> As an ML engineer, I want to create a custom evaluator and save it to AX so my team can reuse it.

**Acceptance:**
- `create_classifier()` accepts name, prompt_template, llm, choices
- `push()` stores the template in the Evaluator Hub
- Requires `llmops.eval.init()` with Arize config

### US2: Online Task on Telemetry Subset

> As an ML engineer, I want to continuously evaluate a subset of telemetry in AX.

**Acceptance:**
- `run_online()` accepts a template name, filter object, and LLM
- Creates an AX online task for that subset

### US3: On-Demand Run with Annotation

> As an ML engineer, I want to run a one-time evaluation over a subset of telemetry and annotate the results in AX.

**Acceptance:**
- `run()` accepts a template name, filter object, and LLM
- Results are written back to AX
- Returns a summary with counts and task_id

### US4: Discover Templates

> As an ML engineer, I want to list available templates in AX.

**Acceptance:**
- `list_remote()` returns available template names

### US5: Dependency Error Handling

> As a developer, I want clear error messages when eval dependencies are missing.

**Acceptance:**
- Errors include: `pip install llmops[eval]`
- Error is raised at usage time, not import time

---

## 11. Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API location | `llmops.eval` | Reserved namespace and clear separation |
| Template storage | Arize AX Evaluator Hub | Centralized, shareable, managed |
| Execution modes | Online tasks + on-demand runs | Supports continuous and ad-hoc evaluation |
| On-demand behavior | Write back to AX + return summary | Matches telemetry-annotation goal |
| Telemetry selection | Filter object | Explicit and backend-aligned |
| Auth surface | `llmops.eval.init()` | Separate from telemetry init |

---

## 12. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Query language for `filter.query` (AX DSL vs OpenInference expressions)? | Open |
| 2 | Naming conventions for templates (namespaces, prefixes)? | Open |
| 3 | How to handle partial failures in large on-demand runs? | Open |
| 4 | Result schema for returned summary (counts, durations, ids)? | Open |

---

## 13. Future Considerations

- Additional built-in templates (relevance, toxicity, redundancy)
- Template versioning and metadata fields
- SDK helpers for common filter presets

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-28
