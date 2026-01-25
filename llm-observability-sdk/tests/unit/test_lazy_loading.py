"""Unit tests for lazy-loading platform modules.

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
class TestLazyLoading:
    """Tests for lazy platform module loading.

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

    def test_accessing_platform_attribute_imports_module(self) -> None:
        """
        PRD: PRD_01, Requirement: F5

        GIVEN the SDK is imported
        WHEN llmops.arize is accessed
        THEN the arize platform module is loaded
        """
        import llmops

        arize_module = getattr(llmops, "arize")
        assert "llmops.arize" in sys.modules
        assert arize_module is not None


@pytest.mark.unit
class TestDependencyErrors:
    """Tests for helpful ImportError messages when deps are missing.

    PRD: PRD_01, Requirements: F11, N7
    """

    def test_missing_arize_deps_raise_helpful_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F11

        GIVEN arize.otel is not installed
        WHEN llmops.arize.instrument() is called
        THEN ImportError includes the install hint
        """
        import builtins
        import llmops

        original_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "arize.otel":
                raise ImportError("No module named arize.otel")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(ImportError, match=r"pip install llmops\[arize\]"):
            getattr(llmops, "arize").instrument()

    def test_missing_mlflow_deps_raise_helpful_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01, Requirement: F11

        GIVEN mlflow is not installed
        WHEN llmops.mlflow.instrument() is called
        THEN ImportError includes the install hint
        """
        import builtins
        import llmops

        original_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "mlflow":
                raise ImportError("No module named mlflow")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(ImportError, match=r"pip install llmops\[mlflow\]"):
            getattr(llmops, "mlflow").instrument()
