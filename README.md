# Know Ball

A new under-the-radar player every day, so you can actually know ball. Covers
the NBA, NFL and MLB.

Each day's page has the player's background, basics, numbers, last five games,
highlights, and recent news.

## How it works

1. `.github/workflows/daily.yml` runs every morning.
2. `knowball/generate.py` rotates through each league's teams. It skips players
   it has already featured, anyone past a career stat cutoff for their position,
   and anyone whose Wikipedia lead mentions a major honor like the Pro Bowl or
   an All-Star selection. It also needs a Wikipedia article, so the page has a
   real story.
3. The result lands in `data/<sport>/latest.json`, with a dated copy and
   `history.json` beside it.
4. `ha/know-ball-card.js` reads each league's `latest.json` and renders it in
   Home Assistant.

Stats vary by position, so a player with none (an offensive lineman, say) gets
a page without the numbers section.

Sources: ESPN's public JSON endpoints, Wikipedia, and YouTube search. All three
are unofficial or best-effort. If YouTube can't be read, the page falls back to
a search link.

## Run it

Python 3.9 or newer, no dependencies.

```bash
python3 -m knowball.generate --sport nba
```

```bash
python3 -m unittest discover -s tests -t .
```

Add `--force` to rebuild a day, or `--date YYYY-MM-DD` to build a specific one.

## Add a sport

1. Add a row to `knowball/sports.py`, with a `StatView` for each kind of player
   whose stat columns differ.
2. Add its key to the `sport` matrix in `.github/workflows/daily.yml`.
3. Add the key to the card's `sports` list, or to `DEFAULT_SPORTS` in
   `ha/know-ball-card.js`.

## Home Assistant

The card lives at `/config/www/know-ball-card.js`, loaded as the Lovelace
resource `/local/know-ball-card.js?v=N`. Bump `N` after each upload.

```yaml
type: custom:know-ball-card
sports: [nba, nfl, mlb]
```

The card shows a tile per league. Tapping one opens that player's full page, and
"All leagues" goes back.
