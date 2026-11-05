"""Choose today's player: rotate through the league, skip stars and repeats."""
from __future__ import annotations

import datetime as dt
import hashlib


def team_of_the_day(teams: list[dict], day: dt.date) -> list[dict]:
    """All teams, starting with today's. Later ones are fallbacks."""
    start = day.toordinal() % len(teams)
    return teams[start:] + teams[:start]


def shuffled(roster: list[dict], day: dt.date, sport: str) -> list[dict]:
    """A stable per-day order, so a re-run the same day picks the same player."""

    def key(player: dict) -> str:
        seed = f"{sport}:{day.isoformat()}:{player['id']}"
        return hashlib.sha256(seed.encode()).hexdigest()

    return sorted(roster, key=key)


def is_under_the_radar(career: float | None, cutoff: float) -> bool:
    """No career number means a rookie, who is unknown by definition."""
    return career is None or career < cutoff
