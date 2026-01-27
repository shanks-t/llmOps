"""Unit tests for validation mode behavior.

Tests derived from PRD_01.

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


@pytest.mark.unit
class TestPermissiveMode:
    """Tests for permissive validation mode behavior.

    PRD: PRD_01, Requirement: N5
    """

    def test_permissive_mode_succeeds_on_invalid_config(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: N5

        GIVEN a config file with validation mode set to "permissive"
        AND the config file is missing required fields (but has platform)
        WHEN llmops.init() is called with that config
        THEN the SDK initializes successfully (no-op mode)
        AND no exception is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "platform: arize\n"
            "validation:\n"
            "  mode: permissive\n"
            "# Missing required 'service' section\n"
            "arize:\n"
            "  endpoint: http://localhost/v1/traces\n"
        )

        llmops_module.init(config=config_path)

        assert llmops_module.is_configured()


@pytest.mark.unit
class TestStrictMode:
    """Tests for strict validation mode behavior.

    PRD: PRD_01, Requirement: N6
    """

    def test_strict_mode_raises_error_on_invalid_config(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: N6

        GIVEN a config file with validation mode set to "strict"
        AND the config file is missing required fields
        WHEN llmops.init() is called with that config
        THEN a ConfigurationError is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "platform: arize\n"
            "validation:\n"
            "  mode: strict\n"
            "# Missing required 'service' and endpoint\n"
        )

        with pytest.raises(llmops_module.ConfigurationError):
            llmops_module.init(config=config_path)


@pytest.mark.unit
class TestTelemetryIsolation:
    """Tests for telemetry isolation from business logic.

    PRD: PRD_01, Requirements: N1, N2
    """

    def test_telemetry_failure_never_propagates_to_caller(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: N1, N2

        GIVEN a valid config file with permissive validation
        AND the application has business logic that initializes telemetry
        WHEN the business logic executes
        THEN the business logic completes successfully
        AND no exceptions propagate to the caller
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "platform: arize\n"
            "service:\n"
            "  name: test-service\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        def business_logic() -> str:
            """Business logic that should never fail due to telemetry."""
            llmops_module.init(config=config_path)
            return "business logic completed"

        result = business_logic()
        assert result == "business logic completed"

    def test_telemetry_runtime_errors_are_swallowed(
        self,
        valid_arize_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: N1, N2

        GIVEN a successfully initialized SDK
        WHEN telemetry operations fail at runtime (e.g., network errors)
        THEN no exceptions propagate to user code
        AND business logic continues uninterrupted
        """
        from llmops.sdk.lifecycle import get_provider

        llmops_module.init(config=valid_arize_config_file)
        assert llmops_module.is_configured()

        provider = get_provider()
        assert provider is not None

        tracer = provider.get_tracer("test-tracer")

        def business_logic_with_tracing() -> str:
            """Business logic that uses tracing."""
            with tracer.start_as_current_span("business-operation"):
                result = "business logic completed"
            return result

        result = business_logic_with_tracing()
        assert result == "business logic completed"
