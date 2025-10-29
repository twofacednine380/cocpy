import os
import json
from dotenv import load_dotenv

from cocpy import COCClient
from cocpy.errors import COCAPIError, AuthError, NotFoundError

import json 

PLAYER_TAG = "#QPL0GRQLR"   # Quadrigesimo
CLAN_TAG = "#2GPVUQYPJ"

def dump(title, data):
    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    with open(f"output_{title}.json", "a", encoding="utf-8") as f:
        # f.write(f"\n=== {title} ===\n")
        json.dump(data, f, indent=2, ensure_ascii=False)

def safe_call(title, fn, *args, **kwargs):
    try:
        data = fn(*args, **kwargs)
        dump(title, data)
        return data
    except (AuthError, NotFoundError) as e:
        print(f"\n=== {title} ===")
        print(f"{e.__class__.__name__}: {e}")
    except COCAPIError as e:
        print(f"\n=== {title} ===")
        print(f"COCAPIError: {e}")

def main():
    load_dotenv()
    token = os.getenv("COC_TOKEN")
    if not token:
        raise SystemExit("COC_TOKEN mancante in .env")

    client = COCClient(token, timeout=20.0, max_retries=2, backoff=0.2)

    # Player
    safe_call(f"Player {PLAYER_TAG}", client.get_player, PLAYER_TAG)

    # Clan core
    safe_call(f"Clan {CLAN_TAG}", client.get_clan, CLAN_TAG)
    safe_call("Clan members (limit=50)", client.list_clan_members, CLAN_TAG, limit=50)
    safe_call("Clan warlog (limit=20)", client.get_clan_warlog, CLAN_TAG, limit=20)

    # Current war
    cw = safe_call("Current war", client.get_current_war, CLAN_TAG)

    # CWL group and one war from it (if available)
    cwl = safe_call("Current War League group", client.get_current_war_league_group, CLAN_TAG)
    if isinstance(cwl, dict):
        war_tags = []
        for rnd in cwl.get("rounds", []):
            war_tags.extend([wt for wt in rnd.get("warTags", []) if wt and wt != "#0"])
        war_tags = list(dict.fromkeys(war_tags))  # unique, preserve order
        if war_tags:
            safe_call(f"CWL war {war_tags[0]}", client.get_cwl_war, war_tags[0])

    # Capital raid seasons
    safe_call("Capital raid seasons (limit=5)", client.get_clan_capital_raid_seasons, CLAN_TAG, limit=5)

if __name__ == "__main__":
    main()