import argparse
import json
import os
from datetime import datetime

from .scraper import fetch_matches


def format_matches_text(matches, date_str):
    lines = [f"{date_str}\n"]

    if not matches:
        lines.append("Maç bulunamadı.")
        return "\n".join(lines)

    for match in matches:
        time_str = match.get("time", "??:??")
        league = match.get("league", "Bilinmiyor")
        home = match.get("home", "?")
        away = match.get("away", "?")
        odds = match.get("odds", {})

        ms1 = odds.get("Maç Sonucu | MS1")
        msx = odds.get("Maç Sonucu | MSX")
        ms2 = odds.get("Maç Sonucu | MS2")

        alt25 = odds.get("Toplam Gol 2.5 | Alt 2.5")
        ust25 = odds.get("Toplam Gol 2.5 | Üst 2.5")

        if ms1 is not None and msx is not None and ms2 is not None:
            ms_text = f"MS: 1 {ms1:.2f} | X {msx:.2f} | 2 {ms2:.2f}"
        else:
            ms_text = "MS: yok"

        if alt25 is not None and ust25 is not None:
            au_text = f"2.5 Alt/Üst: Alt {alt25:.2f} | Üst {ust25:.2f}"
        else:
            au_text = "2.5 Alt/Üst: yok"

        lines.append(f"{time_str} | Lig: {league}")
        lines.append(f"{home} - {away}")
        lines.append(ms_text)
        lines.append(au_text)
        lines.append("")

    return "\n".join(lines).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD", default=None)
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"📅 Fetching matches for {date_str}")

    matches = fetch_matches(date_str)

    os.makedirs("output", exist_ok=True)

    json_dated_path = f"output/{date_str}.json"
    json_latest_path = "output/latest.json"
    txt_dated_path = f"output/{date_str}.txt"
    txt_latest_path = "output/latest.txt"

    with open(json_dated_path, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    with open(json_latest_path, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    text_output = format_matches_text(matches, date_str)

    with open(txt_dated_path, "w", encoding="utf-8") as f:
        f.write(text_output)

    with open(txt_latest_path, "w", encoding="utf-8") as f:
        f.write(text_output)

    print(f"✅ Saved {len(matches)} matches")
    print(f"📁 {json_dated_path}")
    print(f"📁 {json_latest_path}")
    print(f"📁 {txt_dated_path}")
    print(f"📁 {txt_latest_path}")


if __name__ == "__main__":
    main()
