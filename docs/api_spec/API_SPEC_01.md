# PRD_01 — API Specification

**Version:** 0.2
**Date:** 2026-01-22
**Status:** Draft
**Implements:** PRD_01

---

## 1. Overview

This document defines the public API for PRD_01: Multi-Platform Auto-Instrumentation SDK. The SDK exposes platform-specific namespaces, each with an `instrument()` entry point that initializes telemetry for that specific observability backend.

**Design Principle:** Platform selection is explicit in the API call. The SDK never guesses which platform to use.

---

## 2. Package Structure

```
llmops/
├── __init__.py           # Package root with lazy platform accessors
├── exceptions.py         # Shared exceptions (ConfigurationError)
├── config.py             # Shared config loading and validation
├── arize.py              # Public platform module: llmops.arize
├── mlflow.py             # Public platform module: llmops.mlflow (skeleton)
├── _platforms/           # Internal platform implementations
│   ├── __init__.py
│   ├── _base.py          # Platform Protocol definition
│   ├── _registry.py      # Shared instrumentor runner
│   ├── arize.py          # ArizePlatform implementation
│   └── mlflow.py         # MLflowPlatform implementation (skeleton)
└── _internal/            # Shared internal utilities
    └── telemetry.py      # Common telemetry helpers
```

---

## 3. Public API

### 3.1 Platform Namespace Access

The top-level `llmops` package provides lazy accessors to platform modules.

**Access Pattern:**
```python
import llmops

# Access Arize platform (lazy-loaded)
llmops.arize.instrument(config_path="llmops.yaml")
```

**Alternate Import:**
```python
from llmops import arize

arize.instrument(config_path="llmops.yaml")
```

**Module-Level Access (for type checkers):**
```python
import llmops.arize

llmops.arize.instrument(config_path="llmops.yaml")
```

---

### 3.2 `llmops.arize.instrument()`

Initialize Arize telemetry and auto-instrumentation in a single call.

**Signature:**
```python
def instrument(
    config_path: str | Path | None = None,
) -> TracerProvider:
    """
    Initialize Arize telemetry and auto-instrumentation.

    This function:
    1. Resolves config path (argument or LLMOPS_CONFIG_PATH env var)
    2. Loads and validates configuration from the `arize:` section
    3. Creates TracerProvider via arize.otel.register
    4. Applies OpenInference auto-instrumentation for enabled frameworks
    5. Registers atexit handler to flush spans on process exit
    6. Returns the configured provider

    Args:
        config_path: Optional path to `llmops.yaml` (preferred) or `llmops.yml`.
                     If omitted, `LLMOPS_CONFIG_PATH` must be set.

    Returns:
        The configured OpenTelemetry TracerProvider.

    Raises:
        ConfigurationError: If config is missing or invalid (strict mode only).
                           In permissive mode, returns a no-op tracer provider.
        ImportError: If arize-otel package is not installed.

    Note:
        An atexit handler is automatically registered to call provider.shutdown()
        when the process exits. This ensures buffered spans are flushed even in
        scripts without explicit lifecycle management.

    Example:
        >>> import llmops
        >>> provider = llmops.arize.instrument(config_path="llmops.yaml")
        >>> # Your app code runs with auto-instrumentation enabled
    """
```

**Quick Start Example:**
```python
import llmops

# Using environment variable LLMOPS_CONFIG_PATH
llmops.arize.instrument()
```

**Explicit Config Path Example:**
```python
import llmops

llmops.arize.instrument(config_path="/services/chat/llmops.yaml")
```

---

### 3.3 `llmops.mlflow.instrument()` (Skeleton)

Initialize MLflow telemetry and auto-instrumentation. This is a skeleton implementation to validate the platform extensibility architecture.

**Signature:**
```python
def instrument(
    config_path: str | Path | None = None,
) -> TracerProvider:
    """
    Initialize MLflow telemetry and auto-instrumentation.

    NOTE: This is a skeleton implementation. It validates the platform
    abstraction but does not provide full MLflow functionality.

    Args:
        config_path: Optional path to `llmops.yaml` (preferred) or `llmops.yml`.
                     If omitted, `LLMOPS_CONFIG_PATH` must be set.

    Returns:
        A no-op TracerProvider (skeleton implementation).

    Raises:
        ConfigurationError: If config is missing or invalid (strict mode only).
        ImportError: If mlflow package is not installed.
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
- Path must be provided explicitly via `instrument(config_path=...)` or `LLMOPS_CONFIG_PATH`

### 4.2 Environment Variables

| Variable | Purpose |
|----------|---------|
| `LLMOPS_CONFIG_PATH` | Path to config file when not passed to `instrument()` |
| `OTEL_EXPORTER_OTLP_CERTIFICATE` | Fallback for `certificate_file` (CA cert) |

### 4.3 YAML Schema

```yaml
# llmops.yaml
service:
  name: "my-service"           # Required
  version: "1.0.0"             # Optional

# Arize-specific configuration
# Used by llmops.arize.instrument()
arize:
  endpoint: "http://localhost:6006/v1/traces"  # Required
  project_name: "my-project"                   # Optional
  api_key: "${ARIZE_API_KEY}"                  # Optional, prefer env var
  space_id: "${ARIZE_SPACE_ID}"                # Optional (Arize AX only)

  # Transport and processing options
  transport: "http"                            # "http" (default) or "grpc"
  batch_spans: true                            # true (default) or false
  debug: false                                 # Log spans to console (default: false)

  # TLS certificate for self-hosted HTTPS endpoints
  certificate_file: "./certs/ca.pem"           # Optional, relative or absolute

# MLflow-specific configuration (skeleton)
# Used by llmops.mlflow.instrument()
mlflow:
  tracking_uri: "http://localhost:5001"        # Required for mlflow
  experiment_name: "my-experiment"             # Optional

# Instrumentation settings (shared across platforms)
instrumentation:
  google_adk: true             # Auto-instrument Google ADK (default: true)
  google_genai: true           # Auto-instrument Google GenAI (default: true)

# Validation settings
validation:
  mode: permissive             # "strict" or "permissive" (default: permissive)
```

### 4.4 Platform-Specific Config Sections

Each platform reads only its own configuration section plus shared sections:

| Platform | Config Section | Required Fields |
|----------|---------------|-----------------|
| `llmops.arize` | `arize:` | `service.name`, `arize.endpoint` |
| `llmops.mlflow` | `mlflow:` | `service.name`, `mlflow.tracking_uri` |

**Shared sections** (read by all platforms):
- `service:` — Service identity
- `instrumentation:` — Which auto-instrumentors to enable
- `validation:` — Validation mode

---

## 5. Error Handling

### 5.1 Missing Platform Dependencies

When platform-specific packages are not installed:

```python
>>> import llmops
>>> llmops.arize.instrument()
ImportError: Arize platform requires 'arize-otel' package.
Install with: pip install llmops[arize]
```

**Key behaviors:**
- `import llmops` always succeeds (no platform dependencies loaded)
- `import llmops.arize` may succeed (module exists) but `instrument()` fails if deps missing
- Error message includes exact pip install command

### 5.2 Configuration Errors

**Strict mode:**
```python
>>> llmops.arize.instrument(config_path="missing.yaml")
ConfigurationError: Configuration file not found: missing.yaml
```

**Permissive mode:**
```python
>>> llmops.arize.instrument(config_path="invalid.yaml")
# Logs warning, returns no-op TracerProvider
```

### 5.3 Telemetry Isolation

All telemetry failures after initialization are swallowed and logged. Auto-instrumentation failures never raise exceptions to user code.

---

## 6. Platform Interface Contract

All platform modules must implement the Platform Protocol:

```python
# llmops/_platforms/_base.py

from typing import Protocol
from pathlib import Path

class Platform(Protocol):
    """Protocol that all platform implementations must satisfy.
    
    Note: @runtime_checkable is intentionally omitted. Type checkers
    validate Protocol conformance statically. Only add @runtime_checkable
    if isinstance() checks are needed, and avoid such checks in hot paths.
    """

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

    def create_tracer_provider(self, config: "LLMOpsConfig") -> "TracerProvider":
        """Create platform-specific TracerProvider."""
        ...

    def get_instrumentor_registry(self) -> list[tuple[str, str, str]]:
        """Return list of (config_key, module_path, class_name) tuples."""
        ...
```

---

## 7. Instrumentor Registry

### 7.1 Arize Platform Instrumentors

| Config Key | Module | Class | Notes |
|------------|--------|-------|-------|
| `google_adk` | `openinference.instrumentation.google_adk` | `GoogleADKInstrumentor` | Google Agent Development Kit |
| `google_genai` | `openinference.instrumentation.google_genai` | `GoogleGenAIInstrumentor` | Google GenAI SDK |

### 7.2 MLflow Platform Instrumentors (Skeleton)

| Config Key | Module | Class | Notes |
|------------|--------|-------|-------|
| `gemini` | `mlflow.gemini` | `autolog` | Placeholder |
| `openai` | `mlflow.openai` | `autolog` | Placeholder |

### 7.3 Instrumentor Behavior

- Instrumentors are enabled by default (`true` in config)
- Missing instrumentor packages are logged at debug level, not errors
- Instrumentor failures are swallowed (telemetry never breaks business logic)

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

### Modules

| Module | Purpose |
|--------|---------|
| `llmops` | Package root with lazy platform accessors |
| `llmops.arize` | Arize platform auto-instrumentation |
| `llmops.mlflow` | MLflow platform auto-instrumentation (skeleton) |

### Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `llmops.arize.instrument` | `(config_path: str \| Path \| None = None)` | `TracerProvider` |
| `llmops.mlflow.instrument` | `(config_path: str \| Path \| None = None)` | `TracerProvider` |

### Exceptions

| Exception | When Raised |
|-----------|-------------|
| `llmops.ConfigurationError` | Invalid config in strict mode |
| `ImportError` | Platform dependencies missing |

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `llmops.__version__` | `"0.2.0"` | SDK version |

---

## 10. Type Stubs

For IDE support and type checking, the package provides type information:

```python
# llmops/__init__.pyi
from llmops import arize as arize
from llmops import mlflow as mlflow
from llmops.exceptions import ConfigurationError as ConfigurationError

__version__: str

# llmops/arize.pyi
from pathlib import Path
from opentelemetry.sdk.trace import TracerProvider

def instrument(
    config_path: str | Path | None = None,
) -> TracerProvider: ...

# llmops/mlflow.pyi
from pathlib import Path
from opentelemetry.sdk.trace import TracerProvider

def instrument(
    config_path: str | Path | None = None,
) -> TracerProvider: ...
```

---

## 11. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_01.md` | Requirements and success criteria |
| `docs/CONCEPTUAL_ARCHITECTURE.md` | High-level conceptual view |
| `docs/reference_architecture/REFERENCE_ARCHITECTURE_01.md` | Architectural patterns and invariants |
| `docs/analysis/PLATFORM_ARCHITECTURE_ANALYSIS.md` | Analysis of design options |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-22
