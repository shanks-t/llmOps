#!/usr/bin/env python3
"""Validate that observability backends are running and healthy."""

import sys
import urllib.request
import urllib.error


def check_endpoint(name: str, url: str, expected_status: int = 200) -> bool:
    """Check if an endpoint is accessible."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == expected_status:
                print(f"  {name}: {url}")
                return True
            else:
                print(f"  {name}: unexpected status {response.status}")
                return False
    except urllib.error.HTTPError as e:
        # Some endpoints return errors without payload - that's OK
        if e.code in (405, 415, 422):
            print(f"  {name}: {url} (endpoint active)")
            return True
        print(f"  {name}: HTTP {e.code}")
        return False
    except urllib.error.URLError as e:
        print(f"  {name}: connection failed - {e.reason}")
        return False
    except Exception as e:
        print(f"  {name}: {e}")
        return False


def check_otlp_endpoint(name: str, url: str) -> bool:
    """Check if OTLP endpoint accepts POST."""
    try:
        req = urllib.request.Request(url, method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"  {name}: {url}")
            return True
    except urllib.error.HTTPError as e:
        # 415 (Unsupported Media Type) or 422 (Unprocessable) means endpoint is listening
        if e.code in (400, 415, 422):
            print(f"  {name}: {url} (endpoint active)")
            return True
        print(f"  {name}: HTTP {e.code}")
        return False
    except urllib.error.URLError as e:
        print(f"  {name}: connection failed - {e.reason}")
        return False
    except Exception as e:
        print(f"  {name}: {e}")
        return False


def main():
    print("Validating observability backends...\n")

    all_ok = True

    # Phoenix checks
    print("Phoenix (Arize):")
    if not check_endpoint("Health", "http://localhost:6006/healthz"):
        all_ok = False
    if not check_otlp_endpoint("OTLP", "http://localhost:6006/v1/traces"):
        all_ok = False
    print()

    # MLflow checks
    print("MLflow:")
    if not check_endpoint("Health", "http://localhost:5001/health"):
        all_ok = False
    if not check_otlp_endpoint("OTLP", "http://localhost:5001/v1/traces"):
        all_ok = False
    print()

    if all_ok:
        print("All backends are healthy!")
        return 0
    else:
        print("Some backends are not responding. Check docker-compose logs.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
