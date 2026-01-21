# PRD_01 — Arize Single-Backend Auto-Instrumentation

**Version:** 0.1
**Date:** 2026-01-21
**Status:** Draft

---

## 1. Problem Statement

Greenfield GenAI applications need fast, low-friction Arize telemetry without learning OpenTelemetry internals. This PRD assumes no prior SDK exists; this is the first feature and the first public interface.

We need a thin SDK layer that:
- Reads a config file (`llmops.yaml` preferred, `llmops.yml` supported) supplied explicitly
- Initializes Arize telemetry in one call
- Auto-instruments Google ADK and Google GenAI by default
- Remains extendable to future instrumentors (for example, OpenAI)

---

## 2. Product Vision

A single-call initialization API that lets a solo developer on a greenfield app enable Arize GenAI tracing in minutes.

The SDK provides:
- One public `init()` entry point
- A single-user interface for configuration
- Automatic setup for Arize telemetry plus Google ADK and Google GenAI

---

## 3. Target User Persona

### Primary Persona

**Greenfield developer** building a new GenAI application who wants immediate Arize telemetry with minimal setup.

### Non-Target Persona

**Existing OpenTelemetry users** with a global tracer provider and dual-backend requirements. These users require manual configuration and filtered span processors, which this SDK will not automate.

---

## 4. Goals

1. **One-call setup** — `init()` wires Arize, Google ADK, and Google GenAI with no additional code
2. **Config-driven** — Explicit config path via `init()` or env var, file-first with overrides
3. **Safety** — Telemetry never breaks business logic
4. **Extensible** — Design allows adding additional auto-instrumentors (example: OpenAI)

---

## 5. Non-Goals

- Supporting dual-backend or existing global tracer provider setups
- Replacing OpenTelemetry or Arize/Phoenix SDKs
- Building custom OpenTelemetry instrumentors
- Providing manual instrumentation APIs in this iteration

---

## 6. Constraints

| Constraint | Rationale |
|------------|-----------|
| Python ≥3.13 | Matches repo baseline |
| Greenfield only | Avoids conflict with existing tracer providers |
| Single backend | Ensures safe one-line setup |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| A1 | `init()` initializes Arize telemetry and returns a tracer provider | Must |
| A2 | `init()` auto-instruments Google ADK | Must |
| A3 | `init()` auto-instruments Google GenAI | Must |
| A4 | `init()` requires an explicit config path (arg or env var) | Must |
| A5 | `init()` accepts a config path parameter | Must |
| A6 | `init()` supports config path override via env var | Must |
| A7 | `init()` accepts `llmops.yaml` (preferred) and `llmops.yml` (supported) | Must |
| A8 | Sensitive values (example: API keys) can be set via env var overrides | Must |
| A9 | Future instrumentors can be added without changing the public API | Should |

### 7.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| N1 | Telemetry failures do not raise exceptions to user code | Must |
| N2 | Telemetry must never break business logic | Must |
| N3 | Startup time impact remains minimal | Should |
| N4 | All setup completes in a single synchronous call | Must |
| N5 | Permissive validation uses a no-op tracer provider on config errors | Must |
| N6 | Strict validation fails startup on config errors (dev only) | Must |

---

## 8. Configuration

### Config File

The config file is required and must be provided explicitly via `init(config_path=...)` or an environment variable. The preferred filename is `llmops.yaml`, with `llmops.yml` also supported.

### Environment Overrides

An environment variable provides the config path. Sensitive values (example: API keys) should be overridable via environment variables.

### Validation Modes

Config validation supports two modes, defaulting to permissive:
- **Strict (dev)**: raises a configuration error and prevents app startup.
- **Permissive (prod, default)**: logs a warning and continues with a no-op tracer provider.

---

## 9. Success Criteria

- A greenfield application shows Arize GenAI traces after a single `init()` call.
- No additional manual instrumentation is required for Google ADK or Google GenAI.
- Configuration can be set exclusively via `llmops.yaml`, with optional env overrides.

---

## 10. User Story

### US0: One-Call Arize Auto-Instrumentation

> As a greenfield developer, I want a single `init()` call to enable Arize telemetry and auto-instrument Google ADK and Google GenAI so I can see traces immediately.

**Acceptance:**
- `llmops.yaml` (preferred) or `llmops.yml` is supplied via `init()` or env var
- `init()` configures Arize telemetry
- Google ADK and Google GenAI calls are traced without decorators
- Permissive validation falls back to a no-op tracer provider on config errors

---

## 11. Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Exact env var naming for config path and API keys | Needs design |
| 2 | Minimal config fields for Arize and Phoenix endpoints | Needs design |
| 3 | Default validation mode is permissive | Closed |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-21
