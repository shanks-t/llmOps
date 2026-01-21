"""Contract tests for validation modes — PRD_01.

Executable contracts derived from:
- PRD: docs/prd/PRD_01.md
- API: docs/api_spec/API_SPEC_01.md

Requirements covered:
- N1: Telemetry failures do not raise exceptions to user code
- N2: Telemetry must never break business logic
- N5: Permissive validation uses a no-op tracer provider on config errors
- N6: Strict validation fails startup on config errors (dev only)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_01"
API_SPEC_ID = "API_SPEC_01"
CAPABILITY = "validation"


class TestPermissiveMode:
    """Tests for permissive validation mode behavior."""

    def test_permissive_mode_returns_noop_on_invalid_config(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a config file with validation mode set to "permissive"
        AND the config file is missing required fields
        WHEN llmops.init() is called with that config
        THEN a provider is returned (no-op tracer provider)
        AND no exception is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "validation:\n"
            "  mode: permissive\n"
            "# Missing required 'service' and 'arize' sections\n"
        )

        provider = llmops_module.init(config_path=config_path)

        assert provider is not None


class TestStrictMode:
    """Tests for strict validation mode behavior."""

    def test_strict_mode_raises_error_on_invalid_config(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a config file with validation mode set to "strict"
        AND the config file is missing required fields
        WHEN llmops.init() is called with that config
        THEN a ConfigurationError is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "validation:\n"
            "  mode: strict\n"
            "# Missing required 'service' and 'arize' sections\n"
        )

        with pytest.raises(llmops_module.ConfigurationError):
            llmops_module.init(config_path=config_path)


class TestTelemetryIsolation:
    """Tests for telemetry isolation from business logic."""

    def test_telemetry_failure_never_propagates_to_caller(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a valid config file with permissive validation
        AND the application has business logic that initializes telemetry
        WHEN the business logic executes
        THEN the business logic completes successfully
        AND no exceptions propagate to the caller
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "service:\n"
            "  name: test-service\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        # Simulate business logic that wraps telemetry initialization
        def business_logic() -> str:
            """Business logic that should never fail due to telemetry."""
            llmops_module.init(config_path=config_path)
            return "business logic completed"

        # Business logic must complete without exception
        result = business_logic()
        assert result == "business logic completed"

    def test_telemetry_runtime_errors_are_swallowed(
        self,
        valid_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a successfully initialized SDK
        WHEN telemetry operations fail at runtime (e.g., network errors)
        THEN no exceptions propagate to user code
        AND business logic continues uninterrupted
        """
        provider = llmops_module.init(config_path=valid_config_file)
        assert provider is not None

        # Simulate business logic that creates spans
        # Runtime telemetry failures should be swallowed internally
        tracer = provider.get_tracer("test-tracer")

        # Create a span - if telemetry export fails, it should not raise
        def business_logic_with_tracing() -> str:
            """Business logic that uses tracing."""
            with tracer.start_as_current_span("business-operation"):
                # Simulate business logic
                result = "business logic completed"
            return result

        # Business logic must complete without exception
        # even if the span export encounters errors (e.g., unreachable endpoint)
        result = business_logic_with_tracing()
        assert result == "business logic completed"
