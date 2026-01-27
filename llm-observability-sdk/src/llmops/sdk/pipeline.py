"""Pipeline composition: exporter dispatch + instrumentation application.

This module is responsible for:
- Dispatching to the correct exporter based on platform config
- Applying auto-instrumentation based on config
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

from opentelemetry import trace

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

    from llmops.api.types import Config

logger = logging.getLogger(__name__)

# Registry of exporter factories: platform -> (module_path, factory_function_name)
EXPORTER_FACTORIES: dict[str, tuple[str, str]] = {
    "arize": ("llmops.exporters.arize.exporter", "create_arize_provider"),
    "mlflow": ("llmops.exporters.mlflow.exporter", "create_mlflow_provider"),
}


def create_provider(config: Config) -> TracerProvider:
    """Create TracerProvider for the configured platform.

    Args:
        config: SDK configuration with platform field set.

    Returns:
        Configured TracerProvider for the specified platform.

    Raises:
        ValueError: If platform is unknown.
        ImportError: If platform dependencies are not installed.
    """
    platform = config.platform
    if platform not in EXPORTER_FACTORIES:
        raise ValueError(
            f"Unknown platform: {platform}. "
            f"Valid platforms: {', '.join(sorted(EXPORTER_FACTORIES.keys()))}"
        )

    module_path, factory_name = EXPORTER_FACTORIES[platform]
    module = importlib.import_module(module_path)
    factory = getattr(module, factory_name)

    provider: TracerProvider = factory(config)
    trace.set_tracer_provider(provider)
    return provider


def apply_instrumentation(config: Config, provider: TracerProvider) -> None:
    """Apply auto-instrumentation based on config.

    Instrumentor failures are logged but never propagate - telemetry
    should never break business logic.

    Args:
        config: SDK configuration with instrumentation settings.
        provider: TracerProvider to pass to instrumentors.
    """
    # Import instrumentation wrappers lazily to avoid circular imports
    # and to allow instrumentors to fail gracefully if not installed
    instrumentors = [
        ("google_adk", "llmops.instrumentation.google_adk", "instrument"),
        ("google_genai", "llmops.instrumentation.google_genai", "instrument"),
    ]

    for config_key, module_path, func_name in instrumentors:
        enabled = getattr(config.instrumentation, config_key, False)
        if not enabled:
            logger.debug("Instrumentor disabled: %s", config_key)
            continue

        try:
            module = importlib.import_module(module_path)
            instrument_fn = getattr(module, func_name)
            instrument_fn(provider)
            logger.debug("Applied instrumentor: %s", config_key)
        except ImportError as e:
            logger.debug("Instrumentor not installed: %s (%s)", config_key, e)
        except Exception as e:
            # Telemetry never breaks business logic
            logger.warning("Instrumentor failed: %s - %s", config_key, e)
