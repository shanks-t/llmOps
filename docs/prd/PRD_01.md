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

A **platform-explicit SDK** where:

1. Users call `llmops.<platform>.instrument()` to clearly indicate their observability backend
2. Each platform module encapsulates its specific setup logic and dependencies
3. New platforms can be added without changing the core SDK interface
4. The developer experience remains simple: import, call, done

### API Design

```python
import llmops

# Arize/Phoenix backend
llmops.arize.instrument(config_path="llmops.yaml")

# MLflow backend (skeleton implementation)
llmops.mlflow.instrument(config_path="llmops.yaml")
```

The SDK provides:
- Platform-namespaced `instrument()` entry points
- A single-user interface for configuration (shared config file with platform-specific sections)
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

1. **Explicit Platform Selection** — The API call clearly indicates which platform is being used
2. **Platform Isolation** — Each platform's dependencies and logic are encapsulated in its own module
3. **Extensible Architecture** — New platforms can be added without modifying existing platform modules
4. **Consistent Interface** — All platform modules expose the same `instrument()` signature
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
| F1 | Each platform exposes `llmops.<platform>.instrument(config_path)` | Must |
| F2 | `llmops.arize.instrument()` initializes Arize telemetry and returns a tracer provider | Must |
| F3 | `llmops.arize.instrument()` auto-instruments Google ADK | Must |
| F4 | `llmops.arize.instrument()` auto-instruments Google GenAI | Must |
| F5 | Platform modules are lazy-imported (no import-time side effects) | Must |
| F6 | `instrument()` requires an explicit config path (arg or env var) | Must |
| F7 | `instrument()` accepts `llmops.yaml` (preferred) and `llmops.yml` (supported) | Must |
| F8 | Each platform module defines its supported instrumentors | Must |
| F9 | Config schema includes platform-specific sections (`arize:`, `mlflow:`) | Must |
| F10 | Sensitive values (e.g., API keys) can be set via env var overrides | Must |
| F11 | Invalid platform access raises `ImportError` with helpful message | Should |
| F12 | Platform modules share common config loading and validation infrastructure | Should |
| F13 | Future platforms can be added without core SDK changes | Should |
| F14 | `llmops.mlflow.instrument()` exists as a skeleton to validate extensibility | Should |

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
├── __init__.py           # Lazy platform accessors via __getattr__
├── exceptions.py         # Shared exceptions (ConfigurationError)
├── config.py             # Shared config loading and validation
├── arize.py              # Public: llmops.arize.instrument()
├── mlflow.py             # Public: llmops.mlflow.instrument() (skeleton)
├── _platforms/           # Internal platform implementations
│   ├── __init__.py
│   ├── _base.py          # Platform Protocol definition
│   ├── _registry.py      # Shared instrumentor runner
│   ├── arize.py          # ArizePlatform implementation
│   └── mlflow.py         # MLflowPlatform implementation (skeleton)
└── _internal/            # Shared internal utilities
    └── telemetry.py      # Common telemetry helpers
```

### 8.2 Platform Interface

Each platform module must implement the Platform Protocol:

```python
from typing import Protocol

class Platform(Protocol):
    @property
    def name(self) -> str:
        """Platform identifier (e.g., 'arize', 'mlflow')."""
        ...

    @property
    def config_section(self) -> str:
        """Config file section name."""
        ...

    @property
    def install_extra(self) -> str:
        """pip extra name (e.g., 'arize' for pip install llmops[arize])."""
        ...

    def create_tracer_provider(self, config: LLMOpsConfig) -> TracerProvider:
        """Create platform-specific TracerProvider."""
        ...

    def get_instrumentor_registry(self) -> list[tuple[str, str, str]]:
        """Return list of (config_key, module_path, class_name) tuples."""
        ...
```

### 8.3 Config Schema

```yaml
# llmops.yaml
service:
  name: "my-service"
  version: "1.0.0"

# Arize-specific configuration (used by llmops.arize.instrument())
# These fields map directly to arize.otel.register() parameters
arize:
  endpoint: "http://localhost:6006/v1/traces"
  project_name: "my-project"
  api_key: "${ARIZE_API_KEY}"
  space_id: "${ARIZE_SPACE_ID}"
  transport: "http"
  batch: true
  log_to_console: false
  verbose: false

# MLflow-specific configuration (used by llmops.mlflow.instrument())
mlflow:
  tracking_uri: "http://localhost:5001"
  experiment_name: "my-experiment"

# Instrumentation settings (shared across platforms)
instrumentation:
  google_adk: true
  google_genai: true

# Validation settings
validation:
  mode: permissive  # strict or permissive (default permissive)
```

---

## 9. Success Criteria

- A greenfield application shows traces after calling `llmops.arize.instrument()`
- No additional manual instrumentation is required for Google ADK or Google GenAI
- Configuration can be set via `llmops.yaml` with optional env overrides
- The import `import llmops` succeeds without any platform dependencies installed
- `llmops.arize.instrument()` fails gracefully with helpful message if `arize-otel` is not installed
- Adding MLflow skeleton requires:
  1. New platform module in `_platforms/`
  2. New public accessor module
  3. Optional dependencies in `pyproject.toml`
  4. No changes to existing Arize code

---

## 10. User Stories

### US1: Explicit Arize Instrumentation

> As a developer using Arize Phoenix, I want to call `llmops.arize.instrument()` so that my code clearly shows which observability platform I'm using.

**Acceptance:**
- `import llmops` succeeds without Arize dependencies
- `llmops.arize.instrument(config_path="llmops.yaml")` initializes Arize telemetry
- Google ADK and Google GenAI calls are traced
- Permissive validation falls back to a no-op tracer provider on config errors

### US2: Clear Platform Dependencies

> As a developer, I want clear error messages when platform dependencies are missing so that I know exactly what to install.

**Acceptance:**
- `llmops.arize.instrument()` without `arize-otel` installed raises helpful error
- Error message includes: `pip install llmops[arize]`
- Error is raised at call time, not import time

### US3: Multi-Environment Deployment

> As a platform engineer, I want to use the same config file structure with different platforms in different environments so that local development uses Phoenix while production uses Arize AX.

**Acceptance:**
- Config file can have both `arize:` and `mlflow:` sections
- Each platform reads only its own section plus shared sections
- Environment variable `LLMOPS_CONFIG_PATH` works identically across platforms

### US4: Platform Extensibility (MLflow Skeleton)

> As a platform maintainer, I want to add MLflow support without modifying the Arize implementation so that platforms are truly isolated.

**Acceptance:**
- New `llmops/mlflow.py` module added
- New `llmops/_platforms/mlflow.py` implementation (skeleton)
- Arize tests continue to pass unchanged
- `llmops.mlflow.instrument()` can be called (returns stub/no-op provider)

---

## 11. Decisions

The following design decisions were made during architecture analysis:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Platform Registry Pattern | Static modules with lazy loading | Excellent IDE support, simple DX |
| Instrumentation Interface | Protocol (not ABC) | Duck typing, easier testing, more Pythonic |
| API Style | Namespaced only (`llmops.arize.instrument()`) | Single clear path, no ambiguity |
| Entry Points | Deferred | Not needed for POC, can add later |
| Config Validation | Each platform validates its own section | Platform isolation |
| Instrumentor Runner | Shared infrastructure | Reduces duplication, platforms provide registry |
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

### 13.2 Advanced Features (Out of Scope)

- Multi-backend routing (send to multiple platforms simultaneously)
- Platform feature detection and capability querying
- Runtime platform switching
- Platform-specific manual instrumentation APIs
- Entry point discovery for third-party platforms

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-22
