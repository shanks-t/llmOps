"""Google ADK instrumentation wrapper.

This module provides a thin wrapper around the OpenInference Google ADK
instrumentor, isolating vendor-specific code at the edge of the SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider


def instrument(tracer_provider: TracerProvider) -> None:
    """Apply Google ADK instrumentation.

    Args:
        tracer_provider: TracerProvider to use for instrumentation.

    Raises:
        ImportError: If openinference-instrumentation-google-adk is not installed.
    """
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor

    instrumentor = GoogleADKInstrumentor()
    instrumentor.instrument(tracer_provider=tracer_provider)
