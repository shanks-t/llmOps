# Conceptual Architecture

**Version:** 0.3
**Date:** 2026-01-26
**Status:** Draft
**Covers:** PRD_01 (Auto-Instrumentation), PRD_03 (Evaluator Templates)

---

## 1. Overview

This document describes the high-level shape of the llmops SDK. It focuses on concepts and relationships, not implementation details. The system provides **platform-explicit capabilities** where users select their observability backend via namespaced API calls, then access platform-specific features.

**Key Concepts:**
- Platform selection is explicit in the API call (`llmops.<platform>.*`)
- Each platform provides multiple capabilities (telemetry, evaluation, etc.)
- Capabilities within a platform are independent and lazy-loaded

---

## 2. Core Concept

A platform-explicit SDK where:
1. User selects a platform via namespaced import (`llmops.arize`, `llmops.mlflow`)
2. Platform module provides access to capabilities (telemetry, evaluation)
3. Each capability is lazy-loaded and independent
4. Shared infrastructure handles common concerns (config, validation)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION CODE                                 │
│                                                                          │
│  import llmops                                                           │
│                                                                          │
│  # Telemetry (PRD_01)                                                    │
│  llmops.arize.instrument(config_path="llmops.yaml")                      │
│                                                                          │
│  # Evaluation (PRD_03)                                                   │
│  faithfulness = llmops.arize.evals.faithfulness(llm=llm)                 │
│  scores = faithfulness.evaluate({"input": ..., "output": ..., ...})      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          LLMOPS SDK                                       │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    PLATFORM LAYER (lazy-loaded)                    │  │
│  │                                                                    │  │
│  │   ┌─────────────────────────────┐   ┌─────────────────────────┐   │  │
│  │   │       llmops.arize          │   │     llmops.mlflow       │   │  │
│  │   │  ┌──────────┬───────────┐   │   │       (skeleton)        │   │  │
│  │   │  │instrument│   evals   │   │   │                         │   │  │
│  │   │  │ (PRD_01) │  (PRD_03) │   │   │                         │   │  │
│  │   │  └──────────┴───────────┘   │   │                         │   │  │
│  │   └─────────────────────────────┘   └─────────────────────────┘   │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                    │                              │                       │
│                    ▼                              ▼                       │
│  ┌────────────────────────────────┐  ┌────────────────────────────────┐  │
│  │   TELEMETRY INFRASTRUCTURE     │  │   EVALUATION INFRASTRUCTURE    │  │
│  │                                │  │                                │  │
│  │  ┌──────────┐ ┌─────────────┐  │  │  ┌──────────┐ ┌─────────────┐  │  │
│  │  │ Config   │ │Instrumentor │  │  │  │ Template │ │  Evaluator  │  │  │
│  │  │ Loader   │ │  Runner     │  │  │  │ Factory  │ │  Registry   │  │  │
│  │  └──────────┘ └─────────────┘  │  │  └──────────┘ └─────────────┘  │  │
│  │                                │  │                                │  │
│  └────────────────────────────────┘  └────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                    │                              │
                    ▼                              ▼
┌──────────────────────────────┐  ┌──────────────────────────────────────┐
│    EXTERNAL: TELEMETRY       │  │      EXTERNAL: EVALUATION            │
│                              │  │                                      │
│  arize-otel, openinference   │  │  arize-phoenix-evals, LLM providers  │
│  opentelemetry-sdk           │  │  (openai, anthropic, etc.)           │
└──────────────────────────────┘  └──────────────────────────────────────┘
```

---

## 3. Primary Flows

### 3.1 Telemetry Flow (PRD_01)

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

### 3.2 Evaluation Flow (PRD_03)

```
Application code
        │
        ▼
  Access evals module (lazy-loaded)
  llmops.arize.evals ───────────────────────────────┐
        │                                           │
        │                              ┌────────────▼────────────┐
        │                              │ Check evals deps        │
        │                              │ (phoenix-evals?)        │
        │                              └────────────┬────────────┘
        │                                           │
        ▼                                           ▼
  llmops.arize.evals.faithfulness(llm)    ImportError if missing
        │
        ▼
  Create evaluator (wraps phoenix.evals)
        │
        ├─▶ Built-in template (faithfulness)
        │   └─▶ FaithfulnessEvaluator from phoenix.evals
        │
        └─▶ Custom template (create_classifier)
            └─▶ ClassificationEvaluator from phoenix.evals
        │
        ▼
  Return configured evaluator
        │
        ▼
  evaluator.evaluate({"input":..., "output":..., ...})
        │
        ▼
  LLM judge executes prompt
        │
        ▼
  Return Score objects (label, score, explanation)
```

### 3.3 Registry Flow (PRD_03)

```
Setup phase
        │
        ▼
  llmops.arize.evals.register("my_eval", evaluator)
        │
        ▼
  Store in in-memory registry
  _REGISTRY["my_eval"] = evaluator
        │
        ▼
  ─────────────────────────────────────
        │
        ▼
Usage phase (any module)
        │
        ▼
  llmops.arize.evals.get("my_eval")
        │
        ▼
  Retrieve from registry
        │
        ▼
  Return evaluator instance
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

### Telemetry Invariants (PRD_01)

1. **Telemetry never breaks business logic.**
   - All SDK failures are caught and logged
   - No exceptions propagate to user code after initialization

2. **Platform selection is explicit.**
   - Users must call `llmops.<platform>.instrument()`
   - No auto-detection or implicit platform selection

3. **Each platform instrument() call configures exactly one backend.**
   - Single tracer provider per invocation
   - No multi-backend routing within a single call

4. **Configuration is file-first with explicit path selection.**
   - Config path via argument or `LLMOPS_CONFIG_PATH`
   - Shared sections + platform-specific sections

### Evaluation Invariants (PRD_03)

5. **Evaluation capability is independent of telemetry.**
   - `llmops.arize.evals` does not require `instrument()` to be called
   - Evaluators work standalone without TracerProvider
   - Separate dependency chain (phoenix.evals vs arize.otel)

6. **LLM configuration is user-provided for evaluations.**
   - SDK does not manage LLM API keys or model selection
   - Users create LLM instances and pass to factory functions
   - No config file section for eval LLMs (in current scope)

7. **Evaluator registry is process-local and non-persistent.**
   - In-memory storage only
   - Registry clears when process ends
   - Thread-safe for concurrent access

### Shared Invariants

8. **Platform modules are lazy-loaded.**
   - `import llmops` does not import platform dependencies
   - Platform deps only loaded when platform is accessed

9. **Sub-capabilities within a platform are lazy-loaded.**
   - `llmops.arize` can be accessed without loading `llmops.arize.evals`
   - Each capability loads only when accessed
   - Missing dependencies raise `ImportError` with helpful message

10. **Platforms are isolated.**
    - Adding a new platform doesn't modify existing platforms
    - Each platform owns its capability implementations

---

## 7. Separation of Responsibilities

### Core Components

| Component | Responsibility |
|-----------|----------------|
| **Application code** | Calls SDK APIs and runs business logic |
| **Package root (`__init__.py`)** | Lazy-loads platform modules on first access via `__getattr__` |
| **Platform module** | Exposes capabilities (`instrument()`, `evals`), lazy-loads sub-capabilities |

### Telemetry Components (PRD_01)

| Component | Responsibility |
|-----------|----------------|
| **Platform implementation** | Creates platform-specific TracerProvider, defines instrumentor registry |
| **Shared config loader** | Resolves file path, parses YAML, substitutes env vars |
| **Platform config parser** | Extracts platform-specific section, validates fields |
| **Instrumentor runner** | Applies auto-instrumentation from platform's registry |

### Evaluation Components (PRD_03)

| Component | Responsibility |
|-----------|----------------|
| **Evals module** | Exposes evaluation API (`faithfulness()`, `create_classifier()`) |
| **Template factory** | Creates evaluators from built-in or custom templates |
| **Evaluator registry** | Stores/retrieves evaluators by name (in-memory) |
| **Built-in templates** | Pre-configured evaluators using phoenix.evals (Faithfulness, etc.) |

---

## 8. Extension Points

### 8.1 Platform Registry (Conceptual)

```
Platform Registry
├── arize      → Telemetry + Evaluation capabilities
├── mlflow     → Telemetry capability (skeleton)
└── (future)   → Additional backends
```

New platforms are added by:
1. Creating a new platform implementation (`llmops/_platforms/<platform>.py`)
2. Creating a public module (`llmops/<platform>.py`)
3. Adding lazy accessor in `llmops/__init__.py`
4. Adding optional dependencies in `pyproject.toml`

**Key invariant:** Adding a new platform requires no changes to existing platform code.

### 8.2 Instrumentor Registry (Per Platform, PRD_01)

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

### 8.3 Evaluator Registry (Per Platform, PRD_03)

```
Arize Evaluator Registry (In-Memory)
├── (user-registered)  → Custom evaluators via register()
└── (built-in access)  → faithfulness(), create_classifier()

Built-in Templates
├── faithfulness  → FaithfulnessEvaluator (phoenix.evals)
└── (future)      → DocumentRelevance, Correctness, Toxicity, etc.
```

The evaluator registry is runtime-populated. Built-in templates are accessed directly via factory functions, while custom evaluators can be registered for named retrieval.

### 8.4 Adding a New Capability to a Platform

New capabilities (beyond telemetry and evaluation) can be added:
1. Create capability module (`llmops/evals/arize/` or `llmops/<capability>/arize/`)
2. Add lazy accessor in platform module (`llmops/arize.py`)
3. Add optional dependencies in `pyproject.toml`

**Key invariant:** Adding a new capability requires no changes to existing capabilities.

---

## 9. Platform Interface (Conceptual)

### 9.1 Telemetry Interface (PRD_01)

All platforms providing telemetry implement the Platform Protocol:

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

### 9.2 Evaluation Interface (PRD_03)

Evaluation modules expose a consistent API:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Evals Module API                             │
├─────────────────────────────────────────────────────────────────┤
│  Built-in Templates                                             │
│    faithfulness(llm) -> Evaluator                               │
│    (future: relevance, correctness, toxicity, etc.)             │
├─────────────────────────────────────────────────────────────────┤
│  Factory Functions                                              │
│    create_classifier(name, prompt, llm, choices) -> Evaluator   │
├─────────────────────────────────────────────────────────────────┤
│  Registry Functions                                             │
│    register(name, evaluator) -> None                            │
│    get(name) -> Evaluator                                       │
│    list() -> list[str]                                          │
│    clear() -> None                                              │
└─────────────────────────────────────────────────────────────────┘
```

This ensures consistent behavior across all platforms while allowing platform-specific implementation details.

---

## 10. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_01.md` | Auto-instrumentation requirements |
| `docs/prd/PRD_03.md` | Evaluator templates requirements |
| `docs/reference_architecture/REFERENCE_ARCHITECTURE_01.md` | Architectural patterns and invariants |
| `docs/api_spec/API_SPEC_01.md` | Telemetry public interfaces |
| `docs/analysis/PLATFORM_ARCHITECTURE_ANALYSIS.md` | Analysis of design options |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-26
