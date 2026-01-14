"""E2E test fixtures requiring Docker services.

These fixtures handle:
- Service health checking
- Test-specific endpoints (different ports than dev)
- YAML config generation for E2E tests
"""

import os
import time

import pytest
import httpx


# =============================================================================
# E2E Test Endpoints
# =============================================================================
# Uses different ports than dev environment to allow parallel usage:
# - Phoenix: 16006 (dev uses 6006)
# - MLflow: 15001 (dev uses 5001)

PHOENIX_TEST_ENDPOINT = os.environ.get(
    "PHOENIX_TEST_ENDPOINT", "http://localhost:16006/v1/traces"
)
PHOENIX_TEST_BASE = os.environ.get(
    "PHOENIX_TEST_BASE", "http://localhost:16006"
)
MLFLOW_TEST_ENDPOINT = os.environ.get(
    "MLFLOW_TEST_ENDPOINT", "http://localhost:15001"
)


# =============================================================================
# Service Health Check Fixtures
# =============================================================================


def _wait_for_service(name: str, health_url: str, max_retries: int = 30, delay: int = 2):
    """Wait for a service to become healthy."""
    for i in range(max_retries):
        try:
            response = httpx.get(health_url, timeout=5)
            if response.status_code == 200:
                print(f"{name} is healthy at {health_url}")
                return True
        except httpx.RequestError:
            pass

        if i < max_retries - 1:
            time.sleep(delay)

    return False


@pytest.fixture(scope="session")
def docker_services_up():
    """Ensure Docker services are running for E2E tests.

    This fixture is session-scoped to avoid restarting containers
    between tests. If services are not available, tests are skipped.
    """
    phoenix_health = f"{PHOENIX_TEST_BASE}/healthz"
    mlflow_health = f"{MLFLOW_TEST_ENDPOINT}/health"

    services = [
        ("Phoenix", phoenix_health),
        ("MLflow", mlflow_health),
    ]

    for service_name, health_url in services:
        if not _wait_for_service(service_name, health_url):
            pytest.skip(
                f"{service_name} not available at {health_url}. "
                f"Start services with: docker-compose -f docker/docker-compose.test.yml up -d"
            )

    yield


@pytest.fixture
def phoenix_available(docker_services_up):
    """Check that Phoenix is available for tests."""
    return True


@pytest.fixture
def mlflow_available(docker_services_up):
    """Check that MLflow is available for tests."""
    return True


# =============================================================================
# Endpoint Fixtures
# =============================================================================


@pytest.fixture
def phoenix_e2e_endpoint(docker_services_up):
    """Provide Phoenix OTLP endpoint for E2E tests."""
    return PHOENIX_TEST_ENDPOINT


@pytest.fixture
def phoenix_e2e_base(docker_services_up):
    """Provide Phoenix base URL for E2E tests."""
    return PHOENIX_TEST_BASE


@pytest.fixture
def mlflow_e2e_endpoint(docker_services_up):
    """Provide MLflow endpoint for E2E tests."""
    return MLFLOW_TEST_ENDPOINT


# =============================================================================
# YAML Config Fixtures
# =============================================================================


@pytest.fixture
def e2e_config_yaml_phoenix(tmp_path, phoenix_e2e_endpoint):
    """Create YAML config for Phoenix E2E tests."""
    config_file = tmp_path / "llmops.yaml"
    config_file.write_text(
        f"""
service:
  name: e2e-test-service

backend: phoenix

phoenix:
  endpoint: {phoenix_e2e_endpoint}
"""
    )
    return str(config_file)


@pytest.fixture
def e2e_config_yaml_mlflow(tmp_path, mlflow_e2e_endpoint):
    """Create YAML config for MLflow E2E tests."""
    config_file = tmp_path / "llmops.yaml"
    config_file.write_text(
        f"""
service:
  name: e2e-test-service

backend: mlflow

mlflow:
  tracking_uri: {mlflow_e2e_endpoint}
"""
    )
    return str(config_file)


# =============================================================================
# Cleanup Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_llmops_for_e2e():
    """Reset llmops state before and after each E2E test."""
    import llmops

    if llmops.is_configured():
        llmops.shutdown()

    yield

    if llmops.is_configured():
        llmops.shutdown()
