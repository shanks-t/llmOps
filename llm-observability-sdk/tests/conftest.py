"""Shared pytest configuration and fixtures for contract tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def reset_llmops_state() -> Generator[None, None, None]:
    """Reset llmops module state between tests.

    This fixture runs automatically before each test to ensure
    clean state for initialization tests.
    """
    yield
    # Cleanup after test
    try:
        import llmops

        shutdown = getattr(llmops, "shutdown", None)
        if callable(shutdown):
            shutdown()
    except (ImportError, ModuleNotFoundError):
        pass


@pytest.fixture
def valid_config_content() -> str:
    """Return valid YAML config content for tests."""
    return """service:
  name: test-service
  version: "1.0.0"

arize:
  endpoint: http://localhost:6006/v1/traces

instrumentation:
  google_adk: true
  google_genai: true

validation:
  mode: permissive
"""


@pytest.fixture
def valid_config_file(tmp_path: "Path", valid_config_content: str) -> "Path":
    """Create a valid config file and return its path."""
    config_path = tmp_path / "llmops.yaml"
    config_path.write_text(valid_config_content)
    return config_path


@pytest.fixture
def llmops_module() -> Any:
    """Import and return the llmops module."""
    import llmops

    return llmops
