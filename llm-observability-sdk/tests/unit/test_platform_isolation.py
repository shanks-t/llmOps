"""Unit tests for platform isolation.

Tests derived from PRD_01.

Requirements covered:
- F9: Config schema includes platform-specific sections
- F12: Platforms share config loading and validation infrastructure
- F13: Future platforms can be added without core changes
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.unit
class TestPlatformIsolation:
    """Tests for platform-specific config section handling.

    PRD: PRD_01, Requirements: F9, F12, F13
    """

    def test_arize_platform_ignores_mlflow_section(
        self,
        tmp_path: "Path",
        valid_arize_config_with_mlflow_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F9, F12

        GIVEN a config file contains both arize and mlflow sections
        WHEN llmops.instrument() is called with platform: arize
        THEN Arize initializes successfully using only the arize section
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(valid_arize_config_with_mlflow_content)

        llmops_module.instrument(config=config_path)

        assert llmops_module.is_configured()

    def test_mlflow_platform_ignores_arize_section(
        self,
        tmp_path: "Path",
        valid_mlflow_config_with_arize_content: str,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F9, F12

        GIVEN a config file contains both mlflow and arize sections
        WHEN llmops.instrument() is called with platform: mlflow
        THEN MLflow initializes successfully using only the mlflow section
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(valid_mlflow_config_with_arize_content)

        llmops_module.instrument(config=config_path)

        assert llmops_module.is_configured()
