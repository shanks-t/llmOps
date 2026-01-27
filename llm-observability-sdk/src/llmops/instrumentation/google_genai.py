"""Google GenAI instrumentation wrapper.

This module provides a thin wrapper around the OpenInference Google GenAI
instrumentor, isolating vendor-specific code at the edge of the SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider


def instrument(tracer_provider: TracerProvider) -> None:
    """Apply Google GenAI instrumentation.

    Args:
        tracer_provider: TracerProvider to use for instrumentation.

    Raises:
        ImportError: If openinference-instrumentation-google-genai is not installed.
    """
    from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

    instrumentor = GoogleGenAIInstrumentor()
    instrumentor.instrument(tracer_provider=tracer_provider)
