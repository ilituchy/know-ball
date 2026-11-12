import datetime as dt
import json
import unittest

from knowball import enrich, espn, generate, picker
from knowball.sports import SPORTS, StatView

DAY = dt.date(2026, 11, 5)


class Picker(unittest.TestCase):
    def test_rotation_keeps_every_team_and_moves_daily(self):
        teams = [{"id": str(i)} for i in range(30)]
        today = picker.team_of_the_day(teams, DAY)
        tomorrow = picker.team_of_the_day(teams, DAY + dt.timedelta(days=1))
        self.assertEqual(len(today), 30)
        self.assertEqual({t["id"] for t in today}, {t["id"] for t in teams})
        self.assertNotEqual(today[0], tomorrow[0])

    def test_shuffle_is_stable_within_a_day(self):
        roster = [{"id": str(i)} for i in range(15)]
        self.assertEqual(
            picker.shuffled(roster, DAY, "nba"),
            picker.shuffled(list(reversed(roster)), DAY, "nba"),
        )

    def test_star_filter(self):
        self.assertTrue(picker.is_under_the_radar(6.4, 14))
        self.assertTrue(picker.is_under_the_radar(None, 14))
        self.assertFalse(picker.is_under_the_radar(14.0, 14))
        self.assertTrue(picker.is_famous("a two-time pro bowl pick", ("Pro Bowl",)))
        self.assertFalse(picker.is_famous("a backup guard", ("Pro Bowl",)))
        nba = SPORTS["nba"].fame_words
        self.assertTrue(picker.is_famous("the NBA Defensive Player of the Year in 2022", nba))


class Schedule(unittest.TestCase):
    def test_builds_a_day_ahead(self):
        self.assertEqual(
            generate.days_to_build(DAY), [DAY, DAY + dt.timedelta(days=1)]
        )

    def test_latest_never_points_at_tomorrow(self):
        import pathlib
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp)
            for day in ("2026-11-04", "2026-11-05", "2026-11-06"):
                (folder / f"{day}.json").write_text(day)
            generate.point_latest(folder, DAY)
            self.assertEqual((folder / "latest.json").read_text(), "2026-11-05")


class Espn(unittest.TestCase):
    VIEW = StatView("GP", ("GP", "PTS"), ("PTS",), "PTS", 14)
    OV = {
        "statistics": {
            "labels": ["GP", "PTS"],
            "splits": [
                {"displayName": "Regular Season", "stats": ["54", "6.4"]},
                {"displayName": "Career", "stats": ["176", "1,007.4"]},
            ],
        }
    }

    def test_table_and_career(self):
        table = espn.stat_table(self.OV, self.VIEW, "2026-27")
        self.assertEqual(table["rows"][0], {"name": "2026-27", "values": ["54", "6.4"]})
        self.assertEqual(espn.career_value(self.OV, self.VIEW), 1007.4)
        self.assertIsNone(espn.career_value({}, self.VIEW))

    def test_repeated_labels_use_the_first_column(self):
        labels = ["REC", "YDS", "CAR", "YDS"]
        self.assertEqual(espn.first(labels, ["10", "95", "3", "12"], "YDS"), "95")

    def test_empty_rows_are_dropped(self):
        ov = {"statistics": {"labels": ["GP", "PTS"],
                             "splits": [{"displayName": "Career", "stats": ["-", "0.0"]}]}}
        self.assertEqual(espn.stat_table(ov, self.VIEW, "2026")["rows"], [])

    def test_baseball_rates(self):
        bat = ["GP", "AB", "H"]
        self.assertEqual(espn.derived(bat, ["10", "400", "120"], "AVG"), ".300")
        pit = ["IP", "ER"]
        self.assertEqual(espn.derived(pit, ["12.2", "7"], "ERA"), "4.97")

    def test_views_pick_by_position(self):
        nfl = SPORTS["nfl"]
        self.assertEqual(nfl.view_for(["CAR", "YDS", "REC"]).key, "CAR")
        self.assertEqual(nfl.view_for(["REC", "TGTS", "CAR"]).key, "REC")
        self.assertIsNone(nfl.view_for([]))
        self.assertEqual(SPORTS["mlb"].view_for(["GP", "GS", "IP"]).key, "GS")
        self.assertEqual(SPORTS["mlb"].view_for(["GP", "AB", "R"]).key, "AB")

    def test_recent_games_skips_preseason_and_sorts_newest_first(self):
        log = {
            "labels": ["MIN", "PTS"],
            "events": {
                "1": {"gameDate": "2026-10-30T00:00Z"},
                "2": {"gameDate": "2026-11-02T00:00Z"},
                "3": {"gameDate": "2026-10-10T00:00Z"},
            },
            "seasonTypes": [
                {
                    "displayName": "2026-27 Regular Season",
                    "categories": [
                        {"type": "event", "events": [
                            {"eventId": "1", "stats": ["20", "8"]},
                            {"eventId": "2", "stats": ["25", "12"]},
                        ]},
                        {"type": "total", "events": []},
                    ],
                },
                {
                    "displayName": "2026-27 Preseason",
                    "categories": [{"type": "event", "events": [
                        {"eventId": "3", "stats": ["10", "2"]},
                    ]}],
                },
            ],
        }
        games = espn.recent_games(log, ("PTS",))
        self.assertEqual([g["stats"]["PTS"] for g in games], ["12", "8"])


class Wikipedia(unittest.TestCase):
    ARTICLE = (
        "Intro line.\n\n\n== Early life ==\nGrew up nearby.\n\n"
        "== Professional career ==\n\n=== Team A (2020) ===\nFirst stop.\n\n"
        "=== Team B (2024) ===\nSecond stop.\nThird stop.\n\n"
        "== Career statistics ==\nTable text.\n"
    )

    def test_keeps_useful_sections_only(self):
        self.assertEqual(
            enrich.parse_sections(self.ARTICLE),
            [
                {"heading": "The short version", "text": "Intro line."},
                {"heading": "Early life", "text": "Grew up nearby."},
                {"heading": "Lately", "text": "Second stop. Third stop."},
            ],
        )

    def test_trim_ends_on_a_sentence(self):
        self.assertEqual(enrich.trim(["One two. Three four five."], 12), "One two.")


class Names(unittest.TestCase):
    def test_surname_handles_suffixes_and_accents(self):
        self.assertEqual(enrich.surname("Luis García Jr."), "garcia")
        self.assertEqual(enrich.surname("Naji Marshall"), "marshall")


class YouTube(unittest.TestCase):
    def test_keeps_only_videos_about_the_player(self):
        data = {"a": [
            {"videoRenderer": {"videoId": "aaa", "title": {"runs": [{"text": "Jalen Wilson mix"}]}}},
            {"videoRenderer": {"videoId": "bbb", "title": {"runs": [{"text": "Top 10 dunks"}]}}},
        ]}
        page = f"<script>var ytInitialData = {json.dumps(data)};</script>"
        self.assertEqual(
            enrich.parse_youtube_results(page, "Jalen Wilson"),
            [{"id": "aaa", "title": "Jalen Wilson mix"}],
        )

    def test_unparseable_page_is_empty(self):
        self.assertEqual(enrich.parse_youtube_results("<html>", "X"), [])


if __name__ == "__main__":
    unittest.main()
