# LLMOPS SDK Design Philosophy

**Version:** 0.1  
**Date:** 2026-01-27  
**Status:** Draft

---

## 1. Overview

This document defines the design philosophy for the LLMOPS SDK. It establishes principles that guide architectural decisions, API design, and future evolution.

**Audience:** SDK contributors and maintainers  
**Relationship:** Complements PRD and architecture docs; takes precedence on design questions

---

## 2. Core Principles

### 2.1 One Stable Public API, Many Interchangeable Pipelines

The public API is boring and consistent:

```python
import llmops
llmops.init(config="llmops.yaml")
```

That's the entire user-facing surface for initialization. The config file (or `Config` object) determines which backend, which instrumenters, and which behaviors are active.

**Rationale:** If an average app developer has to remember which backend namespace to call, the SDK is leaking internal topology. The "how" (pipeline implementation) should be separable from the "what" (stable API contract).

**Rule:** One `init()`, one `shutdown()`. Config drives composition.

---

### 2.2 API vs SDK Split

Create a hard boundary between contract and mechanism:

| Layer | Location | Stability | Contents |
|-------|----------|-----------|----------|
| **API** | `llmops/api/` | Stable (semver-major) | `init()`, `shutdown()`, `is_configured()`, `Config`, `ConfigurationError` |
| **SDK** | `llmops/sdk/` | Internal | Config loading, lifecycle, pipeline composition |
| **Exporters** | `llmops/exporters/` | Internal | Arize, MLflow, future backends |
| **Instrumentation** | `llmops/instrumentation/` | Internal | Google ADK, Google GenAI hooks |

The API layer has minimal dependencies. The SDK layer contains implementation details that may evolve between minor versions. Exporters and instrumentation are "edge" code that changes frequently.

---

### 2.3 Opinionated Defaults, Explicit Escape Hatches

A great SDK:
- Works in 5 minutes with default configuration
- Can be customized without forking

**Default behavior:**
- Permissive validation (degrades to no-op on errors)
- Auto-instrumentation enabled for all supported frameworks
- Batch span processing enabled

**Escape hatches:**
- Strict validation mode for development
- Per-instrumenter enable/disable flags
- Transport and batching configuration

The SDK should "just work" for the common case while providing knobs for teams with specific requirements.

---

### 2.4 Edge Mess Stays at the Edge

Anything that changes frequently belongs at the edges:
- Arize SDK version updates → `llmops/exporters/arize/`
- ADK instrumentation changes → `llmops/instrumentation/google_adk.py`
- New backend integrations → new exporter module

**Rule:** The core (`llmops/api/`, `llmops/sdk/`) never imports vendor SDKs directly. Vendor code is isolated behind factory functions that are only called when that backend is configured.

This keeps the dependency graph clean and allows adding new backends without touching existing code.

---

### 2.5 Telemetry Never Breaks Business Logic

All SDK failures are caught and logged. No exceptions propagate to user code after `init()` returns.

**Behaviors:**
- `init()` in permissive mode: logs warning, returns successfully (with no-op provider)
- `init()` in strict mode: raises `ConfigurationError` (dev-time feedback)
- Instrumentor failures: logged at debug level, silently skipped
- Export failures: logged, retried per OTel SDK behavior

**Rationale:** Observability is a supporting function. A misconfigured API key should not bring down a production service.

---

## 3. API Stability Rules

### 3.1 Public API Contract

The following are public and stable:

```python
llmops.init(config: str | Path | Config) -> None
llmops.shutdown() -> None
llmops.is_configured() -> bool
llmops.Config  # Dataclass for programmatic config
llmops.ConfigurationError  # Exception
llmops.__version__  # Semver string
llmops.eval  # Reserved namespace (future)
```

**Stability guarantee:** These signatures only change with semver-major versions. If a breaking change is necessary, it will be preceded by at least one minor version with deprecation warnings.

### 3.2 Internal API

Everything under `llmops.sdk.*`, `llmops.exporters.*`, and `llmops.instrumentation.*` is internal. These modules:
- May change between minor versions
- Are not guaranteed stable for external use
- Should not be imported by application code

### 3.3 Configuration Schema

The YAML configuration schema follows additive evolution:
- New optional fields may be added in minor versions
- Required fields cannot be added without a major version
- Field semantics cannot change without a major version
- Environment variable names (e.g., `LLMOPS_CONFIG_PATH`) are stable

---

## 4. Extension Points

### 4.1 Adding a New Exporter

To add support for a new observability backend:

1. Create `llmops/exporters/{name}/exporter.py`
2. Implement a factory function: `create_exporter(config) -> TracerProvider`
3. Add configuration section to schema
4. Register in pipeline dispatch logic

**Invariant:** Adding a new exporter requires no changes to `llmops/api/` or existing exporters.

### 4.2 Adding a New Instrumenter

To add auto-instrumentation for a new framework:

1. Create `llmops/instrumentation/{name}.py`
2. Implement `instrument(tracer_provider)` function that wraps the upstream instrumentor
3. Register in the instrumentor registry
4. Instrumenter failures are swallowed (telemetry safety)

**Invariant:** Adding a new instrumenter requires no changes to `llmops/api/` or public config types.

### 4.3 Instrumentor Registry Pattern

The SDK uses a central registry to manage instrumentors. This pattern enables scaling to many instrumentors without API churn.

**Why a registry:**
- Instrumentors can be added without modifying public `Config` types
- Configuration uses a list (`instrumentation.enabled`) rather than per-instrumentor boolean fields
- Unknown instrumentor names are gracefully ignored with a warning
- Aligns with the "edge mess stays at the edge" principle

**Configuration model:**
```yaml
instrumentation:
  enabled:
    - google_adk
    - google_genai
    - openai  # Future: just add to list, no API changes
```

**Extension process:**
1. Create wrapper module in `llmops/instrumentation/`
2. Add entry to instrumentor registry (single location)
3. Add optional dependency to `pyproject.toml`
4. Done — no public API changes, no config type changes

This pattern allows the instrumentor count to grow (OpenAI, Anthropic, Cohere, LangChain, LlamaIndex, etc.) without accumulating boolean fields in the public configuration types.

### 4.4 Custom Processing (Future)

The architecture accommodates future extension points:
- Span processors for filtering, redacting, or enriching
- Custom exporters beyond the built-in set
- Sampling strategies

These are not in the initial implementation but the pipeline composition layer is designed to support them.

---

## 5. Evaluation Vision (Future)

Evaluation is out of scope for the initial implementation but the design anticipates it.

### 5.1 Concepts

| Concept | Purpose |
|---------|---------|
| **Template** | Reusable eval spec: metrics, judge model, thresholds |
| **Selector** | Query DSL for which telemetry to evaluate |
| **Extractor** | How to get input/output from spans (framework-specific) |

### 5.2 Anticipated API Shape

```python
llmops.eval.register_template(template)
results = llmops.eval.run(
    template="faithfulness_v1",
    selector=Selector.query("span.kind == 'llm'"),
    extractor=Extractor.from_instrumentation("google_adk"),
)
```

**Status:** Deferred. Namespace `llmops.eval` reserved. Will wrap Arize AX evaluation primitives. SDK-first API with optional CLI wrapper.

---

## 6. Semantic Conventions (Future)

### 6.1 Current State

The SDK relies on OpenInference semantic conventions from upstream instrumentors. There is no SDK-defined semantic model.

### 6.2 Future Direction

When patterns stabilize, the SDK may define:
- Thin wrappers over OpenInference constants
- Explicit stability levels (dev/beta/stable) per convention
- Validation helpers for span attributes

**Status:** Deferred. OpenInference is actively evolving; premature standardization would create maintenance burden.

---

## 7. Decision Records

### 7.1 Why Single `init()` Over Namespaced Pattern

**Context:** PRD_01 originally specified `llmops.arize.instrument()` for explicit platform selection.

**Decision:** Replace with single `llmops.init()` with config-driven platform selection.

**Rationale:**
- Better composability (config can be environment-specific)
- Aligns with OTel SDK patterns
- Smaller public API surface
- Platform selection is still explicit via `platform:` config field

**Trade-off:** Less explicit in code which backend is active. Mitigated by requiring explicit `platform:` field in config.

### 7.2 Why Config-Only Exporters

**Context:** Could expose `llmops.exporters.ArizeExporter` for programmatic composition.

**Decision:** Exporters are internal. Users configure via YAML or `Config` object.

**Rationale:**
- Minimal API surface
- Config is the primary UX; programmatic config is secondary
- Avoids exposing vendor-specific types in public API

**Trade-off:** Cannot programmatically compose exporters at runtime. Mitigated by `llmops.Config()` for code-based configuration.

### 7.3 Why Defer Semantic Model

**Context:** Could define SDK-level types for LLM spans (input, output, tokens, etc.).

**Decision:** Defer. Continue relying on OpenInference conventions from instrumentors.

**Rationale:**
- OpenInference is actively evolving
- Premature standardization creates mapping complexity
- Instrumentors already handle convention compliance

**Revisit when:** OpenInference conventions stabilize and teams need SDK-level type safety.

### 7.4 Why Instrumentor Registry Over Explicit Fields

**Context:** Could use explicit boolean fields for each instrumentor in `InstrumentationConfig`:
```python
@dataclass
class InstrumentationConfig:
    google_adk: bool = True
    google_genai: bool = True
    openai: bool = True  # Added for each new instrumentor
```

**Decision:** Use a registry pattern with an `enabled` list instead.

**Rationale:**
- Adding instrumentors should not change public API types
- Boolean fields create API churn as instrumentors are added
- A list-based config (`enabled: [google_adk, openai]`) is more flexible
- Unknown instrumentor names can be gracefully ignored
- Follows OTel pattern where instrumentors are separate packages, not SDK fields

**Trade-off:** Less IDE autocomplete for instrumentor names. Mitigated by documentation and validation warnings for unknown names.

### 7.5 Why Factory Functions Over Protocol

**Context:** Could define a formal `Platform` Protocol that exporters must implement:
```python
class Platform(Protocol):
    def create_tracer_provider(self, config) -> TracerProvider: ...
    def get_instrumentor_registry(self) -> list: ...
```

**Decision:** Use simple factory functions instead.

**Rationale:**
- Exporters are internal, not a third-party extension point
- Factory functions are simpler and sufficient for internal use
- Protocols add boilerplate without benefit when extension is controlled
- Aligns with OTel Python SDK pattern (duck-typed base classes, not Protocols)

**Revisit when:** The SDK needs to support third-party exporter plugins (currently not planned).

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **API** | Stable public interface (`llmops.init()`, etc.) |
| **SDK** | Internal implementation (config loading, pipeline composition) |
| **Exporter** | Component that sends telemetry to a backend (Arize, MLflow) |
| **Exporter Factory** | Function that creates a configured TracerProvider for a specific backend |
| **Instrumenter** | Component that auto-instruments a framework (Google ADK) |
| **Instrumentor Registry** | Central mapping of instrumentor names to their module paths |
| **Processor** | Component that transforms spans (filtering, batching) |
| **Platform** | Observability backend (Arize, MLflow) — term from PRD, now called "exporter" |
| **Pipeline** | Composed chain: instrumenter → processor → exporter |

---

**Document Owner:** Platform Team  
**Last Updated:** 2026-01-27
