# PRD_01 — API Specification

**Version:** 0.2
**Date:** 2026-01-22
**Status:** Draft

---

## 1. Overview

This document defines the public API for PRD_01. The SDK exposes a single entry point for auto-instrumentation of Google ADK and Google GenAI with Arize telemetry.

**Design Principle:** The API should be usable in under 3 lines.

---

## 2. Package Structure

```
llmops/
├── __init__.py      # Public API exports
├── instrument.py    # instrument() entry point
├── config.py        # Config loader and data models
└── _internal/       # Private implementation
```

---

## 3. Public API

### 3.1 `instrument()`

Initialize Arize telemetry and auto-instrumentation in a single call.

**Signature:**
```python
def instrument(
    config_path: str | Path | None = None,
) -> TracerProvider:
    """
    Initialize Arize telemetry and auto-instrumentation.

    Args:
        config_path: Optional path to `llmops.yaml` (preferred) or `llmops.yml`.
                     If omitted, `LLMOPS_CONFIG_PATH` must be set.

    Returns:
        The configured OpenTelemetry TracerProvider.

    Raises:
        ConfigurationError: If config is missing or invalid (startup only).

    Behavior:
        - Loads config from explicit path (`instrument()` arg or `LLMOPS_CONFIG_PATH`).
        - Applies environment variable overrides.
        - Configures Arize telemetry (Phoenix or Arize AX).
        - Sets the global tracer provider.
        - Auto-instruments Google ADK and Google GenAI.
        - Registers an atexit handler to flush spans on process exit.
        - Telemetry failures never break business logic.
        - In permissive mode, returns a no-op tracer provider on config errors.

    Note:
        An atexit handler is automatically registered to call provider.shutdown()
        when the process exits. This ensures buffered spans are flushed even in
        scripts without explicit lifecycle management. For long-running servers,
        you may still call provider.shutdown() in your cleanup code—it's safe
        to call multiple times.
    """
```

**Quick Start Example:**
```python
import llmops

llmops.instrument()
```

**Custom Config Path Example:**
```python
import llmops

llmops.instrument(config_path="/services/chat/llmops.yaml")
```

---

## 4. Configuration

### 4.1 File Name and Location

- Preferred file name is `llmops.yaml`.
- `llmops.yml` is supported.
- The path must be provided explicitly via `instrument()` or `LLMOPS_CONFIG_PATH`.

### 4.2 Environment Overrides

Environment variables override config values. Sensitive values (example: API keys) are expected to be set via environment variables. `LLMOPS_CONFIG_PATH` provides the config path when `instrument()` omits it.

### 4.3 YAML Schema

```yaml
# llmops.yaml
service:
  name: "my-service"
  version: "1.0.0"

arize:
  endpoint: "http://localhost:6006/v1/traces"
  project_name: "my-project"          # Optional
  api_key: "${ARIZE_API_KEY}"         # Optional, prefer env var
  space_id: "${ARIZE_SPACE_ID}"       # Optional (Arize AX)

  # Transport and processing options
  transport: "http"                   # "http" (default) or "grpc"
  batch_spans: true                   # true (default) or false
  debug: false                        # Log spans to console (default: false)

  # TLS certificate for self-hosted HTTPS endpoints
  # Path can be relative (resolved from config file) or absolute
  certificate_file: "./certs/ca.pem"

instrumentation:
  google_adk: true
  google_genai: true

validation:
  mode: permissive  # strict or permissive (default permissive)
```

---

## 5. Error Handling

### 5.1 `ConfigurationError`

Raised only during `instrument()` when configuration is invalid in strict mode.

```python
class ConfigurationError(Exception):
    """Raised when SDK configuration is invalid."""
```

### 5.2 Telemetry Isolation

All telemetry failures are swallowed and logged internally. The SDK must never raise runtime exceptions that affect business logic. In permissive mode, invalid config results in a no-op tracer provider.

---

## 6. Environment Variables

Environment variable names will follow the `LLMOPS_` prefix. Standard OpenTelemetry environment variables are also supported for TLS configuration.

| Variable | Purpose |
|----------|---------|
| `LLMOPS_CONFIG_PATH` | Path to `llmops.yaml` or `llmops.yml` |
| `OTEL_EXPORTER_OTLP_CERTIFICATE` | Fallback for `certificate_file` (CA cert) |

---

## 7. Public API Summary

- `llmops.instrument(config_path: str | Path | None = None) -> TracerProvider`
- `llmops.ConfigurationError`

---

## 8. Related Documents

| Document | Purpose |
|----------|---------|
| `docs/PRD_01.md` | Requirements and success criteria |
| `docs/CONCEPTUAL_ARCHITECTURE_01.md` | High-level conceptual view |
| `docs/REFERENCE_ARCHITECTURE_01.md` | Architectural patterns and invariants |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-22
