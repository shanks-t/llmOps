#!/usr/bin/env python3
"""Validate that Phoenix and MLflow backends are ready to receive telemetry."""

from __future__ import annotations

import sys
import time
from typing import Any

try:
    import requests
except ImportError:
    print("❌ requests library not installed")
    print("   Run: pip install requests")
    sys.exit(1)


def check_health(name: str, url: str) -> bool:
    """Check if backend health endpoint is responding.

    Args:
        name: Backend name for display.
        url: Health check URL.

    Returns:
        True if backend is healthy, False otherwise.
    """
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} is healthy: {url}")
            return True
        else:
            print(f"❌ {name} returned status {response.status_code}: {url}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name} is not reachable: {url}")
        print(f"   Is the container running? Try: docker-compose ps")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ {name} request timed out: {url}")
        return False
    except Exception as e:
        print(f"❌ {name} check failed: {e}")
        return False


def check_otlp_endpoint(name: str, url: str) -> bool:
    """Check if OTLP endpoint is accessible.

    Args:
        name: Backend name for display.
        url: OTLP traces endpoint.

    Returns:
        True if endpoint is accessible, False otherwise.

    Note:
        We don't send actual traces, just check if endpoint responds.
    """
    try:
        # Try to send empty POST (should get 400/415, not connection error)
        response = requests.post(url, timeout=5, headers={"Content-Type": "application/json"})

        # Any response means endpoint is listening (even errors)
        if response.status_code in (200, 400, 415, 405):
            print(f"✅ {name} OTLP endpoint is accessible: {url}")
            return True
        else:
            print(f"⚠️  {name} OTLP endpoint returned unexpected status {response.status_code}")
            return True  # Still accessible, just unexpected response

    except requests.exceptions.ConnectionError:
        print(f"❌ {name} OTLP endpoint is not reachable: {url}")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ {name} OTLP endpoint timed out: {url}")
        return False
    except Exception as e:
        print(f"❌ {name} OTLP check failed: {e}")
        return False


def check_docker_running() -> bool:
    """Check if Docker containers are running.

    Returns:
        True if containers are running, False otherwise.
    """
    try:
        import subprocess

        result = subprocess.run(
            ["docker", "ps", "--filter", "name=phoenix", "--filter", "name=mlflow", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        containers = result.stdout.strip().split("\n")
        containers = [c for c in containers if c]  # Remove empty strings

        if not containers:
            print("❌ No backend containers running")
            print("   Start backends with: cd docker && docker-compose up -d")
            return False

        print(f"✅ Found running containers: {', '.join(containers)}")
        return True

    except FileNotFoundError:
        print("❌ Docker not found. Is Docker Desktop installed?")
        return False
    except Exception as e:
        print(f"⚠️  Could not check Docker containers: {e}")
        return True  # Don't fail if we can't check Docker


def main() -> int:
    """Run all validation checks.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    print("=" * 70)
    print("Backend Validation - Phoenix & MLflow")
    print("=" * 70)
    print()

    all_checks_passed = True

    # Check 1: Docker containers
    print("📦 Checking Docker containers...")
    docker_ok = check_docker_running()
    print()

    if not docker_ok:
        return 1

    # Give containers a moment to fully start
    print("⏳ Waiting for backends to initialize...")
    time.sleep(2)
    print()

    # Check 2: Phoenix health
    print("🔍 Checking Phoenix backend...")
    phoenix_health = check_health("Phoenix", "http://localhost:6006/healthz")
    phoenix_otlp = check_otlp_endpoint("Phoenix", "http://localhost:6006/v1/traces")
    print()

    if not (phoenix_health and phoenix_otlp):
        all_checks_passed = False

    # Check 3: MLflow health
    print("🔍 Checking MLflow backend...")
    mlflow_health = check_health("MLflow", "http://localhost:5001/health")
    mlflow_otlp = check_otlp_endpoint("MLflow", "http://localhost:5001/v1/traces")
    print()

    if not (mlflow_health and mlflow_otlp):
        all_checks_passed = False

    # Summary
    print("=" * 70)
    if all_checks_passed:
        print("✅ All checks passed! Backends are ready to receive telemetry.")
        print()
        print("Access UIs:")
        print("  - Phoenix: http://localhost:6006")
        print("  - MLflow:  http://localhost:5001")
        print()
        return 0
    else:
        print("❌ Some checks failed. See errors above.")
        print()
        print("Troubleshooting:")
        print("  1. Check containers: docker-compose ps")
        print("  2. View logs: docker-compose logs -f")
        print("  3. Restart: docker-compose restart")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
