"""Span filtering and processing utilities for selective telemetry export.

This module provides SpanProcessor implementations that filter spans
based on specific criteria before forwarding to delegate processors,
as well as processors that inject required attributes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from opentelemetry.sdk.trace import SpanProcessor

if TYPE_CHECKING:
    from opentelemetry.context import Context
    from opentelemetry.sdk.trace import ReadableSpan, Span

logger = logging.getLogger(__name__)

# Arize requires this span attribute to route spans to the correct project
ARIZE_PROJECT_NAME_ATTR = "arize.project.name"


class OpenInferenceSpanFilter(SpanProcessor):
    """SpanProcessor that filters to only forward OpenInference (GenAI) spans.

    This processor wraps a delegate SpanProcessor and only forwards spans
    that have the `openinference.span.kind` attribute. This attribute is
    set by OpenInference instrumentors (Google ADK, Google GenAI, etc.)
    to identify GenAI-related spans.

    Use this when you want to send only GenAI telemetry to a specific
    backend (like Arize) while sending all spans to your infrastructure
    backend (like Jaeger/Datadog).

    Args:
        delegate: The SpanProcessor to forward filtered spans to.

    Example:
        >>> from opentelemetry.sdk.trace.export import BatchSpanProcessor
        >>> batch_processor = BatchSpanProcessor(some_exporter)
        >>> filtered = OpenInferenceSpanFilter(batch_processor)
        >>> provider.add_span_processor(filtered)
    """

    OPENINFERENCE_ATTRIBUTE = "openinference.span.kind"

    def __init__(self, delegate: "SpanProcessor") -> None:  # type: ignore[name-defined]
        """Initialize the filter with a delegate processor.

        Args:
            delegate: The SpanProcessor to forward matching spans to.
        """
        self._delegate = delegate

    def on_start(
        self,
        span: "Span",
        parent_context: Optional["Context"] = None,
    ) -> None:
        """Called when a span is started. Forwards to delegate.

        We can't filter on start because attributes aren't finalized yet.
        We forward to delegate so any wrapped processors can do their work.

        Args:
            span: The span that was started.
            parent_context: The parent context of the span.
        """
        # Forward to delegate - we filter on end, not start
        self._delegate.on_start(span, parent_context)

    def on_end(self, span: "ReadableSpan") -> None:
        """Called when a span ends. Forwards only OpenInference spans.

        Args:
            span: The span that ended.
        """
        attributes = span.attributes

        # Handle None or empty attributes
        if not attributes:
            return

        # Only forward spans with OpenInference semantic attribute
        if self.OPENINFERENCE_ATTRIBUTE in attributes:
            self._delegate.on_end(span)

    def shutdown(self) -> None:
        """Shutdown the delegate processor."""
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """Force flush the delegate processor.

        Args:
            timeout_millis: Maximum time to wait for flush in milliseconds.

        Returns:
            True if flush completed successfully, False otherwise.
        """
        if timeout_millis is None:
            return self._delegate.force_flush()
        return self._delegate.force_flush(timeout_millis)


class ArizeProjectNameInjector(SpanProcessor):
    """SpanProcessor that injects the arize.project.name span attribute.

    When using instrument_existing_tracer(), we add a processor to an existing
    TracerProvider that has its own Resource attributes. Arize requires
    either a resource attribute (openinference.project.name) or a span
    attribute (arize.project.name) to route spans to the correct project.

    Since we can't modify the existing TracerProvider's Resource, this
    processor injects the project name as a span attribute on span start.

    Args:
        delegate: The SpanProcessor to forward spans to.
        project_name: The Arize project name to inject.

    Example:
        >>> from opentelemetry.sdk.trace.export import BatchSpanProcessor
        >>> batch_processor = BatchSpanProcessor(arize_exporter)
        >>> injector = ArizeProjectNameInjector(batch_processor, "my-project")
        >>> provider.add_span_processor(injector)
    """

    def __init__(self, delegate: "SpanProcessor", project_name: str) -> None:
        """Initialize the injector with a delegate processor and project name.

        Args:
            delegate: The SpanProcessor to forward spans to.
            project_name: The Arize project name to inject as span attribute.
        """
        self._delegate = delegate
        self._project_name = project_name

    def on_start(
        self,
        span: "Span",
        parent_context: Optional["Context"] = None,
    ) -> None:
        """Called when a span is started. Injects the project name attribute.

        Args:
            span: The span that was started.
            parent_context: The parent context of the span.
        """
        # Inject the project name as a span attribute
        # This allows Arize to route the span to the correct project
        span.set_attribute(ARIZE_PROJECT_NAME_ATTR, self._project_name)

        # Forward to delegate
        self._delegate.on_start(span, parent_context)

    def on_end(self, span: "ReadableSpan") -> None:
        """Called when a span ends. Forwards to delegate.

        Args:
            span: The span that ended.
        """
        self._delegate.on_end(span)

    def shutdown(self) -> None:
        """Shutdown the delegate processor."""
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """Force flush the delegate processor.

        Args:
            timeout_millis: Maximum time to wait for flush in milliseconds.

        Returns:
            True if flush completed successfully, False otherwise.
        """
        if timeout_millis is None:
            return self._delegate.force_flush()
        return self._delegate.force_flush(timeout_millis)
