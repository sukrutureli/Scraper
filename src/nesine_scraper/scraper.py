import requests
from datetime import datetime

URL = "https://bulten.nesine.com/api/bulten/getprebultenfull"

def fetch_matches(date_str):
    payload = {
        "date": date_str
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }

    r = requests.post(URL, json=payload, headers=headers, timeout=20)
    r.raise_for_status()

    data = r.json()

    matches = []

    # ⚠️ field isimleri değişebilir, esnek parse
    for league in data.get("data", []):
        league_name = league.get("name")

        for m in league.get("events", []):
            match = {
                "league": league_name,
                "home": m.get("homeTeamName"),
                "away": m.get("awayTeamName"),
                "date": m.get("eventDate"),
                "odds": {}
            }

            odds_list = m.get("odds", [])

            for o in odds_list:
                name = o.get("name")
                value = o.get("value")

                if name and value:
                    match["odds"][name] = value

            matches.append(match)

    return matches
