"""MLflow platform implementation (skeleton)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider

from llmops._platforms._instrument import instrument_platform
from llmops.config import LLMOpsConfig

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider


class MLflowPlatform:
    """MLflow skeleton implementation."""

    name = "mlflow"
    config_section = "mlflow"
    install_extra = "mlflow"

    def check_dependencies(self) -> None:
        try:
            __import__("mlflow")
        except ImportError:
            raise ImportError(
                "MLflow platform requires 'mlflow' package.\n"
                "Install with: pip install llmops[mlflow]"
            ) from None

    def create_tracer_provider(self, config: LLMOpsConfig) -> "TracerProvider":
        if not config.mlflow.tracking_uri:
            raise ValueError("mlflow.tracking_uri is required")
        resource_attrs: dict[str, str] = {
            SERVICE_NAME: config.service.name,
        }
        if config.service.version:
            resource_attrs[SERVICE_VERSION] = config.service.version
        resource = Resource.create(resource_attrs)
        return TracerProvider(resource=resource)

    def get_instrumentor_registry(self) -> list[tuple[str, str, str]]:
        return [
            ("gemini", "mlflow.gemini", "autolog"),
            ("openai", "mlflow.openai", "autolog"),
        ]

    def instrument(self, config_path: str | Path | None = None) -> "TracerProvider":
        return instrument_platform(self, config_path=config_path)
