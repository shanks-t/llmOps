# Test Suite Refactoring Plan

This document outlines findings from a review of our test suite's use of mocks, evaluated against industry best practices and OpenTelemetry's testing patterns. The goal is to reduce brittleness, eliminate false confidence, and improve test reliability.

## Progress Tracker

| Task | Status | Commit | Notes |
|------|--------|--------|-------|
| P1.2: Add `arize-otel` test dependency | ✅ Done | (already in deps) | Was already a runtime dependency |
| P3.2: Create `FakeArizeOtel` | ✅ Done | `8926621` | See `tests/fakes.py` |
| P2.1: Extract mock fixtures to conftest.py | ✅ Done | `8926621` | `fake_arize_otel`, `patched_arize_otel` fixtures |
| P2.3: Remove `importlib.reload()` anti-pattern | ✅ Done | `8926621` | No longer used in tests |
| P1.1: Integration tests with real arize.otel | 🔲 TODO | — | Highest remaining priority |
| P2.2: Test behavior, not mock calls | 🔲 TODO | — | Continue as files are touched |
| P3.1: Separate unit/integration directories | 🔲 TODO | — | When enough integration tests exist |
| P4.1: Property-based config tests | 🔲 TODO | — | Nice to have |
| P4.2: pytest-opentelemetry | 🔲 TODO | — | Nice to have |

### What Was Done (2024-01)

1. **Created `tests/fakes.py`** with `FakeArizeOtel` class:
   - Typed test double matching `arize.otel.register()` signature
   - Catches typos at test time (unlike MagicMock)
   - Returns real `TracerProvider` instances
   - Provides assertion helpers: `assert_registered_once()`, `assert_registered_with()`

2. **Updated `tests/conftest.py`**:
   - Added `fake_arize_otel` fixture for dependency injection
   - Added `patched_arize_otel` fixture for `sys.modules` patching
   - Added `disable_mock_sdk_telemetry` marker support

3. **Refactored `test_arize_telemetry_spec.py`**:
   - Replaced 3 tests using `MagicMock` + `sys.modules` with `FakeArizeOtel`
   - Removed `from unittest.mock import MagicMock, patch` imports
   - Tests now verify config translation explicitly using typed assertions

4. **Updated `pyproject.toml`**:
   - Registered `disable_mock_sdk_telemetry` pytest marker

### Remaining Work

**High Priority:**
- Add integration tests that use real `arize.otel` library (P1.1)
- Continue refactoring tests to test behavior instead of implementation (P2.2)

**Medium Priority:**
- Separate unit vs integration tests into directories (P3.1)

**Low Priority:**
- Property-based tests for config parsing with `hypothesis` (P4.1)
- `pytest-opentelemetry` for test observability (P4.2)

---

## Background

Our test suite was reviewed in the context of concerns raised about over-reliance on mocks:

> "With mocks, we sell test fidelity for ease of testing."

Key concerns identified:
1. **Tests can be harder to understand** — extra mock code obscures what's being tested
2. **Tests can be harder to maintain** — mocks leak implementation details into tests
3. **Tests provide less assurance** — mocks may not behave like real implementations

## Current State Analysis

### What's Being Mocked

| Layer | What's Mocked | Mock Type | Concern Level |
|-------|---------------|-----------|---------------|
| External API | `arize.otel.register()` | `MagicMock` + `sys.modules` patch | Medium |
| OTel Globals | Internal state (`_TRACER_PROVIDER`, etc.) | Direct attribute manipulation | Low (necessary) |
| Network I/O | OTLP exporters | `InMemorySpanExporter` | Low (appropriate) |
| Python builtins | `__import__` | `monkeypatch` | Medium |
| Stdlib | `atexit.register` | Spy pattern | Low |
| Environment | `os.environ` | `monkeypatch.setenv` | Low |

### What's Done Well

1. **`InMemorySpanExporter`** — This is a "fake" not a "mock", and follows the standard OpenTelemetry testing approach
2. **Environment variable testing** — Using `monkeypatch` is appropriate for env var isolation
3. **Config file testing with `tmp_path`** — Real YAML files exercise real config parsing
4. **Autouse fixtures for state isolation** — Necessary given OpenTelemetry's global state model

### Problem Areas

#### 1. The `arize.otel` Mocking Pattern ✅ ADDRESSED

> **Status:** Replaced with `FakeArizeOtel` in commit `8926621`. See `tests/fakes.py`.

~~Location: `test_arize_telemetry_spec.py` (lines 53-77, 275-297, 652-672)~~

```python
# OLD APPROACH (removed)
mock_arize_otel = MagicMock()
mock_arize_otel.register = MagicMock(return_value=mock_provider)
with patch.dict("sys.modules", {"arize.otel": mock_arize_otel}):
    importlib.reload(telemetry_module)

# NEW APPROACH (tests/fakes.py + conftest.py)
@pytest.mark.disable_mock_sdk_telemetry
def test_config_translation(patched_arize_otel, tmp_path):
    provider = telemetry_module.create_tracer_provider(config)
    patched_arize_otel.assert_registered_with(space_id="test-space")
```

**Improvements made:**
- ✅ `FakeArizeOtel` has typed method signatures (catches typos)
- ✅ Returns real `TracerProvider` instances
- ✅ No more `importlib.reload()` (arize.otel is imported at call time)
- 🔲 Still need integration tests against real `arize.otel` for full confidence

#### 2. Testing Implementation, Not Behavior

```python
# Current approach - tests implementation details
mock_register.assert_called_once()
call_kwargs = mock_register.call_args[1]
assert call_kwargs["transport"] == "HTTP"
```

This couples tests to internal implementation rather than observable outcomes.

#### 3. Repeated Mock Boilerplate ✅ ADDRESSED

> **Status:** Centralized in `conftest.py` fixtures (`fake_arize_otel`, `patched_arize_otel`).

~~The arize.otel mock setup is repeated 4 times with subtle variations.~~

Now tests use shared fixtures:
```python
def test_something(patched_arize_otel, tmp_path):
    # patched_arize_otel is a FakeArizeOtel instance
    # already patched into sys.modules
    ...
```

---

## Refactoring Priorities

### Priority 1: Critical — High Impact on Test Reliability

#### 1.1 Replace `sys.modules` + `MagicMock` with Contract Tests

**Current approach:**
```python
mock_arize_otel = MagicMock()
mock_arize_otel.register = MagicMock(return_value=mock_provider)
with patch.dict("sys.modules", {"arize.otel": mock_arize_otel}):
    importlib.reload(telemetry_module)
```

**Recommended approach:**
```python
@pytest.mark.integration
class TestArizeOtelIntegration:
    """Integration tests using real arize.otel library."""

    def test_register_creates_valid_provider(self, tmp_path):
        """Verify our config translates correctly to arize.otel."""
        config = create_test_config(tmp_path)

        # Call real arize.otel.register() but with test exporter
        provider = create_tracer_provider(config)

        # Verify it's a real, working TracerProvider
        tracer = provider.get_tracer("test")
        with tracer.start_as_current_span("test-span"):
            pass

        spans = get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test-span"
```

**Effort:** Medium-High
**Impact:** Eliminates the biggest source of false confidence

#### 1.2 Add `arize-otel` as a Test Dependency

```toml
# pyproject.toml
[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-mock>=3.14.0",
    "arize-otel>=0.1.0",  # ADD THIS
]
```

**Effort:** Low
**Impact:** Enables all Priority 1 refactors

---

### Priority 2: High — Reduces Brittleness

#### 2.1 Extract Mock Boilerplate into Fixtures

**Add to conftest.py:**
```python
@pytest.fixture
def mock_arize_otel():
    """Provide a standardized arize.otel mock.

    WARNING: Temporary fixture. Prefer integration tests
    against real arize.otel when possible.
    """
    mock = MagicMock()
    mock.register = MagicMock(return_value=MagicMock(spec=TracerProvider))
    mock.Transport = MagicMock()
    mock.Transport.HTTP = "HTTP"
    mock.Transport.GRPC = "GRPC"
    return mock

@pytest.fixture
def patched_arize_otel(mock_arize_otel):
    """Context manager that patches arize.otel in sys.modules."""
    with patch.dict("sys.modules", {"arize.otel": mock_arize_otel}):
        import importlib
        import llmops._internal.telemetry as telemetry_module
        importlib.reload(telemetry_module)
        yield mock_arize_otel
```

**Effort:** Low
**Impact:** Single source of truth for mock behavior

#### 2.2 Test Behavior, Not Implementation Calls

**Before:**
```python
mock_register.assert_called_once()
call_kwargs = mock_register.call_args[1]
assert call_kwargs["transport"] == "HTTP"
```

**After:**
```python
def test_http_transport_produces_working_provider(self, tmp_path):
    """Verify HTTP transport config results in functional tracing."""
    config = create_config(transport="http")
    provider = create_tracer_provider(config)

    # Test that tracing WORKS, not that a function was called
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("test") as span:
        span.set_attribute("test.key", "value")

    spans = get_finished_spans()
    assert spans[0].attributes["test.key"] == "value"
```

**Effort:** Medium
**Impact:** Tests survive refactoring

#### 2.3 Remove `importlib.reload()` Anti-Pattern

**Restructure production code to accept dependencies:**

```python
# Before (requires reload)
def create_tracer_provider(config):
    from arize.otel import register  # Hard import
    return register(...)

# After (injectable)
def create_tracer_provider(config, register_fn=None):
    if register_fn is None:
        from arize.otel import register
        register_fn = register
    return register_fn(...)
```

**Effort:** Medium (requires production code change)
**Impact:** Eliminates flaky reload behavior

---

### Priority 3: Medium — Improves Test Clarity

#### 3.1 Separate Unit Tests from Integration Tests

**Recommended structure:**
```
tests/
├── unit/                          # Fast, isolated tests
│   ├── test_config_parsing.py
│   ├── test_validation.py
│   └── test_lazy_loading.py
├── integration/                   # Tests against real dependencies
│   ├── test_arize_otel.py
│   └── test_otel_provider.py
└── conftest.py
```

**pytest markers:**
```ini
[pytest]
markers =
    unit: Fast isolated tests (no external deps)
    integration: Tests against real libraries
    e2e: End-to-end tests (require running services)
```

**Effort:** Low
**Impact:** Clear expectations about what each test validates

#### 3.2 Create a `FakeArizeOtel` Instead of `MagicMock`

**Problem with MagicMock:**
```python
mock.register()  # Returns MagicMock
mock.regster()   # Typo? Still returns MagicMock! No error.
```

**Solution:**
```python
# tests/fakes.py
class FakeArizeOtel:
    """Test double for arize.otel that validates usage."""

    class Transport:
        HTTP = "HTTP"
        GRPC = "GRPC"

    def __init__(self):
        self.register_calls: list[dict] = []
        self._provider = None

    def register(
        self,
        space_id: str,
        api_key: str,
        project_name: str | None = None,
        endpoint: str | None = None,
        transport: str = "HTTP",
        batch: bool = True,
        log_to_console: bool = False,
    ) -> TracerProvider:
        """Fake register that records calls and returns a real provider."""
        self.register_calls.append({
            "space_id": space_id,
            "api_key": api_key,
            "project_name": project_name,
            "transport": transport,
            "batch": batch,
        })

        if self._provider is None:
            self._provider = TracerProvider()
        return self._provider

    def assert_registered_with(self, **expected):
        """Assert register was called with expected args."""
        assert len(self.register_calls) == 1
        actual = self.register_calls[0]
        for key, value in expected.items():
            assert actual[key] == value, f"{key}: expected {value}, got {actual[key]}"
```

**Usage:**
```python
def test_config_translates_to_arize_params(self, config):
    fake = FakeArizeOtel()
    provider = create_tracer_provider(config, register_fn=fake.register)

    fake.assert_registered_with(
        space_id="test-space",
        transport="HTTP",
    )

    # AND verify the provider actually works
    assert isinstance(provider, TracerProvider)
```

**Effort:** Medium
**Impact:** Catches typos, documents expected API surface

---

### Priority 4: Low — Nice to Have

#### 4.1 Add Property-Based Tests for Config Parsing

```python
from hypothesis import given, strategies as st

@given(
    transport=st.sampled_from(["http", "grpc", "HTTP", "GRPC", "invalid"]),
    batch_spans=st.booleans(),
    debug=st.booleans(),
)
def test_config_options_never_crash(self, transport, batch_spans, debug, tmp_path):
    """Any combination of config options should parse without exception."""
    config_content = f"""
service:
  name: test
arize:
  endpoint: https://example.com
  transport: {transport}
  batch_spans: {batch_spans}
  debug: {debug}
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)

    config = load_config(config_path)
    assert config.arize.transport in ("http", "grpc")
```

**Effort:** Low
**Impact:** Catches edge cases automatically

#### 4.2 Consider `pytest-opentelemetry` for Test Observability

Instrument the test suite itself to identify slow tests and trace execution.

**Effort:** Low
**Impact:** Meta-testing insight

---

## Implementation Order

| Step | Task | Effort | Unlocks | Status |
|------|------|--------|---------|--------|
| 1 | Add `arize-otel` as test dependency | Low | Steps 2-4 | ✅ Done |
| 2 | Create `FakeArizeOtel` | Medium | Better mock immediately | ✅ Done |
| 3 | Extract mock fixtures to conftest.py | Low | Reduces duplication | ✅ Done |
| 4 | Add integration test file | Medium | Real confidence | 🔲 Next |
| 5 | Refactor tests to test behavior | Medium | As you touch each file | 🔲 TODO |
| 6 | Separate test directories | Low | When enough integration tests exist | 🔲 TODO |

---

## Summary Matrix

| Priority | Refactor | Effort | Impact | Addresses | Status |
|----------|----------|--------|--------|-----------|--------|
| P1.1 | Replace `sys.modules` mock with real `arize.otel` | Medium-High | Very High | False confidence | 🔲 TODO |
| P1.2 | Add `arize-otel` test dependency | Low | High | Enables P1.1 | ✅ Done |
| P2.1 | Extract mock boilerplate to fixtures | Low | Medium | Brittleness | ✅ Done |
| P2.2 | Test behavior, not mock calls | Medium | High | False confidence | 🔲 TODO |
| P2.3 | Remove `importlib.reload()` pattern | Medium | Medium | Brittleness | ✅ Done |
| P3.1 | Explicit unit/integration separation | Low | Medium | Clarity | 🔲 TODO |
| P3.2 | `FakeArizeOtel` instead of `MagicMock` | Medium | Medium | False confidence | ✅ Done |
| P4.1 | Property-based config tests | Low | Low | Edge cases | 🔲 TODO |
| P4.2 | `pytest-opentelemetry` | Low | Low | Observability | 🔲 TODO |

---

## References

- [OpenTelemetry Python InMemorySpanExporter tests](https://github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/tests/trace/export/test_in_memory_span_exporter.py)
- [OpenTelemetry FastAPI instrumentation tests](https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/instrumentation/opentelemetry-instrumentation-fastapi/tests/test_fastapi_instrumentation.py)
- [opentelemetry-test-utils](https://pypi.org/project/opentelemetry-test-utils/)
- [Issue: Document how to work with OpenTelemetry when writing unit tests](https://github.com/open-telemetry/opentelemetry-python/issues/3480)
- [OpenTelemetry Python Contrib instrumentation README](https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/instrumentation/README.md)
