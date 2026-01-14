"""Integration test fixtures for llmops SDK.

These fixtures enable testing auto-instrumentation without external services
by using InMemorySpanExporter to capture and verify spans.
"""

import pytest
from typing import Generator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


# =============================================================================
# CORE FIXTURES
# =============================================================================


@pytest.fixture
def in_memory_exporter() -> InMemorySpanExporter:
    """Create a fresh InMemorySpanExporter for capturing spans.

    GIVEN an integration test
    WHEN spans are created
    THEN they can be captured and inspected without external services.
    """
    exporter = InMemorySpanExporter()
    yield exporter
    exporter.clear()


@pytest.fixture
def test_tracer_provider(
    in_memory_exporter: InMemorySpanExporter,
) -> Generator[TracerProvider, None, None]:
    """Create a TracerProvider with InMemorySpanExporter.

    GIVEN an integration test needing to capture spans
    WHEN this fixture is used
    THEN spans are captured in memory for verification.

    NOTE: This fixture sets the global TracerProvider. Due to OpenTelemetry
    limitations, the global provider can only be set once per process.
    Tests using this fixture should be run in isolation or accept that
    subsequent sets will be ignored with a warning.
    """
    resource = Resource.create({SERVICE_NAME: "test-service"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))

    # Set as global provider (may warn if already set)
    trace.set_tracer_provider(provider)

    yield provider

    # Cleanup - force flush any pending spans
    provider.force_flush()


@pytest.fixture
def isolated_tracer_provider(
    in_memory_exporter: InMemorySpanExporter,
) -> Generator[tuple[TracerProvider, "trace.Tracer"], None, None]:
    """Create an isolated TracerProvider that doesn't touch global state.

    Use this fixture when you need to capture spans without affecting
    the global TracerProvider. Returns both the provider and a tracer.

    Usage:
        def test_example(isolated_tracer_provider, in_memory_exporter):
            provider, tracer = isolated_tracer_provider
            with tracer.start_as_current_span("test"):
                pass
            spans = in_memory_exporter.get_finished_spans()
    """
    resource = Resource.create({SERVICE_NAME: "isolated-test-service"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))

    tracer = provider.get_tracer("isolated-test-tracer")

    yield provider, tracer

    provider.force_flush()


@pytest.fixture(autouse=True)
def reset_llmops_state():
    """Reset llmops global state before and after each test.

    Mirrors the pattern from test_configure.py.
    """
    import llmops

    if llmops.is_configured():
        llmops.shutdown()

    yield

    if llmops.is_configured():
        llmops.shutdown()


# =============================================================================
# INSTRUMENTOR FIXTURES
# =============================================================================


@pytest.fixture
def configured_adk_instrumentor(test_tracer_provider: TracerProvider):
    """Configure GoogleADKInstrumentor with test TracerProvider.

    GIVEN GoogleADKInstrumentor is available
    WHEN instrumenting for tests
    THEN spans are captured to InMemorySpanExporter.
    """
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        instrumentor = GoogleADKInstrumentor()
        instrumentor.instrument(tracer_provider=test_tracer_provider)
        yield instrumentor
        instrumentor.uninstrument()
    except ImportError:
        pytest.skip("openinference-instrumentation-google-adk not installed")


@pytest.fixture
def configured_genai_instrumentor(test_tracer_provider: TracerProvider):
    """Configure GoogleGenAIInstrumentor with test TracerProvider.

    GIVEN GoogleGenAIInstrumentor is available
    WHEN instrumenting for tests
    THEN spans are captured to InMemorySpanExporter.
    """
    try:
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        instrumentor = GoogleGenAIInstrumentor()
        instrumentor.instrument(tracer_provider=test_tracer_provider)
        yield instrumentor
        instrumentor.uninstrument()
    except ImportError:
        pytest.skip("openinference-instrumentation-google-genai not installed")


# =============================================================================
# SPAN ASSERTION HELPERS
# =============================================================================


class SpanAssertions:
    """Helper class for asserting span attributes."""

    @staticmethod
    def assert_has_span_with_name(spans, name: str):
        """Assert at least one span has the given name."""
        names = [s.name for s in spans]
        assert name in names, f"Expected span '{name}' not found. Found: {names}"

    @staticmethod
    def assert_span_attribute(span, key: str, expected_value):
        """Assert a span has an attribute with expected value."""
        attrs = dict(span.attributes) if span.attributes else {}
        assert key in attrs, f"Attribute '{key}' not found. Found: {list(attrs.keys())}"
        assert (
            attrs[key] == expected_value
        ), f"Expected {key}={expected_value}, got {attrs[key]}"

    @staticmethod
    def assert_span_has_attribute(span, key: str):
        """Assert a span has an attribute (any value)."""
        attrs = dict(span.attributes) if span.attributes else {}
        assert key in attrs, f"Attribute '{key}' not found. Found: {list(attrs.keys())}"

    @staticmethod
    def assert_span_has_parent(span, parent_span):
        """Assert a span has the expected parent."""
        assert span.parent is not None, "Span has no parent"
        assert span.parent.span_id == parent_span.context.span_id

    @staticmethod
    def get_spans_by_name(spans, name: str):
        """Filter spans by name."""
        return [s for s in spans if s.name == name]

    @staticmethod
    def assert_span_status_ok(span):
        """Assert span status is OK (not error)."""
        from opentelemetry.trace import StatusCode

        assert (
            span.status.status_code == StatusCode.OK
            or span.status.status_code == StatusCode.UNSET
        ), f"Expected OK/UNSET status, got {span.status}"


@pytest.fixture
def span_assertions():
    """Provide helper functions for asserting span attributes.

    Usage:
        def test_example(span_assertions, in_memory_exporter):
            # ... trigger instrumented code ...
            spans = in_memory_exporter.get_finished_spans()
            span_assertions.assert_has_span_with_name(spans, "LLM")
            span_assertions.assert_span_attribute(spans[0], "llm.model_name", "gemini")
    """
    return SpanAssertions()


# =============================================================================
# YAML CONFIG FIXTURES
# =============================================================================


@pytest.fixture
def phoenix_config_yaml(tmp_path):
    """Create a temporary Phoenix configuration file.

    GIVEN tests needing llmops.init() with Phoenix
    WHEN this fixture is used
    THEN a valid YAML config is available.
    """
    config_file = tmp_path / "llmops.yaml"
    config_file.write_text(
        """
service:
  name: integration-test-service

backend: phoenix

phoenix:
  endpoint: http://localhost:6006/v1/traces
"""
    )
    return str(config_file)


@pytest.fixture
def mlflow_config_yaml(tmp_path):
    """Create a temporary MLflow configuration file.

    GIVEN tests needing llmops.init() with MLflow
    WHEN this fixture is used
    THEN a valid YAML config is available.
    """
    config_file = tmp_path / "llmops.yaml"
    config_file.write_text(
        """
service:
  name: integration-test-service

backend: mlflow

mlflow:
  tracking_uri: http://localhost:5001
"""
    )
    return str(config_file)
