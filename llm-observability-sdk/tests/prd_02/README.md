# PRD_02 — Behavioral Test Coverage

This directory contains executable contracts derived from:

- **PRD:** [docs/prd/PRD_02.md](../../../docs/prd/PRD_02.md)
- **API Spec:** [docs/api_spec/API_SPEC_02.md](../../../docs/api_spec/API_SPEC_02.md)

## Coverage Map

| Capability | Test File | API Methods | PRD Requirements |
|------------|-----------|-------------|------------------|
| Add to existing provider | `test_instrument_existing_spec.py` | `instrument_existing_tracer()` | F1, F8 |
| Programmatic configuration | `test_programmatic_config_spec.py` | `instrument_existing_tracer()` | F2, F3, F4, N4 |
| OpenInference span filtering | `test_span_filter_spec.py` | `instrument_existing_tracer()` | F5, F6 |
| Duplicate instrumentation guard | `test_duplicate_guard_spec.py` | `instrument_existing_tracer()` | F7 |
| Error handling + safety | `test_instrument_existing_spec.py` | `instrument_existing_tracer()` | N1, N2, N3 |

## Requirements Coverage Summary

### Functional Requirements

| ID | Requirement | Test File | Status |
|----|-------------|-----------|--------|
| F1 | `instrument_existing_tracer()` adds Arize to existing provider | `test_instrument_existing_spec.py` | Pending |
| F2 | Accepts programmatic credentials | `test_programmatic_config_spec.py` | Pending |
| F3 | Accepts optional config file path | `test_programmatic_config_spec.py` | Pending |
| F4 | Programmatic credentials override config file | `test_programmatic_config_spec.py` | Pending |
| F5 | Only OpenInference spans sent by default | `test_span_filter_spec.py` | Pending |
| F6 | `filter_to_genai_spans=False` sends all spans | `test_span_filter_spec.py` | Pending |
| F7 | Duplicate calls log warning and skip | `test_duplicate_guard_spec.py` | Pending |
| F8 | Google ADK and GenAI auto-instrumented | `test_instrument_existing_spec.py` | Pending |

### Non-Functional Requirements

| ID | Requirement | Test File | Status |
|----|-------------|-----------|--------|
| N1 | Telemetry failures never raise | `test_instrument_existing_spec.py` | Pending |
| N2 | Non-SDK provider logs warning but continues | `test_instrument_existing_spec.py` | Pending |
| N3 | No atexit handler registered | `test_instrument_existing_spec.py` | Pending |
| N4 | Works without config file if credentials provided | `test_programmatic_config_spec.py` | Pending |

## Agent Instructions

Use these tests as the source of behavioral truth for PRD_02.
Do not modify tests unless the PRD or API spec is updated.

```
You are implementing functionality for PRD_02.
Use the tests under llm-observability-sdk/tests/prd_02/ as the source of behavioral truth.
Do not change tests unless the PRD or API spec is updated.
```

## Test Status

Tests are marked with `xfail` until implementation is complete:

- `XFAIL` — Test runs, failure expected (implementation pending)
- `XPASS` — Test unexpectedly passes (implementation landed)
- Remove `xfail` marker once implementation is verified
