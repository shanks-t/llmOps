# PRD_02 — Multi-Platform Auto-Instrumentation

**Version:** 0.1
**Date:** 2026-01-22
**Status:** Draft
**Builds On:** PRD_01

---

## 1. Problem Statement

PRD_01 established a single-call `instrument()` API for Arize telemetry. However, the current design has limitations:

1. **Implicit Backend Coupling** — The top-level `llmops.instrument()` is tightly coupled to Arize via `arize.otel.register`. Users cannot easily switch to other observability platforms.

2. **No Platform Choice** — Users who want MLflow, Datadog, or generic OTLP backends must wait for SDK changes or write custom integrations.

3. **Unclear Intent** — The API doesn't signal which platform's auto-instrumentation is being activated.

We need to refactor the SDK so that platform selection is explicit in the API call itself, while maintaining the simplicity that PRD_01 established.

---

## 2. Product Vision

A **platform-explicit SDK** where:

1. Users call `llmops.<platform>.instrument()` to clearly indicate their observability backend
2. Each platform module encapsulates its specific setup logic and dependencies
3. New platforms can be added without changing the core SDK interface
4. The developer experience remains simple: import, call, done

### API Transformation

**Before (PRD_01):**
```python
import llmops
llmops.instrument(config_path="llmops.yaml")  # Implicitly uses Arize
```

**After (PRD_02):**
```python
import llmops
llmops.arize.instrument(config_path="llmops.yaml")  # Explicitly uses Arize

# Or for future platforms:
llmops.mlflow.instrument(config_path="llmops.yaml")
```

---

## 3. Target User Persona

### Primary Persona

**Platform-aware developer** who wants explicit control over which observability backend is used and benefits from clear, platform-specific documentation and error messages.

### Secondary Persona

**Multi-environment team** that deploys the same application to different environments with different observability backends (e.g., Phoenix locally, Arize AX in production, MLflow in ML team environments).

### Non-Target Persona

**Backend-agnostic abstraction seeker** who wants a single `instrument()` call that auto-detects the backend. This PRD prioritizes explicit platform selection over implicit detection.

---

## 4. Goals

1. **Explicit Platform Selection** — The API call clearly indicates which platform is being used
2. **Platform Isolation** — Each platform's dependencies and logic are encapsulated in its own module
3. **Extensible Architecture** — New platforms can be added without modifying existing platform modules
4. **Consistent Interface** — All platform modules expose the same `instrument()` signature
5. **Preserve PRD_01 Semantics** — Within each platform, the behavior matches PRD_01 (one-call setup, auto-instrumentation, config-driven)

---

## 5. Non-Goals

- **Auto-detection of backend** — We explicitly reject magic detection; users must choose their platform
- **Multi-backend routing** — Sending spans to multiple backends simultaneously is out of scope
- **Backward compatibility shim** — The top-level `llmops.instrument()` will be removed, not deprecated
- **Platform feature parity** — Different platforms may support different instrumentors; this is expected

---

## 6. Constraints

| Constraint | Rationale |
|------------|-----------|
| Python >=3.13 | Matches repo baseline |
| Platform modules are lazy-loaded | Avoid importing platform-specific dependencies until needed |
| Each platform is independently installable | Users only install dependencies for their chosen platform |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| B1 | Each platform exposes `llmops.<platform>.instrument(config_path)` | Must |
| B2 | `llmops.arize.instrument()` replicates PRD_01 behavior exactly | Must |
| B3 | Platform modules are lazy-imported (no import-time side effects) | Must |
| B4 | Each platform module defines its supported instrumentors | Must |
| B5 | Config schema includes platform-specific sections (e.g., `arize:`, `mlflow:`) | Must |
| B6 | Invalid platform access raises `ImportError` with helpful message | Should |
| B7 | Platform modules share common config loading and validation | Should |
| B8 | Future platforms (MLflow, OTLP) can be added without core changes | Should |

### 7.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| BN1 | Telemetry failures never raise exceptions to user code | Must |
| BN2 | Platform-specific dependencies are optional extras | Must |
| BN3 | Error messages indicate which platform-specific package is missing | Should |
| BN4 | Import time for unused platforms is zero | Should |

---

## 8. Architecture

### 8.1 Package Structure

```
llmops/
├── __init__.py           # Lazy platform accessors
├── exceptions.py         # Shared exceptions
├── config.py             # Shared config loading
├── _platforms/           # Platform implementations
│   ├── __init__.py
│   ├── _base.py          # Abstract platform interface
│   ├── arize.py          # Arize/Phoenix implementation
│   └── mlflow.py         # MLflow implementation (future)
├── arize.py              # Public: from llmops import arize
└── mlflow.py             # Public: from llmops import mlflow (future)
```

### 8.2 Platform Interface

Each platform module must implement:

```python
def instrument(
    config_path: str | Path | None = None,
) -> TracerProvider:
    """
    Initialize platform telemetry and auto-instrumentation.

    Semantics match PRD_01 instrument() requirements.
    """
```

### 8.3 Config Schema Evolution

The config file supports platform-specific sections:

```yaml
# llmops.yaml
service:
  name: "my-service"
  version: "1.0.0"

# Arize-specific configuration
arize:
  endpoint: "http://localhost:6006/v1/traces"
  project_name: "my-project"
  api_key: "${ARIZE_API_KEY}"
  space_id: "${ARIZE_SPACE_ID}"
  transport: "http"
  batch_spans: true
  debug: false

# MLflow-specific configuration (future)
mlflow:
  tracking_uri: "http://localhost:5001"
  experiment_name: "my-experiment"

# Instrumentation settings (shared across platforms)
instrumentation:
  google_adk: true
  google_genai: true

validation:
  mode: permissive
```

---

## 9. Success Criteria

- A greenfield application shows traces after calling `llmops.arize.instrument()`
- The import `from llmops import arize` succeeds without importing Arize packages
- `llmops.arize.instrument()` fails gracefully with helpful message if `arize-otel` is not installed
- All PRD_01 test scenarios pass when using `llmops.arize.instrument()` instead of `llmops.instrument()`
- Adding a new platform (e.g., MLflow) requires only:
  1. New platform module in `_platforms/`
  2. New public accessor module
  3. Optional dependencies in `pyproject.toml`

---

## 10. User Stories

### US1: Explicit Arize Instrumentation

> As a developer using Arize Phoenix, I want to call `llmops.arize.instrument()` so that my code clearly shows which observability platform I'm using.

**Acceptance:**
- `import llmops` succeeds without Arize dependencies
- `llmops.arize.instrument(config_path="llmops.yaml")` initializes Arize telemetry
- Google ADK and Google GenAI calls are traced
- Behavior matches PRD_01 exactly

### US2: Clear Platform Dependencies

> As a developer, I want clear error messages when platform dependencies are missing so that I know exactly what to install.

**Acceptance:**
- `llmops.arize.instrument()` without `arize-otel` installed raises helpful error
- Error message includes: `pip install llmops[arize]`
- Error is raised at call time, not import time

### US3: Multi-Environment Deployment

> As a platform engineer, I want to use the same application code with different platforms in different environments so that local development uses Phoenix while production uses Arize AX.

**Acceptance:**
- Config file can have both `arize:` and `mlflow:` sections
- Each platform reads only its own section
- Environment variable `LLMOPS_CONFIG_PATH` works identically across platforms

### US4: Future Platform Addition (MLflow)

> As a platform maintainer, I want to add MLflow support without modifying the Arize implementation so that platforms are truly isolated.

**Acceptance:**
- New `llmops/mlflow.py` module added
- New `llmops/_platforms/mlflow.py` implementation
- Arize tests continue to pass unchanged
- `llmops.mlflow.instrument()` works with MLflow-specific config

---

## 11. Migration Path

### Breaking Changes

| Change | Impact |
|--------|--------|
| Remove `llmops.instrument()` | Direct calls must change to `llmops.arize.instrument()` |
| Config remains compatible | No changes required to `llmops.yaml` files |

### Migration Steps

1. Update import: `llmops.instrument()` → `llmops.arize.instrument()`
2. Optionally: Update dependencies to `llmops[arize]` for explicit platform install

### Rationale for Breaking Change

We choose a clean break over a deprecation cycle because:
1. PRD_01 is still in draft status (not released)
2. Explicit platform selection is a fundamental design change
3. Deprecation warnings create confusion about the "right" way to use the SDK

---

## 12. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Should the config file name become platform-specific (e.g., `llmops-arize.yaml`)? | Needs discussion |
| 2 | How do we handle shared instrumentation config across platforms with different instrumentor support? | Needs design |
| 3 | Should we provide a `llmops.platforms.available()` discovery function? | Needs discussion |
| 4 | How do we version platform modules independently from the core SDK? | Needs design |

---

## 13. Future Considerations

### 13.1 Potential Platforms

| Platform | Auto-Instrumentation Approach | Status |
|----------|------------------------------|--------|
| **Arize Phoenix** | OpenInference instrumentors | PRD_02 (this document) |
| **Arize AX** | OpenInference instrumentors (same as Phoenix) | PRD_02 (this document) |
| **MLflow** | MLflow autolog | Future PRD |
| **Generic OTLP** | OpenInference or OTel GenAI instrumentors | Future PRD |
| **Datadog** | Datadog LLM Observability SDK | Future PRD |

### 13.2 Advanced Features (Out of Scope)

- Multi-backend routing (send to multiple platforms simultaneously)
- Platform feature detection and capability querying
- Runtime platform switching
- Platform-specific manual instrumentation APIs

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-22
