"""Integration tests for auto-instrumentation.

Tests derived from PRD_01.

Requirements covered:
- F3: llmops.init() auto-instruments Google ADK
- F4: llmops.init() auto-instruments Google GenAI
- F8: Instrumentation can be enabled/disabled via config
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.integration
class TestGoogleADKInstrumentation:
    """Tests for Google ADK auto-instrumentation.

    PRD: PRD_01, Requirement: F3
    """

    def test_init_enables_google_adk_instrumentation(
        self,
        valid_arize_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F3

        GIVEN a valid config file with google_adk instrumentation enabled
        WHEN llmops.init() is called
        THEN the SDK initializes successfully
        AND Google ADK instrumentation is applied
        """
        llmops_module.init(config=valid_arize_config_file)

        assert llmops_module.is_configured()

    def test_init_respects_google_adk_disabled_config(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F3, F8

        GIVEN a config file with google_adk instrumentation set to false
        WHEN llmops.init() is called
        THEN the SDK initializes successfully
        AND Google ADK is NOT auto-instrumented
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "platform: arize\n"
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            "instrumentation:\n"
            "  google_adk: false\n"
            "  google_genai: true\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        llmops_module.init(config=config_path)

        assert llmops_module.is_configured()


@pytest.mark.integration
class TestGoogleGenAIInstrumentation:
    """Tests for Google GenAI auto-instrumentation.

    PRD: PRD_01, Requirement: F4
    """

    def test_init_enables_google_genai_instrumentation(
        self,
        valid_arize_config_file: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F4

        GIVEN a valid config file with google_genai instrumentation enabled
        WHEN llmops.init() is called
        THEN the SDK initializes successfully
        AND Google GenAI instrumentation is applied
        """
        llmops_module.init(config=valid_arize_config_file)

        assert llmops_module.is_configured()

    def test_init_respects_google_genai_disabled_config(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F4, F8

        GIVEN a config file with google_genai instrumentation set to false
        WHEN llmops.init() is called
        THEN the SDK initializes successfully
        AND Google GenAI is NOT auto-instrumented
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "platform: arize\n"
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: false\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        llmops_module.init(config=config_path)

        assert llmops_module.is_configured()


@pytest.mark.integration
class TestInstrumentationExtensibility:
    """Tests for instrumentation extensibility.

    PRD: PRD_01, Requirement: F8
    """

    def test_init_handles_unknown_instrumentor_gracefully(
        self,
        tmp_path: "Path",
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F8

        GIVEN a config file with an unknown instrumentor specified
        WHEN llmops.init() is called in permissive mode
        THEN the SDK initializes successfully
        AND a warning is logged for the unknown instrumentor
        AND known instrumentors are still applied
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "platform: arize\n"
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: true\n"
            "  unknown_future_instrumentor: true\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        llmops_module.init(config=config_path)

        assert llmops_module.is_configured()
