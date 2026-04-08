import json
import os
from typing import Any, Dict, List

import requests

URL = "https://bulten.nesine.com/api/bulten/getprebultenfull"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Authorization": "Basic RDQ3MDc4RDMtNjcwQi00OUJBLTgxNUYtM0IyMjI2MTM1MTZCOkI4MzJCQjZGLTQwMjgtNDIwNS05NjFELTg1N0QxRTZEOTk0OA==",
    "Referer": "https://www.nesine.com/",
}


def fetch_matches(date_str: str) -> List[Dict[str, Any]]:
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    os.makedirs("output", exist_ok=True)

    with open("output/raw_response.txt", "w", encoding="utf-8") as f:
        f.write(response.text)

    try:
        payload = response.json()
    except Exception:
        return []

    with open("output/raw_response.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Şimdilik parser kapalı; önce gerçek yapıyı görelim
    return []
