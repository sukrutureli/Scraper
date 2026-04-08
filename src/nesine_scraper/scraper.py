import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

URL = "https://bulten.nesine.com/api/bulten/getprebultenfull"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Authorization": "Basic RDQ3MDc4RDMtNjcwQi00OUJBLTgxNUYtM0IyMjI2MTM1MTZCOkI4MzJCQjZGLTQwMjgtNDIwNS05NjFELTg1N0QxRTZEOTk0OA==",
    "Referer": "https://www.nesine.com/",
}


def _safe_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _find_first(d: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _parse_date_to_ymd(value: Any) -> Optional[str]:
    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None

    # direkt YYYY-MM-DD
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]

    # 08.04.2026 veya 08/04/2026
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%Y-%m-%d")
        except Exception:
            pass

    # ISO benzeri tarih
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass

    return None


def _extract_time(value: Any) -> Optional[str]:
    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None

    # 2026-04-08T19:00:00 -> 19:00
    if "T" in s and ":" in s:
        try:
            return s.split("T", 1)[1][:5]
        except Exception:
            pass

    # 08.04.2026 19:00 -> 19:00
    if " " in s and ":" in s:
        try:
            return s.rsplit(" ", 1)[1][:5]
        except Exception:
            pass

    # direkt saat
    if len(s) >= 5 and s[2] == ":":
        return s[:5]

    return None


def _extract_odds(event: Dict[str, Any]) -> Dict[str, Any]:
    odds_map: Dict[str, Any] = {}

    candidates = []
    for key in ["odds", "Odds", "betOffers", "BetOffers", "markets", "Markets"]:
        value = event.get(key)
        if isinstance(value, list):
            candidates.extend(value)

    for item in candidates:
        if not isinstance(item, dict):
            continue

        market_name = _safe_str(
            _find_first(
                item,
                [
                    "name",
                    "Name",
                    "marketName",
                    "MarketName",
                    "displayName",
                    "DisplayName",
                    "description",
                    "Description",
                ],
            )
        )

        # bazen market'in altında outcomes/selections olur
        child_lists = []
        for child_key in [
            "odds",
            "Odds",
            "outcomes",
            "Outcomes",
            "selections",
            "Selections",
            "options",
            "Options",
        ]:
            child_val = item.get(child_key)
            if isinstance(child_val, list):
                child_lists.extend(child_val)

        if child_lists:
            for child in child_lists:
                if not isinstance(child, dict):
                    continue

                child_name = _safe_str(
                    _find_first(
                        child,
                        [
                            "name",
                            "Name",
                            "label",
                            "Label",
                            "displayName",
                            "DisplayName",
                            "description",
                            "Description",
                        ],
                    )
                )
                child_value = _find_first(
                    child,
                    [
                        "value",
                        "Value",
                        "odd",
                        "Odd",
                        "rate",
                        "Rate",
                        "price",
                        "Price",
                    ],
                )

                if child_name is not None and child_value is not None:
                    key = child_name if not market_name else f"{market_name} | {child_name}"
                    odds_map[key] = child_value
        else:
            value = _find_first(
                item,
                ["value", "Value", "odd", "Odd", "rate", "Rate", "price", "Price"],
            )
            if market_name is not None and value is not None:
                odds_map[market_name] = value

    return odds_map


def _extract_events_from_payload(payload: Any) -> List[Dict[str, Any]]:
    """
    Response yapısı değişebildiği için olabildiğince esnek geziyoruz.
    """
    events: List[Dict[str, Any]] = []

    def walk(node: Any, current_league: Optional[str] = None) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, current_league)
            return

        if not isinstance(node, dict):
            return

        league_name = current_league or _safe_str(
            _find_first(node, ["name", "Name", "leagueName", "LeagueName", "categoryName", "CategoryName"])
        )

        # event listesi taşıyan anahtarlar
        for events_key in ["events", "Events", "matches", "Matches"]:
            child_events = node.get(events_key)
            if isinstance(child_events, list):
                for event in child_events:
                    if isinstance(event, dict):
                        normalized = _normalize_event(event, league_name)
                        if normalized:
                            events.append(normalized)

        # alt düğümler
        for child_key in [
            "data",
            "Data",
            "groups",
            "Groups",
            "leagues",
            "Leagues",
            "sports",
            "Sports",
            "items",
            "Items",
            "categories",
            "Categories",
        ]:
            child = node.get(child_key)
            if child is not None:
                walk(child, league_name)

    walk(payload)
    return events


def _normalize_event(event: Dict[str, Any], league_name: Optional[str]) -> Optional[Dict[str, Any]]:
    home = _safe_str(
        _find_first(
            event,
            [
                "homeTeamName",
                "HomeTeamName",
                "home",
                "Home",
                "homeName",
                "HomeName",
                "team1",
                "Team1",
            ],
        )
    )
    away = _safe_str(
        _find_first(
            event,
            [
                "awayTeamName",
                "AwayTeamName",
                "away",
                "Away",
                "awayName",
                "AwayName",
                "team2",
                "Team2",
            ],
        )
    )

    date_raw = _find_first(
        event,
        [
            "eventDate",
            "EventDate",
            "date",
            "Date",
            "matchDate",
            "MatchDate",
            "startDate",
            "StartDate",
        ],
    )

    match_id = _find_first(event, ["id", "Id", "eventId", "EventId", "matchId", "MatchId"])
    code = _find_first(event, ["code", "Code", "betCode", "BetCode"])

    if not home and not away:
        return None

    return {
        "id": match_id,
        "code": code,
        "league": league_name,
        "home": home,
        "away": away,
        "date_raw": date_raw,
        "date": _parse_date_to_ymd(date_raw),
        "time": _extract_time(date_raw),
        "odds": _extract_odds(event),
    }


def fetch_matches(date_str: str) -> List[Dict[str, Any]]:
    response = requests.get(URL, headers=HEADERS, timeout=30)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        preview = response.text[:1000]
        raise RuntimeError(
            f"Nesine request failed: {exc}\nStatus: {response.status_code}\nPreview:\n{preview}"
        ) from exc

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        preview = response.text[:1000]
        raise RuntimeError(f"JSON parse failed. Preview:\n{preview}") from exc

    all_events = _extract_events_from_payload(payload)

    # bugünün tarihine filtre
    filtered = [e for e in all_events if e.get("date") == date_str]

    # eğer hiç eşleşme çıkmazsa raw date formatı farklı olabilir; o yüzden hepsini dönmek yerine
    # yine bugünkü string geçenleri ikinci kez deneyelim
    if not filtered:
        fallback = []
        for e in all_events:
            raw = _safe_str(e.get("date_raw")) or ""
            if date_str in raw:
                fallback.append(e)
        filtered = fallback

    # aynı maçı iki kez yazmamak için basit dedupe
    unique = []
    seen = set()
    for e in filtered:
        key = (
            e.get("id"),
            e.get("code"),
            e.get("home"),
            e.get("away"),
            e.get("date"),
            e.get("time"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)

    return unique
