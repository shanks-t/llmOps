# PRD_01 — Conceptual Architecture

**Version:** 0.2
**Date:** 2026-01-22
**Status:** Draft

---

## 1. Overview

This document describes the high-level shape of the PRD_01 system. It focuses on concepts and relationships, not implementation details. The system provides **platform-explicit auto-instrumentation** where users select their observability backend via namespaced API calls.

**Key Concept:** Platform selection is explicit in the API call (`llmops.<platform>.instrument()`), not hidden in configuration or auto-detected.

---

## 2. Core Concept

A platform-explicit initialization where:
1. User selects a platform via namespaced import (`llmops.arize`, `llmops.mlflow`)
2. Platform module handles backend-specific telemetry setup
3. Shared infrastructure handles config loading and instrumentation

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION CODE                                 │
│                                                                          │
│  import llmops                                                           │
│  llmops.arize.instrument(config_path="llmops.yaml")  ───────────────┐    │
│                                                                     │    │
│  # Google ADK + Google GenAI calls are auto-traced                  │    │
│                                                                     │    │
└──────────────────────────────────────────────────────────────────────────┘
                                                                      │
                                                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          LLMOPS SDK                                       │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    PLATFORM LAYER (lazy-loaded)                    │  │
│  │                                                                    │  │
│  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐             │  │
│  │   │ llmops.arize│   │llmops.mlflow│   │ (future)    │             │  │
│  │   │             │   │  (skeleton) │   │             │             │  │
│  │   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘             │  │
│  │          │                 │                 │                    │  │
│  └──────────┼─────────────────┼─────────────────┼────────────────────┘  │
│             │                 │                 │                       │
│             ▼                 ▼                 ▼                       │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    SHARED INFRASTRUCTURE                           │  │
│  │                                                                    │  │
│  │   ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐  │  │
│  │   │ Config Loader│   │  Validation  │   │ Instrumentor Runner  │  │  │
│  │   │ (path+env)   │   │(strict/perm) │   │ (registry-based)     │  │  │
│  │   └──────────────┘   └──────────────┘   └──────────────────────┘  │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
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

## 3. Primary Flow (Platform-Explicit Auto-Instrumentation)

```
Application startup
        │
        ▼
  import llmops
        │
        ▼
  Access platform module (lazy-loaded)
  llmops.arize ─────────────────────────────────────┐
        │                                           │
        │                              ┌────────────▼────────────┐
        │                              │ Check platform deps     │
        │                              │ (arize-otel installed?) │
        │                              └────────────┬────────────┘
        │                                           │
        ▼                                           ▼
  llmops.arize.instrument(config_path)    ImportError if missing
        │
        ▼
  Load config (shared infrastructure)
        │
        ▼
  Extract platform section (arize:) + shared sections
        │
        ▼
  Platform creates TracerProvider
  (arize.otel.register for Arize)
        │
        ▼
  Apply auto-instrumentation
  (shared runner with platform's instrumentor registry)
        │
        ▼
  Register atexit handler
        │
        ▼
  Return TracerProvider
        │
        ▼
  GenAI spans exported to selected backend
```

---

## 4. Platform Selection Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER CODE                                    │
│                                                                 │
│   import llmops                                                 │
│   llmops.arize.instrument()     # Explicit platform selection   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LAZY MODULE LOADING                             │
│                                                                 │
│   llmops.__getattr__("arize")                                   │
│       │                                                         │
│       ▼                                                         │
│   from llmops import arize  # Only now imported                 │
│       │                                                         │
│       ▼                                                         │
│   Return arize module                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PLATFORM MODULE                                 │
│                                                                 │
│   arize.instrument(config_path)                                 │
│       │                                                         │
│       ├──▶ Validate arize-otel is installed                     │
│       │                                                         │
│       ├──▶ Load config, extract arize: section                  │
│       │                                                         │
│       ├──▶ Call arize.otel.register(...)                        │
│       │                                                         │
│       └──▶ Apply instrumentors via shared runner                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Configuration Flow

```
┌──────────────────┐     ┌─────────────────────────────────────────┐
│ config path arg  │────▶│           SHARED CONFIG LOADER          │
└──────────────────┘     │                                         │
                         │  - Resolves path (arg or env var)       │
┌──────────────────┐     │  - Parses YAML                          │
│ LLMOPS_CONFIG    │────▶│  - Substitutes env vars                 │
│ _PATH env var    │     │  - Returns raw config dict              │
└──────────────────┘     └──────────────────┬──────────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────────┐
                         │        PLATFORM-SPECIFIC PARSING        │
                         │                                         │
                         │  Platform extracts its section:         │
                         │  - arize: → ArizePlatform               │
                         │  - mlflow: → MLflowPlatform             │
                         │                                         │
                         │  Plus shared sections:                  │
                         │  - service:                             │
                         │  - instrumentation:                     │
                         │  - validation:                          │
                         └──────────────────┬──────────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────────┐
                         │          VALIDATED CONFIG               │
                         │                                         │
                         │  LLMOpsConfig(                          │
                         │    service=ServiceConfig(...),          │
                         │    arize=ArizeConfig(...),  # or mlflow │
                         │    instrumentation=...,                 │
                         │    validation=...,                      │
                         │  )                                      │
                         └─────────────────────────────────────────┘
```

---

## 6. Key Invariants

1. **Telemetry never breaks business logic.**
   - All SDK failures are caught and logged
   - No exceptions propagate to user code after initialization

2. **Platform selection is explicit.**
   - Users must call `llmops.<platform>.instrument()`
   - No auto-detection or implicit platform selection

3. **Platform modules are lazy-loaded.**
   - `import llmops` does not import platform dependencies
   - Platform deps only loaded when platform is accessed

4. **Each platform instrument() call configures exactly one backend.**
   - Single tracer provider per invocation
   - No multi-backend routing within a single call

5. **Platforms are isolated.**
   - Adding a new platform doesn't modify existing platforms
   - Each platform owns its telemetry setup logic

6. **Configuration is file-first with explicit path selection.**
   - Config path via argument or `LLMOPS_CONFIG_PATH`
   - Shared sections + platform-specific sections

---

## 7. Separation of Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Application code** | Calls `llmops.<platform>.instrument()` and runs business logic |
| **Package root (`__init__.py`)** | Lazy-loads platform modules on first access via `__getattr__` |
| **Platform module** | Validates deps, exposes `instrument()` entry point |
| **Platform implementation** | Creates platform-specific TracerProvider, defines instrumentor registry |
| **Shared config loader** | Resolves file path, parses YAML, substitutes env vars |
| **Platform config parser** | Extracts platform-specific section, validates fields |
| **Instrumentor runner** | Applies auto-instrumentation from platform's registry |

---

## 8. Extension Points

### 8.1 Platform Registry (Conceptual)

```
Platform Registry
├── arize      → OpenInference instrumentors, arize.otel.register
├── mlflow     → MLflow autolog (skeleton)
└── (future)   → Additional backends
```

New platforms are added by:
1. Creating a new platform implementation (`llmops/_platforms/<platform>.py`)
2. Creating a public module (`llmops/<platform>.py`)
3. Adding lazy accessor in `llmops/__init__.py`
4. Adding optional dependencies in `pyproject.toml`

**Key invariant:** Adding a new platform requires no changes to existing platform code.

### 8.2 Instrumentor Registry (Per Platform)

```
Arize Instrumentor Registry
├── google_adk    → GoogleADKInstrumentor (enabled by default)
├── google_genai  → GoogleGenAIInstrumentor (enabled by default)
└── (future)      → OpenAIInstrumentor, etc.

MLflow Instrumentor Registry (skeleton)
├── gemini        → mlflow.gemini.autolog()
└── openai        → mlflow.openai.autolog()
```

Each platform defines its own instrumentor registry. The `instrumentation:` config section is shared, but availability depends on the platform.

---

## 9. Platform Interface (Conceptual)

All platforms implement the same interface (Protocol):

```
┌─────────────────────────────────────────────────────────────────┐
│                     Platform Protocol                            │
├─────────────────────────────────────────────────────────────────┤
│  name: str              # "arize", "mlflow", etc.               │
│  config_section: str    # YAML section name                     │
│  install_extra: str     # pip extra name                        │
├─────────────────────────────────────────────────────────────────┤
│  create_tracer_provider(config) -> TracerProvider               │
│  get_instrumentor_registry() -> list[...]                       │
└─────────────────────────────────────────────────────────────────┘
```

This ensures consistent behavior across all platforms while allowing platform-specific implementation details.

---

## 10. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_01.md` | Requirements and success criteria |
| `docs/reference_architecture/REFERENCE_ARCHITECTURE_01.md` | Architectural patterns and invariants |
| `docs/api_spec/API_SPEC_01.md` | Public interfaces and configuration contracts |
| `docs/analysis/PLATFORM_ARCHITECTURE_ANALYSIS.md` | Analysis of architectural options |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-22
