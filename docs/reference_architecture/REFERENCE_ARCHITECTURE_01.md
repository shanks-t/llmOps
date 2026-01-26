# Reference Architecture

**Version:** 0.3
**Date:** 2026-01-26
**Status:** Draft
**Covers:** PRD_01 (Auto-Instrumentation), PRD_03 (Evaluator Templates)

---

## 1. Purpose

This document defines how the llmops SDK should be built. It codifies architectural invariants, boundaries, and patterns for a **multi-platform SDK** with explicit platform selection and multiple capabilities (telemetry, evaluation).

---

## 2. Architectural Shape

### 2.1 Components

#### Core Components

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| **Package Root** | Lazy platform accessors via `__getattr__` | No platform deps at import |
| **Platform Module** | Platform capabilities entry point | One per supported backend |

#### Telemetry Components (PRD_01)

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| **Platform Implementation** | Backend-specific TracerProvider creation | Uses platform's SDK (arize.otel, mlflow) |
| **Shared Config Loader** | Read YAML, substitute env vars | Platform-agnostic |
| **Platform Config Parser** | Extract platform section, validate | Platform-specific validation |
| **Instrumentor Runner** | Apply auto-instrumentation | Shared; uses platform's registry |

#### Evaluation Components (PRD_03)

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| **Evals Module** | Platform-specific evaluation API | Lazy-loaded via `__getattr__` |
| **Template Factory** | Create evaluators from templates | Wraps phoenix.evals |
| **Built-in Templates** | Pre-configured evaluators | Faithfulness, etc. |
| **Evaluator Registry** | Named storage of evaluators | In-memory, thread-safe |

### 2.2 Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            PUBLIC API LAYER                              │
│                                                                         │
│   TELEMETRY (PRD_01)                    EVALUATION (PRD_03)             │
│   llmops.arize.instrument()             llmops.arize.evals.faithfulness()│
│   llmops.mlflow.instrument()            llmops.arize.evals.create_classifier()│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                    │                                    │
                    ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           PLATFORM LAYER                                 │
│                                                                         │
│   ┌─────────────────────────────────┐    ┌─────────────────────┐       │
│   │        ArizePlatform            │    │   MLflowPlatform    │       │
│   │  ┌───────────┬────────────┐     │    │   - (skeleton)      │       │
│   │  │ Telemetry │   Evals    │     │    │                     │       │
│   │  │ arize.otel│phoenix.eval│     │    │                     │       │
│   │  └───────────┴────────────┘     │    │                     │       │
│   └─────────────────────────────────┘    └─────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
          │                     │
          ▼                     ▼
┌──────────────────────────┐  ┌──────────────────────────────────────────┐
│  TELEMETRY INFRASTRUCTURE │  │      EVALUATION INFRASTRUCTURE          │
│                          │  │                                          │
│  ┌──────────────┐        │  │  ┌──────────────┐  ┌─────────────────┐   │
│  │Config Loader │        │  │  │Template Fctry│  │Evaluator Registr│   │
│  │(YAML + env)  │        │  │  │(factories)   │  │(in-memory)      │   │
│  └──────────────┘        │  │  └──────────────┘  └─────────────────┘   │
│  ┌──────────────┐        │  │                                          │
│  │ Instrumentor │        │  │                                          │
│  │   Runner     │        │  │                                          │
│  └──────────────┘        │  │                                          │
└──────────────────────────┘  └──────────────────────────────────────────┘
          │                                    │
          ▼                                    ▼
┌──────────────────────────┐  ┌──────────────────────────────────────────┐
│   EXTERNAL: TELEMETRY    │  │        EXTERNAL: EVALUATION              │
│                          │  │                                          │
│   arize-otel             │  │   arize-phoenix-evals                    │
│   openinference-*        │  │   LLM SDKs (openai, anthropic, etc.)     │
│   opentelemetry-sdk      │  │                                          │
└──────────────────────────┘  └──────────────────────────────────────────┘
```

### 2.3 Dependency Rules

**Strict downward-only dependencies:**

```
Package Root
     │
     ▼
Platform Module
     │
     ├──────────────────────────────────────────────┐
     │                                              │
     ▼                                              ▼
Telemetry Capability                    Evaluation Capability
     │                                              │
     ├─▶ Platform Implementation                    ├─▶ Evals Module
     │        │                                     │        │
     │        ▼                                     │        ▼
     │   Platform SDK (arize.otel)                  │   phoenix.evals
     │        │                                     │        │
     │        ▼                                     │        ▼
     │   Instrumentor Runner                        │   Evaluator Registry
     │                                              │
     ▼                                              │
Shared Config Loader ◀──────────────────────────────┘
     │                   (future: config-driven evals)
     ▼
Validation Utils
```

**Rules:**
- No component may depend on a higher-level component
- Platform implementations may not depend on each other
- Capabilities within a platform are independent (evals doesn't require telemetry)
- Shared infrastructure may not depend on any platform or capability
- Each capability depends on its specific external SDK

---

## 3. Core Invariants

These invariants must hold across all implementations.

### Shared Invariants

### 3.1 Lazy Loading

```
INVARIANT 1: Dependencies are not imported until accessed
```

**Rules:**
- `import llmops` must succeed without any platform dependencies installed
- Platform module is loaded only on first attribute access
- Sub-capabilities (e.g., `arize.evals`) are loaded only when accessed
- Missing dependencies raise `ImportError` at access time, not import time
- Error message includes installation instructions

**Implementation Pattern (Platform):**
```python
# llmops/__init__.py
def __getattr__(name: str):
    if name == "arize":
        from llmops import arize
        return arize
    if name == "mlflow":
        from llmops import mlflow
        return mlflow
    raise AttributeError(f"module 'llmops' has no attribute '{name}'")
```

**Implementation Pattern (Sub-capability):**
```python
# llmops/arize.py
def __getattr__(name: str):
    if name == "evals":
        from llmops.evals import arize as _evals
        return _evals
    raise AttributeError(f"module 'llmops.arize' has no attribute '{name}'")
```

### 3.2 Explicit Platform Selection

```
INVARIANT 2: Platform selection is always explicit in the API call
```

**Rules:**
- Users must call `llmops.<platform>.*`
- No auto-detection of platform from config or environment
- No default platform if none specified
- Platform name is visible in the import/call site

### 3.3 Platform Isolation

```
INVARIANT 3: Platforms are independent and isolated
```

**Rules:**
- Adding a new platform requires no changes to existing platform code
- Platform implementations do not share mutable state
- Configuration sections are platform-specific (`arize:`, `mlflow:`)

### 3.4 Capability Isolation

```
INVARIANT 4: Capabilities within a platform are independent
```

**Rules:**
- Evaluation does not require telemetry to be initialized
- Telemetry does not require evaluation
- Each capability has its own dependency chain
- Adding a new capability requires no changes to existing capabilities

### Telemetry Invariants (PRD_01)

### 3.5 Telemetry Safety

```
INVARIANT 5: Telemetry never breaks business logic
```

**Rules:**
- No SDK call raises exceptions to user code after initialization
- `instrument()` logs failures and returns safely (permissive mode)
- Instrumentor errors do not prevent application startup
- Configuration errors fail fast at startup, not during runtime

### 3.6 Single Backend Per Call

```
INVARIANT 6: Each instrument() call configures exactly one backend
```

**Rules:**
- One TracerProvider per `instrument()` invocation
- No multi-backend routing within a single call
- Calling multiple platforms' `instrument()` is undefined behavior (user error)

### 3.7 Configuration Source of Truth

```
INVARIANT 7: Configuration requires explicit path selection
```

**Rules:**
- `instrument(config_path=...)` must be provided or `LLMOPS_CONFIG_PATH` must be set
- Each platform reads shared sections plus its own section
- Environment variables override file values
- Only one config file is used per process

### Evaluation Invariants (PRD_03)

### 3.8 LLM Configuration Ownership

```
INVARIANT 8: LLM configuration is user-provided for evaluations
```

**Rules:**
- SDK does not manage LLM API keys or model selection
- Users create LLM instances and pass to factory/template functions
- No config file section for eval LLMs (in PRD_03 scope)

### 3.9 Registry Scope

```
INVARIANT 9: Evaluator registry is process-local and non-persistent
```

**Rules:**
- In-memory storage only; clears when process ends
- Thread-safe for concurrent access
- Duplicate names overwrite without error
- Missing names raise `KeyError`

---

## 4. Platform Protocol

### 4.1 Interface Definition

All platforms must implement this protocol:

```python
from typing import Protocol
from pathlib import Path
from opentelemetry.sdk.trace import TracerProvider

class Platform(Protocol):
    """Protocol that all platform implementations must satisfy."""

    @property
    def name(self) -> str:
        """Platform identifier (e.g., 'arize', 'mlflow')."""
        ...

    @property
    def config_section(self) -> str:
        """Config file section name (e.g., 'arize', 'mlflow')."""
        ...

    @property
    def install_extra(self) -> str:
        """pip extra name (e.g., 'arize' for pip install llmops[arize])."""
        ...

    def check_dependencies(self) -> None:
        """Raise ImportError with helpful message if deps missing."""
        ...

    def create_tracer_provider(self, config: LLMOpsConfig) -> TracerProvider:
        """Create platform-specific TracerProvider."""
        ...

    def get_instrumentor_registry(self) -> list[tuple[str, str, str]]:
        """Return list of (config_key, module_path, class_name) tuples."""
        ...
```

### 4.2 Protocol Rationale

**Why Protocol over ABC:**
- No inheritance required (duck typing)
- Easier to test with mocks
- More Pythonic
- Better composition patterns

**Note on `@runtime_checkable`:**
The `@runtime_checkable` decorator is optional. It enables `isinstance()` checks but has a small performance cost when those checks are used. For this SDK:
- Omit `@runtime_checkable` unless `isinstance()` checks are needed
- If used, avoid `isinstance()` checks in hot paths
- Type checkers (mypy, pyright) validate Protocol conformance statically without the decorator

---

## 5. Initialization Flow

### 5.1 Sequence

```
llmops.<platform>.instrument(config_path?)
  │
  ├─▶ Check platform dependencies installed
  │     └─▶ ImportError if missing (with pip install hint)
  │
  ├─▶ Resolve config path (arg > env var > error)
  │
  ├─▶ Load YAML config file (shared infrastructure)
  │
  ├─▶ Substitute environment variables
  │
  ├─▶ Platform extracts its section + shared sections
  │
  ├─▶ Platform validates its configuration
  │     ├─▶ Strict mode: raise ConfigurationError
  │     └─▶ Permissive mode: log warning, use no-op provider
  │
  ├─▶ Platform creates TracerProvider
  │     └─▶ (e.g., arize.otel.register(...))
  │
  ├─▶ Register atexit handler for shutdown
  │
  ├─▶ Apply auto-instrumentation (shared runner)
  │     └─▶ Uses platform's instrumentor registry
  │     └─▶ Each instrumentor failure logged, not raised
  │
  └─▶ Return TracerProvider
```

### 5.2 Dependency Check Pattern

```python
def check_dependencies(self) -> None:
    """Raise ImportError with helpful message if deps missing."""
    try:
        import arize.otel
    except ImportError:
        raise ImportError(
            f"Arize platform requires 'arize-otel' package.\n"
            f"Install with: pip install llmops[arize]"
        ) from None
```

### 5.3 Validation Contract

Validation occurs during `instrument()` only:
- **Strict (dev)**: raises `ConfigurationError`, fails startup
- **Permissive (prod, default)**: logs warning, returns no-op provider

Each platform validates its own configuration section. Shared infrastructure validates common sections (`service:`, `validation:`).

### 5.4 Evaluation Initialization (PRD_03)

```
llmops.arize.evals.faithfulness(llm)
  │
  ├─▶ Trigger lazy load of evals module
  │     └─▶ llmops/arize.py __getattr__("evals")
  │
  ├─▶ Check evaluation dependencies installed
  │     └─▶ ImportError if missing (with pip install hint)
  │
  ├─▶ Create FaithfulnessEvaluator
  │     └─▶ Wraps phoenix.evals.metrics.FaithfulnessEvaluator
  │
  └─▶ Return configured evaluator
```

```
llmops.arize.evals.create_classifier(name, prompt, llm, choices)
  │
  ├─▶ Check evaluation dependencies installed
  │
  ├─▶ Create ClassificationEvaluator
  │     └─▶ Wraps phoenix.evals.ClassificationEvaluator
  │
  └─▶ Return configured evaluator
```

### 5.5 Registry Operations (PRD_03)

```python
# Registry implementation pattern
import threading

_REGISTRY: dict[str, Evaluator] = {}
_LOCK = threading.Lock()

def register(name: str, evaluator: Evaluator) -> None:
    with _LOCK:
        _REGISTRY[name] = evaluator  # Overwrites if exists

def get(name: str) -> Evaluator:
    with _LOCK:
        if name not in _REGISTRY:
            raise KeyError(f"Evaluator '{name}' not registered")
        return _REGISTRY[name]

def list() -> list[str]:
    with _LOCK:
        return list(_REGISTRY.keys())

def clear() -> None:
    with _LOCK:
        _REGISTRY.clear()
```

---

## 6. Error Handling Pattern

### 6.1 Dependency Errors

```
PATTERN: Fail fast with actionable message
```

```python
# At platform access time
>>> import llmops
>>> llmops.arize.instrument()
ImportError: Arize platform requires 'arize-otel' package.
Install with: pip install llmops[arize]
```

### 6.2 Configuration Errors

```
PATTERN: Respect validation mode
```

```python
# Strict mode
>>> llmops.arize.instrument(config_path="missing.yaml")
ConfigurationError: Configuration file not found: missing.yaml

# Permissive mode
>>> llmops.arize.instrument(config_path="invalid.yaml")
# Logs: WARNING - Invalid config, using no-op provider
# Returns: NoOpTracerProvider
```

### 6.3 Telemetry Errors

```
PATTERN: Swallow and log
```

```python
try:
    _internal_telemetry_operation()
except Exception as exc:
    logger.warning("Telemetry error (ignored): %s", exc)
    # Continue execution - never break business logic
```

---

## 7. Configuration Model

### 7.1 Config File Structure

```yaml
# llmops.yaml

# Shared across all platforms
service:
  name: "my-service"           # Required
  version: "1.0.0"             # Optional

# Platform-specific sections (only one is read per instrument() call)
arize:
  endpoint: "http://localhost:6006/v1/traces"  # Required for arize
  project_name: "my-project"
  api_key: "${ARIZE_API_KEY}"
  space_id: "${ARIZE_SPACE_ID}"
  transport: "http"
  batch_spans: true
  debug: false
  certificate_file: "./certs/ca.pem"

mlflow:  # Skeleton
  tracking_uri: "http://localhost:5001"
  experiment_name: "my-experiment"

# Shared instrumentation config
instrumentation:
  google_adk: true
  google_genai: true

# Shared validation config
validation:
  mode: permissive
```

### 7.2 Section Ownership

| Section | Owner | Notes |
|---------|-------|-------|
| `service:` | Shared | All platforms use this |
| `arize:` | ArizePlatform | Only read by Arize |
| `mlflow:` | MLflowPlatform | Only read by MLflow |
| `instrumentation:` | Shared | Platform filters by available instrumentors |
| `validation:` | Shared | All platforms respect this |

### 7.3 Required Fields by Platform

| Platform | Required Fields |
|----------|-----------------|
| `arize` | `service.name`, `arize.endpoint` |
| `mlflow` | `service.name`, `mlflow.tracking_uri` |

---

## 8. Auto-Instrumentation Rules

### 8.1 Instrumentor Registry Pattern

Each platform defines its supported instrumentors:

```python
# Arize platform registry
ARIZE_INSTRUMENTORS = [
    ("google_adk", "openinference.instrumentation.google_adk", "GoogleADKInstrumentor"),
    ("google_genai", "openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor"),
]

# MLflow platform registry (skeleton)
MLFLOW_INSTRUMENTORS = [
    ("gemini", "mlflow.gemini", "autolog"),
    ("openai", "mlflow.openai", "autolog"),
]
```

### 8.2 Shared Instrumentation Runner

The instrumentor runner is shared infrastructure. Platforms provide the registry; the runner applies it:

```python
def apply_instrumentation(
    config: InstrumentationConfig,
    registry: list[tuple[str, str, str]],
    provider: TracerProvider
) -> None:
    """Apply auto-instrumentation from platform's registry."""
    for config_key, module_path, class_name in registry:
        if not getattr(config, config_key, False):
            continue  # Disabled in config

        try:
            module = importlib.import_module(module_path)
            instrumentor = getattr(module, class_name)()
            instrumentor.instrument(tracer_provider=provider)
        except ImportError:
            logger.debug("Instrumentor not installed: %s", module_path)
        except Exception as e:
            logger.warning("Instrumentor failed: %s - %s", config_key, e)
```

### 8.3 Order of Operations

1. Create TracerProvider (platform-specific)
2. Set as global tracer provider
3. Register atexit handler
4. Apply instrumentors from platform's registry (shared runner)

---

## 9. Extension Points

### 9.1 Adding a New Platform

```
INVARIANT 7: New platforms require no changes to existing platforms
```

**Steps to add a platform:**

1. **Create platform implementation** (`llmops/_platforms/newplatform.py`):
   ```python
   class NewPlatform:
       @property
       def name(self) -> str:
           return "newplatform"

       def create_tracer_provider(self, config) -> TracerProvider:
           ...

       def get_instrumentor_registry(self) -> list[tuple[str, str, str]]:
           return [...]
   ```

2. **Create public module** (`llmops/newplatform.py`):
   ```python
   from llmops._platforms.newplatform import NewPlatform

   _platform = NewPlatform()

   def instrument(config_path=None):
       return _platform.instrument(config_path)
   ```

3. **Add lazy accessor** (`llmops/__init__.py`):
   ```python
   def __getattr__(name: str):
       if name == "newplatform":
           from llmops import newplatform
           return newplatform
       # ... existing platforms
   ```

4. **Add optional dependencies** (`pyproject.toml`):
   ```toml
   [project.optional-dependencies]
   newplatform = ["newplatform-sdk>=1.0"]
   ```

### 9.2 Adding a New Instrumentor

**Steps to add an instrumentor to an existing platform:**

1. Add entry to platform's instrumentor registry
2. Add optional dependency to platform's extras
3. No code changes required elsewhere

### 9.3 Adding a New Built-in Evaluator Template (PRD_03)

```
INVARIANT: New templates require no changes to existing templates
```

**Steps to add a built-in template:**

1. **Add template implementation** (`llmops/evals/arize/_templates.py`):
   ```python
   def relevance(llm: LLM) -> Evaluator:
       from phoenix.evals.metrics import DocumentRelevanceEvaluator
       return DocumentRelevanceEvaluator(llm=llm)
   ```

2. **Export from public module** (`llmops/evals/arize/__init__.py`):
   ```python
   from llmops.evals.arize._templates import faithfulness, relevance
   ```

3. **Add optional dependency if needed** (`pyproject.toml`):
   ```toml
   [project.optional-dependencies]
   arize-evals = ["arize-phoenix-evals>=2.0.0"]
   ```

### 9.4 Adding Evaluation to a New Platform

**Steps to add evaluation capability to a platform:**

1. **Create evals module** (`llmops/evals/newplatform/`):
   ```
   llmops/evals/newplatform/
   ├── __init__.py      # Public API
   ├── _registry.py     # Evaluator registry
   └── _templates.py    # Built-in templates
   ```

2. **Add lazy accessor** (`llmops/newplatform.py`):
   ```python
   def __getattr__(name: str):
       if name == "evals":
           from llmops.evals import newplatform as _evals
           return _evals
       raise AttributeError(...)
   ```

3. **Add optional dependencies** (`pyproject.toml`):
   ```toml
   [project.optional-dependencies]
   newplatform-evals = ["newplatform-evals-lib>=1.0"]
   ```

---

## 10. Package Structure

```
llmops/
├── __init__.py              # Lazy accessors, version, ConfigurationError re-export
├── exceptions.py            # ConfigurationError definition
├── config.py                # Shared config loading (YAML, env vars)
├── arize.py                 # Public module: llmops.arize.* (+ __getattr__ for evals)
├── mlflow.py                # Public module: llmops.mlflow.instrument() (skeleton)
├── _platforms/              # Telemetry implementations (PRD_01)
│   ├── __init__.py
│   ├── _base.py             # Platform Protocol definition
│   ├── _registry.py         # Shared instrumentor runner
│   ├── _instrument.py       # Shared instrumentation flow
│   ├── arize.py             # ArizePlatform implementation
│   └── mlflow.py            # MLflowPlatform implementation (skeleton)
├── _internal/
│   ├── __init__.py
│   └── telemetry.py         # Shared telemetry utilities (no-op provider, etc.)
└── evals/                   # Evaluation implementations (PRD_03)
    ├── __init__.py          # Package marker
    └── arize/               # Arize platform evals
        ├── __init__.py      # Public API: faithfulness, create_classifier, etc.
        ├── _registry.py     # In-memory evaluator registry
        └── _templates.py    # Built-in template implementations
```

---

## 11. Testing Strategy

### 11.1 Unit Testing Platforms

Each platform can be tested in isolation:

```python
def test_arize_platform_creates_provider(mock_arize_otel):
    from llmops._platforms.arize import ArizePlatform

    platform = ArizePlatform()
    provider = platform.create_tracer_provider(mock_config)

    mock_arize_otel.register.assert_called_once()
```

### 11.2 Integration Testing

```python
def test_lazy_loading_does_not_import_arize():
    # Ensure arize.otel is not in sys.modules
    import llmops
    assert "arize.otel" not in sys.modules

def test_arize_access_imports_arize():
    import llmops
    _ = llmops.arize  # Access triggers import
    # Now arize module is loaded (but not necessarily arize.otel until instrument())
```

### 11.3 Dependency Error Testing

```python
def test_missing_arize_deps_raises_helpful_error(monkeypatch):
    # Simulate arize.otel not installed
    monkeypatch.setattr("builtins.__import__", mock_import_error)

    with pytest.raises(ImportError, match="pip install llmops\\[arize\\]"):
        llmops.arize.instrument()
```

---

## 12. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_01.md` | Auto-instrumentation requirements |
| `docs/prd/PRD_03.md` | Evaluator templates requirements |
| `docs/CONCEPTUAL_ARCHITECTURE.md` | High-level conceptual view |
| `docs/api_spec/API_SPEC_01.md` | Telemetry public interfaces |
| `docs/analysis/PLATFORM_ARCHITECTURE_ANALYSIS.md` | Analysis of design options |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-26
