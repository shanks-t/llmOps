# PRD_01 — Behavioral Test Coverage

This directory contains executable contracts derived from:

- **PRD:** [docs/prd/PRD_01.md](../../../docs/prd/PRD_01.md)
- **API Spec:** [docs/api_spec/API_SPEC_01.md](../../../docs/api_spec/API_SPEC_01.md)

## Coverage Map

| Capability | Test File | API Methods | PRD Requirements |
|------------|-----------|-------------|------------------|
| SDK initialization | `test_init_spec.py` | `init()` | A1, A4, A5, A6, A7 |
| Config validation | `test_validation_spec.py` | `init()` | N1, N2, N5, N6 |
| Auto-instrumentation | `test_auto_instrumentation_spec.py` | `init()` | A2, A3, A9 |
| Env var overrides | `test_env_overrides_spec.py` | `init()` | A8 |

## Requirements Coverage Summary

### Functional Requirements

| ID | Requirement | Test File | Status |
|----|-------------|-----------|--------|
| A1 | `init()` returns a tracer provider | `test_init_spec.py` | Covered |
| A2 | `init()` auto-instruments Google ADK | `test_auto_instrumentation_spec.py` | Covered |
| A3 | `init()` auto-instruments Google GenAI | `test_auto_instrumentation_spec.py` | Covered |
| A4 | `init()` requires explicit config path | `test_init_spec.py` | Covered |
| A5 | `init()` accepts config path parameter | `test_init_spec.py` | Covered |
| A6 | `init()` supports env var config path | `test_init_spec.py` | Covered |
| A7 | `init()` accepts `.yaml` and `.yml` | `test_init_spec.py` | Covered |
| A8 | Sensitive values via env var overrides | `test_env_overrides_spec.py` | Covered |
| A9 | Future instrumentors extensibility | `test_auto_instrumentation_spec.py` | Covered |

### Non-Functional Requirements

| ID | Requirement | Test File | Status |
|----|-------------|-----------|--------|
| N1 | Telemetry failures don't raise | `test_validation_spec.py` | Covered |
| N2 | Telemetry never breaks business logic | `test_validation_spec.py` | Covered |
| N3 | Minimal startup time impact | — | Not tested (Should) |
| N4 | Single synchronous call | — | Implicit in all tests |
| N5 | Permissive mode uses no-op provider | `test_validation_spec.py` | Covered |
| N6 | Strict mode fails on config errors | `test_validation_spec.py` | Covered |

## Agent Instructions

Use these tests as the source of behavioral truth for PRD_01.
Do not modify tests unless the PRD or API spec is updated.

```
You are implementing functionality for PRD_01.
Use the tests under llm-observability-sdk/tests/prd_01/ as the source of behavioral truth.
Do not change tests unless the PRD or API spec is updated.
```

## Test Status

Tests are marked with `xfail` until implementation is complete:

- `XFAIL` — Test runs, failure expected (implementation pending)
- `XPASS` — Test unexpectedly passes (implementation landed)
- Remove `xfail` marker once implementation is verified
