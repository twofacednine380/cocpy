import json
from urllib.parse import urlparse
import pytest
import requests
from requests.models import Response

from cocpy.client import COCClient
from cocpy.errors import COCAPIError, RateLimitError, NotFoundError, AuthError


class DummySession(requests.Session):
    def __init__(self, seq=None, status=200, payload=None, headers=None):
        super().__init__()
        # seq = list of tuples (status, payload, headers) consumed in order
        self._seq = list(seq) if seq else None
        self._status = status
        self._payload = payload or {"ok": True}
        self._headers = headers or {}
        self.last = None

    def request(self, method, url, **kwargs):
        self.last = {"method": method, "url": url, "params": kwargs.get("params"), "json": kwargs.get("json")}
        r = Response()
        if self._seq is not None and self._seq:
            st, pl, hd = self._seq.pop(0)
            r.status_code = st
            r._content = json.dumps(pl or {}).encode()
            r.headers.update(hd or {})
            return r
        r.status_code = self._status
        r._content = json.dumps(self._payload).encode()
        r.headers.update(self._headers)
        return r


def _path(url):
    u = urlparse(url)
    return u.path


def test_tag_encoding():
    c = COCClient("t", session=DummySession())
    assert c._encode_tag("#2abc") == "%232ABC"
    assert c._encode_tag("2abc") == "%232ABC"


def test_error_mapping_401_404_500_429():
    # 401/403 -> AuthError
    c = COCClient("t", session=DummySession(status=401))
    with pytest.raises(AuthError):
        c.get_player("#AAAA")

    # 404 -> NotFoundError
    c = COCClient("t", session=DummySession(status=404))
    with pytest.raises(NotFoundError):
        c.get_location(1)

    # 500 -> COCAPIError
    c = COCClient("t", session=DummySession(status=500))
    with pytest.raises(COCAPIError):
        c.list_locations()

    # 429 then success -> handled with backoff
    seq = [(429, {"message": "rate"}, {"Retry-After": "0"}), (200, {"ok": True}, {})]
    c = COCClient("t", session=DummySession(seq=seq), backoff=0.0, max_retries=1)
    assert c.list_locations()["ok"] is True

    # 429 exceeding retries -> RateLimitError
    seq = [(429, {}, {"Retry-After": "0"}), (429, {}, {"Retry-After": "0"})]
    c = COCClient("t", session=DummySession(seq=seq), backoff=0.0, max_retries=1)
    with pytest.raises(RateLimitError):
        c.list_locations()


@pytest.mark.parametrize(
    "call,expected_path,expected_params,expected_json",
    [
        # players
        (lambda c: c.get_player("#ABCD"), "/v1/players/%23ABCD", None, None),
        (lambda c: c.verify_player_token("#ABCD", "tok"), "/v1/players/%23ABCD/verifytoken", None, {"token": "tok"}),

        # clans
        (lambda c: c.search_clans(name="abc", min_members=5, max_members=10, min_clan_level=2, limit=3),
         "/v1/clans", {"name": "abc", "minMembers": 5, "maxMembers": 10, "minClanLevel": 2, "limit": 3}, None),
        (lambda c: c.get_clan("#ABCD"), "/v1/clans/%23ABCD", None, None),
        (lambda c: c.list_clan_members("#ABCD", limit=1, after="x"),
         "/v1/clans/%23ABCD/members", {"limit": 1, "after": "x"}, None),
        (lambda c: c.get_clan_warlog("#ABCD", limit=2, before="y"),
         "/v1/clans/%23ABCD/warlog", {"limit": 2, "before": "y"}, None),
        (lambda c: c.get_current_war("#ABCD"), "/v1/clans/%23ABCD/currentwar", None, None),
        (lambda c: c.get_current_war_league_group("#ABCD"), "/v1/clans/%23ABCD/currentwar/leaguegroup", None, None),
        (lambda c: c.get_clan_capital_raid_seasons("#ABCD", limit=1),
         "/v1/clans/%23ABCD/capitalraidseasons", {"limit": 1}, None),

        # CWL
        (lambda c: c.get_cwl_war("#WAR123"), "/v1/clanwarleagues/wars/%23WAR123", None, None),

        # leagues
        (lambda c: c.list_leagues(limit=5), "/v1/leagues", {"limit": 5}, None),
        (lambda c: c.get_league(123), "/v1/leagues/123", None, None),
        (lambda c: c.get_league_seasons(123, limit=1), "/v1/leagues/123/seasons", {"limit": 1}, None),
        (lambda c: c.get_league_season_rankings(123, "2025-09", limit=1),
         "/v1/leagues/123/seasons/2025-09", {"limit": 1}, None),

        # war leagues
        (lambda c: c.list_war_leagues(limit=5), "/v1/warleagues", {"limit": 5}, None),
        (lambda c: c.get_war_league(15), "/v1/warleagues/15", None, None),

        # capital leagues
        (lambda c: c.list_capital_leagues(limit=5), "/v1/capitalleagues", {"limit": 5}, None),
        (lambda c: c.get_capital_league(3), "/v1/capitalleagues/3", None, None),

        # builder base leagues
        (lambda c: c.list_builder_base_leagues(limit=5), "/v1/builderbaseleagues", {"limit": 5}, None),
        (lambda c: c.get_builder_base_league(7), "/v1/builderbaseleagues/7", None, None),

        # locations
        (lambda c: c.list_locations(limit=5), "/v1/locations", {"limit": 5}, None),
        (lambda c: c.get_location(1), "/v1/locations/1", None, None),
        (lambda c: c.get_location_player_rankings(1, limit=2),
         "/v1/locations/1/rankings/players", {"limit": 2}, None),
        (lambda c: c.get_location_player_builder_base_rankings(1, limit=2),
         "/v1/locations/1/rankings/players-builder-base", {"limit": 2}, None),
        (lambda c: c.get_location_player_versus_rankings(1, limit=2),
         "/v1/locations/1/rankings/players-versus", {"limit": 2}, None),
        (lambda c: c.get_location_clan_rankings(1, limit=2),
         "/v1/locations/1/rankings/clans", {"limit": 2}, None),
        (lambda c: c.get_location_clan_builder_base_rankings(1, limit=2),
         "/v1/locations/1/rankings/clans-builder-base", {"limit": 2}, None),
        (lambda c: c.get_location_clan_versus_rankings(1, limit=2),
         "/v1/locations/1/rankings/clans-versus", {"limit": 2}, None),
        (lambda c: c.get_location_capital_rankings(1, limit=2),
         "/v1/locations/1/rankings/capitals", {"limit": 2}, None),

        # labels
        (lambda c: c.list_player_labels(limit=3), "/v1/labels/players", {"limit": 3}, None),
        (lambda c: c.list_clan_labels(limit=3), "/v1/labels/clans", {"limit": 3}, None),

        # gold pass
        (lambda c: c.get_current_goldpass_season(), "/v1/goldpass/seasons/current", None, None),
    ]
)
def test_paths_and_params(call, expected_path, expected_params, expected_json):
    sess = DummySession()
    c = COCClient("t", base_url="https://api.clashofclans.com/v1", session=sess)
    res = call(c)
    assert isinstance(res, dict)
    assert _path(sess.last["url"]) == expected_path
    if expected_params is None:
        assert sess.last["params"] in (None, {})
    else:
        assert sess.last["params"] == expected_params
    if expected_json is None:
        assert sess.last["json"] in (None, {})
    else:
        assert sess.last["json"] == expected_json


def test_paging_guard_raises_on_both_after_before():
    sess = DummySession()
    c = COCClient("t", session=sess)
    with pytest.raises(ValueError):
        c.list_locations(limit=1, after="a", before="b")