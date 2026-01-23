"""Contract tests for lazy-loading platform modules — PRD_01.

Executable contracts derived from:
- PRD: docs/prd/PRD_01.md
- API: docs/api_spec/API_SPEC_01.md

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

# Traceability metadata
PRD_ID = "PRD_01"
API_SPEC_ID = "API_SPEC_01"
CAPABILITY = "lazy_loading"


class TestLazyLoading:
    """Tests for lazy platform module loading."""

    def test_import_llmops_does_not_import_platform_deps(self) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.__getattr__

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
        PRD: PRD_01
        API: API_SPEC_01.llmops.__getattr__

        GIVEN the SDK is imported
        WHEN llmops.arize is accessed
        THEN the arize platform module is loaded
        """
        import llmops

        arize_module = getattr(llmops, "arize")
        assert "llmops.arize" in sys.modules
        assert arize_module is not None


class TestDependencyErrors:
    """Tests for helpful ImportError messages when deps are missing."""

    def test_missing_arize_deps_raise_helpful_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.llmops.arize.instrument()

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
        PRD: PRD_01
        API: API_SPEC_01.llmops.mlflow.instrument()

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
