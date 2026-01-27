"""Configuration loading, parsing, and validation for the llmops SDK."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

from llmops.api.types import (
    ArizeConfig,
    Config,
    InstrumentationConfig,
    MLflowConfig,
    ServiceConfig,
    ValidationConfig,
)
from llmops.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Pattern for environment variable substitution: ${VAR_NAME}
ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

# Valid platform values
VALID_PLATFORMS = {"arize", "mlflow"}


def _substitute_env_vars(value: str, strict: bool) -> str:
    """Substitute ${VAR_NAME} patterns with environment variable values.

    Args:
        value: String potentially containing ${VAR_NAME} patterns.
        strict: If True, raise ConfigurationError for missing env vars.

    Returns:
        String with environment variables substituted.

    Raises:
        ConfigurationError: If strict=True and an env var is not set.
    """

    def replace_match(match: re.Match[str]) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            if strict:
                raise ConfigurationError(
                    f"Environment variable '{var_name}' is not set"
                )
            logger.warning(
                "Environment variable '%s' not set, using empty string", var_name
            )
            return ""
        return env_value

    return ENV_VAR_PATTERN.sub(replace_match, value)


def _substitute_env_vars_recursive(data: Any, strict: bool) -> Any:
    """Recursively substitute environment variables in a data structure.

    Args:
        data: Data structure (dict, list, or scalar) to process.
        strict: If True, raise ConfigurationError for missing env vars.

    Returns:
        Data structure with all string values having env vars substituted.
    """
    if isinstance(data, dict):
        return {k: _substitute_env_vars_recursive(v, strict) for k, v in data.items()}
    elif isinstance(data, list):
        return [_substitute_env_vars_recursive(item, strict) for item in data]
    elif isinstance(data, str):
        return _substitute_env_vars(data, strict)
    else:
        return data


def _parse_service_config(data: dict[str, Any]) -> ServiceConfig:
    """Parse service configuration section."""
    return ServiceConfig(
        name=data.get("name", ""),
        version=data.get("version"),
    )


def _parse_arize_config(
    data: dict[str, Any], config_dir: Path | None = None
) -> ArizeConfig:
    """Parse Arize configuration section.

    Args:
        data: Arize configuration dictionary.
        config_dir: Directory of the config file for resolving relative paths.

    TLS certificate path supports env var fallback:
    - certificate_file: OTEL_EXPORTER_OTLP_CERTIFICATE
    """
    # Validate transport value
    transport = data.get("transport", "http")
    if transport not in ("http", "grpc"):
        logger.warning("Unknown transport '%s', defaulting to 'http'", transport)
        transport = "http"

    # Resolve certificate_file path (relative to config file or absolute)
    certificate_file = data.get(
        "certificate_file",
        os.environ.get("OTEL_EXPORTER_OTLP_CERTIFICATE"),
    )
    if certificate_file and config_dir:
        cert_path = Path(certificate_file)
        if not cert_path.is_absolute():
            certificate_file = str(config_dir / cert_path)

    return ArizeConfig(
        endpoint=data.get("endpoint", ""),
        project_name=data.get("project_name"),
        api_key=data.get("api_key"),
        space_id=data.get("space_id"),
        certificate_file=certificate_file,
        transport=transport,
        batch=data.get("batch", True),
        log_to_console=data.get("log_to_console", False),
        verbose=data.get("verbose", False),
    )


def _parse_instrumentation_config(data: dict[str, Any]) -> InstrumentationConfig:
    """Parse instrumentation configuration section."""
    google_adk = data.get("google_adk", True)
    google_genai = data.get("google_genai", True)

    known_keys = {"google_adk", "google_genai"}
    extra = {k: v for k, v in data.items() if k not in known_keys}

    if extra:
        logger.warning(
            "Unknown instrumentation options ignored: %s", list(extra.keys())
        )

    return InstrumentationConfig(
        google_adk=bool(google_adk),
        google_genai=bool(google_genai),
        extra=extra,
    )


def _parse_mlflow_config(data: dict[str, Any]) -> MLflowConfig:
    """Parse MLflow configuration section."""
    return MLflowConfig(
        tracking_uri=data.get("tracking_uri", ""),
        experiment_name=data.get("experiment_name"),
    )


def _parse_validation_config(data: dict[str, Any]) -> ValidationConfig:
    """Parse validation configuration section."""
    mode = data.get("mode", "permissive")
    if mode not in ("strict", "permissive"):
        logger.warning("Unknown validation mode '%s', defaulting to permissive", mode)
        mode = "permissive"
    return ValidationConfig(mode=mode)


def _validate_config(config: Config) -> list[str]:
    """Validate configuration and return list of error messages.

    Args:
        config: Parsed configuration to validate.

    Returns:
        List of validation error messages. Empty if valid.
    """
    errors: list[str] = []

    if not config.service.name:
        errors.append("service.name is required")

    # Validate platform-specific config exists
    if config.platform == "arize":
        if config.arize is None or not config.arize.endpoint:
            errors.append("arize.endpoint is required when platform is 'arize'")
    elif config.platform == "mlflow":
        if config.mlflow is None or not config.mlflow.tracking_uri:
            errors.append("mlflow.tracking_uri is required when platform is 'mlflow'")

    # Validate certificate file exists if specified
    if config.arize and config.arize.certificate_file:
        cert_path = Path(config.arize.certificate_file)
        if not cert_path.exists():
            errors.append(
                f"Certificate file not found: {config.arize.certificate_file}"
            )

    return errors


def load_config(path: str | Path, strict: bool | None = None) -> Config:
    """Load and parse configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.
        strict: Override validation mode. If None, use mode from config file.

    Returns:
        Parsed and validated Config.

    Raises:
        ConfigurationError: If file doesn't exist, YAML is invalid,
                           or validation fails in strict mode.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {path}")

    try:
        with open(path) as f:
            raw_data = yaml.safe_load(f)
            if raw_data is None:
                raw_data = {}
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}")

    # Determine validation mode early (needed for env var substitution)
    validation_data = raw_data.get("validation", {})
    validation_mode = validation_data.get("mode", "permissive")
    is_strict = strict if strict is not None else (validation_mode == "strict")

    # Substitute environment variables
    try:
        data = _substitute_env_vars_recursive(raw_data, strict=is_strict)
    except ConfigurationError:
        # Re-raise env var errors in strict mode
        raise

    # Parse platform field (required)
    platform = data.get("platform")
    if platform is None:
        raise ConfigurationError(
            "Config must specify 'platform' field. Valid values: arize, mlflow"
        )
    if platform not in VALID_PLATFORMS:
        raise ConfigurationError(
            f"Unknown platform: '{platform}'. Valid values: {', '.join(sorted(VALID_PLATFORMS))}"
        )

    # Parse configuration sections
    # Pass config file directory for resolving relative paths
    config_dir = path.parent

    # Parse platform-specific config
    arize_config = None
    mlflow_config = None

    if "arize" in data:
        arize_config = _parse_arize_config(data["arize"], config_dir=config_dir)
    if "mlflow" in data:
        mlflow_config = _parse_mlflow_config(data["mlflow"])

    config = Config(
        platform=platform,
        service=_parse_service_config(data.get("service", {})),
        arize=arize_config,
        mlflow=mlflow_config,
        instrumentation=_parse_instrumentation_config(data.get("instrumentation", {})),
        validation=_parse_validation_config(data.get("validation", {})),
    )

    # Override validation mode if specified
    if strict is not None:
        config.validation.mode = "strict" if strict else "permissive"

    # Validate configuration
    errors = _validate_config(config)
    if errors and config.is_strict:
        raise ConfigurationError(
            f"Configuration validation failed: {'; '.join(errors)}"
        )

    return config
