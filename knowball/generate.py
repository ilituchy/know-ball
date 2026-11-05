"""Build data/<sport>/<date>.json and latest.json for today's player.

    python -m knowball.generate --sport nba [--date 2026-11-05] [--force]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
from zoneinfo import ZoneInfo

from . import enrich, espn, picker
from .sports import SPORTS, Sport

ROOT = pathlib.Path(__file__).resolve().parent.parent
TZ = ZoneInfo("America/New_York")


def read_history(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def write_json(path: pathlib.Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def choose(sport: Sport, day: dt.date, used: set[str]) -> tuple[dict, dict, dict, dict]:
    for team in picker.team_of_the_day(espn.teams(sport), day):
        for player in picker.shuffled(espn.roster(sport, team["id"]), day, sport.key):
            if player["id"] in used:
                continue
            ov = espn.overview(sport, player["id"])
            career = espn.career_value(ov, sport.star_stat)
            if not picker.is_under_the_radar(career, sport.star_cutoff):
                continue
            wiki = enrich.wikipedia(player["fullName"], sport.wiki_keyword)
            if wiki is None:  # no background story means a thin page
                continue
            return team, player, ov, wiki
    raise RuntimeError("no eligible player found in the whole league")


def player_news(ov: dict, last_name: str, limit: int = 3) -> list[dict]:
    out = []
    for item in ov.get("news") or []:
        text = f"{item.get('headline', '')} {item.get('description', '')}"
        href = ((item.get("links") or {}).get("web") or {}).get("href")
        if href and last_name.lower() in text.lower():
            out.append({"headline": item.get("headline"), "url": href})
    return out[:limit]


def build(sport: Sport, day: dt.date, used: set[str]) -> dict:
    team, player, ov, wiki = choose(sport, day, used)
    bio = espn.athlete(sport, player["id"])
    name = player["fullName"]
    logos = team.get("logos") or [{}]
    return {
        "date": day.isoformat(),
        "sport": sport.key,
        "league": sport.label,
        "player": {
            "id": player["id"],
            "name": name,
            "headshot": (bio.get("headshot") or {}).get("href"),
            "jersey": bio.get("displayJersey"),
            "position": (bio.get("position") or {}).get("displayName"),
            "espn_url": ((player.get("links") or [{}])[0]).get("href"),
        },
        "team": {
            "name": team.get("displayName"),
            "abbreviation": team.get("abbreviation"),
            "logo": logos[0].get("href"),
            "color": team.get("color"),
        },
        "facts": {
            "Age": player.get("age"),
            "Height": player.get("displayHeight"),
            "Weight": player.get("displayWeight"),
            "From": bio.get("displayBirthPlace"),
            "College": (player.get("college") or {}).get("name"),
            "Draft": bio.get("displayDraft") or "Undrafted",
            "Experience": bio.get("displayExperience"),
        },
        "background": wiki,
        "stats": {
            "season_label": (bio.get("statsSummary") or {}).get("displayName"),
            "labels": list(sport.stats),
            "season": espn.split_stats(ov, "Regular Season"),
            "career": espn.split_stats(ov, "Career"),
        },
        "recent_games": espn.recent_games(
            espn.gamelog(sport, player["id"]), sport.game_stats
        ),
        "highlights": enrich.highlights(name, sport.label),
        "news": player_news(ov, player.get("lastName") or name.split()[-1]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", default="nba", choices=sorted(SPORTS))
    parser.add_argument("--date", help="YYYY-MM-DD, default today in New York")
    parser.add_argument("--force", action="store_true", help="rebuild an existing day")
    args = parser.parse_args()

    sport = SPORTS[args.sport]
    day = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(TZ).date()
    folder = ROOT / "data" / sport.key
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{day.isoformat()}.json"
    history_path = folder / "history.json"
    history = read_history(history_path)

    if target.exists() and not args.force:
        print(f"{target.name} already exists")
        return

    history = [h for h in history if h["date"] != day.isoformat()]
    page = build(sport, day, {h["id"] for h in history})
    history.append(
        {"date": day.isoformat(), "id": page["player"]["id"], "name": page["player"]["name"]}
    )
    write_json(target, page)
    write_json(folder / "latest.json", page)
    write_json(history_path, history)
    print(f"{day}: {page['player']['name']} ({page['team']['name']})")


if __name__ == "__main__":
    main()
