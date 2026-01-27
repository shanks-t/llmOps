# Test Coverage Map

This document maps PRD requirements to test locations, providing traceability between specifications and executable contracts.

## How to Run Tests

```bash
# Run all tests (unit + integration, excludes E2E)
just test

# Run unit tests only (fast feedback)
just test-unit

# Run integration tests only
just test-integration

# Run with pytest directly
pytest -m unit -v         # All unit tests
pytest -m integration -v  # All integration tests
pytest tests/unit/ -v     # Unit tests by directory
pytest tests/integration/ -v  # Integration tests by directory
```

---

## PRD_01 — Core Instrumentation

**Source Documents:**
- PRD: [docs/prd/PRD_01.md](../docs/prd/PRD_01.md)
- API Spec: [docs/api_spec/API_SPEC_01.md](../docs/api_spec/API_SPEC_01.md)

### Functional Requirements

| ID | Requirement | Test Location | Status |
|----|-------------|---------------|--------|
| F1 | `llmops.<platform>.instrument(config_path)` exists | `integration/test_arize_instrument.py::TestArizeConfigResolution` | Passing |
| F2 | `instrument()` returns TracerProvider | `integration/test_arize_instrument.py::test_instrument_resolves_config_from_env_var` | Passing |
| F3 | Auto-instruments Google ADK | `integration/test_auto_instrumentation.py::TestGoogleADKInstrumentation` | Passing |
| F4 | Auto-instruments Google GenAI | `integration/test_auto_instrumentation.py::TestGoogleGenAIInstrumentation` | Passing |
| F5 | Platform modules are lazy-imported | `unit/test_lazy_loading.py::TestLazyLoading` | Passing |
| F6 | `instrument()` requires explicit config path | `integration/test_arize_instrument.py::test_instrument_fails_without_config_in_strict_mode` | Passing |
| F7 | Accepts `.yaml` and `.yml` extensions | `integration/test_arize_instrument.py::TestArizeFileExtensions` | Passing |
| F8 | Platforms define supported instrumentors | `integration/test_auto_instrumentation.py::TestInstrumentationExtensibility` | Passing |
| F9 | Config schema includes platform sections | `unit/test_platform_isolation.py::TestPlatformIsolation` | Passing |
| F10 | Sensitive values via env var overrides | `unit/test_config.py::TestEnvVarOverrides` | Passing |
| F11 | Missing deps raise helpful ImportError | `unit/test_lazy_loading.py::TestDependencyErrors` | Passing |
| F12 | Platforms share config loading/validation | `unit/test_platform_isolation.py::test_arize_ignores_mlflow_section` | Passing |
| F13 | Future platforms added without core changes | `unit/test_platform_isolation.py::TestPlatformIsolation` | Passing |
| F14 | `llmops.mlflow.instrument()` skeleton exists | `integration/test_mlflow_instrument.py::TestMLflowSkeletonBehavior` | Passing |

### Non-Functional Requirements

| ID | Requirement | Test Location | Status |
|----|-------------|---------------|--------|
| N1 | Telemetry failures don't raise | `unit/test_validation.py::TestArizeTelemetryIsolation` | Passing |
| N2 | Telemetry never breaks business logic | `unit/test_validation.py::test_telemetry_runtime_errors_are_swallowed` | Passing |
| N3 | Minimal startup time impact | — | Not tested |
| N4 | Single synchronous call | `integration/test_arize_instrument.py::TestArizeLifecycle` | Passing |
| N5 | Permissive mode uses no-op provider | `unit/test_validation.py::TestArizePermissiveMode` | Passing |
| N6 | Strict mode fails on config errors | `unit/test_validation.py::TestArizeStrictMode` | Passing |
| N7 | Missing deps error indicates platform | `unit/test_lazy_loading.py::TestDependencyErrors` | Passing |
| N8 | Import time for unused platforms is zero | `unit/test_lazy_loading.py::test_import_llmops_does_not_import_platform_deps` | Passing |
| N9 | Startup time impact remains minimal | — | Not tested |

### Config Parsing Tests

| Capability | Test Location | Status |
|------------|---------------|--------|
| Transport defaults to HTTP | `unit/test_config.py::test_transport_defaults_to_http` | Passing |
| Transport GRPC parsing | `unit/test_config.py::test_transport_grpc_parsed` | Passing |
| Batch defaults to True | `unit/test_config.py::test_batch_defaults_to_true` | Passing |
| log_to_console defaults to False | `unit/test_config.py::test_log_to_console_defaults_to_false` | Passing |
| verbose defaults to False | `unit/test_config.py::test_verbose_defaults_to_false` | Passing |
| TLS certificate from config | `unit/test_config.py::TestTLSCertificateConfig` | Passing |
| TLS certificate from env var | `unit/test_config.py::test_certificate_file_from_env_var` | Passing |
| Certificate validation | `unit/test_config.py::TestCertificateValidation` | Passing |
| TLS bridge to env vars | `unit/test_config.py::TestTLSBridgeToEnvVars` | Passing |
| project_name parsing | `unit/test_config.py::TestProjectNameHeader` | Passing |

### FakeArizeOtel Integration Tests

| Capability | Test Location | Status |
|------------|---------------|--------|
| Config passed to arize.otel.register | `integration/test_arize_telemetry.py::TestArizeOtelMode` | Passing |
| Config options passed correctly | `integration/test_arize_telemetry.py::test_arize_otel_receives_config_options` | Passing |
| TLS bridge called during creation | `integration/test_arize_telemetry.py::test_create_tracer_provider_calls_tls_bridge` | Passing |

---

## Test Directory Structure

```
tests/
├── unit/                              # Fast, isolated tests
│   ├── test_config.py                 # Config parsing, defaults, env vars
│   ├── test_lazy_loading.py           # Module import behavior
│   ├── test_platform_isolation.py     # Platform registry, cross-config
│   └── test_validation.py             # Strict/permissive mode
├── integration/                       # Real components, FakeArizeOtel
│   ├── test_arize_instrument.py       # Full instrument() flow
│   ├── test_arize_telemetry.py        # Config→arize.otel.register()
│   ├── test_auto_instrumentation.py   # Google ADK/GenAI instrumentors
│   └── test_mlflow_instrument.py      # MLflow skeleton
├── conftest.py                        # Shared fixtures
├── fakes.py                           # FakeArizeOtel test double
└── COVERAGE.md                        # This file
```

---

## Agent Instructions

When implementing functionality:

1. **Find relevant tests:** Search for `PRD:` in test docstrings using grep
2. **Run tests:** `just test` (all) or `just test-unit` / `just test-integration`
3. **Check coverage:** Reference this file for requirement → test mapping
4. **Mark tests passing:** Remove `xfail` markers as implementation lands

```
Run `just test` to execute all tests.
Tests are in tests/unit/ and tests/integration/.
```
