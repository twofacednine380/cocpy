import os
import pytest
from cocpy import COCClient
from cocpy.errors import AuthError, NotFoundError

PLAYER_TAG = "#QPL0GRQLR"  

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def live_client(token):
    return COCClient(token, timeout=20.0, max_retries=2, backoff=0.2)


def _assert_dict(d):  # piccolo helper
    assert isinstance(d, dict)


def test_live_get_player(live_client):
    p = live_client.get_player(PLAYER_TAG)
    _assert_dict(p)
    assert p.get("tag") == PLAYER_TAG
    assert isinstance(p.get("name"), str) and p["name"]  # dovrebbe essere "Quadrigesimo"


def test_live_listing_endpoints(live_client):
    _assert_dict(live_client.list_locations(limit=5))
    _assert_dict(live_client.list_leagues(limit=5))
    _assert_dict(live_client.list_war_leagues(limit=5))
    _assert_dict(live_client.list_capital_leagues(limit=5))
    _assert_dict(live_client.list_builder_base_leagues(limit=5))
    _assert_dict(live_client.list_player_labels(limit=5))
    _assert_dict(live_client.list_clan_labels(limit=5))
    _assert_dict(live_client.get_current_goldpass_season())


def test_live_drill_into_ids(live_client):
    locs = live_client.list_locations(limit=1)
    items = locs.get("items") or []
    if not items:
        pytest.xfail("nessuna location")
    loc_id = items[0]["id"]
    _assert_dict(live_client.get_location(loc_id))
    try:
        _assert_dict(live_client.get_location_player_rankings(loc_id, limit=5))
    except NotFoundError:
        pytest.xfail("rankings giocatori non disponibili")
    try:
        _assert_dict(live_client.get_location_clan_rankings(loc_id, limit=5))
    except NotFoundError:
        pytest.xfail("rankings clan non disponibili")
    try:
        _assert_dict(live_client.get_location_capital_rankings(loc_id, limit=5))
    except NotFoundError:
        pytest.xfail("rankings capitale non disponibili")

    leagues = live_client.list_leagues(limit=1)
    li = leagues.get("items") or []
    if li:
        _assert_dict(live_client.get_league(li[0]["id"]))
        seas = live_client.get_league_seasons(li[0]["id"], limit=1)
        _assert_dict(seas)
        s_items = seas.get("items") or []
        if s_items:
            _assert_dict(live_client.get_league_season_rankings(li[0]["id"], s_items[0]["id"], limit=5))

    wls = live_client.list_war_leagues(limit=1).get("items") or []
    if wls:
        _assert_dict(live_client.get_war_league(wls[0]["id"]))

    cls = live_client.list_capital_leagues(limit=1).get("items") or []
    if cls:
        _assert_dict(live_client.get_capital_league(cls[0]["id"]))

    bbl = live_client.list_builder_base_leagues(limit=1).get("items") or []
    if bbl:
        _assert_dict(live_client.get_builder_base_league(bbl[0]["id"]))


def test_live_clan_flow_smoke(live_client):
    # cerca un clan generico e prova endpoints; tollera privacy/404 con xfail
    clans = live_client.search_clans(name="Aogiri", limit=1)
    items = clans.get("items") or []
    if not items:
        pytest.xfail("nessun clan trovato")
    tag = items[0]["tag"]
    _assert_dict(live_client.get_clan(tag))
    try:
        _assert_dict(live_client.list_clan_members(tag, limit=5))
    except AuthError:
        pytest.xfail("membri clan non pubblici")
    for fn in (
        live_client.get_clan_warlog,
        live_client.get_current_war,
        live_client.get_current_war_league_group,
        live_client.get_clan_capital_raid_seasons,
    ):
        try:
            _assert_dict(fn(tag))
        except (AuthError, NotFoundError):
            pytest.xfail(f"{fn.__name__} non disponibile")


@pytest.mark.skipif(not os.getenv("COC_WAR_TAG"), reason="imposta COC_WAR_TAG per test CWL")
def test_live_cwl_single_war(live_client):
    war_tag = os.getenv("COC_WAR_TAG")  # es. #2PQ9URCCJ
    _assert_dict(live_client.get_cwl_war(war_tag))