from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_API_PREFIX = "/api/v1"
DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_EMAIL = "admin@adwafreight.com"
DEFAULT_PASSWORD = "Admin123!"


@dataclass
class CheckResult:
    name: str
    method: str
    path: str
    ok: bool
    status_code: int | None
    duration_ms: float
    detail: str = ""


class SmokeTester:
    def __init__(
        self,
        *,
        base_url: str,
        api_prefix: str,
        organization_id: str,
        email: str,
        password: str,
        timeout: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix.rstrip("/")
        self.organization_id = organization_id
        self.email = email
        self.password = password
        self.timeout = timeout
        self.token: str | None = None

        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def _print(self, message: str) -> None:
        print(message, flush=True)

    def _build_headers(
        self,
        *,
        use_auth: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {"accept": "application/json"}

        if extra_headers:
            headers.update(extra_headers)

        if use_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    def _send_request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        use_auth: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[httpx.Response | None, float, str]:
        started = time.perf_counter()
        try:
            response = self.client.request(
                method=method,
                url=path,
                headers=self._build_headers(use_auth=use_auth, extra_headers=extra_headers),
                json=json_body,
            )
            duration_ms = (time.perf_counter() - started) * 1000
            return response, duration_ms, ""
        except Exception as exc:
            return None, 0.0, f"{exc.__class__.__name__}: {exc}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        expected_status: int = 200,
        json_body: dict[str, Any] | None = None,
        use_auth: bool = True,
        extra_headers: dict[str, str] | None = None,
        name: str | None = None,
    ) -> CheckResult:
        response, duration_ms, error_detail = self._send_request(
            method,
            path,
            json_body=json_body,
            use_auth=use_auth,
            extra_headers=extra_headers,
        )

        if response is None:
            return CheckResult(
                name=name or path,
                method=method,
                path=path,
                ok=False,
                status_code=None,
                duration_ms=duration_ms,
                detail=error_detail,
            )

        ok = response.status_code == expected_status
        detail = "" if ok else self._safe_body_preview(response)

        return CheckResult(
            name=name or path,
            method=method,
            path=path,
            ok=ok,
            status_code=response.status_code,
            duration_ms=duration_ms,
            detail=detail,
        )

    @staticmethod
    def _safe_body_preview(response: httpx.Response, limit: int = 500) -> str:
        try:
            body = response.json()
            text = json.dumps(body, indent=2, default=str)
        except Exception:
            text = response.text

        text = text.strip()
        if len(text) > limit:
            return text[:limit] + "...[truncated]"
        return text

    def login(self) -> CheckResult:
        path = f"{self.api_prefix}/auth/login"
        response, duration_ms, error_detail = self._send_request(
            "POST",
            path,
            use_auth=False,
            extra_headers={
                "X-Organization-Id": self.organization_id,
                "Content-Type": "application/json",
            },
            json_body={
                "email": self.email,
                "password": self.password,
            },
        )

        if response is None:
            return CheckResult(
                name="auth-login",
                method="POST",
                path=path,
                ok=False,
                status_code=None,
                duration_ms=duration_ms,
                detail=error_detail,
            )

        if response.status_code != 200:
            return CheckResult(
                name="auth-login",
                method="POST",
                path=path,
                ok=False,
                status_code=response.status_code,
                duration_ms=duration_ms,
                detail=self._safe_body_preview(response),
            )

        try:
            payload = response.json()
            token = payload["data"]["access_token"]
            if not isinstance(token, str) or not token.strip():
                raise KeyError("access_token missing or invalid")
            self.token = token
        except Exception as exc:
            return CheckResult(
                name="auth-login",
                method="POST",
                path=path,
                ok=False,
                status_code=response.status_code,
                duration_ms=duration_ms,
                detail=f"Login succeeded but token parse failed: {exc}",
            )

        return CheckResult(
            name="auth-login",
            method="POST",
            path=path,
            ok=True,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

    def load_openapi(self) -> tuple[dict[str, Any] | None, CheckResult]:
        path = f"{self.api_prefix}/openapi.json"
        response, duration_ms, error_detail = self._send_request(
            "GET",
            path,
            use_auth=False,
        )

        if response is None:
            return None, CheckResult(
                name="openapi",
                method="GET",
                path=path,
                ok=False,
                status_code=None,
                duration_ms=duration_ms,
                detail=error_detail,
            )

        if response.status_code != 200:
            return None, CheckResult(
                name="openapi",
                method="GET",
                path=path,
                ok=False,
                status_code=response.status_code,
                duration_ms=duration_ms,
                detail=self._safe_body_preview(response),
            )

        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("OpenAPI response is not a JSON object")
            return payload, CheckResult(
                name="openapi",
                method="GET",
                path=path,
                ok=True,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            return None, CheckResult(
                name="openapi",
                method="GET",
                path=path,
                ok=False,
                status_code=response.status_code,
                duration_ms=duration_ms,
                detail=f"OpenAPI parse failed: {exc}",
            )

    @staticmethod
    def discover_safe_get_paths(openapi_spec: dict[str, Any]) -> list[str]:
        raw_paths = openapi_spec.get("paths", {})
        if not isinstance(raw_paths, dict):
            return []

        discovered: list[str] = []

        preferred_prefixes = (
            "/api/v1/organizations",
            "/api/v1/customer-accounts",
            "/api/v1/staff-users",
            "/api/v1/drivers",
            "/api/v1/brokers",
            "/api/v1/service-plans",
            "/api/v1/dashboard",
            "/api/v1/billing/dashboard",
            "/api/v1/referrals",
            "/api/v1/subscriptions",
            "/api/v1/billing-invoices",
            "/api/v1/payments",
            "/api/v1/notifications",
            "/api/v1/support",
            "/api/v1/review-queue",
            "/api/v1/documents",
            "/api/v1/loads",
        )

        for path, methods in raw_paths.items():
            if not isinstance(path, str) or not isinstance(methods, dict):
                continue
            if "get" not in methods:
                continue
            if "{" in path or "}" in path:
                continue
            if any(path.startswith(prefix) for prefix in preferred_prefixes):
                discovered.append(path)

        return sorted(set(discovered))

    def run(self) -> int:
        results: list[CheckResult] = []

        self._print("\n=== Freight Back Office OS Smoke Test ===")
        self._print(f"Base URL        : {self.base_url}")
        self._print(f"API Prefix      : {self.api_prefix}")
        self._print(f"Organization ID : {self.organization_id}")
        self._print(f"User            : {self.email}\n")

        results.append(
            self._request(
                "GET",
                f"{self.api_prefix}/health",
                expected_status=200,
                use_auth=False,
                name="health",
            )
        )
        results.append(
            self._request(
                "GET",
                f"{self.api_prefix}/health/ready",
                expected_status=200,
                use_auth=False,
                name="health-ready",
            )
        )

        login_result = self.login()
        results.append(login_result)
        if login_result.ok:
            results.append(
                self._request(
                    "GET",
                    f"{self.api_prefix}/auth/me",
                    expected_status=200,
                    use_auth=True,
                    name="auth-me",
                )
            )
        else:
            self._render_results(results)
            return 1

        openapi_spec, openapi_result = self.load_openapi()
        results.append(openapi_result)

        if openapi_spec:
            discovered_paths = self.discover_safe_get_paths(openapi_spec)
            for path in discovered_paths:
                if path in {
                    f"{self.api_prefix}/health",
                    f"{self.api_prefix}/health/ready",
                    f"{self.api_prefix}/auth/me",
                }:
                    continue
                results.append(
                    self._request(
                        "GET",
                        path,
                        expected_status=200,
                        use_auth=True,
                        name=path.removeprefix(f"{self.api_prefix}/"),
                    )
                )

        self._render_results(results)

        failures = [result for result in results if not result.ok]
        return 1 if failures else 0

    def _render_results(self, results: list[CheckResult]) -> None:
        self._print("\n=== Results ===")
        width = max(len(result.name) for result in results) if results else 20

        for result in results:
            icon = "PASS" if result.ok else "FAIL"
            status = str(result.status_code) if result.status_code is not None else "ERR"
            self._print(
                f"{icon:<5}  {result.name:<{width}}  "
                f"{result.method:<4}  {status:<3}  {result.duration_ms:8.2f} ms"
            )
            if result.detail:
                self._print(f"       detail: {result.detail}")

        total = len(results)
        passed = sum(1 for result in results if result.ok)
        failed = total - passed

        self._print("\n=== Summary ===")
        self._print(f"Total  : {total}")
        self._print(f"Passed : {passed}")
        self._print(f"Failed : {failed}")

        if failed:
            self._print("\nSmoke test completed with failures.")
        else:
            self._print("\nSmoke test completed successfully.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Authenticated smoke test for Freight Back Office OS",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-prefix", default=DEFAULT_API_PREFIX)
    parser.add_argument("--org-id", default=DEFAULT_ORG_ID)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tester = SmokeTester(
        base_url=args.base_url,
        api_prefix=args.api_prefix,
        organization_id=args.org_id,
        email=args.email,
        password=args.password,
        timeout=args.timeout,
    )
    try:
        return tester.run()
    finally:
        tester.close()


if __name__ == "__main__":
    raise SystemExit(main())