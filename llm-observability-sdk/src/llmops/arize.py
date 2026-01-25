"""Public Arize platform module for llmops.

Usage:
    # Greenfield (new TracerProvider)
    import llmops
    llmops.arize.instrument(config_path="/path/to/llmops.yaml")

    # Add-on (existing TracerProvider)
    import llmops
    llmops.arize.instrument_existing_tracer(
        endpoint="https://otlp.arize.com/v1",
        api_key=os.environ["ARIZE_API_KEY"],
        space_id=os.environ["ARIZE_SPACE_ID"],
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from llmops._platforms.arize import ArizePlatform
from llmops.exceptions import ConfigurationError

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

ConfigurationError = ConfigurationError

_platform = ArizePlatform()


def instrument(config_path: str | Path | None = None) -> "TracerProvider":
    """Initialize Arize telemetry and auto-instrumentation.

    Creates a new TracerProvider configured for Arize and sets it as the
    global tracer provider. Use this for greenfield applications without
    existing OpenTelemetry setup.

    Args:
        config_path: Path to llmops.yaml configuration file.

    Returns:
        The configured TracerProvider.

    See Also:
        instrument_existing_tracer: For applications with existing OTel setup.
    """
    return _platform.instrument(config_path=config_path)


def instrument_existing_tracer(
    config_path: str | Path | None = None,
    *,
    endpoint: str | None = None,
    api_key: str | None = None,
    space_id: str | None = None,
    project_name: str | None = None,
    filter_to_genai_spans: bool = True,
) -> None:
    """Add Arize telemetry to an existing global TracerProvider.

    Use this when your application already has OpenTelemetry configured
    with a global TracerProvider. This function:

    1. Gets the existing global TracerProvider
    2. Creates an Arize SpanProcessor
    3. Optionally wraps it with OpenInference filtering
    4. Adds the processor to the existing provider
    5. Applies OpenInference auto-instrumentation (Google ADK, etc.)

    Unlike instrument(), this function does NOT:
    - Create a new TracerProvider
    - Set the global TracerProvider
    - Register an atexit handler (user owns the provider lifecycle)

    Args:
        config_path: Optional path to llmops.yaml. Not required if all
                     credentials are provided via kwargs.
        endpoint: Arize OTLP endpoint. Overrides config file value.
        api_key: Arize API key. Overrides config file value.
        space_id: Arize space ID. Overrides config file value.
        project_name: Arize project name. Overrides config file value.
        filter_to_genai_spans: If True (default), only spans with
                               openinference.span.kind attribute are
                               sent to Arize. Set to False to send all spans.

    Returns:
        None. The function modifies the existing provider in place.

    Raises:
        ConfigurationError: If configuration is invalid.
        ImportError: If arize-otel package is not installed.

    Note:
        - Calling this function twice on the same provider logs a warning
          and does nothing (idempotent).
        - If no SDK TracerProvider exists, a warning is logged but the
          function continues (may not work correctly).

    Example:
        # Programmatic configuration (no config file needed)
        >>> import llmops
        >>> llmops.arize.instrument_existing_tracer(
        ...     endpoint="https://otlp.arize.com/v1",
        ...     api_key=os.environ["ARIZE_API_KEY"],
        ...     space_id=os.environ["ARIZE_SPACE_ID"],
        ... )

        # With config file
        >>> llmops.arize.instrument_existing_tracer(config_path="llmops.yaml")

        # Send all spans (not just GenAI)
        >>> llmops.arize.instrument_existing_tracer(
        ...     config_path="llmops.yaml",
        ...     filter_to_genai_spans=False,
        ... )
    """
    _platform.instrument_existing_tracer(
        config_path=config_path,
        endpoint=endpoint,
        api_key=api_key,
        space_id=space_id,
        project_name=project_name,
        filter_to_genai_spans=filter_to_genai_spans,
    )
