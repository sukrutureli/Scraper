import json
import os
from datetime import datetime
from .scraper import fetch_matches

def main(date=None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    print(f"📅 Fetching matches for {date}")

    matches = fetch_matches(date)

    os.makedirs("output", exist_ok=True)

    file_path = f"output/{date}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    # latest
    with open("output/latest.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(matches)} matches")

if __name__ == "__main__":
    main()