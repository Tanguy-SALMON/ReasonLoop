#!/usr/bin/env python3
"""
Integration Test Script for ReasonLoop <-> be-campaign Communication

This script tests the complete integration flow:
1. ReasonLoop internal API authentication
2. Website intelligence analysis
3. SSRF protection (localhost rejection)
4. Error handling when ReasonLoop is down

Prerequisites:
    - Set INTERNAL_SERVICE_SECRET in environment
    - ReasonLoop running on port 8001 (for full tests)

Usage:
    # Run all tests (requires ReasonLoop to be running)
    python scripts/test_integration.py

    # Run with mock mode (no external services required)
    python scripts/test_integration.py --mock

    # Run specific test
    python scripts/test_integration.py --test auth
"""

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx

# Test configuration
REASONLOOP_URL = os.getenv("REASONLOOP_URL", "http://localhost:8001")
INTERNAL_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "test-secret-key-12345")
API_PREFIX = "/api/v1"


@dataclass
class TestResult:
    """Result of a single test"""

    name: str
    passed: bool
    message: str
    duration_ms: float = 0


class IntegrationTester:
    """
    Integration test runner for ReasonLoop service.

    Tests:
    1. Health check (public)
    2. Internal health check (requires auth)
    3. Authentication rejection (missing header)
    4. Authentication rejection (wrong secret)
    5. SSRF protection (localhost rejection)
    6. Website analysis (requires running service)
    """

    def __init__(self, base_url: str, secret: str):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.results: list[TestResult] = []

    @property
    def internal_endpoint(self) -> str:
        return f"{self.base_url}{API_PREFIX}/internal/v1"

    @property
    def public_endpoint(self) -> str:
        return f"{self.base_url}{API_PREFIX}"

    def _get_headers(
        self, include_secret: bool = True, wrong_secret: bool = False
    ) -> dict:
        """Build request headers"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if include_secret:
            headers["X-Internal-Secret"] = (
                "wrong-secret" if wrong_secret else self.secret
            )
        return headers

    async def run_all_tests(self, mock_mode: bool = False) -> bool:
        """Run all integration tests"""
        print("\n" + "=" * 70)
        print("ReasonLoop Integration Tests")
        print("=" * 70)
        print(f"Target: {self.base_url}")
        print(f"Secret: {'*' * (len(self.secret) - 4)}{self.secret[-4:]}")
        print(f"Mode: {'MOCK' if mock_mode else 'LIVE'}")
        print("=" * 70 + "\n")

        # Run tests
        await self.test_public_health()
        await self.test_internal_health_with_auth()
        await self.test_auth_missing_header()
        await self.test_auth_wrong_secret()
        await self.test_ssrf_localhost_rejection()

        if not mock_mode:
            await self.test_website_analysis()
            await self.test_website_analysis_cached()

        # Print results
        self._print_results()

        # Return overall status
        failed = sum(1 for r in self.results if not r.passed)
        return failed == 0

    async def test_public_health(self) -> TestResult:
        """Test 1: Public health endpoint should be accessible without auth"""
        import time

        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.public_endpoint}/health")

                if response.status_code == 200:
                    result = TestResult(
                        name="Public Health Check",
                        passed=True,
                        message=f"Status: {response.status_code}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                else:
                    result = TestResult(
                        name="Public Health Check",
                        passed=False,
                        message=f"Expected 200, got {response.status_code}",
                        duration_ms=(time.time() - start) * 1000,
                    )
        except httpx.ConnectError:
            result = TestResult(
                name="Public Health Check",
                passed=False,
                message=f"Connection refused - is ReasonLoop running on {self.base_url}?",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            result = TestResult(
                name="Public Health Check",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

        self.results.append(result)
        return result

    async def test_internal_health_with_auth(self) -> TestResult:
        """Test 2: Internal health endpoint with valid auth"""
        import time

        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.internal_endpoint}/health",
                    headers=self._get_headers(include_secret=True),
                )

                if response.status_code == 200:
                    data = response.json()
                    result = TestResult(
                        name="Internal Health (with auth)",
                        passed=True,
                        message=f"Service: {data.get('service', 'unknown')}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                else:
                    result = TestResult(
                        name="Internal Health (with auth)",
                        passed=False,
                        message=f"Expected 200, got {response.status_code}",
                        duration_ms=(time.time() - start) * 1000,
                    )
        except httpx.ConnectError:
            result = TestResult(
                name="Internal Health (with auth)",
                passed=False,
                message="Connection refused",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            result = TestResult(
                name="Internal Health (with auth)",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

        self.results.append(result)
        return result

    async def test_auth_missing_header(self) -> TestResult:
        """Test 3: Internal endpoint should reject missing X-Internal-Secret"""
        import time

        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.internal_endpoint}/health",
                    headers=self._get_headers(include_secret=False),
                )

                if response.status_code == 403:
                    result = TestResult(
                        name="Auth: Missing Header (expect 403)",
                        passed=True,
                        message="Correctly rejected with 403",
                        duration_ms=(time.time() - start) * 1000,
                    )
                else:
                    result = TestResult(
                        name="Auth: Missing Header (expect 403)",
                        passed=False,
                        message=f"Expected 403, got {response.status_code}",
                        duration_ms=(time.time() - start) * 1000,
                    )
        except httpx.ConnectError:
            result = TestResult(
                name="Auth: Missing Header (expect 403)",
                passed=False,
                message="Connection refused",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            result = TestResult(
                name="Auth: Missing Header (expect 403)",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

        self.results.append(result)
        return result

    async def test_auth_wrong_secret(self) -> TestResult:
        """Test 4: Internal endpoint should reject wrong secret"""
        import time

        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.internal_endpoint}/health",
                    headers=self._get_headers(include_secret=True, wrong_secret=True),
                )

                if response.status_code == 403:
                    result = TestResult(
                        name="Auth: Wrong Secret (expect 403)",
                        passed=True,
                        message="Correctly rejected with 403",
                        duration_ms=(time.time() - start) * 1000,
                    )
                else:
                    result = TestResult(
                        name="Auth: Wrong Secret (expect 403)",
                        passed=False,
                        message=f"Expected 403, got {response.status_code}",
                        duration_ms=(time.time() - start) * 1000,
                    )
        except httpx.ConnectError:
            result = TestResult(
                name="Auth: Wrong Secret (expect 403)",
                passed=False,
                message="Connection refused",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            result = TestResult(
                name="Auth: Wrong Secret (expect 403)",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

        self.results.append(result)
        return result

    async def test_ssrf_localhost_rejection(self) -> TestResult:
        """Test 5: Analyze endpoint should reject localhost URLs"""
        import time

        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.internal_endpoint}/analyze",
                    headers=self._get_headers(),
                    json={"url": "http://localhost:8080/admin", "force_refresh": True},
                )

                if response.status_code == 400:
                    result = TestResult(
                        name="SSRF: Localhost Rejection (expect 400)",
                        passed=True,
                        message="Correctly rejected localhost URL",
                        duration_ms=(time.time() - start) * 1000,
                    )
                else:
                    result = TestResult(
                        name="SSRF: Localhost Rejection (expect 400)",
                        passed=False,
                        message=f"Expected 400, got {response.status_code}",
                        duration_ms=(time.time() - start) * 1000,
                    )
        except httpx.ConnectError:
            result = TestResult(
                name="SSRF: Localhost Rejection (expect 400)",
                passed=False,
                message="Connection refused",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            result = TestResult(
                name="SSRF: Localhost Rejection (expect 400)",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

        self.results.append(result)
        return result

    async def test_website_analysis(self) -> TestResult:
        """Test 6: Full website analysis (slow, requires network)"""
        import time

        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.internal_endpoint}/analyze",
                    headers=self._get_headers(),
                    json={
                        "url": "https://httpbin.org/html",  # Simple test page
                        "force_refresh": True,
                    },
                )

                duration = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "unknown")
                    result = TestResult(
                        name="Website Analysis (httpbin.org)",
                        passed=status in ("success", "cached"),
                        message=f"Status: {status}, Time: {duration:.0f}ms",
                        duration_ms=duration,
                    )
                else:
                    result = TestResult(
                        name="Website Analysis (httpbin.org)",
                        passed=False,
                        message=f"Status {response.status_code}: {response.text[:100]}",
                        duration_ms=duration,
                    )
        except httpx.TimeoutException:
            result = TestResult(
                name="Website Analysis (httpbin.org)",
                passed=False,
                message="Request timed out after 60s",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            result = TestResult(
                name="Website Analysis (httpbin.org)",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

        self.results.append(result)
        return result

    async def test_website_analysis_cached(self) -> TestResult:
        """Test 7: Cached analysis should be fast"""
        import time

        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.internal_endpoint}/analyze",
                    headers=self._get_headers(),
                    json={
                        "url": "https://httpbin.org/html",
                        "force_refresh": False,  # Use cache
                    },
                )

                duration = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    is_cached = data.get("cached", False)
                    result = TestResult(
                        name="Cached Analysis (should be fast)",
                        passed=is_cached and duration < 1000,
                        message=f"Cached: {is_cached}, Time: {duration:.0f}ms",
                        duration_ms=duration,
                    )
                else:
                    result = TestResult(
                        name="Cached Analysis (should be fast)",
                        passed=False,
                        message=f"Status {response.status_code}",
                        duration_ms=duration,
                    )
        except Exception as e:
            result = TestResult(
                name="Cached Analysis (should be fast)",
                passed=False,
                message=f"Error: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

        self.results.append(result)
        return result

    def _print_results(self) -> None:
        """Print formatted test results"""
        print("\n" + "-" * 70)
        print("Test Results")
        print("-" * 70)

        for result in self.results:
            icon = "✓" if result.passed else "✗"
            status = "PASS" if result.passed else "FAIL"
            print(f"{icon} [{status}] {result.name}")
            print(f"         {result.message} ({result.duration_ms:.0f}ms)")

        print("-" * 70)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"\nTotal: {passed}/{total} passed, {failed} failed")

        if failed > 0:
            print("\n⚠️  Some tests failed. Check configuration:")
            print(
                f"   - INTERNAL_SERVICE_SECRET is set: {bool(os.getenv('INTERNAL_SERVICE_SECRET'))}"
            )
            print(f"   - ReasonLoop URL: {self.base_url}")
            print("   - Is ReasonLoop running? Try: poetry run python -m api.main")


async def main():
    parser = argparse.ArgumentParser(description="ReasonLoop Integration Tests")
    parser.add_argument(
        "--mock", action="store_true", help="Run in mock mode (skip live tests)"
    )
    parser.add_argument("--url", default=REASONLOOP_URL, help="ReasonLoop URL")
    parser.add_argument(
        "--secret", default=INTERNAL_SECRET, help="Internal service secret"
    )
    args = parser.parse_args()

    tester = IntegrationTester(args.url, args.secret)
    success = await tester.run_all_tests(mock_mode=args.mock)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
