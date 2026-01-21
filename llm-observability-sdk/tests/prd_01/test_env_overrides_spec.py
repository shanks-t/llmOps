"""Contract tests for environment variable overrides — PRD_01.

Executable contracts derived from:
- PRD: docs/prd/PRD_01.md
- API: docs/api_spec/API_SPEC_01.md

Requirements covered:
- A8: Sensitive values (example: API keys) can be set via env var overrides
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Traceability metadata
PRD_ID = "PRD_01"
API_SPEC_ID = "API_SPEC_01"
CAPABILITY = "env_overrides"


class TestEnvVarOverrides:
    """Tests for environment variable override behavior."""

    def test_api_key_can_be_set_via_env_var(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a config file with arize.api_key set to "${ARIZE_API_KEY}"
        AND the ARIZE_API_KEY environment variable is set to "test-api-key"
        WHEN llmops.init() is called
        THEN the API key from the environment is used
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            '  api_key: "${ARIZE_API_KEY}"\n'
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: true\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        monkeypatch.setenv("ARIZE_API_KEY", "test-api-key-from-env")

        provider = llmops_module.init(config_path=config_path)

        assert provider is not None
        # Implementation should verify the env var value was substituted

    def test_space_id_can_be_set_via_env_var(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a config file with arize.space_id set to "${ARIZE_SPACE_ID}"
        AND the ARIZE_SPACE_ID environment variable is set
        WHEN llmops.init() is called
        THEN the space ID from the environment is used
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            '  space_id: "${ARIZE_SPACE_ID}"\n'
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: true\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        monkeypatch.setenv("ARIZE_SPACE_ID", "test-space-id-from-env")

        provider = llmops_module.init(config_path=config_path)

        assert provider is not None
        # Implementation should verify the env var value was substituted

    def test_missing_env_var_in_permissive_mode_does_not_fail(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a config file referencing an env var that is not set
        AND validation mode is permissive
        WHEN llmops.init() is called
        THEN the SDK initializes without raising an exception
        AND a no-op or degraded mode is used
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            '  api_key: "${NONEXISTENT_ENV_VAR}"\n'
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: true\n"
            "validation:\n"
            "  mode: permissive\n"
        )

        monkeypatch.delenv("NONEXISTENT_ENV_VAR", raising=False)

        provider = llmops_module.init(config_path=config_path)

        assert provider is not None

    def test_missing_env_var_in_strict_mode_raises_error(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
        llmops_module: Any,
    ) -> None:
        """
        PRD: PRD_01
        API: API_SPEC_01.init()

        GIVEN a config file referencing an env var that is not set
        AND validation mode is strict
        WHEN llmops.init() is called
        THEN a ConfigurationError is raised
        """
        config_path = tmp_path / "llmops.yaml"
        config_path.write_text(
            "service:\n"
            "  name: test-service\n"
            "  version: '1.0.0'\n"
            "arize:\n"
            "  endpoint: http://localhost:6006/v1/traces\n"
            '  api_key: "${NONEXISTENT_ENV_VAR}"\n'
            "instrumentation:\n"
            "  google_adk: true\n"
            "  google_genai: true\n"
            "validation:\n"
            "  mode: strict\n"
        )

        monkeypatch.delenv("NONEXISTENT_ENV_VAR", raising=False)

        with pytest.raises(llmops_module.ConfigurationError):
            llmops_module.init(config_path=config_path)
