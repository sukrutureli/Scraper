import json
import time
from typing import Any, Dict, List

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ChunkedEncodingError, ConnectionError, ReadTimeout
from urllib3.util.retry import Retry

URL = "https://bulten.nesine.com/api/bulten/getprebultenfull"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Authorization": "Basic RDQ3MDc4RDMtNjcwQi00OUJBLTgxNUYtM0IyMjI2MTM1MTZCOkI4MzJCQjZGLTQwMjgtNDIwNS05NjFELTg1N0QxRTZEOTk0OA==",
    "Referer": "https://www.nesine.com/",
    "Connection": "keep-alive",
}

REQUEST_TIMEOUT = (10, 60)


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

    if mtid == 38:
        return {1: "Var", 2: "Yok"}.get(n, f"N{n}")

    return f"N{n}"


def _market_name(mtid: int, sov: Any) -> str:
    if mtid == 1:
        return "Maç Sonucu"
    if mtid == 12:
        return f"Toplam Gol {sov}"
    if mtid == 38:
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


def _build_session() -> requests.Session:
    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=5)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)

    return session


def _download_payload() -> Dict[str, Any]:
    last_error = None

    for attempt in range(1, 6):
        session = _build_session()
        try:
            response = session.get(URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()

        except (ChunkedEncodingError, ConnectionError, ReadTimeout, json.JSONDecodeError) as exc:
            last_error = exc
            print(f"⚠️ İstek denemesi başarısız ({attempt}/5): {type(exc).__name__} - {exc}")
            time.sleep(attempt * 2)

        finally:
            session.close()

    raise RuntimeError(f"Nesine verisi alınamadı. Son hata: {last_error}")


def fetch_matches(date_str: str) -> List[Dict[str, Any]]:
    payload = _download_payload()

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
