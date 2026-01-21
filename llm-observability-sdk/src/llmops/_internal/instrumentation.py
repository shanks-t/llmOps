"""Auto-instrumentation for LLM frameworks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

    from llmops.config import InstrumentationConfig

logger = logging.getLogger(__name__)

# Registry of known instrumentors
# Format: (config_key, module_path, class_name)
INSTRUMENTOR_REGISTRY: list[tuple[str, str, str]] = [
    (
        "google_adk",
        "openinference.instrumentation.google_adk",
        "GoogleADKInstrumentor",
    ),
    (
        "google_genai",
        "openinference.instrumentation.google_genai",
        "GoogleGenAIInstrumentor",
    ),
]


def apply_instrumentation(
    config: InstrumentationConfig,
    provider: TracerProvider,
) -> None:
    """Apply auto-instrumentation based on configuration.

    Instruments enabled LLM frameworks. Failures are logged but never
    propagate to the caller (telemetry must not break business logic).

    Args:
        config: Instrumentation configuration with enable flags.
        provider: TracerProvider to use for instrumentation.
    """
    for config_key, module_path, class_name in INSTRUMENTOR_REGISTRY:
        # Check if this instrumentor is enabled in config
        enabled = getattr(config, config_key, False)

        if not enabled:
            logger.debug("Instrumentation disabled: %s", config_key)
            continue

        # Try to import and apply the instrumentor
        try:
            _apply_instrumentor(module_path, class_name, provider)
            logger.debug("Instrumentation enabled: %s", config_key)
        except ImportError:
            logger.debug(
                "Instrumentation package not installed: %s (install with "
                "'pip install llmops[phoenix]')",
                module_path,
            )
        except Exception as e:
            # Swallow all errors - telemetry must not break business logic
            logger.warning(
                "Failed to enable instrumentation %s: %s",
                config_key,
                e,
            )


def _apply_instrumentor(
    module_path: str,
    class_name: str,
    provider: TracerProvider,
) -> None:
    """Import and apply a single instrumentor.

    Args:
        module_path: Full module path (e.g., "openinference.instrumentation.google_adk").
        class_name: Instrumentor class name (e.g., "GoogleADKInstrumentor").
        provider: TracerProvider to use.

    Raises:
        ImportError: If the instrumentor package is not installed.
        Exception: If instrumentation fails for any other reason.
    """
    module = __import__(module_path, fromlist=[class_name])
    instrumentor_class = getattr(module, class_name)
    instrumentor = instrumentor_class()
    instrumentor.instrument(tracer_provider=provider)
