"""One entry per sport. Adding a league should only need a new row here."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatView:
    """Which numbers matter for one kind of player.

    ESPN's stat columns differ by position, so a view is chosen by looking for
    `key` in a player's first two columns.
    """

    key: str
    stats: tuple[str, ...]  # columns to show, in order
    games: tuple[str, ...]  # game-log columns to show, in order
    star_stat: str  # career column used to spot established players
    star_cutoff: float  # at or above this counts as "known"


@dataclass(frozen=True)
class Sport:
    key: str  # data/<key>/ and the card's `sport:` option
    label: str
    espn_path: str  # ESPN's "<sport>/<league>" path
    wiki_keyword: str  # used to find the right Wikipedia article
    fame_words: tuple[str, ...]  # any of these in the article's lead rules a player out
    views: tuple[StatView, ...]
    skip_groups: tuple[str, ...] = ()  # roster groups to ignore
    # ESPN leaves draft blank for some drafted baseball players, so a blank
    # only means "undrafted" where its draft data is complete.
    blank_draft_means_undrafted: bool = True

    def view_for(self, labels: list[str]) -> StatView | None:
        return next((v for v in self.views if v.key in labels[:2]), None)


SPORTS = {
    "nba": Sport(
        key="nba",
        label="NBA",
        espn_path="basketball/nba",
        wiki_keyword="basketball",
        fame_words=("All-Star", "All-NBA", "MVP", "Most Valuable Player"),
        views=(
            StatView(
                key="GP",
                stats=("GP", "MIN", "PTS", "REB", "AST", "FG%", "3P%"),
                games=("MIN", "PTS", "REB", "AST"),
                star_stat="PTS",
                star_cutoff=14.0,
            ),
        ),
    ),
    "nfl": Sport(
        key="nfl",
        label="NFL",
        espn_path="football/nfl",
        wiki_keyword="football",
        fame_words=("Pro Bowl", "All-Pro", "MVP", "Most Valuable Player", "Heisman"),
        skip_groups=("practiceSquad", "suspended"),
        views=(
            StatView(
                key="CMP",
                stats=("CMP", "ATT", "CMP%", "YDS", "TD", "INT", "RTG"),
                games=("CMP", "ATT", "YDS", "TD", "INT"),
                star_stat="YDS",
                star_cutoff=12000,
            ),
            StatView(
                key="CAR",
                stats=("CAR", "YDS", "AVG", "TD", "REC"),
                games=("CAR", "YDS", "TD", "REC"),
                star_stat="YDS",
                star_cutoff=3000,
            ),
            StatView(
                key="REC",
                stats=("REC", "TGTS", "YDS", "AVG", "TD"),
                games=("REC", "TGTS", "YDS", "TD"),
                star_stat="YDS",
                star_cutoff=3000,
            ),
            StatView(
                key="TOT",
                stats=("TOT", "SOLO", "SACK", "FF", "INT", "PD"),
                games=("TOT", "SOLO", "SACK", "INT"),
                star_stat="TOT",
                star_cutoff=400,
            ),
        ),
    ),
    "mlb": Sport(
        key="mlb",
        label="MLB",
        espn_path="baseball/mlb",
        wiki_keyword="baseball",
        blank_draft_means_undrafted=False,
        fame_words=(
            "All-Star",
            "Gold Glove",
            "Silver Slugger",
            "Cy Young",
            "MVP",
            "Most Valuable Player",
        ),
        views=(
            StatView(
                key="AB",
                stats=("GP", "AB", "H", "AVG", "HR", "RBI", "BB", "SO"),
                games=("AB", "H", "HR", "RBI"),
                star_stat="H",
                star_cutoff=1000,
            ),
            StatView(
                key="GS",
                stats=("GP", "GS", "IP", "ERA", "BB", "K"),
                games=("IP", "H", "ER", "K"),
                star_stat="K",
                star_cutoff=1000,
            ),
        ),
    ),
}
