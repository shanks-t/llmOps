"""Public API for the LLMOPS SDK.

This module re-exports the stable public interface:
- instrument() - Initialize the SDK
- shutdown() - Shutdown the SDK and flush telemetry
- is_configured() - Check if the SDK has been initialized
- Config and related types - Programmatic configuration
"""

from __future__ import annotations

from llmops.api._init import instrument, is_configured, shutdown
from llmops.api.types import (
    ArizeConfig,
    Config,
    InstrumentationConfig,
    MLflowConfig,
    ServiceConfig,
    ValidationConfig,
)

__all__ = [
    "instrument",
    "shutdown",
    "is_configured",
    "Config",
    "ServiceConfig",
    "ArizeConfig",
    "MLflowConfig",
    "InstrumentationConfig",
    "ValidationConfig",
]
