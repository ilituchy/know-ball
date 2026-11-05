"""ESPN's public JSON endpoints, reduced to the fields Know Ball uses."""
from __future__ import annotations

from .http import get_json
from .sports import Sport, StatView

SITE = "https://site.api.espn.com/apis/site/v2/sports"
WEB = "https://site.web.api.espn.com/apis/common/v3/sports"


def teams(sport: Sport) -> list[dict]:
    data = get_json(f"{SITE}/{sport.espn_path}/teams?limit=200")
    found = [t["team"] for t in data["sports"][0]["leagues"][0]["teams"]]
    return sorted(found, key=lambda t: int(t["id"]))


def roster(sport: Sport, team_id: str) -> list[dict]:
    raw = get_json(f"{SITE}/{sport.espn_path}/teams/{team_id}/roster")["athletes"]
    # Basketball is a flat list; football and baseball arrive in groups.
    flat: list[dict] = []
    for item in raw:
        if item.get("position") in sport.skip_groups:
            continue
        flat.extend(item["items"] if "items" in item else [item])
    return flat


def athlete(sport: Sport, athlete_id: str) -> dict:
    return get_json(f"{WEB}/{sport.espn_path}/athletes/{athlete_id}")["athlete"]


def overview(sport: Sport, athlete_id: str) -> dict:
    return get_json(f"{WEB}/{sport.espn_path}/athletes/{athlete_id}/overview")


def gamelog(sport: Sport, athlete_id: str) -> dict:
    return get_json(f"{WEB}/{sport.espn_path}/athletes/{athlete_id}/gamelog")


def stat_labels(ov: dict) -> list[str]:
    return (ov.get("statistics") or {}).get("labels") or []


def split_row(ov: dict, split: str) -> list[str] | None:
    for row in (ov.get("statistics") or {}).get("splits") or []:
        if row.get("displayName") == split:
            return row.get("stats") or []
    return None


def number(value: str | None) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def first(labels: list[str], row: list[str], label: str) -> str | None:
    """Value of a column. Labels repeat (YDS for rushing and receiving), and
    the player's main category always comes first."""
    if label in labels and labels.index(label) < len(row):
        return row[labels.index(label)]
    return None


def innings(value: float) -> float:
    """Baseball writes 12 and 2/3 innings as 12.2."""
    whole = int(value)
    return whole + (value - whole) * 10 / 3


def derived(labels: list[str], row: list[str], label: str) -> str | None:
    """Rates ESPN leaves out of its overview: batting average and ERA."""
    get = lambda name: number(first(labels, row, name))  # noqa: E731
    if label == "AVG" and get("AB"):
        return f"{get('H') / get('AB'):.3f}".lstrip("0")
    if label == "ERA" and get("IP"):
        return f"{get('ER') * 9 / innings(get('IP')):.2f}"
    return None


def show(labels: list[str], row: list[str], label: str) -> str:
    value = first(labels, row, label)
    if value is None:
        value = derived(labels, row, label)
    return value if value is not None else "-"


def stat_table(ov: dict, view: StatView | None, season_name: str) -> dict:
    """Rows of numbers for the page, leaving out empty ones."""
    labels = stat_labels(ov)
    if view is None:
        return {"labels": [], "rows": []}
    rows = []
    for name, split in ((season_name, "Regular Season"), ("Career", "Career")):
        row = split_row(ov, split)
        if not row:
            continue
        values = [show(labels, row, label) for label in view.stats]
        if any(number(v) for v in values):
            rows.append({"name": name, "values": values})
    return {"labels": list(view.stats), "rows": rows}


def career_value(ov: dict, view: StatView | None) -> float | None:
    row = split_row(ov, "Career")
    if view is None or not row:
        return None
    return number(first(stat_labels(ov), row, view.star_stat))


def recent_games(log: dict, labels: tuple[str, ...], limit: int = 5) -> list[dict]:
    """Newest regular-season and playoff games first."""
    meta = log.get("events") or {}
    all_labels = log.get("labels") or []
    games: list[dict] = []
    for season in log.get("seasonTypes") or []:
        name = (season.get("displayName") or "").lower()
        if "preseason" in name or "spring" in name:
            continue
        for cat in season.get("categories") or []:
            if cat.get("type") != "event":
                continue
            for ev in cat.get("events") or []:
                info = meta.get(ev.get("eventId")) or {}
                row = ev.get("stats") or []
                games.append(
                    {
                        "date": info.get("gameDate"),
                        "opponent": (info.get("opponent") or {}).get("abbreviation"),
                        "at_vs": info.get("atVs"),
                        "result": info.get("gameResult"),
                        "score": info.get("score"),
                        "stats": {k: first(all_labels, row, k) for k in labels},
                    }
                )
    games.sort(key=lambda g: g["date"] or "", reverse=True)
    return games[:limit]
