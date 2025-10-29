from __future__ import annotations

import time
from typing import Any, Dict, Optional, List
from urllib.parse import quote

import requests

from .errors import COCAPIError, RateLimitError, NotFoundError, AuthError


class COCClient:
    """
    Client for the Clash of Clans REST API.

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

    # --- public: players ----------------------------------------------------

    def get_player(self, tag: str) -> Dict[str, Any]:
        """GET /players/{playerTag}"""
        path = f"/players/{self._encode_tag(tag)}"
        return self._request("GET", path)

    def verify_player_token(self, tag: str, player_token: str) -> Dict[str, Any]:
        """POST /players/{playerTag}/verifytoken"""
        path = f"/players/{self._encode_tag(tag)}/verifytoken"
        payload = {"token": player_token}
        return self._request("POST", path, json=payload)

    # --- public: clans ------------------------------------------------------

    def search_clans(
        self,
        *,
        name: Optional[str] = None,
        war_frequency: Optional[str] = None,
        location_id: Optional[int] = None,
        min_members: Optional[int] = None,
        max_members: Optional[int] = None,
        min_clan_points: Optional[int] = None,
        min_clan_level: Optional[int] = None,
        label_ids: Optional[str] = None,  # comma separated ids
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GET /clans with filters"""
        params: Dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if war_frequency is not None:
            params["warFrequency"] = war_frequency
        if location_id is not None:
            params["locationId"] = int(location_id)
        if min_members is not None:
            params["minMembers"] = int(min_members)
        if max_members is not None:
            params["maxMembers"] = int(max_members)
        if min_clan_points is not None:
            params["minClanPoints"] = int(min_clan_points)
        if min_clan_level is not None:
            params["minClanLevel"] = int(min_clan_level)
        if label_ids is not None:
            params["labelIds"] = label_ids
        params.update(self._paging_params(limit=limit, after=after, before=before))
        return self._request("GET", "/clans", params=params or None)

    def get_clan(self, tag: str) -> Dict[str, Any]:
        """GET /clans/{clanTag}"""
        return self._request("GET", f"/clans/{self._encode_tag(tag)}")

    def list_clan_members(
        self, tag: str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /clans/{clanTag}/members"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/clans/{self._encode_tag(tag)}/members", params=params or None)

    def get_clan_warlog(
        self, tag: str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /clans/{clanTag}/warlog"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/clans/{self._encode_tag(tag)}/warlog", params=params or None)

    def get_current_war(self, tag: str) -> Dict[str, Any]:
        """GET /clans/{clanTag}/currentwar"""
        return self._request("GET", f"/clans/{self._encode_tag(tag)}/currentwar")

    def get_current_war_league_group(self, tag: str) -> Dict[str, Any]:
        """GET /clans/{clanTag}/currentwar/leaguegroup"""
        return self._request("GET", f"/clans/{self._encode_tag(tag)}/currentwar/leaguegroup")

    def get_clan_capital_raid_seasons(
        self, tag: str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /clans/{clanTag}/capitalraidseasons"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/clans/{self._encode_tag(tag)}/capitalraidseasons", params=params or None)

    # --- public: clan war leagues ------------------------------------------

    def get_cwl_war(self, war_tag: str) -> Dict[str, Any]:
        """GET /clanwarleagues/wars/{warTag}"""
        return self._request("GET", f"/clanwarleagues/wars/{self._encode_tag(war_tag)}")

    # --- public: leagues ----------------------------------------------------

    def list_leagues(self, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None) -> Dict[str, Any]:
        """GET /leagues"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", "/leagues", params=params or None)

    def get_league(self, league_id: int | str) -> Dict[str, Any]:
        """GET /leagues/{leagueId}"""
        return self._request("GET", f"/leagues/{league_id}")

    def get_league_seasons(
        self, league_id: int | str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /leagues/{leagueId}/seasons"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/leagues/{league_id}/seasons", params=params or None)

    def get_league_season_rankings(
        self, league_id: int | str, season_id: str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /leagues/{leagueId}/seasons/{seasonId}"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/leagues/{league_id}/seasons/{season_id}", params=params or None)

    # --- public: war leagues -----------------------------------------------

    def list_war_leagues(self, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None) -> Dict[str, Any]:
        """GET /warleagues"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", "/warleagues", params=params or None)

    def get_war_league(self, league_id: int | str) -> Dict[str, Any]:
        """GET /warleagues/{leagueId}"""
        return self._request("GET", f"/warleagues/{league_id}")

    # --- public: capital leagues -------------------------------------------

    def list_capital_leagues(self, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None) -> Dict[str, Any]:
        """GET /capitalleagues"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", "/capitalleagues", params=params or None)

    def get_capital_league(self, league_id: int | str) -> Dict[str, Any]:
        """GET /capitalleagues/{leagueId}"""
        return self._request("GET", f"/capitalleagues/{league_id}")

    # --- public: builder base leagues --------------------------------------

    def list_builder_base_leagues(self, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None) -> Dict[str, Any]:
        """GET /builderbaseleagues"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", "/builderbaseleagues", params=params or None)

    def get_builder_base_league(self, league_id: int | str) -> Dict[str, Any]:
        """GET /builderbaseleagues/{leagueId}"""
        return self._request("GET", f"/builderbaseleagues/{league_id}")

    # --- public: locations --------------------------------------------------

    def list_locations(self, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None) -> Dict[str, Any]:
        """GET /locations"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", "/locations", params=params or None)

    def get_location(self, location_id: int | str) -> Dict[str, Any]:
        """GET /locations/{locationId}"""
        return self._request("GET", f"/locations/{location_id}")

    # rankings: players
    def get_location_player_rankings(
        self, location_id: int | str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /locations/{locationId}/rankings/players"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/locations/{location_id}/rankings/players", params=params or None)

    def get_location_player_builder_base_rankings(
        self, location_id: int | str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /locations/{locationId}/rankings/players-builder-base (Builder Base)"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/locations/{location_id}/rankings/players-builder-base", params=params or None)

    def get_location_player_versus_rankings(
        self, location_id: int | str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /locations/{locationId}/rankings/players-versus (deprecated)"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/locations/{location_id}/rankings/players-versus", params=params or None)

    # rankings: clans
    def get_location_clan_rankings(
        self, location_id: int | str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /locations/{locationId}/rankings/clans"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/locations/{location_id}/rankings/clans", params=params or None)

    def get_location_clan_builder_base_rankings(
        self, location_id: int | str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /locations/{locationId}/rankings/clans-builder-base (Builder Base)"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/locations/{location_id}/rankings/clans-builder-base", params=params or None)

    def get_location_clan_versus_rankings(
        self, location_id: int | str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /locations/{locationId}/rankings/clans-versus (deprecated)"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/locations/{location_id}/rankings/clans-versus", params=params or None)

    # rankings: capitals
    def get_location_capital_rankings(
        self, location_id: int | str, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None
    ) -> Dict[str, Any]:
        """GET /locations/{locationId}/rankings/capitals"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", f"/locations/{location_id}/rankings/capitals", params=params or None)

    # --- public: labels -----------------------------------------------------

    def list_player_labels(self, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None) -> Dict[str, Any]:
        """GET /labels/players"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", "/labels/players", params=params or None)

    def list_clan_labels(self, *, limit: Optional[int] = None, after: Optional[str] = None, before: Optional[str] = None) -> Dict[str, Any]:
        """GET /labels/clans"""
        params = self._paging_params(limit=limit, after=after, before=before)
        return self._request("GET", "/labels/clans", params=params or None)

    # --- public: gold pass --------------------------------------------------

    def get_current_goldpass_season(self) -> Dict[str, Any]:
        """GET /goldpass/seasons/current"""
        return self._request("GET", "/goldpass/seasons/current")

    # --- internals ----------------------------------------------------------

    @staticmethod
    def _encode_tag(tag: str) -> str:
        """
        API expects %23<UPPERCASE_TAG> in the path.
        Accepts '#ABCD' or 'ABCD'.
        """
        t = tag.strip().upper().lstrip("#")
        return f"%23{quote(t, safe='')}"

    @staticmethod
    def _paging_params(*, limit: Optional[int], after: Optional[str], before: Optional[str]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = int(limit)
        if after is not None and before is not None:
            raise ValueError("Specify only one of 'after' or 'before'.")
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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