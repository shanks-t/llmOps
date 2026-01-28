# PRD_01 — API Specification

**Version:** 0.3
**Date:** 2026-01-27
**Status:** Draft
**Implements:** PRD_01

---

## 1. Overview

This document defines the public API for PRD_01: Config-Driven Auto-Instrumentation SDK. The SDK exposes a single `instrument()` entry point that initializes telemetry based on configuration. Platform selection is explicit in the configuration file via the `platform` field.

**Design Principle:** One `instrument()`, one `shutdown()`. Config drives composition. Platform selection is explicit in configuration, not in API calls.

---

## 2. Package Structure

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

## 3. Public API

### 3.1 `llmops.instrument()`

Initialize telemetry and auto-instrumentation based on configuration.

**Signature:**
```python
def instrument(
    config: str | Path | Config,
) -> None:
    """
    Initialize telemetry and auto-instrumentation.

    This function:
    1. Resolves config (path string, Path object, or Config dataclass)
    2. If path: loads YAML, substitutes env vars, parses into Config
    3. Validates configuration (strict mode raises, permissive logs warning)
    4. Dispatches to exporter factory based on `platform` field
    5. Creates TracerProvider via platform-specific exporter
    6. Applies auto-instrumentation for enabled instrumentors
    7. Registers atexit handler to flush spans on process exit
    8. Marks SDK as configured

    Args:
        config: Path to `llmops.yaml`, Path object, or Config dataclass.
                If omitted, falls back to `LLMOPS_CONFIG_PATH` env var.

    Returns:
        None

    Raises:
        ConfigurationError: If config is missing or invalid (strict mode only).
                           In permissive mode, logs warning and uses no-op provider.

    Example:
        >>> import llmops
        >>> llmops.instrument(config="llmops.yaml")
        >>> # Your app code runs with auto-instrumentation enabled
    """
```

**Quick Start Example:**
```python
import llmops

# Using config file path
llmops.instrument(config="llmops.yaml")
```

**Environment Variable Fallback:**
```python
import llmops

# Falls back to LLMOPS_CONFIG_PATH if set
llmops.instrument()
```

**Programmatic Config:**
```python
import llmops

config = llmops.Config(
    platform="arize",
    service=llmops.ServiceConfig(name="my-service"),
    arize=llmops.ArizeConfig(endpoint="http://localhost:6006/v1/traces"),
)
llmops.instrument(config=config)
```

---

### 3.2 `llmops.shutdown()`

Shutdown telemetry and flush buffered spans.

**Signature:**
```python
def shutdown() -> None:
    """
    Shutdown telemetry and flush buffered spans.

    This function is automatically registered as an atexit handler by instrument().
    Call explicitly for controlled shutdown in tests or long-running services.
    """
```

---

### 3.3 `llmops.is_configured()`

Check if the SDK has been initialized.

**Signature:**
```python
def is_configured() -> bool:
    """
    Check if the SDK has been initialized.

    Returns:
        True if instrument() has been called successfully, False otherwise.
    """
```

---

### 3.4 `llmops.ConfigurationError`

Exception raised for configuration errors.

**Location:** `llmops.exceptions.ConfigurationError`

**Re-exported at:** `llmops.ConfigurationError`

```python
class ConfigurationError(Exception):
    """Raised when SDK configuration is invalid.

    In strict mode: Raised for missing files, invalid YAML, missing required
    fields, or missing environment variables.

    In permissive mode: Only raised when no config can be found at all.
    Other errors result in a no-op tracer provider.
    """
```

---

## 4. Configuration

### 4.1 File Location

- Preferred file name: `llmops.yaml`
- Supported alternate: `llmops.yml`
- Path provided via `init(config=...)` or `LLMOPS_CONFIG_PATH` env var

### 4.2 Environment Variables

| Variable | Purpose |
|----------|---------|
| `LLMOPS_CONFIG_PATH` | Path to config file when not passed to `instrument()` |
| `OTEL_EXPORTER_OTLP_CERTIFICATE` | Fallback for `certificate_file` (CA cert) |

### 4.3 YAML Schema

```yaml
# llmops.yaml

# Required: Platform selection
platform: arize                # or "mlflow"

# Required: Service identification
service:
  name: "my-service"           # Required
  version: "1.0.0"             # Optional

# Platform-specific sections (only matching platform is read)
arize:
  endpoint: "http://localhost:6006/v1/traces"  # Required
  project_name: "my-project"                   # Optional
  api_key: "${ARIZE_API_KEY}"                  # Optional, env var substitution
  space_id: "${ARIZE_SPACE_ID}"                # Optional (Arize AX only)
  transport: "http"                            # "http" (default) or "grpc"
  batch: true                                  # true (default) or false

mlflow:
  tracking_uri: "http://localhost:5001"        # Required for mlflow
  experiment_name: "my-experiment"             # Optional

# Auto-instrumentation configuration (list-based registry)
instrumentation:
  enabled:
    - google_adk
    - google_genai

# Validation settings
validation:
  mode: permissive             # "strict" or "permissive" (default: permissive)
```

### 4.4 Config Section Ownership

| Section | Owner | Notes |
|---------|-------|-------|
| `platform:` | SDK | Determines exporter dispatch |
| `service:` | Shared | All platforms use this |
| `arize:` | Arize exporter | Only read when platform is "arize" |
| `mlflow:` | MLflow exporter | Only read when platform is "mlflow" |
| `instrumentation:` | SDK | Shared across all platforms |
| `validation:` | SDK | Shared across all platforms |

### 4.5 Required Fields

| Platform | Required Fields |
|----------|-----------------|
| All | `platform`, `service.name` |
| `arize` | `arize.endpoint` |
| `mlflow` | `mlflow.tracking_uri` |

---

## 5. Error Handling

### 5.1 Missing Platform Dependencies

When platform-specific packages are not installed:

```python
>>> import llmops
>>> llmops.instrument(config="llmops.yaml")  # with platform: arize
ConfigurationError: Arize platform requires 'arize-otel' package.
Install with: pip install llmops[arize]
```

**Key behaviors:**
- `import llmops` always succeeds (no platform dependencies loaded)
- Exporter modules loaded only when `instrument()` dispatches to them
- Error message includes exact pip install command

### 5.2 Configuration Errors

**Strict mode:**
```python
>>> llmops.instrument(config="missing.yaml")
ConfigurationError: Configuration file not found: missing.yaml
```

**Permissive mode:**
```python
>>> llmops.instrument(config="invalid.yaml")
# Logs warning, uses no-op TracerProvider, returns successfully
```

### 5.3 Telemetry Isolation

All telemetry failures after initialization are swallowed and logged. Auto-instrumentation failures never raise exceptions to user code.

---

## 6. Exporter Factory Interface

Exporters are implemented as factory functions, not classes or protocols. Each exporter module provides a function that creates a configured TracerProvider.

### 6.1 Factory Function Pattern

```python
# llmops/exporters/arize/exporter.py

def create_arize_provider(config: Config) -> TracerProvider:
    """
    Create Arize TracerProvider.

    Args:
        config: Validated Config object with arize section populated.

    Returns:
        Configured TracerProvider for Arize backend.

    Raises:
        ImportError: If arize-otel package is not installed.
    """
    ...
```

### 6.2 Exporter Registry

The SDK maintains a registry mapping platform names to factory functions:

```python
# Registry structure (internal)
EXPORTER_REGISTRY = {
    "arize": ("llmops.exporters.arize.exporter", "create_arize_provider"),
    "mlflow": ("llmops.exporters.mlflow.exporter", "create_mlflow_provider"),
}
```

### 6.3 Adding a New Exporter

To add a new exporter:

1. Create module at `llmops/exporters/{name}/exporter.py`
2. Implement `create_{name}_provider(config) -> TracerProvider`
3. Implement `check_dependencies()` that raises `ImportError` with install instructions
4. Add entry to exporter registry
5. Add configuration section parser
6. Add optional dependencies to `pyproject.toml`

**Invariant:** No changes to public API or existing exporters required.

---

## 7. Instrumentor Registry

### 7.1 Registry Structure

The SDK maintains a central registry of available instrumentors:

```python
# Registry structure (internal)
INSTRUMENTOR_REGISTRY = {
    "google_adk": ("llmops.instrumentation.google_adk", "instrument"),
    "google_genai": ("llmops.instrumentation.google_genai", "instrument"),
}
```

### 7.2 Available Instrumentors

| Config Key | Upstream Module | Notes |
|------------|-----------------|-------|
| `google_adk` | `openinference.instrumentation.google_adk` | Google Agent Development Kit |
| `google_genai` | `openinference.instrumentation.google_genai` | Google GenAI SDK |

### 7.3 Configuration

Instrumentors are configured via a list in the config file:

```yaml
instrumentation:
  enabled:
    - google_adk
    - google_genai
    - openai  # Future: just add to list, no API changes
```

### 7.4 Instrumentor Behavior

- Unknown instrumentor names are logged as warnings, not errors
- Missing instrumentor packages are logged at debug level
- Instrumentor failures are swallowed (telemetry never breaks business logic)
- Adding new instrumentors requires no public API changes

---

## 8. Installation Extras

The package uses optional dependencies for platform-specific packages:

```toml
# pyproject.toml
[project.optional-dependencies]
arize = [
    "arize-otel>=0.1.0",
    "openinference-instrumentation-google-adk>=0.1.0",
    "openinference-instrumentation-google-genai>=0.1.0",
]
mlflow = [
    "mlflow>=2.10.0",
]
all = [
    "llmops[arize]",
    "llmops[mlflow]",
]
```

**Install commands:**
```bash
# Arize platform only
pip install llmops[arize]

# MLflow platform only (skeleton)
pip install llmops[mlflow]

# All platforms
pip install llmops[all]
```

---

## 9. Public API Summary

### Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `llmops.instrument` | `(config: str \| Path \| Config)` | `None` |
| `llmops.shutdown` | `()` | `None` |
| `llmops.is_configured` | `()` | `bool` |

### Types

| Type | Purpose |
|------|---------|
| `llmops.Config` | Programmatic configuration dataclass |
| `llmops.ServiceConfig` | Service identification config |
| `llmops.ArizeConfig` | Arize-specific configuration |
| `llmops.MLflowConfig` | MLflow-specific configuration |
| `llmops.InstrumentationConfig` | Instrumentation settings |
| `llmops.ValidationConfig` | Validation mode settings |

### Exceptions

| Exception | When Raised |
|-----------|-------------|
| `llmops.ConfigurationError` | Invalid config (strict mode), missing dependencies |

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `llmops.__version__` | `"0.3.0"` | SDK version |

### Reserved Namespaces

| Namespace | Status | Purpose |
|-----------|--------|---------|
| `llmops.eval` | Reserved (future) | Batch evaluation and CI regression testing |

---

## 10. Type Stubs

For IDE support and type checking, the package provides type information:

```python
# llmops/__init__.pyi
from pathlib import Path
from llmops.api.types import Config as Config
from llmops.api.types import ServiceConfig as ServiceConfig
from llmops.api.types import ArizeConfig as ArizeConfig
from llmops.api.types import MLflowConfig as MLflowConfig
from llmops.api.types import InstrumentationConfig as InstrumentationConfig
from llmops.api.types import ValidationConfig as ValidationConfig
from llmops.exceptions import ConfigurationError as ConfigurationError

__version__: str

def instrument(config: str | Path | Config = ...) -> None: ...
def shutdown() -> None: ...
def is_configured() -> bool: ...
```

---

## 11. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_01.md` | Requirements and success criteria |
| `docs/CONCEPTUAL_ARCHITECTURE.md` | High-level conceptual view |
| `docs/reference_architecture/REFERENCE_ARCHITECTURE_01.md` | Architectural patterns and invariants |
| `docs/DESIGN_PHILOSOPHY.md` | Design principles and API stability rules |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-27
