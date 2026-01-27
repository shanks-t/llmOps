"""LLMOPS SDK - LLM Observability for Python.

This SDK provides a single entry point for LLM observability:

    import llmops
    llmops.init(config="llmops.yaml")

Configuration drives platform selection - specify `platform: arize` or
`platform: mlflow` in your YAML config file.
"""

from __future__ import annotations

from llmops.api import (
    ArizeConfig,
    Config,
    InstrumentationConfig,
    MLflowConfig,
    ServiceConfig,
    ValidationConfig,
    init,
    is_configured,
    shutdown,
)
from llmops.exceptions import ConfigurationError

__version__ = "0.3.0"

__all__ = [
    # Entry points
    "init",
    "shutdown",
    "is_configured",
    # Configuration types
    "Config",
    "ServiceConfig",
    "ArizeConfig",
    "MLflowConfig",
    "InstrumentationConfig",
    "ValidationConfig",
    # Exceptions
    "ConfigurationError",
    # Metadata
    "__version__",
]
