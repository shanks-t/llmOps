# PRD_01 — Reference Architecture

**Version:** 0.1
**Date:** 2026-01-21
**Status:** Draft

---

## 1. Purpose

This document defines how the PRD_01 system should be built. It codifies architectural invariants, boundaries, and patterns for a single-backend Arize auto-instrumentation SDK.

---

## 2. Architectural Shape

### 2.1 Components

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| **Public API** | `init()` entry point | Only public interface in this iteration |
| **Config Loader** | Read `llmops.yaml`/`llmops.yml`, apply overrides | Explicit path via init or env |
| **Telemetry Setup** | Configure OTel + Arize exporter | Single backend only |
| **Instrumentor Runner** | Enable Google ADK + Google GenAI | Default enabled |

### 2.2 Dependency Rule

Strict downward-only dependencies:

```
Public API → Config Loader → Telemetry Setup → Instrumentor Runner
```

No component may depend on a higher-level component.

---

## 3. Core Invariants

These invariants must hold across all implementations.

### 3.1 Telemetry Safety

```
INVARIANT 1: Telemetry never breaks business logic
```

**Rules:**
- No SDK call raises exceptions to user code.
- `init()` logs failures and returns safely.
- Instrumentor errors do not prevent application startup.
- Configuration errors fail fast at startup, not during runtime operations.

### 3.2 Single Backend

```
INVARIANT 2: Only one tracer provider and one backend are configured
```

**Rules:**
- The SDK always owns the tracer provider lifecycle.
- The SDK does not attach to an existing global provider.
- No multi-backend routing or span filtering is introduced.

### 3.3 Configuration Source of Truth

```
INVARIANT 3: Configuration requires explicit path selection
```

**Rules:**
- `init(config_path=...)` must be provided or `LLMOPS_CONFIG_PATH` must be set.
- Supported filenames are `llmops.yaml` (preferred) and `llmops.yml`.
- Environment variables override file values.
- Only one config file is used per process.

---

## 4. Initialization Flow

### 4.1 Sequence

```
init(config_path?)
  → resolve config path
  → load llmops.yml
  → merge env overrides
  → validate config
  → initialize tracer provider + exporter
  → auto-instrument Google ADK + Google GenAI
  → return tracer provider
```

### 4.2 Validation Contract

Validation occurs during `init()` only and respects the configured mode:
- **Strict (dev)**: raises a configuration error and fails startup.
- **Permissive (prod)**: logs a warning, returns a no-op tracer provider.
- Missing optional fields use defaults.

---

## 5. Error Handling Pattern

Telemetry errors are isolated from business logic.

```
INVARIANT 4: SDK failures are swallowed and logged
```

**Pattern:**
```python
try:
    _internal_operation()
except Exception as exc:
    _log_internal_error(exc)
    return None
```

All internal operations follow this pattern, including instrumentation and export.

### 5.1 Validation Mode Behavior

- **Strict (dev)**: `init()` raises `ConfigurationError` on invalid config.
- **Permissive (prod, default)**: `init()` logs a warning and returns a no-op tracer provider.

---

## 6. Configuration Model

### 6.1 Required Fields

| Field | Required | Notes |
|-------|----------|-------|
| `service.name` | Yes | Service identity for tracing |
| `arize.endpoint` | Yes | Phoenix or Arize AX OTLP endpoint |
| `validation.mode` | Yes | `strict` or `permissive` |

### 6.2 Optional Fields

| Field | Default | Notes |
|-------|---------|-------|
| `service.version` | `null` | Optional metadata |
| `arize.project_name` | `null` | Phoenix project label |
| `instrumentation.google_adk` | `true` | Enabled by default |
| `instrumentation.google_genai` | `true` | Enabled by default |
| `privacy.capture_content` | `false` | Content capture opt-in |
| `validation.mode` | `permissive` | `strict` or `permissive` (default permissive) |

---

## 7. Auto-Instrumentation Rules

### 7.1 Instrumentors

- Google ADK instrumentor uses the SDK-provided tracer provider.
- Google GenAI instrumentor uses the SDK-provided tracer provider.
- Missing instrumentor packages log a warning and continue.

### 7.2 Order of Operations

1. Configure tracer provider and exporter
2. Set global tracer provider (SDK-owned)
3. Install instrumentors

---

## 8. Extension Points

The public API must not change when adding instrumentors.

```
Instrumentor Registry
├── Google ADK (default)
├── Google GenAI (default)
└── OpenAI (future)
```

Each instrumentor receives the same tracer provider instance.

---

## 9. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/PRD_01.md` | Requirements and success criteria |
| `docs/CONCEPTUAL_ARCHITECTURE_01.md` | High-level conceptual view |
| API Specification (next) | Public interface and config contracts |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-21
