"""Tests for llmops.configure()."""

import pytest
import llmops
from llmops import ConfigurationError


class TestConfigure:
    """Tests for the configure() function."""

    def test_configure_requires_backend_and_endpoint(self):
        """configure() should raise if backend provided without endpoint."""
        with pytest.raises(ConfigurationError, match="Must provide either"):
            llmops.configure(backend="phoenix", endpoint="")

    def test_configure_unknown_backend_raises(self):
        """configure() should raise for unknown backend."""
        with pytest.raises(ConfigurationError, match="Unknown backend"):
            llmops.configure(backend="unknown", endpoint="http://localhost:9999")

    def test_configure_phoenix_succeeds(self):
        """configure() should succeed with phoenix backend."""
        llmops.configure(
            backend="phoenix",
            endpoint="http://localhost:6006/v1/traces",
            service_name="test",
        )
        llmops.shutdown()

    def test_configure_mlflow_succeeds(self):
        """configure() should succeed with mlflow backend."""
        pytest.importorskip("mlflow")
        llmops.configure(
            backend="mlflow",
            endpoint="http://localhost:5001",
            service_name="test",
        )
        llmops.shutdown()

    def test_configure_multi_backend_succeeds(self):
        """configure() should succeed with multiple backends."""
        pytest.importorskip("mlflow")
        llmops.configure(
            backends=[
                {"type": "phoenix", "endpoint": "http://localhost:6006/v1/traces"},
                {"type": "mlflow", "endpoint": "http://localhost:5001"},
            ],
            service_name="test-multi",
        )
        llmops.shutdown()

    def test_configure_backends_requires_type(self):
        """configure() should raise if backend config missing type."""
        with pytest.raises(ConfigurationError, match="must have a 'type'"):
            llmops.configure(
                backends=[{"endpoint": "http://localhost:6006/v1/traces"}],
                service_name="test",
            )

    def test_configure_backends_requires_endpoint(self):
        """configure() should raise if backend config missing endpoint."""
        with pytest.raises(ConfigurationError, match="requires an 'endpoint'"):
            llmops.configure(
                backends=[{"type": "phoenix"}],
                service_name="test",
            )
