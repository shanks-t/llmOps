# PRD_01 — Reference Architecture

**Version:** 0.2
**Date:** 2026-01-27
**Status:** Draft

---

## 1. Purpose

This document defines how the PRD_01 system should be built. It codifies architectural invariants, boundaries, and patterns for a **config-driven auto-instrumentation SDK** with a single entry point.

---

## 2. Architectural Shape

### 2.1 Components

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| **Public API** | `instrument()`, `shutdown()`, `is_configured()`, `Config` types | Stable, semver-major only |
| **SDK Layer** | Config loading, lifecycle, pipeline composition | Internal, may change |
| **Exporters** | Platform-specific TracerProvider creation | Internal, isolated per-platform |
| **Instrumentation** | Auto-instrumentation wrappers + registry | Internal, registry-based |

### 2.2 Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            PUBLIC API LAYER                              │
│                                                                         │
│   llmops.instrument(config)    llmops.shutdown()    llmops.is_configured()    │
│   llmops.Config          llmops.ConfigurationError                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              SDK LAYER                                   │
│                                                                         │
│   ┌─────────────────────┐    ┌─────────────────────┐                    │
│   │    Config Loading   │    │ Pipeline Composition│                    │
│   │    (YAML + env)     │    │ (exporter dispatch) │                    │
│   └─────────────────────┘    └─────────────────────┘                    │
│                                                                         │
│   ┌─────────────────────┐    ┌─────────────────────┐                    │
│   │  Lifecycle Mgmt     │    │   Validation        │                    │
│   │  (state, shutdown)  │    │   (strict/permissive)│                   │
│   └─────────────────────┘    └─────────────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            EDGE LAYERS                                   │
│                                                                         │
│   ┌─────────────────────────────┐    ┌─────────────────────────────┐   │
│   │         EXPORTERS           │    │      INSTRUMENTATION        │   │
│   │                             │    │                             │   │
│   │  arize/exporter.py          │    │  google_adk.py              │   │
│   │  mlflow/exporter.py         │    │  google_genai.py            │   │
│   │  (factory functions)        │    │  _registry.py               │   │
│   └─────────────────────────────┘    └─────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL DEPENDENCIES                            │
│                                                                         │
│   arize-otel          mlflow            opentelemetry-sdk               │
│   openinference-*     mlflow-genai      opentelemetry-api               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Dependency Rules

**Strict downward-only dependencies:**

```
Public API (llmops/api/)
     │
     ▼
SDK Layer (llmops/sdk/)
     │
     ├──────────────────────────────┐
     ▼                              ▼
Exporters (llmops/exporters/)    Instrumentation (llmops/instrumentation/)
     │                              │
     ▼                              ▼
External SDKs (arize.otel, etc)  External instrumentors (openinference-*)
```

**Rules:**
- No component may depend on a higher-level component
- Exporter implementations may not depend on each other
- SDK layer may not import vendor SDKs directly
- Instrumentation wrappers may not depend on exporters

---

## 3. Core Invariants

These invariants must hold across all implementations.

### 3.1 Telemetry Safety

```
INVARIANT 1: Telemetry never breaks business logic
```

**Rules:**
- No SDK call raises exceptions to user code after initialization (permissive mode)
- `instrument()` in permissive mode logs failures and returns with no-op provider
- `instrument()` in strict mode raises `ConfigurationError` for invalid config
- Instrumentor errors do not prevent application startup
- Configuration errors fail fast at startup, not during runtime

### 3.2 Explicit Platform Selection

```
INVARIANT 2: Platform selection is explicit in configuration
```

**Rules:**
- Users must specify `platform:` field in configuration
- No auto-detection of platform from environment
- No default platform if none specified
- Platform determines which exporter factory is invoked

### 3.3 Lazy Dependency Loading

```
INVARIANT 3: Platform dependencies are not imported until instrument() dispatches to them
```

**Rules:**
- `import llmops` must succeed without any platform dependencies installed
- Exporter modules loaded only when configured platform matches
- Missing platform dependencies raise `ConfigurationError` at init time
- Error message includes installation instructions

### 3.4 Exporter Isolation

```
INVARIANT 4: Exporters are independent and isolated
```

**Rules:**
- Adding a new exporter requires no changes to existing exporter code
- Each exporter owns its TracerProvider lifecycle
- Exporter implementations do not share mutable state
- Configuration sections are platform-specific (`arize:`, `mlflow:`)

### 3.5 Single Backend Per Call

```
INVARIANT 5: Each instrument() call configures exactly one backend
```

**Rules:**
- One TracerProvider per `instrument()` invocation
- No multi-backend routing within a single call
- Calling `instrument()` multiple times logs a warning

### 3.6 Configuration Source of Truth

```
INVARIANT 6: Configuration requires explicit path or programmatic Config
```

**Rules:**
- `init(config=...)` must be provided as path or `Config` object
- Fallback to `LLMOPS_CONFIG_PATH` environment variable if no argument
- Each platform reads shared sections plus its own section
- Environment variables substitute `${VAR_NAME}` patterns in YAML
- Only one config source is used per init call

---

## 4. Exporter Factory Interface

### 4.1 Factory Function Pattern

Exporters are implemented as factory functions, not classes or protocols. Each exporter module provides a function that creates a configured TracerProvider.

**Factory signature:**
```
create_{platform}_provider(config: Config) -> TracerProvider
```

**Responsibilities:**
- Check that platform dependencies are installed
- Extract platform-specific config section
- Create and configure TracerProvider
- Return provider (SDK sets it as global)

### 4.2 Exporter Registry

The SDK maintains a registry mapping platform names to factory functions. Dispatch is a simple dictionary lookup followed by dynamic import.

**Registry structure:**
```
platform_name -> (module_path, factory_function_name)
```

**Dispatch flow:**
1. Read `platform` from config
2. Look up module path and function name in registry
3. Import module dynamically
4. Call factory function with config
5. Set returned TracerProvider as global

### 4.3 Adding a New Exporter

To add a new exporter:

1. Create module at `llmops/exporters/{name}/exporter.py`
2. Implement `create_{name}_provider(config) -> TracerProvider`
3. Implement `check_dependencies()` that raises `ImportError` with install instructions
4. Add entry to exporter registry in pipeline module
5. Add configuration section parser
6. Add optional dependencies to `pyproject.toml`

**Invariant:** No changes to public API or existing exporters required.

---

## 5. Initialization Flow

### 5.1 Sequence

```
llmops.instrument(config="llmops.yaml")
  │
  ├─▶ Resolve config source (path string, Path object, or Config)
  │
  ├─▶ If path: Load and parse YAML config
  │     ├─▶ Substitute environment variables
  │     └─▶ Parse into Config dataclass
  │
  ├─▶ Validate configuration
  │     ├─▶ Strict mode: raise ConfigurationError on invalid
  │     └─▶ Permissive mode: log warning, continue with defaults
  │
  ├─▶ Dispatch to exporter factory based on `platform` field
  │     ├─▶ Check platform dependencies installed
  │     └─▶ Create TracerProvider
  │
  ├─▶ Set TracerProvider as global
  │
  ├─▶ Apply auto-instrumentation
  │     ├─▶ Read enabled instrumentors from config
  │     ├─▶ For each enabled instrumentor in registry:
  │     │     ├─▶ Import instrumentor module
  │     │     ├─▶ Call instrument(provider)
  │     │     └─▶ Log and continue on failure
  │     └─▶ Unknown instrumentors logged as warnings
  │
  ├─▶ Register atexit handler for shutdown
  │
  └─▶ Mark SDK as configured
```

### 5.2 Validation Modes

Validation occurs during `instrument()` only:
- **Strict (development)**: raises `ConfigurationError`, fails startup
- **Permissive (production, default)**: logs warning, uses no-op provider

Each exporter validates its own configuration section. Shared infrastructure validates common sections (`service:`, `validation:`).

---

## 6. Error Handling Pattern

### 6.1 Dependency Errors

**Pattern:** Fail fast with actionable message

When platform dependencies are not installed, raise `ConfigurationError` (wrapping `ImportError`) with installation instructions.

### 6.2 Configuration Errors

**Pattern:** Respect validation mode

- Strict mode: raise `ConfigurationError` with details
- Permissive mode: log warning, use no-op provider, continue

### 6.3 Instrumentation Errors

**Pattern:** Swallow and log

Instrumentor failures are logged at warning level but never propagate. Application startup continues. Telemetry should never break business logic.

### 6.4 Runtime Telemetry Errors

**Pattern:** Swallow and log

Export failures are handled by OpenTelemetry SDK (retry, backoff). SDK does not add additional error handling for runtime telemetry.

---

## 7. Configuration Model

### 7.1 Config File Structure

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

# Auto-instrumentation configuration
instrumentation:
  enabled:
    - google_adk
    - google_genai

# Validation mode
validation:
  mode: permissive  # or "strict"
```

### 7.2 Section Ownership

| Section | Owner | Notes |
|---------|-------|-------|
| `platform:` | SDK | Determines exporter dispatch |
| `service:` | Shared | All platforms use this |
| `arize:` | Arize exporter | Only read when platform is "arize" |
| `mlflow:` | MLflow exporter | Only read when platform is "mlflow" |
| `instrumentation:` | SDK | Shared across all platforms |
| `validation:` | SDK | Shared across all platforms |

### 7.3 Required Fields

| Platform | Required Fields |
|----------|-----------------|
| All | `platform`, `service.name` |
| `arize` | `arize.endpoint` |
| `mlflow` | `mlflow.tracking_uri` |

---

## 8. Auto-Instrumentation Architecture

### 8.1 Instrumentor Registry

The SDK maintains a central registry of available instrumentors. Each entry maps a config key to a module path and function name.

**Registry structure:**
```
config_key -> (module_path, function_name)
```

**Example entries:**
- `google_adk` -> `(llmops.instrumentation.google_adk, instrument)`
- `google_genai` -> `(llmops.instrumentation.google_genai, instrument)`

### 8.2 Configuration Model

Instrumentation is configured via a list of enabled instrumentors, not individual boolean fields. This allows adding new instrumentors without changing the public API.

```yaml
instrumentation:
  enabled:
    - google_adk
    - google_genai
    - openai  # Future: just add to list
```

### 8.3 Application Flow

1. Read `instrumentation.enabled` list from config
2. For each name in the list:
   - Look up in instrumentor registry
   - If not found: log warning, continue
   - If found: import module, call instrument function
   - On ImportError: log debug (not installed), continue
   - On other error: log warning, continue
3. Application startup completes regardless of instrumentor failures

### 8.4 Adding a New Instrumentor

To add a new instrumentor:

1. Create module at `llmops/instrumentation/{name}.py`
2. Implement `instrument(tracer_provider: TracerProvider) -> None`
3. Add entry to instrumentor registry
4. Add optional dependency to `pyproject.toml`

**Invariant:** No changes to public API types required.

### 8.5 Instrumentor Module Contract

Each instrumentor module must provide:
- `instrument(tracer_provider: TracerProvider) -> None` function
- Lazy import of upstream instrumentor (inside function body)
- Raise `ImportError` if upstream package not installed

---

## 9. Package Structure

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

---

## 10. Testing Strategy

### 10.1 Unit Testing Exporters

Each exporter can be tested in isolation by mocking the upstream SDK:

- Test factory function creates provider with correct config
- Test dependency check raises helpful ImportError
- Test config section extraction

### 10.2 Unit Testing Instrumentation

Each instrumentor wrapper can be tested by mocking the upstream instrumentor:

- Test instrument function calls upstream correctly
- Test ImportError when upstream not installed
- Test graceful handling of upstream errors

### 10.3 Integration Testing

- Test `instrument()` with valid config creates working provider
- Test `instrument()` with missing dependencies raises ConfigurationError
- Test `instrument()` in permissive mode continues on invalid config
- Test `shutdown()` flushes and cleans up
- Test instrumentor failures don't break init

### 10.4 Config Loading Tests

- Test YAML parsing and validation
- Test environment variable substitution
- Test path resolution (argument vs env var)
- Test strict vs permissive validation modes

---

## 11. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_01.md` | Requirements and success criteria |
| `docs/CONCEPTUAL_ARCHITECTURE.md` | High-level conceptual view |
| `docs/DESIGN_PHILOSOPHY.md` | Design principles and decisions |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-27
