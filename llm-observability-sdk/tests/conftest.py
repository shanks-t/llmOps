"""Shared pytest configuration and fixtures for contract tests.

This module provides test fixtures that:
1. Reset OpenTelemetry global state between tests for isolation
2. Use InMemorySpanExporter to avoid network calls during unit tests
3. Mock the SDK's telemetry creation to use test-friendly components
4. Provide typed fakes (FakeArizeOtel) instead of MagicMock

Following OpenTelemetry Python SDK testing patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator

import sys
from types import ModuleType

import pytest
from opentelemetry import trace as trace_api
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from tests.fakes import FakeArizeOtel

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

    current_provider = trace_api.get_tracer_provider()
    shutdown_fn = getattr(current_provider, "shutdown", None)
    if callable(shutdown_fn):
        try:
            shutdown_fn()
        except Exception:  # nosec B110 - cleanup errors should not fail tests
            pass

    trace_api._TRACER_PROVIDER_SET_ONCE = Once()
    trace_api._TRACER_PROVIDER = None
    trace_api._PROXY_TRACER_PROVIDER = trace_api.ProxyTracerProvider()


@pytest.fixture
def in_memory_exporter() -> InMemorySpanExporter:
    """Provide an InMemorySpanExporter for capturing spans in tests."""
    return InMemorySpanExporter()


@pytest.fixture
def test_tracer_provider(in_memory_exporter: InMemorySpanExporter) -> TracerProvider:
    """Create a test TracerProvider with in-memory exporter."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))
    return provider


def _create_test_tracer_provider(
    config: "LLMOpsConfig",
    in_memory_exporter: InMemorySpanExporter,
) -> TracerProvider:
    """Create a TracerProvider for tests that mimics production behavior."""
    resource_attrs: dict[str, str] = {
        SERVICE_NAME: config.service.name,
    }
    if config.service.version:
        resource_attrs[SERVICE_VERSION] = config.service.version

    resource = Resource.create(resource_attrs)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))
    trace_api.set_tracer_provider(provider)
    return provider


@pytest.fixture(autouse=True)
def reset_otel_state() -> Generator[None, None, None]:
    """Reset OpenTelemetry global state before and after each test."""
    _reset_trace_globals()
    yield
    _reset_trace_globals()


@pytest.fixture(autouse=True)
def mock_sdk_telemetry(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    in_memory_exporter: InMemorySpanExporter,
) -> Generator[InMemorySpanExporter, None, None]:
    """Replace SDK's tracer provider creation with test-friendly version.

    This fixture is automatically applied to all tests. To disable it for
    tests that need to verify real arize.otel interactions, use the
    'disable_mock_sdk_telemetry' marker:

        @pytest.mark.disable_mock_sdk_telemetry
        def test_something(patched_arize_otel):
            ...
    """
    # Check if test has the disable marker
    if request.node.get_closest_marker("disable_mock_sdk_telemetry"):
        yield in_memory_exporter
        return

    import sys

    def mock_create_tracer_provider(config: "LLMOpsConfig") -> TracerProvider:
        return _create_test_tracer_provider(config, in_memory_exporter)

    import llmops  # noqa: F401 - ensures module is loaded
    import llmops._internal.telemetry as telemetry_module
    from llmops.config import ArizeConfig, LLMOpsConfig, MLflowConfig, ServiceConfig

    module_names = [
        "llmops._internal.telemetry",
        "llmops._platforms.arize",
    ]
    for module_name in module_names:
        module = sys.modules.get(module_name)
        if module is None:
            continue
        if hasattr(module, "create_tracer_provider"):
            monkeypatch.setattr(
                module, "create_tracer_provider", mock_create_tracer_provider
            )

    noop_config = LLMOpsConfig(
        service=ServiceConfig(name="llmops-noop"),
        arize=ArizeConfig(endpoint=""),
        mlflow=MLflowConfig(tracking_uri=""),
    )
    monkeypatch.setattr(
        telemetry_module,
        "create_noop_tracer_provider",
        lambda: _create_test_tracer_provider(noop_config, in_memory_exporter),
    )

    yield in_memory_exporter

    in_memory_exporter.clear()


@pytest.fixture
def valid_arize_config_content() -> str:
    """Return valid Arize YAML config content for tests."""
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
def valid_arize_config_file(
    tmp_path: "Path", valid_arize_config_content: str
) -> "Path":
    """Create a valid Arize config file and return its path."""
    config_path = tmp_path / "llmops.yaml"
    config_path.write_text(valid_arize_config_content)
    return config_path


@pytest.fixture
def valid_arize_config_with_mlflow_content(valid_arize_config_content: str) -> str:
    """Return a config that includes both Arize and MLflow sections."""
    return (
        valid_arize_config_content
        + "\nmlflow:\n  tracking_uri: http://localhost:5001\n"
    )


@pytest.fixture
def valid_mlflow_config_content() -> str:
    """Return valid MLflow YAML config content for tests."""
    return """service:
  name: test-service
  version: "1.0.0"

mlflow:
  tracking_uri: http://localhost:5001

validation:
  mode: permissive
"""


@pytest.fixture
def valid_mlflow_config_file(
    tmp_path: "Path", valid_mlflow_config_content: str
) -> "Path":
    """Create a valid MLflow config file and return its path."""
    config_path = tmp_path / "llmops.yaml"
    config_path.write_text(valid_mlflow_config_content)
    return config_path


@pytest.fixture
def valid_mlflow_config_with_arize_content(valid_mlflow_config_content: str) -> str:
    """Return a config that includes both MLflow and Arize sections."""
    return (
        valid_mlflow_config_content
        + "\narize:\n  endpoint: http://localhost:6006/v1/traces\n"
    )


@pytest.fixture
def llmops_module() -> Any:
    """Import and return the llmops module."""
    import llmops

    return llmops


@pytest.fixture
def llmops_arize_module(llmops_module: Any) -> Any:
    """Return the llmops.arize module."""
    return getattr(llmops_module, "arize")


@pytest.fixture
def llmops_mlflow_module(llmops_module: Any) -> Any:
    """Return the llmops.mlflow module."""
    if "mlflow" not in sys.modules:
        sys.modules["mlflow"] = ModuleType("mlflow")
    return getattr(llmops_module, "mlflow")


@pytest.fixture
def fake_arize_otel(in_memory_exporter: InMemorySpanExporter) -> FakeArizeOtel:
    """Provide a FakeArizeOtel instance for testing arize.otel interactions.

    This is preferred over MagicMock because:
    - It has explicit method signatures matching the real API
    - It catches typos at test time (AttributeError vs silent MagicMock)
    - It returns real TracerProvider instances
    - It allows span capture via InMemorySpanExporter

    Usage:
        def test_something(fake_arize_otel):
            provider = some_function_that_calls_register(fake_arize_otel.register)
            fake_arize_otel.assert_registered_with(space_id="expected")
    """
    return FakeArizeOtel(exporter=in_memory_exporter)


@pytest.fixture
def patched_arize_otel(
    fake_arize_otel: FakeArizeOtel,
) -> Generator[FakeArizeOtel, None, None]:
    """Patch arize.otel in sys.modules with FakeArizeOtel.

    This fixture patches sys.modules so that `from arize.otel import register`
    uses the fake. Since create_tracer_provider imports arize.otel at call time
    (not module load time), no reload is necessary.

    Usage:
        @pytest.mark.disable_mock_sdk_telemetry
        def test_something(patched_arize_otel, tmp_path):
            # Create config and call code that imports arize.otel
            provider = create_tracer_provider(config)
            patched_arize_otel.assert_registered_with(space_id="test")
    """
    # Create a module-like object that has our fake's attributes
    class FakeArizeOtelModule:
        register = fake_arize_otel.register
        Transport = FakeArizeOtel.Transport

    # Save original arize.otel module if it exists
    original_module = sys.modules.get("arize.otel")

    # Patch sys.modules with our fake
    sys.modules["arize.otel"] = FakeArizeOtelModule()  # type: ignore[assignment]

    try:
        yield fake_arize_otel
    finally:
        # Restore original module
        if original_module is not None:
            sys.modules["arize.otel"] = original_module
        else:
            sys.modules.pop("arize.otel", None)
