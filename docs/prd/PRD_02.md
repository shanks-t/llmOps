# PRD_02 — Add-On Instrumentation for Existing OpenTelemetry Users (Nurse Handoff)

**Version:** 0.1
**Date:** 2026-01-24
**Status:** Draft

---

## 1. Problem Statement

PRD_01 serves greenfield applications with no existing telemetry. Many production applications already have OpenTelemetry configured, sending traces to infrastructure backends (Dynatrace, Datadog, Google Cloud Trace).

These teams want to add Arize for LLM-specific observability without disrupting their existing setup.

**Current limitation:** `llmops.arize.instrument()` creates a new global TracerProvider, replacing the user's existing provider and breaking their current observability.

**What users need:** Add Arize telemetry to their existing provider, not replace it.

---

## 2. Product Vision

An **add-on pattern** that:

1. Works with an existing global TracerProvider
2. Adds Arize as an additional export destination
3. Only sends GenAI-relevant spans to Arize by default
4. Requires minimal configuration

```python
import llmops

# User's existing setup already configured
# ...

# Add Arize instrumentation to existing provider
llmops.arize.instrument_existing_tracer(
    endpoint="https://otlp.arize.com/v1",
    api_key=os.environ["ARIZE_API_KEY"],
    space_id=os.environ["ARIZE_SPACE_ID"],
)
```

---

## 3. Target User Persona

### Primary Persona

**Enterprise developer with existing observability** — Has a production application sending traces to an infrastructure backend and wants to add Arize for GenAI insights without disrupting current telemetry.

### Non-Target Persona

- **Greenfield developers** — Use `llmops.arize.instrument()` from PRD_01
- **Users wanting full trace duplication** — This feature filters to GenAI spans by default

---

## 4. Goals

1. **Non-Disruptive** — Never replace existing TracerProvider
2. **Selective Export** — Only GenAI spans go to Arize by default
3. **Minimal Configuration** — Works with just credentials; no config file required
4. **Idempotent** — Calling twice doesn't add duplicate processors

---

## 5. Non-Goals

- Replacing `instrument()` API from PRD_01
- Supporting MLflow with this pattern
- Providing lifecycle management (shutdown)
- Custom filtering beyond GenAI/all toggle

---

## 6. Constraints

| Constraint | Rationale |
|------------|-----------|
| Existing SDK TracerProvider required | Cannot add processors to NoOp providers reliably |
| GenAI filtering uses OpenInference attribute | Standard from OpenInference instrumentors |
| No atexit registration | User owns provider lifecycle |

---

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | `instrument_existing_tracer()` adds Arize to existing global provider | Must |
| F2 | Accepts programmatic credentials (endpoint, api_key, space_id) | Must |
| F3 | Accepts optional config file path | Should |
| F4 | Programmatic credentials override config file values | Must |
| F5 | Only OpenInference spans sent to Arize by default | Must |
| F6 | `filter_to_genai_spans=False` sends all spans | Must |
| F7 | Duplicate calls log warning and skip | Must |
| F8 | Google ADK and GenAI auto-instrumented against existing provider | Must |

### 7.2 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| N1 | Telemetry failures never raise exceptions | Must |
| N2 | Non-SDK provider logs warning but continues | Must |
| N3 | No atexit handler registered | Must |
| N4 | Works without config file if credentials provided | Must |

---

## 8. User Stories

### US1: Add Arize to Existing Setup

> As a developer with Dynatrace configured, I want to add Arize for GenAI traces without losing my infrastructure observability.

**Acceptance:**
- Existing traces continue flowing to original backend
- GenAI spans appear in both backends
- Non-GenAI spans only go to original backend

### US2: Programmatic Configuration

> As a developer, I want to configure Arize with environment variables so I don't need a config file.

**Acceptance:**
- `instrument_existing_tracer(endpoint=..., api_key=..., space_id=...)` works without config file

### US3: Prevent Duplicate Instrumentation

> As a developer, I want the SDK to be safe to call multiple times.

**Acceptance:**
- Second call logs warning
- No duplicate processor added

---

## 9. Success Criteria

- Existing TracerProvider users can add Arize with one function call
- GenAI spans appear in Arize; infrastructure spans stay in original backend
- No config file required with programmatic credentials
- Calling twice is safe

---

## 10. Relationship to PRD_01

| Behavior | `instrument()` (PRD_01) | `instrument_existing_tracer()` (PRD_02) |
|----------|------------------------|----------------------------------------|
| Creates new provider | Yes | No |
| Sets global provider | Yes | No (uses existing) |
| Registers atexit | Yes | No |
| `filter_to_genai_spans` default | False | True |
| Config file required | Yes | No |

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-24
