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
# Stub articles make a thin page. MLB's run shortest; this keeps about 3 in 4.
MIN_BIO_CHARS = 700


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
            view = sport.view_for(espn.stat_labels(ov))
            if view and not picker.is_under_the_radar(
                espn.career_value(ov, view), view.star_cutoff
            ):
                continue
            born = (player.get("dateOfBirth") or "")[:4] or None
            wiki = enrich.wikipedia(player["fullName"], sport.wiki_keyword, born)
            if wiki is None or bio_length(wiki) < MIN_BIO_CHARS:
                continue
            if picker.is_famous(wiki["sections"][0]["text"], sport.fame_words):
                continue
            return team, player, ov, wiki
    raise RuntimeError("no eligible player found in the whole league")


def bio_length(wiki: dict) -> int:
    return sum(len(section["text"]) for section in wiki["sections"])


def player_news(ov: dict, last_name: str, limit: int = 3) -> list[dict]:
    out = []
    for item in ov.get("news") or []:
        text = f"{item.get('headline', '')} {item.get('description', '')}"
        href = ((item.get("links") or {}).get("web") or {}).get("href")
        if href and last_name in enrich.plain(text):
            out.append({"headline": item.get("headline"), "url": href})
    return out[:limit]


def build(sport: Sport, day: dt.date, used: set[str]) -> dict:
    team, player, ov, wiki = choose(sport, day, used)
    bio = espn.athlete(sport, player["id"])
    name = player["fullName"]
    view = sport.view_for(espn.stat_labels(ov))
    season = (bio.get("statsSummary") or {}).get("displayName") or ""
    college = (player.get("college") or {}).get("name")
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
            "College": college,
            "Draft": bio.get("displayDraft")
            or ("Undrafted" if sport.blank_draft_means_undrafted else None),
            "Experience": bio.get("displayExperience"),
        },
        "background": wiki,
        "stats": espn.stat_table(ov, view, season.split()[0] if season else "This season"),
        "recent_games": espn.recent_games(
            espn.gamelog(sport, player["id"]), view.games if view else ()
        ),
        "highlights": enrich.highlights(name, sport.label),
        "news": player_news(ov, enrich.surname(name)),
    }


def days_to_build(today: dt.date) -> list[dt.date]:
    """Today and tomorrow. GitHub's scheduled runs start hours late, so
    building a day ahead means the page is ready at midnight."""
    return [today, today + dt.timedelta(days=1)]


def build_day(sport: Sport, folder: pathlib.Path, day: dt.date, force: bool) -> None:
    target = folder / f"{day.isoformat()}.json"
    if target.exists() and not force:
        print(f"{target.name} already exists")
        return
    history_path = folder / "history.json"
    history = [h for h in read_history(history_path) if h["date"] != day.isoformat()]
    page = build(sport, day, {h["id"] for h in history})
    history.append(
        {"date": day.isoformat(), "id": page["player"]["id"], "name": page["player"]["name"]}
    )
    write_json(target, page)
    write_json(history_path, sorted(history, key=lambda h: h["date"]))
    print(f"{day}: {page['player']['name']} ({page['team']['name']})")


def point_latest(folder: pathlib.Path, today: dt.date) -> None:
    """latest.json is the newest page that isn't in the future."""
    dated = sorted(
        f for f in folder.glob("????-??-??.json") if f.stem <= today.isoformat()
    )
    if dated:
        (folder / "latest.json").write_text(dated[-1].read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", default="nba", choices=sorted(SPORTS))
    parser.add_argument("--date", help="build only this YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="rebuild days that exist")
    args = parser.parse_args()

    sport = SPORTS[args.sport]
    today = dt.datetime.now(TZ).date()
    folder = ROOT / "data" / sport.key
    folder.mkdir(parents=True, exist_ok=True)
    days = [dt.date.fromisoformat(args.date)] if args.date else days_to_build(today)
    for day in days:
        build_day(sport, folder, day, args.force)
    point_latest(folder, today)


if __name__ == "__main__":
    main()
