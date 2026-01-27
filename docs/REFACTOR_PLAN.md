# LLMOPS SDK Refactor Plan

**Version:** 0.1  
**Date:** 2026-01-27  
**Status:** Draft  
**Implements:** DESIGN_PHILOSOPHY.md

---

## 1. Overview

### 1.1 Current State

```
llmops/
├── __init__.py              # Lazy loads arize/mlflow modules
├── arize.py                 # llmops.arize.instrument()
├── mlflow.py                # llmops.mlflow.instrument()
├── config.py                # Config dataclasses + YAML loading
├── exceptions.py            # ConfigurationError
├── _platforms/              # Platform implementations
│   ├── _base.py             # Platform Protocol
│   ├── _registry.py         # Instrumentor runner
│   ├── _instrument.py       # Shared instrumentation workflow
│   ├── arize.py             # ArizePlatform class
│   └── mlflow.py            # MLflowPlatform class
└── _internal/
    ├── telemetry.py         # arize.otel.register() wrapper
    └── instrumentation.py   # Dead code (duplicate)
```

**Public API:** `llmops.arize.instrument(config_path)`, `llmops.mlflow.instrument(config_path)`

### 1.2 Target State

```
llmops/
├── __init__.py              # Re-exports from api/
├── api/
│   ├── __init__.py          # Public: init, shutdown, is_configured, Config
│   ├── init.py              # init(), shutdown(), is_configured()
│   └── types.py             # Config dataclasses
├── sdk/
│   ├── config/
│   │   ├── model.py         # Internal config validation
│   │   └── load.py          # YAML loading + env substitution
│   ├── lifecycle.py         # Global state management
│   └── pipeline.py          # Exporter dispatch + instrumenter application
├── exporters/
│   ├── arize/
│   │   ├── __init__.py
│   │   ├── exporter.py      # create_arize_provider()
│   │   └── mapper.py        # Config → arize.otel args
│   └── mlflow/
│       ├── __init__.py
│       └── exporter.py      # Skeleton
├── instrumentation/
│   ├── __init__.py
│   ├── google_adk.py        # ADK instrumentor wrapper
│   └── google_genai.py      # GenAI instrumentor wrapper
├── _internal/
│   ├── __init__.py
│   └── logging.py           # SDK internal logging
└── exceptions.py            # ConfigurationError
```

**Public API:** `llmops.init(config)`, `llmops.shutdown()`, `llmops.is_configured()`, `llmops.Config`

### 1.3 Breaking Changes

| Change | Migration |
|--------|-----------|
| `llmops.arize.instrument()` removed | Use `llmops.init(config="...")` |
| `llmops.mlflow.instrument()` removed | Use `llmops.init(config="...")` |
| Config requires `platform:` field | Add `platform: arize` to YAML |
| `instrument()` returned TracerProvider | `init()` returns None |

---

## 2. Phase 1: Package Restructure

Create the new directory structure without deleting old code yet.

### 2.1 Create Directories

```bash
mkdir -p llm-observability-sdk/src/llmops/api
mkdir -p llm-observability-sdk/src/llmops/sdk/config
mkdir -p llm-observability-sdk/src/llmops/exporters/arize
mkdir -p llm-observability-sdk/src/llmops/exporters/mlflow
mkdir -p llm-observability-sdk/src/llmops/instrumentation
```

### 2.2 Create api/types.py

Define public config types:

```python
# llmops/api/types.py
from dataclasses import dataclass, field

@dataclass
class ServiceConfig:
    name: str
    version: str = "0.0.0"

@dataclass
class ArizeConfig:
    endpoint: str
    project_name: str | None = None
    api_key: str | None = None
    space_id: str | None = None
    transport: str = "http"
    batch_spans: bool = True
    debug: bool = False
    certificate_file: str | None = None

@dataclass
class MLflowConfig:
    tracking_uri: str
    experiment_name: str | None = None

@dataclass
class InstrumentationConfig:
    google_adk: bool = True
    google_genai: bool = True

@dataclass
class ValidationConfig:
    mode: str = "permissive"  # "strict" | "permissive"

@dataclass
class Config:
    platform: str  # "arize" | "mlflow"
    service: ServiceConfig
    arize: ArizeConfig | None = None
    mlflow: MLflowConfig | None = None
    instrumentation: InstrumentationConfig = field(default_factory=InstrumentationConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
```

### 2.3 Create sdk/config/load.py

Move YAML loading logic:

```python
# llmops/sdk/config/load.py
import os
import re
from pathlib import Path
import yaml
from llmops.api.types import Config, ServiceConfig, ArizeConfig, ...
from llmops.exceptions import ConfigurationError

def load_config(path: str | Path) -> Config:
    """Load and parse config from YAML file."""
    path = Path(path)
    if not path.exists():
        raise ConfigurationError(f"Config file not found: {path}")
    
    with open(path) as f:
        raw = yaml.safe_load(f)
    
    raw = _substitute_env_vars(raw)
    return _parse_config(raw)

def _substitute_env_vars(data: dict) -> dict:
    """Replace ${VAR} with environment variable values."""
    # Implementation from current config.py
    ...

def _parse_config(raw: dict) -> Config:
    """Parse raw dict into Config dataclass."""
    if "platform" not in raw:
        raise ConfigurationError("Config must specify 'platform' field")
    # Implementation
    ...
```

### 2.4 Create sdk/lifecycle.py

Global state management:

```python
# llmops/sdk/lifecycle.py
from opentelemetry.sdk.trace import TracerProvider

_configured: bool = False
_provider: TracerProvider | None = None

def set_configured(provider: TracerProvider) -> None:
    global _configured, _provider
    _configured = True
    _provider = provider

def is_configured() -> bool:
    return _configured

def get_provider() -> TracerProvider | None:
    return _provider

def shutdown() -> None:
    global _configured, _provider
    if _provider is not None:
        _provider.shutdown()
    _configured = False
    _provider = None
```

### 2.5 Create api/init.py

Main entry points:

```python
# llmops/api/init.py
import atexit
from pathlib import Path
from llmops.api.types import Config
from llmops.sdk.config.load import load_config
from llmops.sdk.lifecycle import set_configured, is_configured as _is_configured, shutdown as _shutdown
from llmops.sdk.pipeline import create_provider, apply_instrumentation
from llmops.exceptions import ConfigurationError

def init(config: str | Path | Config) -> None:
    """Initialize LLMOPS SDK with the given configuration."""
    if isinstance(config, (str, Path)):
        config = load_config(config)
    
    provider = create_provider(config)
    apply_instrumentation(config, provider)
    set_configured(provider)
    atexit.register(_shutdown)

def shutdown() -> None:
    """Shutdown the SDK and flush pending telemetry."""
    _shutdown()

def is_configured() -> bool:
    """Check if the SDK has been initialized."""
    return _is_configured()
```

### 2.6 Create api/__init__.py

Public exports:

```python
# llmops/api/__init__.py
from llmops.api.init import init, shutdown, is_configured
from llmops.api.types import (
    Config,
    ServiceConfig,
    ArizeConfig,
    MLflowConfig,
    InstrumentationConfig,
    ValidationConfig,
)

__all__ = [
    "init",
    "shutdown",
    "is_configured",
    "Config",
    "ServiceConfig",
    "ArizeConfig",
    "MLflowConfig",
    "InstrumentationConfig",
    "ValidationConfig",
]
```

---

## 3. Phase 2: Exporter Migration

### 3.1 Create exporters/arize/exporter.py

```python
# llmops/exporters/arize/exporter.py
from opentelemetry.sdk.trace import TracerProvider
from llmops.api.types import Config
from llmops.exporters.arize.mapper import map_config_to_register_args

def create_arize_provider(config: Config) -> TracerProvider:
    """Create TracerProvider configured for Arize."""
    try:
        from arize.otel import register
    except ImportError:
        raise ImportError(
            "Arize exporter requires 'arize-otel' package.\n"
            "Install with: pip install llmops[arize]"
        )
    
    args = map_config_to_register_args(config)
    return register(**args)

def check_dependencies() -> None:
    """Raise ImportError if Arize dependencies are missing."""
    try:
        import arize.otel
    except ImportError:
        raise ImportError(
            "Arize exporter requires 'arize-otel' package.\n"
            "Install with: pip install llmops[arize]"
        )
```

### 3.2 Create exporters/arize/mapper.py

```python
# llmops/exporters/arize/mapper.py
import os
from llmops.api.types import Config

def map_config_to_register_args(config: Config) -> dict:
    """Map Config to arize.otel.register() kwargs."""
    arize = config.arize
    if arize is None:
        raise ValueError("Arize config section required when platform is 'arize'")
    
    # Handle TLS certificate
    if arize.certificate_file:
        os.environ.setdefault("OTEL_EXPORTER_OTLP_CERTIFICATE", arize.certificate_file)
    
    return {
        "endpoint": arize.endpoint,
        "space_id": arize.space_id,
        "api_key": arize.api_key,
        "project_name": arize.project_name or config.service.name,
        "model_id": config.service.name,
        "model_version": config.service.version,
        "batch": arize.batch_spans,
        "log_to_console": arize.debug,
    }
```

### 3.3 Create exporters/mlflow/exporter.py

```python
# llmops/exporters/mlflow/exporter.py
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from llmops.api.types import Config

def create_mlflow_provider(config: Config) -> TracerProvider:
    """Create TracerProvider configured for MLflow (skeleton)."""
    try:
        import mlflow
    except ImportError:
        raise ImportError(
            "MLflow exporter requires 'mlflow' package.\n"
            "Install with: pip install llmops[mlflow]"
        )
    
    # Skeleton implementation - just creates a basic provider
    resource = Resource.create({
        "service.name": config.service.name,
        "service.version": config.service.version,
    })
    return TracerProvider(resource=resource)

def check_dependencies() -> None:
    """Raise ImportError if MLflow dependencies are missing."""
    try:
        import mlflow
    except ImportError:
        raise ImportError(
            "MLflow exporter requires 'mlflow' package.\n"
            "Install with: pip install llmops[mlflow]"
        )
```

### 3.4 Create sdk/pipeline.py

```python
# llmops/sdk/pipeline.py
import importlib
import logging
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry import trace
from llmops.api.types import Config

logger = logging.getLogger("llmops")

EXPORTER_FACTORIES = {
    "arize": ("llmops.exporters.arize.exporter", "create_arize_provider"),
    "mlflow": ("llmops.exporters.mlflow.exporter", "create_mlflow_provider"),
}

INSTRUMENTOR_REGISTRY = [
    ("google_adk", "openinference.instrumentation.google_adk", "GoogleADKInstrumentor"),
    ("google_genai", "openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor"),
]

def create_provider(config: Config) -> TracerProvider:
    """Create TracerProvider for the configured platform."""
    platform = config.platform
    if platform not in EXPORTER_FACTORIES:
        raise ValueError(f"Unknown platform: {platform}. Valid: {list(EXPORTER_FACTORIES.keys())}")
    
    module_path, factory_name = EXPORTER_FACTORIES[platform]
    module = importlib.import_module(module_path)
    factory = getattr(module, factory_name)
    
    provider = factory(config)
    trace.set_tracer_provider(provider)
    return provider

def apply_instrumentation(config: Config, provider: TracerProvider) -> None:
    """Apply auto-instrumentation based on config."""
    for config_key, module_path, class_name in INSTRUMENTOR_REGISTRY:
        enabled = getattr(config.instrumentation, config_key, False)
        if not enabled:
            continue
        
        try:
            module = importlib.import_module(module_path)
            instrumentor_class = getattr(module, class_name)
            instrumentor = instrumentor_class()
            instrumentor.instrument(tracer_provider=provider)
            logger.debug("Applied instrumentor: %s", config_key)
        except ImportError:
            logger.debug("Instrumentor not installed: %s", module_path)
        except Exception as e:
            logger.warning("Instrumentor failed: %s - %s", config_key, e)
```

---

## 4. Phase 3: Remove Old API

### 4.1 Delete Files

| File | Action |
|------|--------|
| `llmops/arize.py` | Delete |
| `llmops/mlflow.py` | Delete |
| `llmops/_platforms/__init__.py` | Delete |
| `llmops/_platforms/_base.py` | Delete |
| `llmops/_platforms/_registry.py` | Delete |
| `llmops/_platforms/_instrument.py` | Delete |
| `llmops/_platforms/arize.py` | Delete |
| `llmops/_platforms/mlflow.py` | Delete |
| `llmops/_internal/instrumentation.py` | Delete |
| `llmops/_internal/telemetry.py` | Delete |
| `llmops/config.py` | Delete (moved to sdk/config/) |

### 4.2 Delete Directories

```bash
rm -rf llmops/_platforms/
# Keep llmops/_internal/ but remove old files
```

### 4.3 Update __init__.py

```python
# llmops/__init__.py
"""LLMOPS SDK - LLM Observability for Python."""

from llmops.api import (
    init,
    shutdown,
    is_configured,
    Config,
    ServiceConfig,
    ArizeConfig,
    MLflowConfig,
    InstrumentationConfig,
    ValidationConfig,
)
from llmops.exceptions import ConfigurationError

__version__ = "0.3.0"

__all__ = [
    "init",
    "shutdown",
    "is_configured",
    "Config",
    "ServiceConfig",
    "ArizeConfig",
    "MLflowConfig",
    "InstrumentationConfig",
    "ValidationConfig",
    "ConfigurationError",
    "__version__",
]
```

---

## 5. Phase 4: Instrumentation Wrappers

### 5.1 Create instrumentation/google_adk.py

```python
# llmops/instrumentation/google_adk.py
"""Google ADK instrumentation wrapper."""

def instrument(tracer_provider):
    """Apply Google ADK instrumentation."""
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor
    instrumentor = GoogleADKInstrumentor()
    instrumentor.instrument(tracer_provider=tracer_provider)
```

### 5.2 Create instrumentation/google_genai.py

```python
# llmops/instrumentation/google_genai.py
"""Google GenAI instrumentation wrapper."""

def instrument(tracer_provider):
    """Apply Google GenAI instrumentation."""
    from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
    instrumentor = GoogleGenAIInstrumentor()
    instrumentor.instrument(tracer_provider=tracer_provider)
```

---

## 6. Config Schema Changes

### 6.1 New Required Field

Add `platform` as a required top-level field:

```yaml
# llmops.yaml
platform: arize  # NEW: Required field

service:
  name: "my-service"
  version: "1.0.0"

arize:
  endpoint: "https://otlp.arize.com/v1"
  # ... rest unchanged
```

### 6.2 Validation

- `platform` must be one of: `["arize", "mlflow"]`
- Corresponding section must exist (if `platform: arize`, then `arize:` section required)
- `service.name` remains required

---

## 7. File-by-File Summary

### 7.1 Files to Create

| File | Purpose |
|------|---------|
| `api/__init__.py` | Public exports |
| `api/init.py` | `init()`, `shutdown()`, `is_configured()` |
| `api/types.py` | Config dataclasses |
| `sdk/__init__.py` | Package marker |
| `sdk/config/__init__.py` | Package marker |
| `sdk/config/model.py` | Internal config validation |
| `sdk/config/load.py` | YAML loading |
| `sdk/lifecycle.py` | Global state |
| `sdk/pipeline.py` | Exporter dispatch + instrumentation |
| `exporters/__init__.py` | Package marker |
| `exporters/arize/__init__.py` | Package marker |
| `exporters/arize/exporter.py` | Arize factory |
| `exporters/arize/mapper.py` | Config mapping |
| `exporters/mlflow/__init__.py` | Package marker |
| `exporters/mlflow/exporter.py` | MLflow skeleton |
| `instrumentation/__init__.py` | Package marker |
| `instrumentation/google_adk.py` | ADK wrapper |
| `instrumentation/google_genai.py` | GenAI wrapper |
| `_internal/logging.py` | SDK logging |

### 7.2 Files to Delete

| File | Reason |
|------|--------|
| `arize.py` | Replaced by `init()` |
| `mlflow.py` | Replaced by `init()` |
| `config.py` | Moved to `sdk/config/` |
| `_platforms/*` | Entire directory removed |
| `_internal/instrumentation.py` | Dead code |
| `_internal/telemetry.py` | Moved to `exporters/arize/` |

### 7.3 Files to Modify

| File | Changes |
|------|---------|
| `__init__.py` | New exports, remove lazy loading |
| `exceptions.py` | Keep as-is |

---

## 8. Testing Updates

### 8.1 Update Test Imports

**Before:**
```python
from llmops.arize import instrument
provider = instrument(config_path="test.yaml")
```

**After:**
```python
import llmops
llmops.init(config="test.yaml")
# No return value - use llmops.is_configured() to verify
```

### 8.2 Update Test Config Files

Add `platform: arize` to all test YAML files:

```yaml
platform: arize  # Add this line
service:
  name: "test-service"
# ... rest unchanged
```

### 8.3 New Test Cases

| Test | Purpose |
|------|---------|
| `test_init_from_yaml` | Verify `init()` loads YAML config |
| `test_init_from_config_object` | Verify `init()` accepts `Config` |
| `test_init_missing_platform` | Verify error for missing platform field |
| `test_init_invalid_platform` | Verify error for unknown platform |
| `test_is_configured_before_init` | Returns False |
| `test_is_configured_after_init` | Returns True |
| `test_shutdown_flushes` | Verify shutdown calls provider.shutdown() |
| `test_double_init_warning` | Second init logs warning (or raises) |

---

## 9. Documentation Updates

### 9.1 PRD Updates

Add note to PRD_01.md:

```markdown
> **Note:** The API described in this document (`llmops.arize.instrument()`) has been
> superseded by the single-init pattern (`llmops.init()`). See DESIGN_PHILOSOPHY.md
> for the updated design rationale.
```

### 9.2 Example Updates

Update all examples in `docs/` and `examples/` to use:

```python
import llmops
llmops.init(config="llmops.yaml")
```

---

## 10. Migration Checklist

### Phase 1: Package Restructure
- [ ] Create `api/` directory and files
- [ ] Create `sdk/config/` directory and files
- [ ] Create `sdk/lifecycle.py`
- [ ] Create `sdk/pipeline.py`
- [ ] Verify imports work alongside old code

### Phase 2: Exporter Migration
- [ ] Create `exporters/arize/` with exporter.py and mapper.py
- [ ] Create `exporters/mlflow/` with skeleton
- [ ] Verify Arize exporter works via new path

### Phase 3: Remove Old API
- [ ] Delete `arize.py`, `mlflow.py`
- [ ] Delete `_platforms/` directory
- [ ] Delete old `_internal/` files
- [ ] Update `__init__.py` exports
- [ ] Delete `config.py` (after migration complete)

### Phase 4: Finalize
- [ ] Create instrumentation wrappers
- [ ] Update all test configs with `platform:` field
- [ ] Update all test imports
- [ ] Run `just` to verify quality checks pass
- [ ] Update examples and documentation

---

**Document Owner:** Platform Team  
**Last Updated:** 2026-01-27
