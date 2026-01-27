"""Unit tests for SDK import behavior.

Tests derived from PRD_01.

Requirements covered:
- F5: Platform modules are lazy-imported (no import-time side effects)
- F11: Missing platform dependencies raise helpful ImportError
- N8: Import time for unused platforms is zero
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest


@pytest.mark.unit
class TestImportBehavior:
    """Tests for SDK import behavior.

    PRD: PRD_01, Requirements: F5, N8
    """

    def test_import_llmops_does_not_import_platform_deps(self) -> None:
        """
        PRD: PRD_01, Requirement: F5, N8

        GIVEN the SDK is imported
        WHEN import llmops is executed
        THEN platform dependencies are not imported
        """
        sys.modules.pop("arize.otel", None)
        sys.modules.pop("mlflow", None)

        import llmops

        assert "arize.otel" not in sys.modules
        assert "mlflow" not in sys.modules
        assert isinstance(llmops, ModuleType)

    def test_sdk_exports_expected_api(self) -> None:
        """
        GIVEN the SDK is imported
        WHEN inspecting the module
        THEN expected public API is available
        """
        import llmops

        # Entry points
        assert hasattr(llmops, "init")
        assert hasattr(llmops, "shutdown")
        assert hasattr(llmops, "is_configured")

        # Config types
        assert hasattr(llmops, "Config")
        assert hasattr(llmops, "ServiceConfig")
        assert hasattr(llmops, "ArizeConfig")
        assert hasattr(llmops, "MLflowConfig")

        # Exceptions
        assert hasattr(llmops, "ConfigurationError")


@pytest.mark.unit
@pytest.mark.disable_mock_sdk_telemetry
class TestDependencyErrors:
    """Tests for helpful ImportError messages when deps are missing.

    PRD: PRD_01, Requirements: F11, N7
    """

    def test_missing_arize_deps_raise_helpful_error_in_strict_mode(
        self,
        tmp_path: "Any",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F11

        GIVEN arize.otel is not installed
        AND strict validation mode is enabled
        WHEN llmops.init() is called with arize platform
        THEN ConfigurationError includes the install hint
        """
        import llmops
        from llmops.exporters.arize import exporter as arize_exporter

        # Mock check_dependencies to raise ImportError
        def mock_check_dependencies() -> None:
            raise ImportError(
                "Arize exporter requires 'arize-otel' package.\n"
                "Install with: pip install llmops[arize]"
            )

        monkeypatch.setattr(
            arize_exporter, "check_dependencies", mock_check_dependencies
        )

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "platform: arize\n"
            "service:\n"
            "  name: test-service\n"
            "arize:\n"
            "  endpoint: http://localhost/v1/traces\n"
            "validation:\n"
            "  mode: strict\n"
        )

        with pytest.raises(
            llmops.ConfigurationError, match=r"pip install llmops\[arize\]"
        ):
            llmops.init(config=config_path)

    def test_missing_mlflow_deps_raise_helpful_error_in_strict_mode(
        self,
        tmp_path: "Any",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F11

        GIVEN mlflow is not installed
        AND strict validation mode is enabled
        WHEN llmops.init() is called with mlflow platform
        THEN ConfigurationError includes the install hint
        """
        import llmops
        from llmops.exporters.mlflow import exporter as mlflow_exporter

        # Mock check_dependencies to raise ImportError
        def mock_check_dependencies() -> None:
            raise ImportError(
                "MLflow exporter requires 'mlflow' package.\n"
                "Install with: pip install llmops[mlflow]"
            )

        monkeypatch.setattr(
            mlflow_exporter, "check_dependencies", mock_check_dependencies
        )

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "platform: mlflow\n"
            "service:\n"
            "  name: test-service\n"
            "mlflow:\n"
            "  tracking_uri: http://localhost:5001\n"
            "validation:\n"
            "  mode: strict\n"
        )

        with pytest.raises(
            llmops.ConfigurationError, match=r"pip install llmops\[mlflow\]"
        ):
            llmops.init(config=config_path)
