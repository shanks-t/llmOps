"""Public configuration types for the LLMOPS SDK.

These types are part of the stable public API and follow semver guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceConfig:
    """Service identification configuration."""

    name: str
    version: str | None = None


@dataclass
class ArizeConfig:
    """Arize telemetry configuration.

    These fields map directly to arize.otel.register() parameters.
    """

    endpoint: str
    project_name: str | None = None
    api_key: str | None = None
    space_id: str | None = None
    # TLS certificate for server verification (.pem)
    # Can be relative path (resolved from config file) or absolute path
    # Fallback: OTEL_EXPORTER_OTLP_CERTIFICATE env var
    certificate_file: str | None = None
    # Transport protocol: "http" (default) or "grpc"
    transport: str = "http"
    # Span processor: True for BatchSpanProcessor (default), False for SimpleSpanProcessor
    batch: bool = True
    # Log spans to console (useful during development)
    log_to_console: bool = False
    # Print configuration details to stdout
    verbose: bool = False


@dataclass
class MLflowConfig:
    """MLflow telemetry configuration."""

    tracking_uri: str
    experiment_name: str | None = None


@dataclass
class InstrumentationConfig:
    """Auto-instrumentation configuration."""

    google_adk: bool = True
    google_genai: bool = True
    # Extra keys are stored here for forward compatibility
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationConfig:
    """Validation mode configuration."""

    mode: str = "permissive"  # "strict" | "permissive"


@dataclass
class Config:
    """Complete SDK configuration.

    The `platform` field is required and determines which exporter is used.
    Valid values: "arize", "mlflow"
    """

    platform: str  # "arize" | "mlflow"
    service: ServiceConfig
    arize: ArizeConfig | None = None
    mlflow: MLflowConfig | None = None
    instrumentation: InstrumentationConfig = field(
        default_factory=InstrumentationConfig
    )
    validation: ValidationConfig = field(default_factory=ValidationConfig)

    @property
    def is_strict(self) -> bool:
        """Return True if validation mode is strict."""
        return self.validation.mode == "strict"
