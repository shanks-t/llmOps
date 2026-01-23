"""Contract tests for platform isolation — PRD_01.

Executable contracts derived from:
- PRD: docs/prd/PRD_01.md
- API: docs/api_spec/API_SPEC_01.md

Requirements covered:
- F9: Config schema includes platform-specific sections
- F12: Platforms share config loading and validation infrastructure
- F13: Future platforms can be added without core changes
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_01"
API_SPEC_ID = "API_SPEC_01"
CAPABILITY = "platform_isolation"


class TestPlatformIsolation:
    """Tests for platform-specific config section handling."""

    def test_arize_ignores_mlflow_section(
        self,
        tmp_path: "Path",
        valid_arize_config_with_mlflow_content: str,
        llmops_arize_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

        GIVEN a config file contains both arize and mlflow sections
        WHEN llmops.arize.instrument() is called
        THEN Arize initializes successfully using only the arize section
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(valid_arize_config_with_mlflow_content)

        provider = llmops_arize_module.instrument(config_path=config_path)

        assert provider is not None

    def test_mlflow_ignores_arize_section(
        self,
        tmp_path: "Path",
        valid_mlflow_config_with_arize_content: str,
        llmops_mlflow_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

        GIVEN a config file contains both mlflow and arize sections
        WHEN llmops.mlflow.instrument() is called
        THEN MLflow initializes successfully using only the mlflow section
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(valid_mlflow_config_with_arize_content)

        provider = llmops_mlflow_module.instrument(config_path=config_path)

        assert provider is not None
