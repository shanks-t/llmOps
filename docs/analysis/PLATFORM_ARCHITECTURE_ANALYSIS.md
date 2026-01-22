# Platform Registry & Instrumentation Interface — Architecture Analysis

**Version:** 0.1
**Date:** 2026-01-22
**Status:** Draft
**Purpose:** Explore architectural options for PRD_02 implementation

---

## 1. Overview

This document analyzes different approaches for implementing:

1. **Platform Registry** — How platforms (Arize, MLflow, etc.) are discovered and accessed
2. **Instrumentation Interface** — How platform modules implement the `instrument()` contract

We evaluate each approach against criteria including developer experience, extensibility, type safety, and alignment with Python ecosystem standards.

---

## 2. Platform Registry Patterns

### 2.1 Pattern A: Static Module Imports (Explicit Namespaces)

**Approach:** Each platform is a dedicated module that users import directly.

```python
# User code
import llmops.arize
llmops.arize.instrument(config_path="llmops.yaml")

# Or
from llmops import arize
arize.instrument(config_path="llmops.yaml")
```

**Implementation:**
```python
# llmops/__init__.py
from llmops import arize  # Eager import
# or
def __getattr__(name):    # Lazy import
    if name == "arize":
        from llmops import arize
        return arize
    raise AttributeError(f"module 'llmops' has no attribute '{name}'")
```

**Examples in Industry:**
- `boto3.client('s3')` vs `boto3.resource('s3')` — explicit service selection
- `sqlalchemy.dialects.postgresql` — database-specific modules
- `requests_oauthlib` — extension as separate module

**Trade-offs:**

| Pros | Cons |
|------|------|
| Excellent IDE support (autocomplete, type checking) | New platforms require code changes to `__init__.py` |
| Clear, explicit API | Cannot add platforms without SDK release |
| No magic or discovery overhead | Platform list is hardcoded |
| Easy to understand and debug | |

**Best for:** SDKs with a known, stable set of backends that change infrequently.

---

### 2.2 Pattern B: Entry Points (Plugin Discovery)

**Approach:** Platforms register themselves via Python entry points (setuptools/importlib.metadata).

```python
# User code
import llmops
llmops.get_platform("arize").instrument(config_path="llmops.yaml")

# Or with convenience accessor
llmops.platforms.arize.instrument(config_path="llmops.yaml")
```

**Implementation:**
```toml
# In platform package's pyproject.toml (e.g., llmops-arize)
[project.entry-points."llmops.platforms"]
arize = "llmops_arize:ArizePlatform"
```

```python
# llmops/registry.py
from importlib.metadata import entry_points

def discover_platforms() -> dict[str, type]:
    eps = entry_points(group="llmops.platforms")
    return {ep.name: ep.load() for ep in eps}

def get_platform(name: str):
    platforms = discover_platforms()
    if name not in platforms:
        raise ValueError(f"Unknown platform: {name}. Available: {list(platforms.keys())}")
    return platforms[name]()
```

**Examples in Industry:**
- **pytest** — `pytest11` entry point for plugins
- **OpenTelemetry** — `opentelemetry_instrumentor` entry point
- **Flask** — `flask.commands` entry point for CLI extensions
- **tox** — `tox` entry point for plugins

**Trade-offs:**

| Pros | Cons |
|------|------|
| Truly extensible — third parties can add platforms | Worse IDE support (dynamic discovery) |
| Platforms can be versioned independently | Entry point scanning has overhead |
| No core SDK changes for new platforms | Harder to debug (where did this platform come from?) |
| Standard Python pattern | Type checking is weaker |
| Supports optional dependencies naturally | Users must know platform names as strings |

**Best for:** SDKs designed for ecosystem extensibility where third parties add backends.

---

### 2.3 Pattern C: Configuration-Driven Registry

**Approach:** The config file specifies which platform to use; a registry maps names to implementations.

```yaml
# llmops.yaml
platform: arize  # Selects the platform
arize:
  endpoint: "http://localhost:6006/v1/traces"
```

```python
# User code
import llmops
llmops.instrument(config_path="llmops.yaml")  # Platform from config
```

**Implementation:**
```python
# llmops/registry.py
PLATFORM_REGISTRY = {
    "arize": "llmops._platforms.arize:ArizePlatform",
    "mlflow": "llmops._platforms.mlflow:MLflowPlatform",
}

def get_platform_from_config(config_path: str):
    config = load_config(config_path)
    platform_name = config.get("platform")
    if platform_name not in PLATFORM_REGISTRY:
        raise ConfigurationError(f"Unknown platform: {platform_name}")
    module_path, class_name = PLATFORM_REGISTRY[platform_name].rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()
```

**Examples in Industry:**
- **Django** — `DATABASES['default']['ENGINE']` selects database backend
- **Celery** — `broker_url` determines message broker
- **logging** — `handlers` config selects handler classes

**Trade-offs:**

| Pros | Cons |
|------|------|
| Single `instrument()` call (simpler API) | Platform choice hidden in config (less explicit) |
| Config is the source of truth | Harder to catch errors at import time |
| Easy environment-based switching | IDE can't help with platform-specific options |
| Familiar pattern from Django/Celery | Config validation more complex |

**Best for:** Applications where platform selection is an operational concern, not a development concern.

---

### 2.4 Pattern D: Factory Function with Enum

**Approach:** A factory function accepts a platform identifier (enum or string literal).

```python
# User code
import llmops
from llmops import Platform

provider = llmops.instrument(
    platform=Platform.ARIZE,  # or platform="arize"
    config_path="llmops.yaml"
)
```

**Implementation:**
```python
# llmops/__init__.py
from enum import Enum

class Platform(Enum):
    ARIZE = "arize"
    MLFLOW = "mlflow"

def instrument(
    platform: Platform | str,
    config_path: str | Path | None = None,
) -> TracerProvider:
    platform_name = platform.value if isinstance(platform, Platform) else platform
    platform_impl = _get_platform_impl(platform_name)
    return platform_impl.instrument(config_path)
```

**Examples in Industry:**
- **boto3** — `boto3.client('s3')` with string service names
- **OpenTelemetry** — `trace.get_tracer("name")` with string identifiers
- **httpx** — `httpx.Client(http2=True)` with feature flags

**Trade-offs:**

| Pros | Cons |
|------|------|
| Single entry point with explicit platform selection | Enum must be updated for new platforms |
| Good IDE support with Enum | String variant loses type safety |
| Clear what platforms are available | Mixes concerns (platform + config path) |
| Easy to validate platform choice | |

**Best for:** SDKs where platform selection is a code-level decision with a fixed set of options.

---

### 2.5 Pattern E: Hybrid (Recommended)

**Approach:** Combine static modules (Pattern A) with lazy loading and optional entry point extension.

```python
# Primary API: Static modules (great DX)
import llmops
llmops.arize.instrument(config_path="llmops.yaml")

# Alternative: Factory for dynamic selection
llmops.instrument(platform="arize", config_path="llmops.yaml")

# Extension: Entry points for third-party platforms
llmops.platforms["custom"].instrument(...)
```

**Implementation:**
```python
# llmops/__init__.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llmops import arize as arize
    from llmops import mlflow as mlflow

def __getattr__(name: str):
    """Lazy-load platform modules."""
    if name == "arize":
        from llmops import arize
        return arize
    if name == "mlflow":
        from llmops import mlflow
        return mlflow
    raise AttributeError(f"module 'llmops' has no attribute '{name}'")

def __dir__():
    return ["arize", "mlflow", "instrument", "ConfigurationError", ...]

# Optional: Dynamic platform access
class _PlatformRegistry:
    def __getitem__(self, name: str):
        # Check built-in platforms first
        if name in ("arize", "mlflow"):
            return __getattr__(name)
        # Fall back to entry points for third-party
        return _load_entry_point_platform(name)

platforms = _PlatformRegistry()
```

**Examples in Industry:**
- **OpenTelemetry SDK** — Built-in exporters + entry point discovery
- **SQLAlchemy** — Built-in dialects + third-party dialect support
- **pytest** — Built-in plugins + entry point plugins

**Trade-offs:**

| Pros | Cons |
|------|------|
| Best DX for common platforms (static modules) | More complex implementation |
| Extensible for edge cases (entry points) | Two ways to do the same thing |
| Excellent IDE support for built-in platforms | Documentation must cover both patterns |
| Third parties can extend without forking | |

**Best for:** SDKs that want excellent DX for common cases while remaining extensible.

---

## 3. Instrumentation Interface Patterns

### 3.1 Pattern A: Abstract Base Class (ABC)

**Approach:** Define an abstract class that all platforms must inherit from.

```python
# llmops/_platforms/_base.py
from abc import ABC, abstractmethod

class Platform(ABC):
    """Abstract base for platform implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform identifier."""
        ...

    @property
    @abstractmethod
    def config_section(self) -> str:
        """Config file section name."""
        ...

    @abstractmethod
    def instrument(
        self,
        config_path: str | Path | None = None,
    ) -> TracerProvider:
        """Initialize telemetry and auto-instrumentation."""
        ...

    @abstractmethod
    def get_instrumentor_registry(self) -> list[tuple[str, str, str]]:
        """Return instrumentors as (config_key, module, class) tuples."""
        ...
```

```python
# llmops/_platforms/arize.py
class ArizePlatform(Platform):
    @property
    def name(self) -> str:
        return "arize"

    def instrument(self, config_path=None) -> TracerProvider:
        # Implementation
        ...
```

**Examples in Industry:**
- **OpenTelemetry** — `SpanExporter`, `SpanProcessor` ABCs
- **Django** — `BaseCache`, `BaseEmailBackend` ABCs
- **SQLAlchemy** — `Dialect` base class

**Trade-offs:**

| Pros | Cons |
|------|------|
| Clear contract — IDE shows required methods | Inheritance can be inflexible |
| Runtime validation via `isinstance()` | ABC registration can be confusing |
| Self-documenting interface | Harder to test (must subclass) |
| Familiar OOP pattern | Python's ABC can feel heavyweight |

---

### 3.2 Pattern B: Protocol (Structural Typing)

**Approach:** Define a Protocol that describes the interface without inheritance.

```python
# llmops/_platforms/_base.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class Platform(Protocol):
    """Protocol for platform implementations."""

    @property
    def name(self) -> str: ...

    @property
    def config_section(self) -> str: ...

    def instrument(
        self,
        config_path: str | Path | None = None,
    ) -> TracerProvider: ...

    def get_instrumentor_registry(self) -> list[tuple[str, str, str]]: ...
```

```python
# llmops/_platforms/arize.py
class ArizePlatform:  # No inheritance required
    @property
    def name(self) -> str:
        return "arize"

    def instrument(self, config_path=None) -> TracerProvider:
        # Implementation
        ...
```

**Examples in Industry:**
- **typing** — `Iterable`, `Sized`, `Callable` protocols
- **collections.abc** — Protocol-like ABCs
- **Modern Python libraries** — Increasingly using Protocol over ABC

**Trade-offs:**

| Pros | Cons |
|------|------|
| No inheritance required (duck typing) | `@runtime_checkable` has performance cost |
| Better for composition | Less obvious what to implement |
| Easier to mock in tests | Runtime checking is optional |
| More Pythonic (duck typing) | IDE support varies |

---

### 3.3 Pattern C: Function-Based (No Classes)

**Approach:** Each platform is a module with functions, no class abstraction.

```python
# llmops/arize.py
def instrument(config_path: str | Path | None = None) -> TracerProvider:
    """Initialize Arize telemetry."""
    config = _load_config(config_path)
    provider = _create_arize_provider(config)
    _apply_instrumentors(provider, config)
    return provider

def get_instrumentor_registry() -> list[tuple[str, str, str]]:
    return [
        ("google_adk", "openinference.instrumentation.google_adk", "GoogleADKInstrumentor"),
        ("google_genai", "openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor"),
    ]
```

**Examples in Industry:**
- **requests** — `requests.get()`, `requests.post()` (module-level functions)
- **json** — `json.dumps()`, `json.loads()`
- **os.path** — Function-based API

**Trade-offs:**

| Pros | Cons |
|------|------|
| Simplest possible API | No formal interface contract |
| No class instantiation overhead | Harder to share state between calls |
| Easy to understand | Can't use `isinstance()` checks |
| Natural for simple cases | Composition patterns are awkward |

---

### 3.4 Pattern D: Decorated Registration

**Approach:** Platforms register themselves via decorators.

```python
# llmops/registry.py
_PLATFORMS: dict[str, type] = {}

def register_platform(name: str):
    def decorator(cls):
        _PLATFORMS[name] = cls
        return cls
    return decorator

def get_platform(name: str):
    return _PLATFORMS[name]()
```

```python
# llmops/_platforms/arize.py
from llmops.registry import register_platform

@register_platform("arize")
class ArizePlatform:
    def instrument(self, config_path=None):
        ...
```

**Examples in Industry:**
- **Flask** — `@app.route()` decorator registration
- **Click** — `@click.command()` decorator
- **pytest** — `@pytest.fixture` registration

**Trade-offs:**

| Pros | Cons |
|------|------|
| Self-registering (no central registry file) | Import order matters |
| Familiar Flask/FastAPI pattern | Module must be imported to register |
| Easy to add new platforms | Hidden side effects on import |
| Declarative | Harder to see all platforms at once |

---

### 3.5 Pattern E: Factory with Dependency Injection

**Approach:** A factory creates platform instances, injecting shared dependencies.

```python
# llmops/factory.py
class PlatformFactory:
    def __init__(self, config_loader, instrumentor_runner):
        self._config_loader = config_loader
        self._instrumentor_runner = instrumentor_runner

    def create(self, platform_name: str) -> Platform:
        platform_class = self._resolve_platform(platform_name)
        return platform_class(
            config_loader=self._config_loader,
            instrumentor_runner=self._instrumentor_runner,
        )
```

**Examples in Industry:**
- **Angular** — Dependency injection throughout
- **pytest** — Fixture injection
- **FastAPI** — `Depends()` injection

**Trade-offs:**

| Pros | Cons |
|------|------|
| Highly testable (inject mocks) | More complex setup |
| Shared services are explicit | Overkill for simple SDKs |
| Clear dependency graph | Unfamiliar to some Python developers |
| Enables advanced patterns | Configuration can be verbose |

---

## 4. Comparison Matrix

### 4.1 Platform Registry Patterns

| Pattern | DX | Type Safety | Extensibility | Complexity | Recommendation |
|---------|-----|-------------|---------------|------------|----------------|
| A: Static Modules | Excellent | Excellent | Poor | Low | Good for stable platforms |
| B: Entry Points | Fair | Poor | Excellent | Medium | Good for plugin ecosystems |
| C: Config-Driven | Good | Fair | Good | Medium | Good for ops-driven selection |
| D: Factory + Enum | Good | Good | Fair | Low | Good for fixed platform set |
| **E: Hybrid** | **Excellent** | **Excellent** | **Good** | **Medium** | **Recommended** |

### 4.2 Instrumentation Interface Patterns

| Pattern | Type Safety | Testability | Simplicity | Flexibility | Recommendation |
|---------|-------------|-------------|------------|-------------|----------------|
| A: ABC | Excellent | Good | Good | Fair | Good for formal contracts |
| **B: Protocol** | **Excellent** | **Excellent** | **Good** | **Excellent** | **Recommended** |
| C: Functions | Poor | Excellent | Excellent | Poor | Good for simple cases |
| D: Decorators | Fair | Fair | Good | Good | Good for plugin systems |
| E: DI Factory | Excellent | Excellent | Poor | Excellent | Good for complex systems |

---

## 5. Industry Standards & Best Practices

### 5.1 OpenTelemetry SDK Pattern

OpenTelemetry uses a combination of:
- **Abstract base classes** for core interfaces (`SpanExporter`, `SpanProcessor`)
- **Entry points** for auto-discovered instrumentors
- **Explicit registration** for exporters and processors

```python
# OpenTelemetry pattern
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
```

**Lesson:** Explicit configuration with composable components.

### 5.2 pytest Plugin Pattern

pytest uses:
- **Entry points** for plugin discovery (`pytest11` group)
- **Hook specifications** (Protocol-like) for plugin interface
- **Fixture injection** for dependency management

```python
# pytest plugin pattern
# pyproject.toml
[project.entry-points.pytest11]
my_plugin = "my_plugin:plugin"

# my_plugin.py
def pytest_configure(config):
    ...
```

**Lesson:** Entry points work well for ecosystem extensibility.

### 5.3 SQLAlchemy Dialect Pattern

SQLAlchemy uses:
- **Static imports** for common dialects (`from sqlalchemy.dialects import postgresql`)
- **URL-based selection** (`create_engine("postgresql://...")`)
- **Entry points** for third-party dialects

```python
# SQLAlchemy pattern
from sqlalchemy import create_engine

# Dialect selected by URL scheme
engine = create_engine("postgresql://user:pass@localhost/db")
```

**Lesson:** URL/config-driven selection with static imports as convenience.

### 5.4 boto3 Client Pattern

boto3 uses:
- **Factory function** with string service names
- **Lazy service loading** (services loaded on first use)
- **Shared session** for configuration

```python
# boto3 pattern
import boto3

s3 = boto3.client('s3')  # Factory with string identifier
dynamodb = boto3.resource('dynamodb')
```

**Lesson:** Simple factory API, but loses type safety.

---

## 6. Recommendation for llmops

Based on the analysis, I recommend:

### 6.1 Platform Registry: Hybrid (Pattern E)

**Primary API:** Static module imports with lazy loading
```python
import llmops
llmops.arize.instrument(config_path="llmops.yaml")
```

**Rationale:**
- Excellent IDE support for the 2-3 platforms we'll ship
- Lazy loading avoids importing unused platform dependencies
- Entry points can be added later for third-party platforms without breaking the primary API

### 6.2 Instrumentation Interface: Protocol (Pattern B)

**Interface:**
```python
@runtime_checkable
class Platform(Protocol):
    @property
    def name(self) -> str: ...

    def instrument(
        self,
        config_path: str | Path | None = None,
    ) -> TracerProvider: ...
```

**Rationale:**
- No inheritance required (more Pythonic)
- Excellent testability (easy to mock)
- Type checkers understand Protocols well
- Flexible for future evolution

### 6.3 Implementation Sketch

```python
# llmops/__init__.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llmops import arize as arize

def __getattr__(name: str):
    if name == "arize":
        from llmops import arize
        return arize
    raise AttributeError(f"module 'llmops' has no attribute '{name}'")

# llmops/_platforms/_base.py
from typing import Protocol

class Platform(Protocol):
    @property
    def name(self) -> str: ...

    def instrument(self, config_path=None) -> TracerProvider: ...

# llmops/arize.py
from llmops._platforms.arize import ArizePlatform

_platform = ArizePlatform()

def instrument(config_path=None):
    return _platform.instrument(config_path)
```

---

## 7. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | Should we support both `llmops.arize.instrument()` and `llmops.instrument(platform="arize")`? | API surface area |
| 2 | Should entry points be supported in v0.2 or deferred? | Scope |
| 3 | How do we handle platform-specific configuration validation? | Config complexity |
| 4 | Should platforms share an instrumentor runner or each have their own? | Code reuse |

---

## 8. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/prd/PRD_02.md` | Multi-platform requirements |
| `docs/api_spec/API_SPEC_02.md` | API specification |
| `docs/CONCEPTUAL_ARCHITECTURE.md` | High-level system shape |
| `docs/reference_architecture/REFERENCE_ARCHITECTURE_01.md` | Architectural patterns |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-22
