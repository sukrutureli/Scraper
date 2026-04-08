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

# Detail URL kalıbı.
# Senin dediğine göre detail URL içindeki id, Python'daki event id ile aynı.
# Gerekirse sadece bu pattern'i değiştirirsin.
DETAIL_URL_TEMPLATE = "https://istatistik.nesine.com/mac/{event_id}"


def _normalize_date(date_str: str) -> str:
    parts = date_str.split(".")
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return date_str


def _build_detail_url(event_id: Any) -> str:
    if event_id is None:
        return ""
    return DETAIL_URL_TEMPLATE.format(event_id=event_id)


def _option_label(mtid: int, n: int, sov: Any) -> str:
    if mtid == 1:
        return {1: "ms1", 2: "ms0", 3: "ms2"}.get(n, f"n{n}")

    if mtid == 12:
        return {1: "alt", 2: "ust"}.get(n, f"n{n}")

    if mtid == 38:
        return {1: "var", 2: "yok"}.get(n, f"n{n}")

    return f"n{n}"


def _extract_core_odds(markets: List[Dict[str, Any]]) -> Dict[str, float]:
    odds: Dict[str, float] = {}

    for market in markets:
        mtid = market.get("MTID")
        sov = market.get("SOV")
        oca = market.get("OCA", [])

        # Sadece ihtiyacımız olan marketler:
        # 1 = Maç Sonucu
        # 12 = Toplam Gol 2.5
        # 38 = KG Var/Yok
        if mtid not in (1, 12, 38):
            continue

        # Toplam Gol marketinde özellikle 2.5 istiyoruz
        if mtid == 12 and str(sov) != "2.5":
            continue

        for option in oca:
            n = option.get("N")
            o = option.get("O")

            if n is None or o is None:
                continue

            key = _option_label(mtid, n, sov)
            if key in ("ms1", "ms0", "ms2", "alt", "ust", "var", "yok"):
                odds[key] = float(o)

    return odds


def _extract_mbs(markets: List[Dict[str, Any]]) -> int:
    for market in markets:
        try:
            mbs = market.get("MBS")
            if mbs is not None:
                return int(mbs)
        except Exception:
            pass
    return 0


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

        event_id = event.get("C")
        home = event.get("HN")
        away = event.get("AN")

        if not home or not away:
            continue

        markets = event.get("MA", [])
        core_odds = _extract_core_odds(markets)

        match = {
            "event_id": event_id,
            "league_code": event.get("LC"),
            "date": normalized_date,
            "time": event.get("T") or "",
            "day": event.get("DAY") or "",
            "name": event.get("ENO") or f"{home} - {away}",
            "home": home,
            "away": away,
            "url": _build_detail_url(event_id),
            "mbs": _extract_mbs(markets),
            "ms1": core_odds.get("ms1", 0.0),
            "ms0": core_odds.get("ms0", 0.0),
            "ms2": core_odds.get("ms2", 0.0),
            "alt": core_odds.get("alt", 0.0),
            "ust": core_odds.get("ust", 0.0),
            "var": core_odds.get("var", 0.0),
            "yok": core_odds.get("yok", 0.0),
        }

        matches.append(match)

    unique_matches = []
    seen = set()

    for m in matches:
        key = (
            m.get("event_id"),
            m.get("home"),
            m.get("away"),
            m.get("date"),
            m.get("time"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_matches.append(m)

    unique_matches.sort(key=lambda x: (x.get("time") or "", x.get("name") or ""))
    return unique_matches
