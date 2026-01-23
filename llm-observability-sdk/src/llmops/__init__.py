"""LLM Observability SDK — Platform-explicit auto-instrumentation.

This SDK provides platform namespaces for explicit backend selection:

    import llmops
    llmops.arize.instrument(config_path="/path/to/llmops.yaml")
    llmops.mlflow.instrument(config_path="/path/to/llmops.yaml")
"""

from __future__ import annotations

from llmops.exceptions import ConfigurationError

__version__ = "0.2.0"

__all__ = [
    "ConfigurationError",
    "__version__",
    "arize",
    "mlflow",
]


def __getattr__(name: str):
    if name in {"arize", "mlflow"}:
        import importlib

        return importlib.import_module(f"llmops.{name}")
    raise AttributeError(f"module 'llmops' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted(__all__)
