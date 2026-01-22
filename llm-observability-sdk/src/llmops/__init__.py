"""LLM Observability SDK — Unified auto-instrumentation for LLM applications.

This SDK provides a single entry point for auto-instrumentation of Google ADK
and Google GenAI with Arize telemetry.

Usage:
    import llmops

    # Initialize with config file path
    llmops.instrument(config_path="/path/to/llmops.yaml")

    # Or use LLMOPS_CONFIG_PATH environment variable
    # export LLMOPS_CONFIG_PATH=/path/to/llmops.yaml
    llmops.instrument()

    # Your app code runs with auto-instrumentation enabled
    # ...
"""

from llmops.exceptions import ConfigurationError
from llmops.instrument import instrument

__version__ = "0.1.0"

__all__ = [
    "instrument",
    "ConfigurationError",
    "__version__",
]
