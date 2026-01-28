# PRD_01 — Conceptual Architecture

**Version:** 0.2
**Date:** 2026-01-27
**Status:** Draft

---

## 1. Overview

This document describes the high-level shape of the PRD_01 system. It focuses on concepts and relationships, not implementation details. The system provides **config-driven auto-instrumentation** where users configure their observability backend via a YAML file or programmatic `Config` object.

**Key Concept:** A single `instrument()` entry point with configuration determining which backend, instrumentors, and behaviors are active. The public API is minimal and stable; complexity is hidden in internal layers.

---

## 2. Core Concept

A config-driven initialization where:
1. User calls `llmops.instrument(config="llmops.yaml")`
2. Config specifies `platform: arize` (or `mlflow`)
3. SDK dispatches to the appropriate exporter factory
4. Auto-instrumentation is applied based on config

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION CODE                                 │
│                                                                          │
│  import llmops                                                           │
│  llmops.instrument(config="llmops.yaml")  ──────────────────────────────┐      │
│                                                                   │      │
│  # Google ADK + Google GenAI calls are auto-traced                │      │
│                                                                   │      │
└──────────────────────────────────────────────────────────────────────────┘
                                                                    │
                                                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          LLMOPS SDK                                       │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      PUBLIC API LAYER (llmops/api/)                │  │
│  │                                                                    │  │
│  │   instrument()    shutdown()    is_configured()    Config types     │  │
│  │                                                                    │  │
│  └──────────────────────────────┬─────────────────────────────────────┘  │
│                                 │                                        │
│                                 ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      SDK LAYER (llmops/sdk/)                       │  │
│  │                                                                    │  │
│  │   ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐  │  │
│  │   │ Config Loader│   │  Lifecycle   │   │ Pipeline Composition │  │  │
│  │   │ (YAML + env) │   │  Management  │   │ (exporter dispatch)  │  │  │
│  │   └──────────────┘   └──────────────┘   └──────────────────────┘  │  │
│  │                                                                    │  │
│  └──────────────────────────────┬─────────────────────────────────────┘  │
│                                 │                                        │
│             ┌───────────────────┼───────────────────┐                    │
│             ▼                   ▼                   ▼                    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐    │
│  │    EXPORTERS    │ │ INSTRUMENTATION │ │      _internal/         │    │
│  │                 │ │                 │ │                         │    │
│  │ arize/          │ │ google_adk.py   │ │ telemetry utilities     │    │
│  │ mlflow/         │ │ google_genai.py │ │                         │    │
│  │                 │ │ (registry)      │ │                         │    │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  ARIZE BACKEND   │ │  MLFLOW BACKEND  │ │  FUTURE BACKEND  │
│                  │ │    (skeleton)    │ │                  │
│ Phoenix/Arize AX │ │ MLflow Tracking  │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 3. Primary Flow (Config-Driven Auto-Instrumentation)

```
Application startup
        │
        ▼
  import llmops
        │
        ▼
  llmops.instrument(config="llmops.yaml")
        │
        ▼
  ┌─────────────────────────────────────┐
  │         CONFIG LOADING              │
  │                                     │
  │  - Resolve path (arg or env var)    │
  │  - Parse YAML                       │
  │  - Substitute environment variables │
  │  - Validate configuration           │
  └──────────────────┬──────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │       PLATFORM DISPATCH             │
  │                                     │
  │  Read `platform:` field from config │
  │       │                             │
  │       ├── "arize"  → Arize factory  │
  │       └── "mlflow" → MLflow factory │
  └──────────────────┬──────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │      EXPORTER CREATION              │
  │                                     │
  │  Factory creates TracerProvider     │
  │  (e.g., arize.otel.register())      │
  │  Set as global tracer provider      │
  └──────────────────┬──────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │      AUTO-INSTRUMENTATION           │
  │                                     │
  │  Apply instrumentors from registry  │
  │  based on `instrumentation.enabled` │
  │  list in config                     │
  └──────────────────┬──────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │      LIFECYCLE SETUP                │
  │                                     │
  │  - Register atexit handler          │
  │  - Mark SDK as configured           │
  └──────────────────┬──────────────────┘
                     │
                     ▼
  GenAI spans exported to selected backend
```

---

## 4. Configuration Flow

```
┌──────────────────┐     ┌─────────────────────────────────────────┐
│ config path arg  │────▶│           SHARED CONFIG LOADER          │
└──────────────────┘     │                                         │
                         │  - Resolves path (arg or env var)       │
┌──────────────────┐     │  - Parses YAML                          │
│ LLMOPS_CONFIG    │────▶│  - Substitutes env vars                 │
│ _PATH env var    │     │  - Returns Config object                │
└──────────────────┘     └──────────────────┬──────────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────────┐
                         │          PLATFORM DISPATCH              │
                         │                                         │
                         │  `platform:` field determines exporter: │
                         │  - "arize" → llmops/exporters/arize/    │
                         │  - "mlflow" → llmops/exporters/mlflow/  │
                         │                                         │
                         │  Shared sections used by all platforms: │
                         │  - service:                             │
                         │  - instrumentation:                     │
                         │  - validation:                          │
                         └─────────────────────────────────────────┘
```

---

## 5. Key Invariants

1. **Telemetry never breaks business logic.**
   - All SDK failures are caught and logged
   - No exceptions propagate to user code after initialization (in permissive mode)

2. **Platform selection is explicit in configuration.**
   - The `platform:` field must be specified in config
   - No auto-detection or implicit platform selection
   - Platform name is visible in configuration, not hidden in code

3. **Exporter dependencies are lazy-loaded.**
   - `import llmops` does not import platform dependencies
   - Exporter modules loaded only when `instrument()` dispatches to them
   - Missing dependencies raise `ConfigurationError` at init time

4. **Each instrument() call configures exactly one backend.**
   - Single TracerProvider per invocation
   - No multi-backend routing within a single call

5. **Exporters are isolated.**
   - Adding a new exporter doesn't modify existing exporters
   - Each exporter owns its TracerProvider creation logic

6. **Configuration is file-first with explicit path selection.**
   - Config path via argument or `LLMOPS_CONFIG_PATH`
   - Shared sections + platform-specific sections

---

## 6. Separation of Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Application code** | Calls `llmops.instrument()` and runs business logic |
| **Public API (`llmops/api/`)** | Stable interface: `instrument()`, `shutdown()`, `is_configured()`, `Config` types |
| **SDK layer (`llmops/sdk/`)** | Config loading, lifecycle management, pipeline composition |
| **Exporters (`llmops/exporters/`)** | Platform-specific TracerProvider creation |
| **Instrumentation (`llmops/instrumentation/`)** | Auto-instrumentation wrappers and registry |
| **Config loader** | Resolves file path, parses YAML, substitutes env vars |
| **Pipeline composition** | Dispatches to exporter factory, applies instrumentors |

---

## 7. Extension Points

### 7.1 Exporter Registry

```
Exporter Registry (in pipeline.py)
├── arize      → llmops/exporters/arize/exporter.py
├── mlflow     → llmops/exporters/mlflow/exporter.py (skeleton)
└── (future)   → Additional backends
```

New exporters are added by:
1. Creating exporter module in `llmops/exporters/{name}/`
2. Implementing factory function: `create_{name}_provider(config) -> TracerProvider`
3. Registering in exporter dispatch dictionary
4. Adding optional dependencies in `pyproject.toml`

**Key invariant:** Adding a new exporter requires no changes to `llmops/api/` or existing exporters.

### 7.2 Instrumentor Registry

```
Instrumentor Registry
├── google_adk    → GoogleADKInstrumentor wrapper
├── google_genai  → GoogleGenAIInstrumentor wrapper
├── openai        → (future) OpenAIInstrumentor
├── anthropic     → (future) AnthropicInstrumentor
└── ...
```

Instrumentors are managed via a central registry. Configuration specifies which instrumentors to enable via a list, not individual boolean fields:

```yaml
instrumentation:
  enabled:
    - google_adk
    - google_genai
```

New instrumentors are added by:
1. Creating wrapper module in `llmops/instrumentation/{name}.py`
2. Registering in the instrumentor registry
3. No changes to public API types required

### 7.3 Evaluator Registry (Future)

Reserved extension point. Will follow the same registry pattern as instrumentors.

---

## 8. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_01.md` | Requirements and success criteria |
| `docs/reference_architecture/REFERENCE_ARCHITECTURE_01.md` | Architectural patterns and invariants |
| `docs/DESIGN_PHILOSOPHY.md` | Design principles and API stability rules |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-27
