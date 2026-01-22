"""Shared pytest configuration and fixtures for contract tests.

This module provides test fixtures that:
1. Reset OpenTelemetry global state between tests for isolation
2. Use InMemorySpanExporter to avoid network calls during unit tests
3. Mock the SDK's telemetry creation to use test-friendly components

Following OpenTelemetry Python SDK testing patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator

import pytest
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource

if TYPE_CHECKING:
    from pathlib import Path
    from llmops.config import LLMOpsConfig


def _reset_trace_globals() -> None:
    """Reset OpenTelemetry trace globals for test isolation.

    This ensures each test starts with a clean slate and avoids
    "tracer provider already set" errors.

    WARNING: Only use this in tests. This accesses internal OTel APIs.
    """
    from opentelemetry.util._once import Once

    # Shutdown any existing provider to stop background threads
    # and prevent network calls during flush
    current_provider = trace_api.get_tracer_provider()
    shutdown_fn = getattr(current_provider, "shutdown", None)
    if callable(shutdown_fn):
        try:
            shutdown_fn()
        except Exception:  # nosec B110 - intentional: cleanup errors should not fail tests
            pass

    trace_api._TRACER_PROVIDER_SET_ONCE = Once()
    trace_api._TRACER_PROVIDER = None
    trace_api._PROXY_TRACER_PROVIDER = trace_api.ProxyTracerProvider()


@pytest.fixture
def in_memory_exporter() -> InMemorySpanExporter:
    """Provide an InMemorySpanExporter for capturing spans in tests.

    Use this fixture when you need to assert on captured spans.
    The exporter stores all spans in memory with no network calls.
    """
    return InMemorySpanExporter()


@pytest.fixture
def test_tracer_provider(in_memory_exporter: InMemorySpanExporter) -> TracerProvider:
    """Create a test TracerProvider with in-memory exporter.

    Uses SimpleSpanProcessor for synchronous, deterministic behavior
    (unlike BatchSpanProcessor which has background threads).
    """
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))
    return provider


def _create_test_tracer_provider(
    config: "LLMOpsConfig",
    in_memory_exporter: InMemorySpanExporter,
) -> TracerProvider:
    """Create a TracerProvider for tests that mimics production behavior.

    This function mirrors the production create_tracer_provider() but:
    - Uses InMemorySpanExporter instead of OTLPSpanExporter
    - Uses SimpleSpanProcessor instead of BatchSpanProcessor
    - Still sets resource attributes from config (for assertion tests)
    - Still sets the global tracer provider

    Args:
        config: The SDK configuration (used for resource attributes).
        in_memory_exporter: The in-memory exporter to capture spans.

    Returns:
        Configured TracerProvider set as the global provider.
    """
    # Build resource attributes (same as production)
    resource_attrs: dict[str, str] = {
        SERVICE_NAME: config.service.name,
    }
    if config.service.version:
        resource_attrs[SERVICE_VERSION] = config.service.version

    resource = Resource.create(resource_attrs)
    provider = TracerProvider(resource=resource)

    # Use in-memory exporter with synchronous processor
    provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))

    # Set as global tracer provider (same as production)
    trace_api.set_tracer_provider(provider)

    return provider


@pytest.fixture(autouse=True)
def reset_otel_state() -> Generator[None, None, None]:
    """Reset OpenTelemetry global state before and after each test.

    This fixture runs automatically for all tests to ensure:
    - Tests don't interfere with each other's global state
    - No "tracer provider already set" errors
    - Clean shutdown of any providers created during tests
    """
    _reset_trace_globals()
    yield
    _reset_trace_globals()


@pytest.fixture(autouse=True)
def mock_sdk_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    in_memory_exporter: InMemorySpanExporter,
) -> Generator[InMemorySpanExporter, None, None]:
    """Replace SDK's tracer provider creation with test-friendly version.

    This fixture:
    - Intercepts calls to create_tracer_provider()
    - Returns a provider with InMemorySpanExporter (no network calls)
    - Preserves config-based resource attributes for assertion tests

    The fixture yields the in_memory_exporter so tests can optionally
    inspect captured spans if needed.
    """
    import sys

    def mock_create_tracer_provider(config: "LLMOpsConfig") -> TracerProvider:
        return _create_test_tracer_provider(config, in_memory_exporter)

    # Access the actual instrument module via sys.modules (not the function)
    # This is necessary because llmops.__init__ exports 'instrument' as a function,
    # which shadows the llmops.instrument module in import resolution
    import llmops  # noqa: F401 - ensures module is loaded

    instrument_module = sys.modules["llmops.instrument"]
    monkeypatch.setattr(
        instrument_module,
        "create_tracer_provider",
        mock_create_tracer_provider,
    )

    yield in_memory_exporter

    # Clear any captured spans after test
    in_memory_exporter.clear()


@pytest.fixture
def valid_config_content() -> str:
    """Return valid YAML config content for tests."""
    return """service:
  name: test-service
  version: "1.0.0"

arize:
  endpoint: http://localhost:6006/v1/traces

instrumentation:
  google_adk: true
  google_genai: true

validation:
  mode: permissive
"""


@pytest.fixture
def valid_config_file(tmp_path: "Path", valid_config_content: str) -> "Path":
    """Create a valid config file and return its path."""
    config_path = tmp_path / "llmops.yaml"
    config_path.write_text(valid_config_content)
    return config_path


@pytest.fixture
def llmops_module() -> Any:
    """Import and return the llmops module."""
    import llmops

    return llmops
