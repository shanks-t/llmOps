# PRD_02 — Reference Architecture

**Version:** 0.1
**Date:** 2026-01-22
**Status:** Draft
**Builds On:** REFERENCE_ARCHITECTURE_01 (PRD_01)

---

## 1. Purpose

This document defines how the PRD_02 system should be built. It codifies architectural invariants, boundaries, and patterns for a **multi-platform auto-instrumentation SDK** with explicit platform selection.

**Key Evolution from PRD_01:**
- Adds Platform Layer between Public API and Shared Infrastructure
- Introduces Platform Protocol for consistent interface across backends
- Defines lazy-loading requirements for platform modules
- Establishes platform isolation invariants

---

## 2. Architectural Shape

### 2.1 Components

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| **Package Root** | Lazy platform accessors via `__getattr__` | No platform deps at import |
| **Platform Module** | `<platform>.instrument()` entry point | One per supported backend |
| **Platform Implementation** | Backend-specific TracerProvider creation | Uses platform's SDK (arize.otel, mlflow) |
| **Shared Config Loader** | Read YAML, substitute env vars | Platform-agnostic |
| **Platform Config Parser** | Extract platform section, validate | Platform-specific validation |
| **Instrumentor Runner** | Apply auto-instrumentation | Uses platform's registry |

### 2.2 Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            PUBLIC API LAYER                              │
│                                                                         │
│   llmops.arize.instrument()    llmops.mlflow.instrument()               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           PLATFORM LAYER                                 │
│                                                                         │
│   ┌─────────────────────┐    ┌─────────────────────┐                    │
│   │   ArizePlatform     │    │   MLflowPlatform    │                    │
│   │   - arize.otel      │    │   - mlflow.autolog  │                    │
│   │   - OpenInference   │    │   - MLflow tracing  │                    │
│   └─────────────────────┘    └─────────────────────┘                    │
│                                                                         │
│   All implement: Platform Protocol                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SHARED INFRASTRUCTURE LAYER                         │
│                                                                         │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│   │Config Loader │  │  Validation  │  │   Instrumentor Application   │  │
│   │(YAML + env)  │  │(strict/perm) │  │   (registry-based)           │  │
│   └──────────────┘  └──────────────┘  └──────────────────────────────┘  │
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
Package Root
     │
     ▼
Platform Module ──────────────────────────┐
     │                                    │
     ▼                                    ▼
Platform Implementation          Shared Config Loader
     │                                    │
     ▼                                    ▼
Platform SDK (arize.otel)        Validation Utils
     │
     ▼
Instrumentor Runner
```

**Rules:**
- No component may depend on a higher-level component
- Platform implementations may not depend on each other
- Shared infrastructure may not depend on any platform
- Platform modules depend on their specific external SDK

---

## 3. Core Invariants

These invariants must hold across all implementations.

### 3.1 Telemetry Safety

```
INVARIANT 1: Telemetry never breaks business logic
```

**Rules:**
- No SDK call raises exceptions to user code after initialization
- `instrument()` logs failures and returns safely (permissive mode)
- Instrumentor errors do not prevent application startup
- Configuration errors fail fast at startup, not during runtime

### 3.2 Explicit Platform Selection

```
INVARIANT 2: Platform selection is always explicit in the API call
```

**Rules:**
- Users must call `llmops.<platform>.instrument()`
- No auto-detection of platform from config or environment
- No default platform if none specified
- Platform name is visible in the import/call site

### 3.3 Lazy Platform Loading

```
INVARIANT 3: Platform dependencies are not imported until platform is accessed
```

**Rules:**
- `import llmops` must succeed without any platform dependencies installed
- Platform module is loaded only on first attribute access
- Missing platform dependencies raise `ImportError` at access time, not import time
- Error message includes installation instructions

**Implementation Pattern:**
```python
# llmops/__init__.py
def __getattr__(name: str):
    if name == "arize":
        from llmops import arize
        return arize
    raise AttributeError(f"module 'llmops' has no attribute '{name}'")
```

### 3.4 Platform Isolation

```
INVARIANT 4: Platforms are independent and isolated
```

**Rules:**
- Adding a new platform requires no changes to existing platform code
- Each platform owns its TracerProvider lifecycle
- Platform implementations do not share mutable state
- Configuration sections are platform-specific (`arize:`, `mlflow:`)

### 3.5 Single Backend Per Call

```
INVARIANT 5: Each instrument() call configures exactly one backend
```

**Rules:**
- One TracerProvider per `instrument()` invocation
- No multi-backend routing within a single call
- Calling multiple platforms' `instrument()` is undefined behavior (user error)

### 3.6 Configuration Source of Truth

```
INVARIANT 6: Configuration requires explicit path selection
```

**Rules:**
- `instrument(config_path=...)` must be provided or `LLMOPS_CONFIG_PATH` must be set
- Each platform reads shared sections plus its own section
- Environment variables override file values
- Only one config file is used per process

---

## 4. Platform Protocol

### 4.1 Interface Definition

All platforms must implement this protocol:

```python
from typing import Protocol, runtime_checkable
from pathlib import Path
from opentelemetry.sdk.trace import TracerProvider

@runtime_checkable
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

**Why `@runtime_checkable`:**
- Enables `isinstance()` checks if needed
- Useful for debugging and validation
- Small performance cost is acceptable at startup

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
  ├─▶ Load YAML config file
  │
  ├─▶ Substitute environment variables
  │
  ├─▶ Extract platform section + shared sections
  │
  ├─▶ Validate configuration
  │     ├─▶ Strict mode: raise ConfigurationError
  │     └─▶ Permissive mode: log warning, use no-op provider
  │
  ├─▶ Platform creates TracerProvider
  │     └─▶ (e.g., arize.otel.register(...))
  │
  ├─▶ Register atexit handler for shutdown
  │
  ├─▶ Apply auto-instrumentation from registry
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

mlflow:  # Future
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

# MLflow platform registry (future)
MLFLOW_INSTRUMENTORS = [
    ("gemini", "mlflow.gemini", "autolog"),
    ("openai", "mlflow.openai", "autolog"),
]
```

### 8.2 Instrumentation Flow

```python
def apply_instrumentation(config: InstrumentationConfig, registry: list, provider: TracerProvider):
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
4. Apply instrumentors from platform's registry

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

       def instrument(self, config_path=None) -> TracerProvider:
           ...
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

---

## 10. Package Structure

```
llmops/
├── __init__.py              # Lazy accessors, version, ConfigurationError re-export
├── exceptions.py            # ConfigurationError definition
├── config.py                # Shared config loading (YAML, env vars)
├── arize.py                 # Public module: llmops.arize.instrument()
├── mlflow.py                # Public module: llmops.mlflow.instrument() (future)
├── _platforms/
│   ├── __init__.py
│   ├── _base.py             # Platform Protocol definition
│   ├── _registry.py         # Shared instrumentor application logic
│   ├── arize.py             # ArizePlatform implementation
│   └── mlflow.py            # MLflowPlatform implementation (future)
└── _internal/
    ├── __init__.py
    └── telemetry.py         # Shared telemetry utilities (no-op provider, etc.)
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
| `docs/prd/PRD_02.md` | Requirements and success criteria |
| `docs/CONCEPTUAL_ARCHITECTURE_02.md` | High-level conceptual view |
| `docs/api_spec/API_SPEC_02.md` | Public interface and config contracts |
| `docs/analysis/PLATFORM_ARCHITECTURE_ANALYSIS.md` | Analysis of design options |
| `docs/reference_architecture/REFERENCE_ARCHITECTURE_01.md` | Original PRD_01 reference architecture |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-22
