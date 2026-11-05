"""One entry per sport. Adding a league should only need a new row here."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sport:
    key: str  # data/<key>/ and the card's `sport:` option
    label: str
    espn_path: str  # ESPN's "<sport>/<league>" path
    wiki_keyword: str  # used to find the right Wikipedia article
    star_stat: str  # stat name in ESPN's overview `names` list
    star_cutoff: float  # career value at or above this counts as "known"
    stats: tuple[str, ...]  # ESPN labels to show, in order
    game_stats: tuple[str, ...]  # game-log labels to show, in order


SPORTS = {
    "nba": Sport(
        key="nba",
        label="NBA",
        espn_path="basketball/nba",
        wiki_keyword="basketball",
        star_stat="avgPoints",
        star_cutoff=14.0,
        stats=("GP", "MIN", "PTS", "REB", "AST", "FG%", "3P%"),
        game_stats=("MIN", "PTS", "REB", "AST"),
    ),
}
