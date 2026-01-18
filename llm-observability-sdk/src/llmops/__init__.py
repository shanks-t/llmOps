"""
LLM Observability SDK — Unified auto-instrumentation for LLM applications.

This SDK provides a thin orchestration layer over existing auto-instrumentation
libraries. Each backend uses its native instrumentation.

- Phoenix: OpenInference semantic conventions
- MLflow: MLflow native autolog

Usage:
    import llmops

    # Configure for Phoenix
    llmops.configure(
        backend="phoenix",
        endpoint="http://localhost:6006/v1/traces",
        service_name="my-agent",
    )

    # OR configure for MLflow
    llmops.configure(
        backend="mlflow",
        endpoint="http://localhost:5001",
        service_name="my-agent",
    )

    # Your app code runs with auto-instrumentation enabled
    # ...

    llmops.shutdown()
"""

from llmops.configure import (
    configure,
    init,
    shutdown,
    ConfigurationError,
    get_backend,
    is_configured,
)

__version__ = "0.1.0"

__all__ = [
    "configure",
    "init",
    "shutdown",
    "ConfigurationError",
    "get_backend",
    "is_configured",
    "__version__",
]
