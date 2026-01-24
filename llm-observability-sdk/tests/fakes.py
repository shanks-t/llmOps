"""Test fakes for external dependencies.

This module provides typed test doubles (fakes) that validate usage and
document expected API surfaces. Prefer these over MagicMock for better
type safety and self-documenting tests.

Following the testing philosophy:
- Fakes are working implementations with shortcuts
- They validate usage patterns (unlike MagicMock which accepts anything)
- They catch typos and API drift at test time
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan


class Transport(str, Enum):
    """Fake Transport enum matching arize.otel.Transport.

    This is a str enum so that values can be compared directly:
        Transport.HTTP == "http"  # True
    """

    GRPC = "grpc"
    HTTPS = "https"
    HTTP = "http"


@dataclass
class RegisterCall:
    """Record of a call to arize.otel.register().

    Captures all parameters for verification in tests.
    """

    space_id: str | None
    api_key: str | None
    project_name: str | None
    endpoint: str | None
    transport: Transport
    batch: bool
    set_global_tracer_provider: bool
    headers: dict[str, str] | None
    verbose: bool
    log_to_console: bool


class FakeArizeOtel:
    """Test double for arize.otel that validates usage.

    Unlike MagicMock, this fake:
    - Has explicit method signatures that match the real API
    - Records calls for verification
    - Returns real TracerProvider instances
    - Catches typos (fake.regster() would raise AttributeError)

    Usage:
        fake = FakeArizeOtel()
        provider = create_tracer_provider(config, register_fn=fake.register)

        fake.assert_registered_with(space_id="test-space", transport=Transport.HTTP)
        assert isinstance(provider, TracerProvider)

    WARNING: This is a temporary fixture. Prefer integration tests against
    real arize.otel when possible.
    """

    def __init__(self, exporter: InMemorySpanExporter | None = None) -> None:
        """Initialize the fake with optional exporter for span capture."""
        self.register_calls: list[RegisterCall] = []
        self._exporter = exporter or InMemorySpanExporter()
        self._provider: TracerProvider | None = None

    def register(
        self,
        space_id: str | None = None,
        api_key: str | None = None,
        project_name: str | None = None,
        endpoint: str | None = None,
        transport: Transport = Transport.GRPC,
        batch: bool = True,
        set_global_tracer_provider: bool = True,
        headers: dict[str, str] | None = None,
        verbose: bool = True,
        log_to_console: bool = False,
    ) -> TracerProvider:
        """Fake register that records calls and returns a real provider.

        This method has the same signature as arize.otel.register() and
        returns a real TracerProvider configured with an InMemorySpanExporter.

        Args:
            space_id: Arize space identifier.
            api_key: Arize API key.
            project_name: Project name for traces.
            endpoint: OTLP endpoint URL.
            transport: Transport protocol (GRPC, HTTP, HTTPS).
            batch: Use BatchSpanProcessor if True, SimpleSpanProcessor if False.
            set_global_tracer_provider: Set as global tracer provider.
            headers: Additional headers for requests.
            verbose: Print configuration details.
            log_to_console: Log spans to console.

        Returns:
            A real TracerProvider configured with InMemorySpanExporter.
        """
        self.register_calls.append(
            RegisterCall(
                space_id=space_id,
                api_key=api_key,
                project_name=project_name,
                endpoint=endpoint,
                transport=transport,
                batch=batch,
                set_global_tracer_provider=set_global_tracer_provider,
                headers=headers,
                verbose=verbose,
                log_to_console=log_to_console,
            )
        )

        if self._provider is None:
            resource = Resource.create({SERVICE_NAME: project_name or "fake-service"})
            self._provider = TracerProvider(resource=resource)
            self._provider.add_span_processor(SimpleSpanProcessor(self._exporter))

        return self._provider

    @property
    def provider(self) -> TracerProvider | None:
        """Return the provider created by register(), if any."""
        return self._provider

    @property
    def exporter(self) -> InMemorySpanExporter:
        """Return the exporter for span verification."""
        return self._exporter

    def get_finished_spans(self) -> tuple[ReadableSpan, ...]:
        """Return all finished spans captured by the exporter."""
        return self._exporter.get_finished_spans()

    def clear_spans(self) -> None:
        """Clear all captured spans."""
        self._exporter.clear()

    def assert_registered_once(self) -> None:
        """Assert that register() was called exactly once."""
        assert len(self.register_calls) == 1, (
            f"Expected register() to be called once, "
            f"but was called {len(self.register_calls)} times"
        )

    def assert_registered_with(self, **expected: object) -> None:
        """Assert register() was called with expected arguments.

        Args:
            **expected: Keyword arguments to match against the register call.
                Only specified arguments are checked.

        Raises:
            AssertionError: If no calls were made or arguments don't match.
        """
        if not self.register_calls:
            raise AssertionError("register() was never called")

        actual = self.register_calls[-1]
        for key, value in expected.items():
            actual_value = getattr(actual, key)
            assert actual_value == value, (
                f"register() {key}: expected {value!r}, got {actual_value!r}"
            )

    def assert_not_called(self) -> None:
        """Assert that register() was never called."""
        assert len(self.register_calls) == 0, (
            f"Expected register() to not be called, "
            f"but was called {len(self.register_calls)} times"
        )
