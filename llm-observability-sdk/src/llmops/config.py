"""Configuration loading, parsing, and validation for the llmops SDK."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from llmops.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Pattern for environment variable substitution: ${VAR_NAME}
ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


@dataclass
class ServiceConfig:
    """Service identification configuration."""

    name: str
    version: str | None = None


@dataclass
class ArizeConfig:
    """Arize telemetry configuration."""

    endpoint: str
    project_name: str | None = None
    api_key: str | None = None
    space_id: str | None = None


@dataclass
class InstrumentationConfig:
    """Auto-instrumentation configuration."""

    google_adk: bool = True
    google_genai: bool = True
    # Extra keys are stored here for forward compatibility
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class PrivacyConfig:
    """Privacy configuration."""

    capture_content: bool = False


@dataclass
class ValidationConfig:
    """Validation mode configuration."""

    mode: str = "permissive"  # "strict" or "permissive"


@dataclass
class LLMOpsConfig:
    """Complete SDK configuration."""

    service: ServiceConfig
    arize: ArizeConfig
    instrumentation: InstrumentationConfig = field(
        default_factory=InstrumentationConfig
    )
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)

    @property
    def is_strict(self) -> bool:
        """Return True if validation mode is strict."""
        return self.validation.mode == "strict"


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


def _substitute_env_vars_recursive(
    data: Any, strict: bool
) -> Any:
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


def _parse_arize_config(data: dict[str, Any]) -> ArizeConfig:
    """Parse Arize configuration section."""
    return ArizeConfig(
        endpoint=data.get("endpoint", ""),
        project_name=data.get("project_name"),
        api_key=data.get("api_key"),
        space_id=data.get("space_id"),
    )


def _parse_instrumentation_config(data: dict[str, Any]) -> InstrumentationConfig:
    """Parse instrumentation configuration section."""
    # Extract known keys
    google_adk = data.get("google_adk", True)
    google_genai = data.get("google_genai", True)

    # Collect unknown keys for forward compatibility
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


def _parse_privacy_config(data: dict[str, Any]) -> PrivacyConfig:
    """Parse privacy configuration section."""
    return PrivacyConfig(
        capture_content=data.get("capture_content", False),
    )


def _parse_validation_config(data: dict[str, Any]) -> ValidationConfig:
    """Parse validation configuration section."""
    mode = data.get("mode", "permissive")
    if mode not in ("strict", "permissive"):
        logger.warning("Unknown validation mode '%s', defaulting to permissive", mode)
        mode = "permissive"
    return ValidationConfig(mode=mode)


def _validate_config(config: LLMOpsConfig) -> list[str]:
    """Validate configuration and return list of error messages.

    Args:
        config: Parsed configuration to validate.

    Returns:
        List of validation error messages. Empty if valid.
    """
    errors: list[str] = []

    # Service name is required
    if not config.service.name:
        errors.append("service.name is required")

    # Arize endpoint is required
    if not config.arize.endpoint:
        errors.append("arize.endpoint is required")

    return errors


def load_config(path: Path, strict: bool | None = None) -> LLMOpsConfig:
    """Load and parse configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.
        strict: Override validation mode. If None, use mode from config file.

    Returns:
        Parsed and validated LLMOpsConfig.

    Raises:
        ConfigurationError: If file doesn't exist, YAML is invalid,
                           or validation fails in strict mode.
    """
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

    # Parse configuration sections
    config = LLMOpsConfig(
        service=_parse_service_config(data.get("service", {})),
        arize=_parse_arize_config(data.get("arize", {})),
        instrumentation=_parse_instrumentation_config(data.get("instrumentation", {})),
        privacy=_parse_privacy_config(data.get("privacy", {})),
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
