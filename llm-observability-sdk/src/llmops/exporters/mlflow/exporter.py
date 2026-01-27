"""MLflow exporter implementation (skeleton).

This module provides TracerProvider creation for the MLflow platform.
Note: This is a skeleton implementation for future development.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from llmops.api.types import Config

logger = logging.getLogger(__name__)


def check_dependencies() -> None:
    """Verify MLflow dependencies are installed.

    Raises:
        ImportError: If mlflow package is not installed.
    """
    try:
        __import__("mlflow")
    except ImportError:
        raise ImportError(
            "MLflow exporter requires 'mlflow' package.\n"
            "Install with: pip install llmops[mlflow]"
        ) from None


def create_mlflow_provider(config: Config) -> TracerProvider:
    """Create TracerProvider configured for MLflow.

    Note: This is a skeleton implementation. MLflow tracing integration
    is still in development.

    Args:
        config: SDK configuration with mlflow section.

    Returns:
        TracerProvider configured for MLflow.

    Raises:
        ImportError: If mlflow is not installed.
        ValueError: If mlflow config section is missing.
    """
    check_dependencies()

    if config.mlflow is None:
        raise ValueError("MLflow config section required when platform is 'mlflow'")

    # Create a basic TracerProvider with service resource attributes
    resource = Resource.create(
        {
            "service.name": config.service.name,
            "service.version": config.service.version or "0.0.0",
        }
    )
    provider = TracerProvider(resource=resource)

    logger.debug(
        "TracerProvider configured for MLflow with tracking_uri: %s",
        config.mlflow.tracking_uri,
    )

    return provider
