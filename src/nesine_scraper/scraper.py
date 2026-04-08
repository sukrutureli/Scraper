import json
from typing import Any, Dict, List

import requests

URL = "https://bulten.nesine.com/api/bulten/getprebultenfull"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Authorization": "Basic RDQ3MDc4RDMtNjcwQi00OUJBLTgxNUYtM0IyMjI2MTM1MTZCOkI4MzJCQjZGLTQwMjgtNDIwNS05NjFELTg1N0QxRTZEOTk0OA==",
    "Referer": "https://www.nesine.com/",
}


def _normalize_date(date_str: str) -> str:
    parts = date_str.split(".")
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return date_str


def _option_label(mtid: int, n: int, sov: Any) -> str:
    if mtid == 1:
        return {1: "MS1", 2: "MSX", 3: "MS2"}.get(n, f"N{n}")

    if mtid == 12:
        line = str(sov)
        return {1: f"Alt {line}", 2: f"Üst {line}"}.get(n, f"N{n}")

    # KG Var/Yok için olası marketlerden biri
    if mtid in (20,):
        return {1: "Var", 2: "Yok"}.get(n, f"N{n}")

    return f"N{n}"


def _market_name(mtid: int, sov: Any) -> str:
    if mtid == 1:
        return "Maç Sonucu"
    if mtid == 12:
        return f"Toplam Gol {sov}"
    if mtid in (20,):
        return "KG Var/Yok"
    return f"MTID_{mtid}"


def _extract_odds(markets: List[Dict[str, Any]]) -> Dict[str, Any]:
    odds: Dict[str, Any] = {}

    for market in markets:
        mtid = market.get("MTID")
        sov = market.get("SOV")
        oca = market.get("OCA", [])

        market_name = _market_name(mtid, sov)

        for option in oca:
            n = option.get("N")
            o = option.get("O")

            if n is None or o is None:
                continue

            label = _option_label(mtid, n, sov)
            odds[f"{market_name} | {label}"] = o

    return odds


def fetch_matches(date_str: str) -> List[Dict[str, Any]]:
    response = requests.get(URL, headers=HEADERS, timeout=30)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Nesine request failed: {exc}\nStatus: {response.status_code}\nPreview:\n{response.text[:1000]}"
        ) from exc

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON parse failed. Preview:\n{response.text[:1000]}") from exc

    events = payload.get("sg", {}).get("EA", [])
    matches: List[Dict[str, Any]] = []

    for event in events:
        # sadece futbol
        if event.get("TYPE") != 1:
            continue

        raw_date = event.get("D")
        normalized_date = _normalize_date(raw_date) if raw_date else None

        if normalized_date != date_str:
            continue

        home = event.get("HN")
        away = event.get("AN")

        if not home or not away:
            continue

        match = {
            "id": event.get("C"),
            "event_version": event.get("EV"),
            "code": event.get("BC"),
            "league_code": event.get("LC"),
            "league": event.get("LC"),
            "home": home,
            "away": away,
            "match_name": event.get("ENO"),
            "date": normalized_date,
            "time": event.get("T"),
            "day": event.get("DAY"),
            "type": event.get("TYPE"),
            "gt": event.get("GT"),
            "odds": _extract_odds(event.get("MA", [])),
        }

        matches.append(match)

    unique_matches = []
    seen = set()

    for m in matches:
        key = (m.get("id"), m.get("home"), m.get("away"), m.get("date"), m.get("time"))
        if key in seen:
            continue
        seen.add(key)
        unique_matches.append(m)

    return unique_matches
