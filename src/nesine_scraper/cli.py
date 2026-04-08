import argparse
import json
import os
from datetime import datetime

from .scraper import fetch_matches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD", default=None)
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"📅 Fetching matches for {date_str}")

    matches = fetch_matches(date_str)

    os.makedirs("output", exist_ok=True)

    dated_path = f"output/{date_str}.json"
    latest_path = "output/latest.json"

    with open(dated_path, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(matches)} matches")
    print(f"📁 {dated_path}")
    print(f"📁 {latest_path}")


if __name__ == "__main__":
    main()
