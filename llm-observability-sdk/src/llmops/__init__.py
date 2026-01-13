"""
LLM Observability SDK — Unified auto-instrumentation for LLM applications.

This SDK provides a thin orchestration layer over existing auto-instrumentation
libraries (Phoenix/OpenInference, MLflow).

Usage:
    import llmops

    llmops.configure(
        backend="phoenix",
        endpoint="http://localhost:6006/v1/traces",
        service_name="my-agent",
    )

    # Your app code runs with auto-instrumentation enabled
    # ...

    llmops.shutdown()
"""

from llmops.configure import configure, shutdown, ConfigurationError, BackendConfig

__version__ = "0.1.0"

__all__ = [
    "configure",
    "shutdown",
    "ConfigurationError",
    "BackendConfig",
    "__version__",
]
