# PRD_01 — Behavioral Test Coverage

This directory contains executable contracts derived from:

- **PRD:** [docs/prd/PRD_01.md](../../../docs/prd/PRD_01.md)
- **API Spec:** [docs/api_spec/API_SPEC_01.md](../../../docs/api_spec/API_SPEC_01.md)

## Coverage Map

| Capability | Test File | API Methods | PRD Requirements |
|------------|-----------|-------------|------------------|
| Arize instrument entrypoint | `test_arize_instrument_spec.py` | `llmops.arize.instrument()` | F1, F2, F6, F7, N4 |
| Arize validation + safety | `test_arize_validation_spec.py` | `llmops.arize.instrument()` | N1, N2, N5, N6 |
| Arize auto-instrumentation | `test_arize_auto_instrumentation_spec.py` | `llmops.arize.instrument()` | F3, F4, F8 |
| Arize env var overrides | `test_arize_env_overrides_spec.py` | `llmops.arize.instrument()` | F10 |
| Arize telemetry config | `test_arize_telemetry_spec.py` | `_platforms.arize` | F2 |
| MLflow skeleton entrypoint | `test_mlflow_instrument_spec.py` | `llmops.mlflow.instrument()` | F1, F6, F7, F14, N5, N6 |
| Lazy loading + dependency errors | `test_lazy_loading_spec.py` | `llmops.__getattr__` | F5, F11, N8 |
| Platform isolation | `test_platform_isolation_spec.py` | `llmops.<platform>.instrument()` | F9, F12, F13 |

## Requirements Coverage Summary

### Functional Requirements

| ID | Requirement | Test File | Status |
|----|-------------|-----------|--------|
| F1 | Each platform exposes `llmops.<platform>.instrument(config_path)` | `test_arize_instrument_spec.py` | Covered |
| F2 | `llmops.arize.instrument()` returns a tracer provider | `test_arize_instrument_spec.py` | Covered |
| F3 | `llmops.arize.instrument()` auto-instruments Google ADK | `test_arize_auto_instrumentation_spec.py` | Covered |
| F4 | `llmops.arize.instrument()` auto-instruments Google GenAI | `test_arize_auto_instrumentation_spec.py` | Covered |
| F5 | Platform modules are lazy-imported | `test_lazy_loading_spec.py` | Covered |
| F6 | `instrument()` requires explicit config path | `test_arize_instrument_spec.py` | Covered |
| F7 | `instrument()` accepts `.yaml` and `.yml` | `test_arize_instrument_spec.py` | Covered |
| F8 | Platforms define supported instrumentors | `test_arize_auto_instrumentation_spec.py` | Covered |
| F9 | Config schema includes platform sections | `test_platform_isolation_spec.py` | Covered |
| F10 | Sensitive values via env var overrides | `test_arize_env_overrides_spec.py` | Covered |
| F11 | Missing platform deps raise helpful ImportError | `test_lazy_loading_spec.py` | Covered |
| F12 | Platforms share config loading/validation | `test_platform_isolation_spec.py` | Covered |
| F13 | Future platforms added without core changes | `test_platform_isolation_spec.py` | Covered |
| F14 | `llmops.mlflow.instrument()` skeleton exists | `test_mlflow_instrument_spec.py` | Covered |

### Non-Functional Requirements

| ID | Requirement | Test File | Status |
|----|-------------|-----------|--------|
| N1 | Telemetry failures don't raise | `test_arize_validation_spec.py` | Covered |
| N2 | Telemetry never breaks business logic | `test_arize_validation_spec.py` | Covered |
| N3 | Minimal startup time impact | — | Not tested (Should) |
| N4 | Single synchronous call | `test_arize_instrument_spec.py` | Covered |
| N5 | Permissive mode uses no-op provider | `test_arize_validation_spec.py` | Covered |
| N6 | Strict mode fails on config errors | `test_arize_validation_spec.py` | Covered |
| N7 | Missing deps error indicates platform | `test_lazy_loading_spec.py` | Covered |
| N8 | Import time for unused platforms is zero | `test_lazy_loading_spec.py` | Covered |
| N9 | Startup time impact remains minimal | — | Not tested (Should) |

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
