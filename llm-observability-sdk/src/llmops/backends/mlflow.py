"""MLflow backend implementation."""

from __future__ import annotations


def setup(endpoint: str, service_name: str, skip_autolog: bool = False) -> None:
    """
    Enable MLflow auto-instrumentation.

    Args:
        endpoint: MLflow tracking server URI (e.g., "http://localhost:5001")
        service_name: Used as experiment name
        skip_autolog: If True, skip enabling autolog (used when Phoenix is also enabled)
    """
    try:
        import mlflow
    except ImportError:
        raise ImportError(
            "mlflow is required for MLflow backend. "
            "Install with: pip install llmops[mlflow]"
        )

    # Set tracking URI
    mlflow.set_tracking_uri(endpoint)
    print(f"llmops: MLflow tracking URI: {endpoint}")

    # Set experiment
    mlflow.set_experiment(service_name)
    print(f"llmops: MLflow experiment: {service_name}")

    # Enable tracing
    mlflow.tracing.enable()
    print("llmops: MLflow tracing enabled")

    # Enable autologs (skip if Phoenix is handling instrumentation)
    if not skip_autolog:
        _try_autolog("gemini")
    else:
        print("llmops: Skipping MLflow autolog (Phoenix handling instrumentation)")


def _try_autolog(name: str) -> None:
    """Try to enable an MLflow autolog, skip if not available."""
    import mlflow

    try:
        module = getattr(mlflow, name, None)
        if module and hasattr(module, "autolog"):
            module.autolog()
            print(f"llmops: Enabled mlflow.{name}.autolog()")
        else:
            print(f"llmops: mlflow.{name} not available")
    except Exception as e:
        print(f"llmops: Failed to enable mlflow.{name}.autolog(): {e}")
