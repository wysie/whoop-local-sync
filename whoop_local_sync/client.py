from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .oauth import TOKEN_URL, token_payload

API_BASE = "https://api.prod.whoop.com/developer/v2"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class WhoopHTTPError(RuntimeError):
    def __init__(self, status: int, url: str, detail: str):
        super().__init__(f"HTTP {status} from {url}: {detail}")
        self.status = status
        self.url = url
        self.detail = detail


@dataclass
class WhoopClient:
    access_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str | None = None
    api_base: str = API_BASE
    user_agent: str = DEFAULT_USER_AGENT
    max_attempts: int = 5

    def http_json(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 45,
    ) -> Dict[str, Any]:
        body = None
        h = {"Accept": "application/json", "User-Agent": self.user_agent}
        if headers:
            h.update(headers)
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        req = urllib.request.Request(url, method=method, data=body, headers=h)
        for attempt in range(1, self.max_attempts + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")
                if e.code in {429, 500, 502, 503, 504} and attempt < self.max_attempts:
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    try:
                        delay = float(retry_after) if retry_after else min(60.0, 2.0 * attempt)
                    except Exception:
                        delay = min(60.0, 2.0 * attempt)
                    time.sleep(delay)
                    continue
                raise WhoopHTTPError(e.code, url, detail) from e
        raise RuntimeError(f"Failed after {self.max_attempts} attempts: {url}")

    def exchange_code(self, code: str) -> Dict[str, Any]:
        if not (self.client_id and self.client_secret and self.redirect_uri):
            raise ValueError("client_id, client_secret, and redirect_uri are required")
        return self.http_json(
            TOKEN_URL,
            method="POST",
            data=token_payload(
                grant_type="authorization_code",
                client_id=self.client_id,
                client_secret=self.client_secret,
                code=code,
                redirect_uri=self.redirect_uri,
            ),
        )

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        if not (self.client_id and self.client_secret):
            raise ValueError("client_id and client_secret are required")
        return self.http_json(
            TOKEN_URL,
            method="POST",
            data=token_payload(
                grant_type="refresh_token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=refresh_token,
            ),
        )

    def api_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.access_token:
            raise ValueError("access_token is required")
        params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        url = f"{self.api_base}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return self.http_json(url, headers={"Authorization": f"Bearer {self.access_token}"})

    def api_list(self, path: str, params: Optional[Dict[str, Any]] = None, max_pages: int = 25) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        params = dict(params or {})
        for _ in range(max_pages):
            payload = self.api_get(path, params)
            records = payload.get("records")
            if isinstance(records, list):
                out.extend(records)
            elif isinstance(payload, list):
                out.extend(payload)
            else:
                if payload:
                    out.append(payload)
                break
            token = payload.get("next_token") or payload.get("nextToken")
            if not token:
                break
            params["nextToken"] = token
        return out

    def fetch_range(self, start: str, end: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "range": {"start": start, "end": end},
            "profile": None,
            "body_measurement": None,
            "cycles": [],
            "recoveries": [],
            "sleeps": [],
            "workouts": [],
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        for key, path in [("profile", "/user/profile/basic"), ("body_measurement", "/user/measurement/body")]:
            try:
                data[key] = self.api_get(path)
            except Exception as e:
                data[key] = {"error": str(e)}
        params = {"start": start, "end": end}
        for key, path in [("cycles", "/cycle"), ("recoveries", "/recovery"), ("sleeps", "/activity/sleep"), ("workouts", "/activity/workout")]:
            data[key] = self.api_list(path, params)
        return data
