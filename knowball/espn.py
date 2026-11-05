"""ESPN's public JSON endpoints, reduced to the fields Know Ball uses."""
from __future__ import annotations

from .http import get_json
from .sports import Sport

SITE = "https://site.api.espn.com/apis/site/v2/sports"
WEB = "https://site.web.api.espn.com/apis/common/v3/sports"


def teams(sport: Sport) -> list[dict]:
    data = get_json(f"{SITE}/{sport.espn_path}/teams?limit=200")
    found = [t["team"] for t in data["sports"][0]["leagues"][0]["teams"]]
    return sorted(found, key=lambda t: int(t["id"]))


def roster(sport: Sport, team_id: str) -> list[dict]:
    raw = get_json(f"{SITE}/{sport.espn_path}/teams/{team_id}/roster")["athletes"]
    # Basketball is a flat list; football groups players by position.
    flat: list[dict] = []
    for item in raw:
        flat.extend(item["items"] if "items" in item else [item])
    return flat


def athlete(sport: Sport, athlete_id: str) -> dict:
    return get_json(f"{WEB}/{sport.espn_path}/athletes/{athlete_id}")["athlete"]


def overview(sport: Sport, athlete_id: str) -> dict:
    return get_json(f"{WEB}/{sport.espn_path}/athletes/{athlete_id}/overview")


def gamelog(sport: Sport, athlete_id: str) -> dict:
    return get_json(f"{WEB}/{sport.espn_path}/athletes/{athlete_id}/gamelog")


def split_stats(ov: dict, split: str) -> dict[str, str]:
    """Map label -> value for a split such as 'Regular Season' or 'Career'."""
    stats = ov.get("statistics") or {}
    for row in stats.get("splits") or []:
        if row.get("displayName") == split:
            return dict(zip(stats.get("labels") or [], row.get("stats") or []))
    return {}


def career_value(ov: dict, stat_name: str) -> float | None:
    stats = ov.get("statistics") or {}
    names = stats.get("names") or []
    if stat_name not in names:
        return None
    for row in stats.get("splits") or []:
        if row.get("displayName") == "Career":
            try:
                return float(row["stats"][names.index(stat_name)])
            except (ValueError, IndexError, KeyError):
                return None
    return None


def recent_games(log: dict, labels: tuple[str, ...], limit: int = 5) -> list[dict]:
    """Newest regular-season/playoff games first, skipping preseason."""
    meta = log.get("events") or {}
    all_labels = log.get("labels") or []
    games: list[dict] = []
    for season in log.get("seasonTypes") or []:
        if "preseason" in (season.get("displayName") or "").lower():
            continue
        for cat in season.get("categories") or []:
            if cat.get("type") != "event":
                continue
            for ev in cat.get("events") or []:
                info = meta.get(ev.get("eventId")) or {}
                row = dict(zip(all_labels, ev.get("stats") or []))
                games.append(
                    {
                        "date": info.get("gameDate"),
                        "opponent": (info.get("opponent") or {}).get("abbreviation"),
                        "at_vs": info.get("atVs"),
                        "result": info.get("gameResult"),
                        "score": info.get("score"),
                        "stats": {k: row.get(k) for k in labels},
                    }
                )
    games.sort(key=lambda g: g["date"] or "", reverse=True)
    return games[:limit]
