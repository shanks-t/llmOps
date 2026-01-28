# PRD_01 — Multi-Platform Auto-Instrumentation SDK

**Version:** 0.2
**Date:** 2026-01-22
**Status:** Draft

---

## 1. Problem Statement

Greenfield GenAI applications need fast, low-friction telemetry without learning OpenTelemetry internals. The initial design assumed a single backend (Arize), but this creates limitations:

1. **Implicit Backend Coupling** — A top-level `llmops.instrument()` would be tightly coupled to one backend. Users cannot easily switch to other observability platforms.

2. **No Platform Choice** — Users who want MLflow, Datadog, or generic OTLP backends would need SDK changes or custom integrations.

3. **Unclear Intent** — A generic `instrument()` API doesn't signal which platform's auto-instrumentation is being activated.

We need a thin SDK layer that:
- Provides **explicit platform selection** via namespaced APIs (`llmops.<platform>.instrument()`)
- Reads a config file (`llmops.yaml` preferred, `llmops.yml` supported) supplied explicitly
- Initializes platform-specific telemetry in one call
- Auto-instruments Google ADK and Google GenAI by default
- Remains extensible to future platforms and instrumentors

---

## 2. Product Vision

A **config-driven auto-instrumentation SDK** where:

1. Users call `llmops.instrument(config)` with a configuration file that specifies the platform
2. Platform selection is explicit in configuration, not scattered across code
3. New platforms can be added without changing the public API
4. The developer experience remains simple: import, configure, call `instrument()`, done

### API Design

```python
import llmops

# Single entry point - platform determined by config
llmops.instrument(config="llmops.yaml")

# Or with programmatic config
llmops.instrument(config=llmops.Config(platform="arize", ...))
```

The SDK provides:
- A single `instrument()` entry point with config-driven platform selection
- A unified configuration file with platform-specific sections
- Automatic setup for platform-specific telemetry plus Google ADK and Google GenAI

---

## 3. Target User Persona

### Primary Persona

**Platform-aware developer** building a new GenAI application who wants explicit control over which observability backend is used and benefits from clear, platform-specific documentation and error messages.

### Secondary Persona

**Multi-environment team** that deploys the same application to different environments with different observability backends (e.g., Phoenix locally, Arize AX in production, MLflow in ML team environments).

### Non-Target Persona

- **Existing OpenTelemetry users** with a global tracer provider and dual-backend requirements. These users require manual configuration and filtered span processors, which this SDK will not automate.
- **Backend-agnostic abstraction seeker** who wants a single `instrument()` call that auto-detects the backend. This PRD prioritizes explicit platform selection over implicit detection.

---

## 4. Goals

1. **Explicit Platform Selection** — Platform is explicit in configuration (`platform: arize`)
2. **Platform Isolation** — Each platform's dependencies and logic are encapsulated in its own exporter module
3. **Extensible Architecture** — New platforms (exporters) can be added without modifying existing code
4. **Consistent Interface** — Single `instrument()` entry point, config drives composition
5. **One-call setup** — `instrument()` wires telemetry and auto-instrumentation with no additional code
6. **Config-driven** — Explicit config path via `instrument()` or env var, file-first with overrides
7. **Safety** — Telemetry never breaks business logic

---

## 5. Non-Goals

- **Auto-detection of backend** — We explicitly reject magic detection; users must choose their platform
- **Multi-backend routing** — Sending spans to multiple backends simultaneously is out of scope
- **Supporting dual-backend or existing global tracer provider setups**
- **Replacing OpenTelemetry or platform-specific SDKs**
- **Building custom OpenTelemetry instrumentors**
- **Providing manual instrumentation APIs in this iteration**
- **Full MLflow implementation** — MLflow is a skeleton to validate extensibility

---

## 6. Constraints

| Constraint | Rationale |
|------------|-----------|
| Python >=3.13 | Matches repo baseline |
| Greenfield only | Avoids conflict with existing tracer providers |
| Single backend per call | Ensures safe one-line setup |
| Platform modules are lazy-loaded | Avoid importing platform-specific dependencies until needed |
| Each platform is independently installable | Users only install dependencies for their chosen platform |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | `llmops.instrument(config)` initializes telemetry based on `platform` field in config | Must |
| F2 | `llmops.instrument()` with `platform: arize` initializes Arize telemetry | Must |
| F3 | `llmops.instrument()` auto-instruments Google ADK when enabled | Must |
| F4 | `llmops.instrument()` auto-instruments Google GenAI when enabled | Must |
| F5 | Exporter modules are lazy-loaded (no import-time side effects) | Must |
| F6 | `instrument()` requires an explicit config path (arg or env var) or Config object | Must |
| F7 | `instrument()` accepts `llmops.yaml` (preferred) and `llmops.yml` (supported) | Must |
| F8 | Instrumentors are managed via a central registry | Must |
| F9 | Config schema includes `platform` field and platform-specific sections | Must |
| F10 | Sensitive values (e.g., API keys) can be set via env var substitution | Must |
| F11 | Missing platform dependencies raise `ConfigurationError` with helpful message | Should |
| F12 | Exporters share common config loading and validation infrastructure | Should |
| F13 | Future exporters can be added without public API changes | Should |
| F14 | MLflow exporter exists as a skeleton to validate extensibility | Should |

### 7.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| N1 | Telemetry failures do not raise exceptions to user code | Must |
| N2 | Telemetry must never break business logic | Must |
| N3 | Platform-specific dependencies are optional extras | Must |
| N4 | All setup completes in a single synchronous call | Must |
| N5 | Permissive validation uses a no-op tracer provider on config errors | Must |
| N6 | Strict validation fails startup on config errors (dev only) | Must |
| N7 | Error messages indicate which platform-specific package is missing | Should |
| N8 | Import time for unused platforms is zero | Should |
| N9 | Startup time impact remains minimal | Should |

---

## 8. Architecture

### 8.1 Package Structure

```
llmops/
├── __init__.py              # Re-exports from api/, version
├── exceptions.py            # ConfigurationError
├── api/
│   ├── __init__.py          # Public API re-exports
│   ├── _init.py             # instrument(), shutdown(), is_configured()
│   └── types.py             # Config, ServiceConfig, etc.
├── sdk/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── load.py          # YAML loading, env var substitution
│   ├── lifecycle.py         # Global state management
│   └── pipeline.py          # Exporter dispatch, instrumentation
├── exporters/
│   ├── __init__.py
│   ├── arize/
│   │   ├── __init__.py
│   │   └── exporter.py      # create_arize_provider()
│   └── mlflow/
│       ├── __init__.py
│       └── exporter.py      # create_mlflow_provider()
├── instrumentation/
│   ├── __init__.py
│   ├── _registry.py         # Instrumentor registry
│   ├── google_adk.py        # instrument() wrapper
│   └── google_genai.py      # instrument() wrapper
├── eval/                    # RESERVED: Evaluation (future)
│   └── (structure TBD)
└── _internal/
    ├── __init__.py
    └── telemetry.py         # Shared utilities
```

### 8.2 Exporter Factory Interface

Exporters are implemented as factory functions (not classes or protocols). Each exporter module provides a function that creates a configured TracerProvider.

```python
# Factory signature
def create_{platform}_provider(config: Config) -> TracerProvider:
    """Create platform-specific TracerProvider."""
    ...
```

### 8.3 Config Schema

```yaml
# llmops.yaml

# Required: Platform selection
platform: arize  # or "mlflow"

# Required: Service identification
service:
  name: "my-service"
  version: "1.0.0"  # Optional

# Platform-specific sections (only matching platform is read)
arize:
  endpoint: "http://localhost:6006/v1/traces"
  project_name: "my-project"
  api_key: "${ARIZE_API_KEY}"
  space_id: "${ARIZE_SPACE_ID}"
  transport: "http"
  batch: true

mlflow:
  tracking_uri: "http://localhost:5001"
  experiment_name: "my-experiment"

# Auto-instrumentation configuration (list-based registry)
instrumentation:
  enabled:
    - google_adk
    - google_genai

# Validation mode
validation:
  mode: permissive  # or "strict"
```

---

## 9. Success Criteria

- A greenfield application shows traces after calling `llmops.instrument(config="llmops.yaml")` with `platform: arize`
- No additional manual instrumentation is required for Google ADK or Google GenAI
- Configuration can be set via `llmops.yaml` with optional env var substitution
- The import `import llmops` succeeds without any platform dependencies installed
- `llmops.instrument()` with missing platform dependencies raises `ConfigurationError` with helpful message
- Adding MLflow exporter requires:
  1. New exporter module in `llmops/exporters/mlflow/`
  2. Entry in exporter registry
  3. Optional dependencies in `pyproject.toml`
  4. No changes to public API or existing Arize exporter

---

## 10. User Stories

### US1: Config-Driven Arize Instrumentation

> As a developer using Arize Phoenix, I want to call `llmops.instrument()` with a config file so that platform selection is explicit in configuration.

**Acceptance:**
- `import llmops` succeeds without Arize dependencies
- `llmops.instrument(config="llmops.yaml")` with `platform: arize` initializes Arize telemetry
- Google ADK and Google GenAI calls are traced
- Permissive validation falls back to a no-op tracer provider on config errors

### US2: Clear Platform Dependencies

> As a developer, I want clear error messages when platform dependencies are missing so that I know exactly what to install.

**Acceptance:**
- `llmops.instrument()` with `platform: arize` without `arize-otel` installed raises `ConfigurationError`
- Error message includes: `pip install llmops[arize]`
- Error is raised at init time, not import time

### US3: Multi-Environment Deployment

> As a platform engineer, I want to use the same config file structure with different platforms in different environments so that local development uses Phoenix while production uses Arize AX.

**Acceptance:**
- Config file can have both `arize:` and `mlflow:` sections
- The `platform:` field determines which section is read
- Environment variable `LLMOPS_CONFIG_PATH` works as fallback for config path

### US4: Exporter Extensibility (MLflow Skeleton)

> As a platform maintainer, I want to add MLflow support without modifying the Arize implementation so that exporters are truly isolated.

**Acceptance:**
- New `llmops/exporters/mlflow/` module added
- Arize tests continue to pass unchanged
- `llmops.instrument()` with `platform: mlflow` can be called (returns stub/no-op provider)
- No changes to public API required

---

## 11. Decisions

The following design decisions were made during architecture analysis:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API Style | Single `instrument()` with config-driven platform | Better composability, smaller API surface |
| Exporter Pattern | Factory functions (not Protocol) | Simpler, sufficient for internal use |
| Instrumentor Pattern | Registry with list-based config | Avoids API churn as instrumentors are added |
| Entry Points | Deferred | Not needed for POC, can add later |
| Config Validation | Each exporter validates its own section | Exporter isolation |
| Instrumentor Runner | Shared infrastructure | Reduces duplication, exporters share registry |
| MLflow Scope | Skeleton/stub | Validates extensibility without full implementation |

---

## 12. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Exact env var naming for config path and API keys | Resolved: `LLMOPS_CONFIG_PATH`, platform-specific keys |
| 2 | Minimal config fields for Arize and Phoenix endpoints | Resolved: See config schema above |
| 3 | Default validation mode | Resolved: Permissive |
| 4 | Should we support both API styles? | Resolved: Namespaced only |
| 5 | Entry points in this version? | Resolved: Deferred |

---

## 13. Future Considerations

### 13.1 Potential Platforms

| Platform | Auto-Instrumentation Approach | Status |
|----------|------------------------------|--------|
| **Arize Phoenix** | OpenInference instrumentors | This PRD |
| **Arize AX** | OpenInference instrumentors | This PRD |
| **MLflow** | MLflow autolog | Skeleton in this PRD |
| **Generic OTLP** | OpenInference or OTel GenAI instrumentors | Future |
| **Datadog** | Datadog LLM Observability SDK | Future |

### 13.2 Evaluation (Future)

The SDK will support batch evaluation and CI regression testing via the reserved `llmops.eval` namespace. This will wrap Arize AX evaluation primitives with an SDK-first API.

- Batch evaluation of spans against evaluators (LLM-as-judge, code evaluators)
- CI regression testing with golden datasets
- Programmatic-first API with optional CLI wrapper

**Status:** Namespace reserved. Implementation deferred until Arize AX primitives are better understood.

### 13.3 Advanced Features (Out of Scope)

- Multi-backend routing (send to multiple platforms simultaneously)
- Platform feature detection and capability querying
- Runtime platform switching
- Platform-specific manual instrumentation APIs
- Entry point discovery for third-party exporters

---

## 14. Related PRDs

| PRD | Relationship |
|-----|--------------|
| PRD_02 | Add-on pattern for existing OpenTelemetry users. Uses `filter_to_genai_spans=True` by default, while `instrument()` uses `False`. |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-24
