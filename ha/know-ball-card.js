// Know Ball: Lovelace card that shows today's player from the know-ball repo.
// Options: sport (default "nba"), url (override the JSON location).
const BASE = "https://raw.githubusercontent.com/ilituchy/know-ball/main/data";
const REFRESH_MS = 60 * 60 * 1000;

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
  .hero { display: flex; gap: 16px; align-items: flex-end; padding: 20px 20px 0;
    border-top: 5px solid var(--kb-team); position: relative; }
  .eyebrow { padding-right: 48px; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--secondary-text-color); }
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
  .msg { padding: 24px; color: var(--secondary-text-color); }
`;

class KnowBallCard extends HTMLElement {
  setConfig(config) {
    this._config = { sport: "nba", ...config };
    this._url = this._config.url || `${BASE}/${this._config.sport}/latest.json`;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
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
    return 12;
  }

  async _load() {
    try {
      const res = await fetch(`${this._url}?t=${Math.floor(Date.now() / REFRESH_MS)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this._render(await res.json());
    } catch (err) {
      if (!this._rendered) this._message(`Couldn't load today's player (${esc(err.message)}).`);
    }
  }

  _message(text) {
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="msg">${text}</div></ha-card>`;
  }

  _render(d) {
    this._rendered = true;
    const color = /^[0-9a-f]{6}$/i.test(d.team?.color || "") ? `#${d.team.color}` : "var(--primary-color)";
    const facts = Object.entries(d.facts || {}).filter(([, v]) => v !== null && v !== "");
    const stats = d.stats || {};
    const labels = stats.labels || [];
    const statRow = (name, row) =>
      row && Object.keys(row).length
        ? `<tr><td>${esc(name)}</td>${labels.map((l) => `<td>${esc(row[l] ?? "–")}</td>`).join("")}</tr>`
        : "";
    const statRows = statRow((stats.season_label || "This season").replace(/ regular season stats$/i, ""), stats.season) + statRow("Career", stats.career);
    const games = d.recent_games || [];
    const gameLabels = Object.keys(games[0]?.stats || {});
    const highlights = d.highlights || {};
    const videos = highlights.videos || [];
    const news = (d.news || []).filter((n) => safeUrl(n.url));
    const bg = d.background || {};

    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card style="--kb-team:${color}">
        <div class="hero">
          ${safeUrl(d.team?.logo) ? `<img class="logo" src="${safeUrl(d.team.logo)}" alt="">` : ""}
          ${safeUrl(d.player?.headshot) ? `<img class="shot" src="${safeUrl(d.player.headshot)}" alt="">` : ""}
          <div class="who">
            <div class="eyebrow">Know Ball · ${esc(niceDate(d.date))}</div>
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
window.customCards.push({ type: "know-ball-card", name: "Know Ball", description: "A new under-the-radar player every day" });
