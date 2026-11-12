// Know Ball: Lovelace card showing today's player for each league.
// Tapping a league's tile opens that player's full page; Back returns to the tiles.
// Options: sports (default ["nba", "nfl", "mlb"]).
const BASE = "https://raw.githubusercontent.com/ilituchy/know-ball/main/data";
const REFRESH_MS = 60 * 60 * 1000;
const DEFAULT_SPORTS = ["nba", "nfl", "mlb"];
const todayInNewYork = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => (/^https:\/\//i.test(u || "") ? esc(u) : "");
const niceDate = (iso) => {
  const [y, m, d] = String(iso).split("T")[0].split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
};
const shortDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "America/New_York" }) : "";

const STYLE = `
  ha-card { overflow: hidden; max-width: 880px; margin: 0 auto; }
  ha-card.wide { max-width: 1500px; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 290px), 1fr)); gap: 16px; padding: 16px; }
  .tile { all: unset; box-sizing: border-box; cursor: pointer; display: flex; flex-direction: column; min-width: 0;
    background: var(--secondary-background-color); border-radius: 10px; overflow: hidden;
    border-top: 4px solid var(--kb-team); }
  .tile:hover { filter: brightness(1.12); }
  .tile:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .tile img { width: min(82%, 300px); align-self: center; display: block; margin-top: 12px; }
  .tile .info { flex: 1; display: flex; flex-direction: column; gap: 12px; padding: 14px 18px 18px;
    border-top: 1px solid var(--divider-color); }
  .tile .name { font-size: 26px; font-weight: 700; line-height: 1.15; margin: 3px 0; color: var(--primary-text-color); }
  .tile .meta { font-size: 14px; color: var(--secondary-text-color); }
  .tile .bio { margin: 0; font-size: 14px; line-height: 1.45; color: var(--primary-text-color);
    display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 4; overflow: hidden; }
  .tile .mini { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 12px; margin: 0; }
  .tile .mini dt { font-size: 11px; color: var(--secondary-text-color); }
  .tile .mini dd { margin: 0; font-size: 14px; color: var(--primary-text-color); overflow-wrap: anywhere; }
  .tile .line { margin-top: auto; padding-top: 10px; border-top: 1px solid var(--divider-color); }
  .tile .season { font-size: 11px; color: var(--secondary-text-color); margin-bottom: 4px; }
  .tile .nums { display: flex; justify-content: space-between; gap: 8px; font-variant-numeric: tabular-nums; }
  .tile .nums b { display: block; font-size: 17px; font-weight: 600; color: var(--primary-text-color); }
  .tile .nums span { font-size: 11px; color: var(--secondary-text-color); }
  .tile.off { cursor: default; padding: 16px; color: var(--secondary-text-color); }
  .back { all: unset; cursor: pointer; display: inline-block; padding: 12px 20px; font-size: 14px; color: var(--primary-color); }
  .back:focus-visible { outline: 2px solid var(--primary-color); }
  .hero { display: flex; gap: 16px; align-items: flex-end; padding: 20px 20px 0;
    border-top: 5px solid var(--kb-team); position: relative; }
  .eyebrow { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--secondary-text-color); }
  h1 { font-size: clamp(26px, 6vw, 38px); line-height: 1.1; margin: 4px 0; font-weight: 700; color: var(--primary-text-color); }
  .sub { color: var(--secondary-text-color); padding-bottom: 16px; }
  .who { flex: 1; min-width: 0; align-self: center; }
  .shot { width: min(34%, 180px); display: block; flex: none; }
  .logo { position: absolute; top: 14px; right: 16px; width: 40px; height: 40px; }
  .body { padding: 0 20px 20px; border-top: 1px solid var(--divider-color); }
  h2 { font-size: 13px; letter-spacing: .06em; text-transform: uppercase; color: var(--secondary-text-color);
    margin: 22px 0 10px; font-weight: 600; }
  h3 { font-size: 15px; margin: 14px 0 2px; color: var(--primary-text-color); font-weight: 600; }
  p { margin: 0 0 6px; line-height: 1.55; color: var(--primary-text-color); }
  .facts { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 150px), 1fr)); gap: 10px 16px; }
  .facts dt { font-size: 12px; color: var(--secondary-text-color); }
  .facts dd { margin: 0; color: var(--primary-text-color); }
  table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th { font-size: 12px; font-weight: 500; color: var(--secondary-text-color); }
  th, td { padding: 6px 4px; text-align: right; color: var(--primary-text-color); }
  thead th { color: var(--secondary-text-color); }
  th:first-child, td:first-child { text-align: left; }
  tbody tr { border-top: 1px solid var(--divider-color); }
  .scroll { overflow-x: auto; }
  .win { color: var(--success-color, #43a047); }
  .loss { color: var(--error-color, #db4437); }
  .vids { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr)); gap: 12px; }
  .vids a { text-decoration: none; color: var(--primary-text-color); font-size: 13px; line-height: 1.35; }
  .vids img { width: 100%; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 8px; display: block; margin-bottom: 6px; }
  ul { margin: 0; padding: 0; list-style: none; }
  li { padding: 6px 0; }
  a { color: var(--primary-color); }
  .foot { font-size: 12px; color: var(--secondary-text-color); margin-top: 20px; }
`;

// Wikipedia's first sentence is mostly name and team, which the tile already shows.
// Short intros borrow from the next sections so the tile still has a story.
const TEASER_CHARS = 220;
const teaser = (d) => {
  const [intro, ...rest] = (d.background?.sections || []).map((s) => s.text || "");
  if (!intro) return "";
  let text = intro.replace(/^.{40,}?[a-z)]\. (?=[A-Z])/, "") || intro;
  for (const more of rest) {
    if (text.length >= TEASER_CHARS) break;
    text += ` ${more}`;
  }
  return text;
};
const TILE_FACTS = ["Age", "Height", "From", "College", "Draft"];
const TILE_STATS = 5;

const teamColor = (d) => (/^[0-9a-f]{6}$/i.test(d.team?.color || "") ? `#${d.team.color}` : "var(--primary-color)");

class KnowBallCard extends HTMLElement {
  setConfig(config) {
    this._sports = config.sports || DEFAULT_SPORTS;
    this._data = {};
    this._open = null;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
    }
  }

  set hass(_hass) {
    if (!this._started) {
      this._started = true;
      this._load();
    }
  }

  connectedCallback() {
    this._timer = setInterval(() => this._load(), REFRESH_MS);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  getCardSize() {
    return 6;
  }

  async _load() {
    const stamp = Math.floor(Date.now() / REFRESH_MS);
    await Promise.all(
      this._sports.map(async (sport) => {
        try {
          // Pages are built a day ahead; latest.json covers a missed day.
          let res = await fetch(`${BASE}/${sport}/${todayInNewYork()}.json?t=${stamp}`);
          if (!res.ok) res = await fetch(`${BASE}/${sport}/latest.json?t=${stamp}`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          this._data[sport] = await res.json();
        } catch (err) {
          // Keep yesterday's page if a refresh fails; a tile says so otherwise.
          console.warn("know-ball", sport, err);
        }
      })
    );
    this._draw();
  }

  _onClick(event) {
    const target = event.composedPath().find((el) => el.dataset?.open !== undefined || el.dataset?.back !== undefined);
    if (!target) return;
    this._open = target.dataset.open ?? null;
    this._draw();
    this.scrollIntoView({ block: "start" });
  }

  _draw() {
    const page = this._data[this._open];
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>${page ? this._detail(page) : this._tiles()}`;
    this.shadowRoot.querySelector("[data-back]")?.focus();
  }

  _tiles() {
    const tiles = this._sports.map((sport) => {
      const d = this._data[sport];
      if (!d) return `<div class="tile off">${esc(sport.toUpperCase())}: today's player didn't load.</div>`;
      return `<button class="tile" data-open="${esc(sport)}" style="--kb-team:${teamColor(d)}"
          aria-label="${esc(d.league)}: ${esc(d.player?.name)}">
        ${safeUrl(d.player?.headshot) ? `<img src="${safeUrl(d.player.headshot)}" alt="">` : ""}
        <div class="info">
          <div class="eyebrow">${esc(d.league)}</div>
          <div>
            <div class="name">${esc(d.player?.name)}</div>
            <div class="meta">${esc(d.team?.name)} · ${esc(d.player?.position)}</div>
          </div>
          ${teaser(d) ? `<p class="bio">${esc(teaser(d))}</p>` : ""}
          <dl class="mini">${TILE_FACTS.filter((k) => d.facts?.[k]).map((k) => `<div><dt>${esc(k)}</dt><dd>${esc(d.facts[k])}</dd></div>`).join("")}</dl>
          ${this._numbers(d)}
        </div>
      </button>`;
    });
    return `<ha-card class="wide"><div class="tiles">${tiles.join("")}</div></ha-card>`;
  }

  _numbers(d) {
    const row = d.stats?.rows?.[0];
    if (!row) return "";
    const cells = (d.stats.labels || [])
      .slice(0, TILE_STATS)
      .map((label, i) => `<div><b>${esc(row.values[i])}</b><span>${esc(label)}</span></div>`);
    return `<div class="line"><div class="season">${esc(row.name)}</div><div class="nums">${cells.join("")}</div></div>`;
  }

  _detail(d) {
    const facts = Object.entries(d.facts || {}).filter(([, v]) => v !== null && v !== "");
    const stats = d.stats || {};
    const labels = stats.labels || [];
    const statRows = (stats.rows || [])
      .map((r) => `<tr><td>${esc(r.name)}</td>${r.values.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`)
      .join("");
    const games = d.recent_games || [];
    const gameLabels = Object.keys(games[0]?.stats || {});
    const highlights = d.highlights || {};
    const videos = highlights.videos || [];
    const news = (d.news || []).filter((n) => safeUrl(n.url));
    const bg = d.background || {};

    return `<ha-card style="--kb-team:${teamColor(d)}">
        <button class="back" data-back aria-label="Back to all leagues">← All leagues</button>
        <div class="hero">
          ${safeUrl(d.team?.logo) ? `<img class="logo" src="${safeUrl(d.team.logo)}" alt="">` : ""}
          ${safeUrl(d.player?.headshot) ? `<img class="shot" src="${safeUrl(d.player.headshot)}" alt="">` : ""}
          <div class="who">
            <div class="eyebrow" style="padding-right:48px">${esc(d.league)} · ${esc(niceDate(d.date))}</div>
            <h1>${esc(d.player?.name)}</h1>
            <div class="sub">${esc(d.team?.name)} · ${esc(d.player?.position)}${d.player?.jersey ? ` · ${esc(d.player.jersey)}` : ""}</div>
          </div>
        </div>
        <div class="body">
          <h2>The basics</h2>
          <dl class="facts">${facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>
          ${(bg.sections || []).length ? `<h2>Background</h2>` : ""}
          ${(bg.sections || []).map((s, i) => `${i ? `<h3>${esc(s.heading)}</h3>` : ""}<p>${esc(s.text)}</p>`).join("")}
          ${statRows ? `<h2>Numbers</h2><div class="scroll"><table>
            <thead><tr><th></th>${labels.map((l) => `<th>${esc(l)}</th>`).join("")}</tr></thead>
            <tbody>${statRows}</tbody></table></div>` : ""}
          ${games.length ? `<h2>Last ${games.length} games</h2><div class="scroll"><table>
            <thead><tr><th>Game</th><th>Result</th>${gameLabels.map((l) => `<th>${esc(l)}</th>`).join("")}</tr></thead>
            <tbody>${games.map((g) => `<tr><td>${esc(shortDate(g.date))} ${esc(g.at_vs)} ${esc(g.opponent)}</td>
              <td class="${g.result === "W" ? "win" : g.result === "L" ? "loss" : ""}">${esc(g.result)} ${esc(g.score)}</td>
              ${gameLabels.map((l) => `<td>${esc(g.stats[l] ?? "–")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : ""}
          <h2>Highlights</h2>
          ${videos.length ? `<div class="vids">${videos.map((v) => {
            const id = encodeURIComponent(v.id);
            return `<a href="https://www.youtube.com/watch?v=${id}" target="_blank" rel="noreferrer">
              <img src="https://i.ytimg.com/vi/${id}/hqdefault.jpg" alt="" loading="lazy">${esc(v.title)}</a>`;
          }).join("")}</div>` : ""}
          ${safeUrl(highlights.search_url) ? `<p style="margin-top:10px"><a href="${safeUrl(highlights.search_url)}" target="_blank" rel="noreferrer">More on YouTube</a></p>` : ""}
          ${news.length ? `<h2>In the news</h2><ul>${news.map((n) => `<li><a href="${safeUrl(n.url)}" target="_blank" rel="noreferrer">${esc(n.headline)}</a></li>`).join("")}</ul>` : ""}
          <div class="foot">Stats from ESPN.${safeUrl(bg.url) ? ` Background from <a href="${safeUrl(bg.url)}" target="_blank" rel="noreferrer">Wikipedia</a>.` : ""}</div>
        </div>
      </ha-card>`;
  }
}

if (!customElements.get("know-ball-card")) customElements.define("know-ball-card", KnowBallCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "know-ball-card", name: "Know Ball", description: "A new under-the-radar player every day, by league" });
