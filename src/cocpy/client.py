from __future__ import annotations

import time
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from .errors import COCAPIError, RateLimitError, NotFoundError, AuthError


class COCClient:
    """
    Minimal client for the Clash of Clans REST API.

    Base URL: https://api.clashofclans.com/v1
    Auth: Bearer JWT from https://developer.clashofclans.com
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://api.clashofclans.com/v1",
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff: float = 0.75,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self._session = session or requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "cocpy/0.1.0",
        })

    # --- public methods -----------------------------------------------------

    def get_player(self, tag: str) -> Dict[str, Any]:
        path = f"/players/{self._encode_tag(tag)}"
        return self._request("GET", path)

    def verify_player_token(self, tag: str, player_token: str) -> Dict[str, Any]:
        path = f"/players/{self._encode_tag(tag)}/verifytoken"
        payload = {"token": player_token}
        return self._request("POST", path, json=payload)

    def list_locations(self, *, limit: Optional[int] = None,
                       after: Optional[str] = None, before: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if limit is not None:
            params["limit"] = int(limit)
        if after is not None and before is not None:
            raise ValueError("Specify only one of 'after' or 'before'.")
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before
        return self._request("GET", "/locations", params=params or None)

    def get_location(self, location_id: int | str) -> Dict[str, Any]:
        return self._request("GET", f"/locations/{location_id}")

    # --- internals ----------------------------------------------------------

    def _encode_tag(self, tag: str) -> str:
        """
        API expects %23<UPPERCASE_TAG> in the path.
        Accepts '#ABCD' or 'ABCD'.
        """
        t = tag.strip().upper().lstrip("#")
        return f"%23{quote(t, safe='')}"

    def _request(self, method: str, path: str,
                 params: Optional[Dict[str, Any]] = None,
                 json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self.base_url + path
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = self._session.request(
                    method, url, params=params, json=json, timeout=self.timeout
                )
                if resp.status_code == 429:
                    if attempt == self.max_retries:
                        raise RateLimitError("Rate limit exceeded")
                    # honor Retry-After if present
                    delay = self._parse_retry_after(resp.headers.get("Retry-After")) or self.backoff * (2 ** attempt)
                    time.sleep(delay)
                    continue

                if resp.status_code in (401, 403):
                    raise AuthError(resp.text)
                if resp.status_code == 404:
                    raise NotFoundError(resp.text)
                if resp.status_code >= 400:
                    raise COCAPIError(f"{resp.status_code}: {resp.text}")

                return resp.json()

            except (requests.Timeout, requests.ConnectionError) as e:
                last_exc = e
                if attempt == self.max_retries:
                    raise COCAPIError(str(e)) from e
                time.sleep(self.backoff * (2 ** attempt))

        assert False, f"unreachable; last_exc={last_exc}"

    @staticmethod
    def _parse_retry_after(value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None