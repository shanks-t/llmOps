# Testing Philosophy

This document establishes our testing philosophy, derived from OpenTelemetry's engineering practices and lessons learned from over-reliance on mocks.

---

## Core Principle

> "With mocks, we sell test fidelity for ease of testing."

Every mock is a trade-off. We accept reduced confidence in exchange for test speed or isolation. This trade-off should be made consciously, not by default.

---

## The Testing Pyramid for Instrumentation Libraries

```
                    /\
                   /  \
                  / E2E \        Few: Real services, real network
                 /-------\
                /         \
               / Integration \   Some: Real libraries, mocked network
              /---------------\
             /                 \
            /       Unit        \  Many: Real logic, isolated I/O
           /---------------------\
```

**Unit tests** should be the foundation, but for an instrumentation SDK, **integration tests against real libraries are more valuable than mocked unit tests**.

---

## Hierarchy of Test Doubles

Prefer test doubles in this order:

### 1. Real Components (Best)

Use the actual component when feasible. For observability SDKs, this means:
- Real config parsing with real YAML files
- Real `TracerProvider` instances
- Real span creation and attribute setting

### 2. Fakes

A fake is a working implementation with shortcuts. OpenTelemetry's `InMemorySpanExporter` is the canonical example:
- It implements the full `SpanExporter` interface
- It stores spans in memory instead of sending over network
- It behaves like production code, just with a different storage backend

**Use fakes when:** The real component requires infrastructure (network, database) that's impractical in tests.

### 3. Stubs

A stub returns predetermined responses. Use when you need to simulate specific scenarios:
- Error conditions
- Edge cases
- Specific return values

**Use stubs when:** You need to force a specific code path that's hard to trigger naturally.

### 4. Spies

A spy wraps a real component and records interactions. Useful for verifying side effects without replacing behavior:
- Verify a cleanup handler was registered
- Confirm a method was called without changing what it does

**Use spies when:** You need to verify something happened while preserving real behavior.

### 5. Mocks (Use Sparingly)

A mock is a programmable test double that verifies interactions. Mocks are the most flexible but most dangerous:
- They verify *how* code works, not *what* it does
- They couple tests to implementation details
- They can pass while production fails

**Use mocks only when:**
- The real component is truly unavailable
- You're testing interaction with an external API you don't control
- No fake or stub can serve the purpose

---

## What to Test

### Test Behavior, Not Implementation

**Avoid:**
```python
mock_register.assert_called_once()
assert call_kwargs["transport"] == "HTTP"
```

**Prefer:**
```python
provider = create_tracer_provider(config)
tracer = provider.get_tracer("test")
with tracer.start_as_current_span("test") as span:
    span.set_attribute("key", "value")

spans = get_finished_spans()
assert spans[0].attributes["key"] == "value"
```

The first test verifies *how* we create a provider. The second verifies *that* we create a working provider.

### Test Contracts, Not Calls

When you must verify interaction with an external library:
- Test that your output conforms to expected contracts
- Don't test that you called specific internal functions

### Test Error Paths with Real Errors

Don't mock exceptions unless necessary:
```python
# Avoid
mock_lib.connect.side_effect = ConnectionError("mocked")

# Prefer: trigger real error conditions when possible
config = create_config(endpoint="https://invalid.endpoint.local")
with pytest.raises(ConnectionError):
    connect(config)
```

---

## When Mocks Are Acceptable

### External Network Calls

Mocking network I/O is almost always correct:
- Use `InMemorySpanExporter` instead of OTLP exporters
- Use `responses` or `httpx.MockTransport` for HTTP clients
- Use test containers for databases when integration testing

### Third-Party APIs You Don't Control

If an external library:
- Has no test mode or fake implementation
- Cannot be installed in CI
- Requires credentials or infrastructure

Then mocking is acceptable, but:
- Create a typed fake with explicit interface
- Don't use `MagicMock` with implicit any-attribute behavior
- Add integration tests that run against the real library periodically

### Non-Deterministic Behavior

Mock time, randomness, and UUIDs when you need deterministic tests:
```python
@pytest.fixture
def fixed_time(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 1234567890.0)
```

---

## When Mocks Are Not Acceptable

### Your Own Code

Never mock your own modules to test them:
```python
# Wrong: testing create_tracer_provider by mocking internal functions
with patch("llmops._internal.telemetry.some_helper"):
    create_tracer_provider(config)
```

If you need to mock your own code, it's a sign the code needs refactoring.

### Configuration and Parsing

Use real config files, real parsers, real validation:
```python
# Use tmp_path to create real files
config_path = tmp_path / "config.yaml"
config_path.write_text(config_content)
config = load_config(config_path)
```

### The Component Under Test

Never mock the thing you're testing. This seems obvious but happens when mocking gets out of control.

---

## Structural Guidelines

### Separate Test Types Clearly

```
tests/
├── unit/           # Fast, no external deps, run always
├── integration/    # Real libraries, no network, run always
└── e2e/            # Real services, run in CI/manually
```

### Name Tests by Behavior

```python
# Avoid: named by implementation
def test_calls_register_with_transport():

# Prefer: named by behavior
def test_http_transport_creates_working_provider():
```

### One Assertion Per Concept

Multiple `assert` statements are fine if they verify one logical concept:
```python
def test_span_has_correct_attributes():
    span = get_span()
    # These all verify "correct attributes"
    assert span.name == "expected"
    assert span.attributes["key"] == "value"
    assert span.status.is_ok
```

---

## The Mock Smell Test

Before adding a mock, ask:

1. **Can I use the real component?** Often yes, with minor setup.
2. **Does a fake exist?** OpenTelemetry provides test utilities.
3. **Am I testing behavior or implementation?** Refactor if implementation.
4. **Will this test catch real bugs?** If the mock can drift from reality, no.
5. **Will this test break on valid refactors?** If yes, it's too coupled.

If you proceed with a mock:
- Use `spec=RealClass` to constrain behavior
- Create explicit fakes over `MagicMock`
- Document why a mock was necessary
- Add a TODO to replace with integration test

---

## OpenTelemetry's Example

OpenTelemetry's instrumentation tests demonstrate these principles:

1. **Real applications:** FastAPI tests use real FastAPI apps with `TestClient`
2. **Real spans:** Tests verify actual span output, not mock calls
3. **Real metrics:** In-memory readers capture real metric data
4. **Minimal mocking:** Mocks appear only at true boundaries (network)

Their tests answer: "Does this instrumentation produce correct telemetry?"

Not: "Did we call the right functions?"

---

## Summary

| Principle | Guidance |
|-----------|----------|
| Default stance | No mocks; prove you need one |
| Hierarchy | Real > Fake > Stub > Spy > Mock |
| Test target | Behavior and outcomes |
| Mock scope | External boundaries only |
| Validation | Can this test catch real bugs? |
| Maintenance | Will this test survive refactoring? |

Tests should give us confidence that production works. Every mock reduces that confidence. Choose wisely.
