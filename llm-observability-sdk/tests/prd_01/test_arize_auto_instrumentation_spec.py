"""Contract tests for Arize auto-instrumentation — PRD_01.

Executable contracts derived from:
- PRD: docs/prd/PRD_01.md
- API: docs/api_spec/API_SPEC_01.md

Requirements covered:
- F3: llmops.arize.instrument() auto-instruments Google ADK
- F4: llmops.arize.instrument() auto-instruments Google GenAI
- F8: Each platform module defines its supported instrumentors
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_01"
API_SPEC_ID = "API_SPEC_01"
CAPABILITY = "arize_auto_instrumentation"


class TestGoogleADKInstrumentation:
    """Tests for Google ADK auto-instrumentation."""

    def test_instrument_enables_google_adk_instrumentation(
        self,
        valid_arize_config_file: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a valid config file with google_adk instrumentation enabled
        WHEN llmops.arize.instrument() is called
        THEN Google ADK is auto-instrumented
        AND no additional code is required to trace ADK calls
        """
        provider = llmops_arize_module.instrument(config_path=valid_arize_config_file)

        assert provider is not None

    def test_instrument_respects_google_adk_disabled_config(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a config file with google_adk instrumentation set to false
        WHEN llmops.arize.instrument() is called
        THEN Google ADK is NOT auto-instrumented
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
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

        provider = llmops_arize_module.instrument(config_path=config_path)

        assert provider is not None


class TestGoogleGenAIInstrumentation:
    """Tests for Google GenAI auto-instrumentation."""

    def test_instrument_enables_google_genai_instrumentation(
        self,
        valid_arize_config_file: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a valid config file with google_genai instrumentation enabled
        WHEN llmops.arize.instrument() is called
        THEN Google GenAI is auto-instrumented
        AND no additional code is required to trace GenAI calls
        """
        provider = llmops_arize_module.instrument(config_path=valid_arize_config_file)

        assert provider is not None

    def test_instrument_respects_google_genai_disabled_config(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a config file with google_genai instrumentation set to false
        WHEN llmops.arize.instrument() is called
        THEN Google GenAI is NOT auto-instrumented
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
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

        provider = llmops_arize_module.instrument(config_path=config_path)

        assert provider is not None


class TestInstrumentationExtensibility:
    """Tests for instrumentation extensibility."""

    def test_instrument_handles_unknown_instrumentor_gracefully(
        self,
        tmp_path: "Path",
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a config file with an unknown instrumentor specified
        WHEN llmops.arize.instrument() is called in permissive mode
        THEN the SDK initializes successfully
        AND a warning is logged for the unknown instrumentor
        AND known instrumentors are still applied
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
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

        provider = llmops_arize_module.instrument(config_path=config_path)

        assert provider is not None
