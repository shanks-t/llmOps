"""Shared instrumentor runner for platform registries."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

    from llmops.config import InstrumentationConfig

logger = logging.getLogger(__name__)


def apply_instrumentation(
    config: "InstrumentationConfig",
    registry: list[tuple[str, str, str]],
    provider: "TracerProvider",
) -> None:
    """Apply auto-instrumentation from a platform's registry.

    Instruments enabled LLM frameworks. Failures are logged but never
    propagate to the caller (telemetry must not break business logic).
    """
    for config_key, module_path, class_name in registry:
        enabled = getattr(config, config_key, False)
        if not enabled:
            logger.debug("Instrumentation disabled: %s", config_key)
            continue

        try:
            module = importlib.import_module(module_path)
            instrumentor_class = getattr(module, class_name)
            instrumentor = instrumentor_class()
            instrumentor.instrument(tracer_provider=provider)
            logger.debug("Instrumentation enabled: %s", config_key)
        except ImportError:
            logger.debug("Instrumentation package not installed: %s", module_path)
        except Exception as exc:
            logger.warning("Failed to enable instrumentation %s: %s", config_key, exc)
