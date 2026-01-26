# PRD_03 — LLM-as-a-Judge Evaluator Templates

**Version:** 0.1  
**Date:** 2026-01-26  
**Status:** Draft  
**Depends on:** PRD_01 (Platform Architecture)

---

## 1. Problem Statement

GenAI applications require consistent, scalable evaluation capabilities to validate LLM outputs. Currently, developers face several challenges:

1. **No standard evaluation patterns** — Each project implements evaluation logic from scratch, leading to inconsistent practices across teams.

2. **Boilerplate overhead** — Using libraries like `arize-phoenix-evals` directly requires repetitive setup code for each evaluator.

3. **No reusability mechanism** — Custom evaluation templates cannot be easily shared or reused within or across projects.

4. **Evaluation-telemetry gap** — While PRD_01 establishes tracing infrastructure, there's no SDK-level support for evaluating LLM outputs.

We need an SDK feature that:
- Provides pre-built evaluation templates for common use cases (starting with Faithfulness/hallucination detection)
- Offers factory functions for creating custom LLM-as-a-judge evaluators
- Enables template registration for project-wide reuse
- Follows the platform-namespaced architecture established in PRD_01

---

## 2. Product Vision

A **platform-namespaced evaluation API** (`llmops.arize.evals`) where:

1. Users access built-in templates for common evaluations with one function call
2. Factory functions create custom evaluators with minimal boilerplate
3. An in-memory registry enables named template storage and retrieval
4. The API mirrors Phoenix Evals patterns for developer familiarity

### API Design

```python
import llmops
from phoenix.evals.llm import LLM

# Configure LLM (user responsibility)
llm = LLM(provider="openai", model="gpt-4o")

# Built-in template: Faithfulness evaluation
faithfulness = llmops.arize.evals.faithfulness(llm=llm)
scores = faithfulness.evaluate({
    "input": "What is the capital of France?",
    "output": "Paris is the capital of France.",
    "context": "Paris is the capital and largest city of France."
})

# Custom evaluator via factory
tone_eval = llmops.arize.evals.create_classifier(
    name="tone_check",
    prompt_template="Is the response professional? Response: {output}",
    llm=llm,
    choices={"professional": 1.0, "unprofessional": 0.0},
)

# Register for project-wide reuse
llmops.arize.evals.register("tone_check", tone_eval)

# Retrieve registered evaluator
eval_ref = llmops.arize.evals.get("tone_check")
scores = eval_ref.evaluate({"output": "Hello, how can I assist you today?"})
```

The SDK provides:
- Platform-namespaced `evals` entry point (`llmops.arize.evals`)
- Built-in Faithfulness template from Phoenix Evals
- Factory function wrapping `phoenix.evals.create_classifier`
- Simple in-memory registry for named template storage

---

## 3. Target User Persona

### Primary Persona

**ML Engineer evaluating GenAI outputs** who wants to:
- Quickly set up LLM-as-a-judge evaluation for common use cases
- Create custom evaluation criteria without learning low-level APIs
- Reuse evaluation templates across different parts of their project

### Non-Target Persona

- **Production evaluation pipeline builder** — This PRD focuses on SDK-level primitives, not production-grade evaluation infrastructure (future work)
- **Multi-platform evaluation user** — Only Arize platform is supported in this iteration

---

## 4. Goals

| ID | Goal | Priority |
|----|------|----------|
| G1 | Provide pre-built Faithfulness evaluator template | Must |
| G2 | Factory function for custom LLM-as-a-judge evaluators | Must |
| G3 | In-memory registry for named template storage/retrieval | Must |
| G4 | Lazy-load evals module (no import-time deps) | Must |
| G5 | Maintain platform isolation (Arize-specific) | Must |
| G6 | Follow existing SDK patterns from PRD_01 | Should |

---

## 5. Non-Goals

- **Telemetry integration** — Running evaluations on exported spans or logging results as annotations is out of scope (future PRD)
- **Multiple built-in templates** — Only Faithfulness is included; additional templates (Relevance, Toxicity, etc.) are future work
- **Persistent registry** — Arize AX-backed template storage is out of scope
- **Code-based evaluators** — Non-LLM evaluators are out of scope
- **MLflow platform support** — Evals are Arize-platform-specific in this PRD
- **DataFrame batch evaluation** — Focus is on single-record evaluation API
- **Config-driven LLM** — LLM configuration in llmops.yaml is future work

---

## 6. Constraints

| Constraint | Rationale |
|------------|-----------|
| Python >=3.13 | Matches repo baseline from PRD_01 |
| `arize-phoenix-evals>=2.0.0` dependency | Core evaluation functionality |
| LLM configuration is user-provided | Avoids SDK responsibility for API keys/models |
| Lazy loading required | Avoid importing deps until accessed |
| Platform-namespaced API | Consistency with PRD_01 architecture |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | `llmops.arize.evals.faithfulness(llm)` returns configured evaluator | Must |
| F2 | `llmops.arize.evals.create_classifier(...)` creates custom evaluator | Must |
| F3 | `llmops.arize.evals.register(name, evaluator)` stores evaluator by name | Must |
| F4 | `llmops.arize.evals.get(name)` retrieves registered evaluator | Must |
| F5 | `llmops.arize.evals.list()` returns names of registered evaluators | Should |
| F6 | `evaluator.evaluate(input_dict)` returns list of Score objects | Must |
| F7 | Evals module is lazy-loaded on first access | Must |
| F8 | Missing deps raise `ImportError` with helpful message | Must |
| F9 | Registry raises `KeyError` for unregistered names | Should |
| F10 | `llmops.arize.evals.clear()` clears registry (for testing) | Should |

### 7.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| N1 | `import llmops` succeeds without `arize-phoenix-evals` | Must |
| N2 | Error messages include installation instructions | Must |
| N3 | Built-in templates use Phoenix Evals benchmarked prompts | Must |
| N4 | Registry is thread-safe for concurrent access | Should |
| N5 | Evaluation errors are catchable (don't crash calling code) | Should |

---

## 8. Architecture

### 8.1 Package Structure

```
llmops/
├── __init__.py              # Existing (no changes needed)
├── arize.py                 # Add __getattr__ for 'evals' lazy loading
├── evals/                   # NEW: Evaluation module
│   ├── __init__.py          # Package marker
│   └── arize/               # Arize platform evals
│       ├── __init__.py      # Public API: faithfulness, create_classifier, etc.
│       ├── _registry.py     # In-memory template registry
│       └── _templates.py    # Built-in template implementations
└── _platforms/
    └── arize.py             # Existing (unchanged)
```

### 8.2 Module Loading Pattern

```
User Code: llmops.arize.evals.faithfulness(llm)
                │
                ▼
llmops.arize (module)
                │
                ├─▶ __getattr__("evals") triggered
                │
                ▼
from llmops.evals import arize as _evals_module
                │
                ├─▶ llmops/evals/arize/__init__.py
                │     └─▶ check_dependencies()
                │           - Imports phoenix.evals
                │           - Raises ImportError if missing
                │
                ▼
Return _evals_module
                │
                ▼
_evals_module.faithfulness(llm)
                │
                ├─▶ Creates FaithfulnessEvaluator from phoenix.evals
                └─▶ Returns configured evaluator
```

### 8.3 Registry Design

The in-memory registry provides named storage for evaluator instances within a running process.

#### Interface

```python
def register(name: str, evaluator: Evaluator) -> None:
    """
    Register an evaluator by name. Overwrites if name exists.
    
    Args:
        name: Unique identifier for the evaluator
        evaluator: Any evaluator instance (built-in or custom)
    """

def get(name: str) -> Evaluator:
    """
    Retrieve a registered evaluator.
    
    Raises:
        KeyError: If name is not registered
    """

def list() -> list[str]:
    """List all registered evaluator names."""

def clear() -> None:
    """Clear all registered evaluators. Primarily for testing."""
```

#### Characteristics

| Characteristic | Value |
|----------------|-------|
| Storage | `dict[str, Evaluator]` |
| Thread safety | `threading.Lock` for all operations |
| Duplicate handling | Overwrites existing (no error) |
| Missing key | Raises `KeyError` |
| Persistence | None (process-local only) |
| Scope | Global within `llmops.evals.arize` module |

#### Lifecycle

```
Process Start
     │
     ▼
Application startup (e.g., main.py, app.py)
     │
     ├─▶ register("hallucination", faithfulness(llm))
     ├─▶ register("tone_check", create_classifier(...))
     └─▶ register("relevance", create_classifier(...))
     │
     ▼
Application runs
     │
     ├─▶ service_a.py: get("hallucination").evaluate(...)
     ├─▶ service_b.py: get("tone_check").evaluate(...)
     └─▶ tests.py: get("relevance").evaluate(...)
     │
     ▼
Process End → Registry contents lost
```

#### When the Registry Is Useful

| Scenario | Useful? | Why |
|----------|---------|-----|
| Long-running service | Yes | Register once, use throughout request lifecycle |
| Jupyter notebook | Yes | Define evals once, reuse across cells |
| Multi-module project | Yes | Centralized definition, use by name anywhere |
| CLI tool (short-lived) | Marginal | Consider using factory directly |
| Serverless | Marginal | Cold starts require re-registration |

### 8.4 Dependencies

| Dependency | Required For | Installation |
|------------|--------------|--------------|
| `arize-phoenix-evals>=2.0.0` | Core evaluation functionality | `pip install llmops[arize-evals]` |
| LLM provider SDK (openai, etc.) | LLM execution | User responsibility |

### 8.5 Configuration Relationship

For PRD_03, evaluations are **independent of `llmops.yaml`**:

| Aspect | Relationship |
|--------|-------------|
| LLM configuration | User-provided at call time (not from config) |
| Eval-specific config | None in this PRD |
| Telemetry config | Separate concern; `instrument()` and evals are independent |

**Rationale:**
- LLM credentials are sensitive; avoid config file exposure
- LLM choice may vary per evaluator (cost vs. accuracy)
- Simpler initial scope

**Future direction** (not in PRD_03):
```yaml
# Potential future llmops.yaml addition
arize:
  evals:
    default_llm:
      provider: "openai"
      model: "gpt-4o-mini"
```

---

## 9. Success Criteria

- A user can evaluate LLM outputs using the built-in Faithfulness template in under 5 lines of code
- Custom evaluators can be created using `create_classifier()`
- Registered evaluators can be retrieved by name in different modules
- `import llmops` succeeds without `arize-phoenix-evals` installed
- `llmops.arize.evals.faithfulness()` raises helpful error if deps missing
- Registry maintains evaluators correctly across multiple uses

---

## 10. User Stories

### US1: Built-in Faithfulness Evaluation

> As an ML engineer, I want to quickly check if my RAG application's outputs are grounded in the retrieved context, so that I can detect hallucinations.

**Acceptance:**
- `llmops.arize.evals.faithfulness(llm=llm)` returns a configured evaluator
- Evaluator accepts `{input, output, context}` dict
- Returns Score with label (`faithful`/`unfaithful`) and numeric score (1.0/0.0)
- Uses Phoenix Evals benchmarked prompt (93% precision on HaluEval)

### US2: Custom Evaluator Creation

> As an ML engineer, I want to create a custom evaluation template for my specific use case (e.g., tone checking), so that I can measure what matters for my application.

**Acceptance:**
- `create_classifier()` accepts name, prompt_template, llm, and choices
- Prompt template supports `{variable}` placeholders
- Created evaluator can be used immediately
- Returns Score objects with label, score, and explanation

### US3: Template Reuse via Registry

> As an ML engineer working on a large project, I want to register evaluation templates by name so that I can use them consistently across different modules without recreating them.

**Acceptance:**
- `register(name, evaluator)` stores evaluator
- `get(name)` retrieves the same evaluator instance
- `list()` returns all registered names
- `KeyError` raised for unregistered names

### US4: Dependency Error Handling

> As a developer setting up the SDK, I want clear error messages when dependencies are missing so that I know what to install.

**Acceptance:**
- `llmops.arize.evals.faithfulness()` without `arize-phoenix-evals` raises error
- Error message includes: `pip install llmops[arize-evals]`
- Error is raised at usage time, not import time

---

## 11. Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API location | `llmops.arize.evals` | Platform-namespaced per PRD_01 pattern |
| Registry scope | In-memory, process-local | Simplest first step; persistent is future |
| Built-in templates | Faithfulness only | Start with most common use case |
| LLM configuration | User-provided | Avoid SDK credential responsibility |
| Loading strategy | Lazy on first access | Match PRD_01 pattern |
| Underlying library | `arize-phoenix-evals` | Battle-tested, benchmarked prompts |
| Accessor location | In `llmops/arize.py` | Platform is primary organizing principle |

---

## 12. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Should `register()` warn on overwrite? | Open |
| 2 | Should we expose `evaluate_dataframe()` for batch? | Deferred to future PRD |
| 3 | Thread-local vs global registry option? | Resolved: Global with lock |

---

## 13. Future Considerations

### 13.1 Additional Built-in Templates

| Template | Use Case | Priority |
|----------|----------|----------|
| Document Relevance | RAG retrieval quality | High |
| Correctness | Q&A accuracy | High |
| Toxicity | Safety/content moderation | Medium |
| Tool Calling | Agent tool selection | Medium |

### 13.2 Telemetry Integration (Future PRD)

- Export spans from Arize AX
- Run evaluators on exported data
- Log evaluation results as span annotations
- `llmops.arize.evals.evaluate_spans(...)` API

### 13.3 Persistent Registry (Future PRD)

- Store templates in Arize AX
- Cross-project template sharing
- Template versioning

### 13.4 Config-Driven LLM (Future PRD)

- Default LLM settings in `llmops.yaml`
- Override at call time if needed

### 13.5 MLflow Platform Support

- `llmops.mlflow.evals` namespace
- Shared evaluator Protocol across platforms

---

**Document Owner:** Platform Team  
**Last Updated:** 2026-01-26
