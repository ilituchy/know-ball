"""Non-ESPN sources: Wikipedia background and YouTube highlights.

Both are best-effort. A failure here should thin out the page, not stop it.
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse

from .http import get_json, get_text

WIKI = "https://en.wikipedia.org/w/api.php"
MAX_SECTION_CHARS = 700
BACKGROUND_SECTIONS = ("early", "high school", "college", "personal")
SUFFIXES = ("jr", "sr", "ii", "iii", "iv", "v")
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def plain(text: str) -> str:
    """Lowercase without accents, so Garcia matches García."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def surname(name: str) -> str:
    words = [w for w in plain(name).split() if w.strip(".") not in SUFFIXES]
    return words[-1]


def wikipedia(name: str, keyword: str, birth_year: str | None = None) -> dict | None:
    """Return the useful sections of the article about this athlete, if any."""
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f'"{name}" {keyword} player',
            "gsrlimit": 5,
            "prop": "description",
        }
    )
    pages = (get_json(f"{WIKI}?{query}").get("query") or {}).get("pages") or {}
    last = surname(name)
    for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        desc = (page.get("description") or "").lower()
        if keyword not in desc or last not in plain(page.get("title", "")):
            continue
        born = re.search(r"born (\d{4})", desc)
        if born and birth_year and born.group(1) != birth_year:
            continue  # a different player with the same name
        return article(page["pageid"])
    return None


def article(page_id: int) -> dict | None:
    # Full-text extracts come back for one page per request, so this is a
    # separate call from the search above.
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "pageids": page_id,
            "prop": "extracts|info",
            "inprop": "url",
            "explaintext": 1,
        }
    )
    page = get_json(f"{WIKI}?{query}")["query"]["pages"][str(page_id)]
    if not page.get("extract"):
        return None
    return {
        "sections": parse_sections(page["extract"]),
        "url": page.get("fullurl"),
        "title": page.get("title"),
    }


def trim(paragraphs: list[str], limit: int = MAX_SECTION_CHARS) -> str:
    """Join paragraphs and cut at a sentence end near the limit."""
    text = " ".join(paragraphs)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind('." '))
    return cut[: end + 1] if end > 0 else cut.rstrip() + "…"


def parse_sections(extract: str) -> list[dict]:
    """Turn a plain-text article into the few sections worth reading."""
    chunks = re.split(r"^==\s*([^=]+?)\s*==\s*$", extract, flags=re.M)
    sections = [{"heading": "The short version", "text": trim(paragraphs_of(chunks[0]))}]
    for heading, body in zip(chunks[1::2], chunks[2::2]):
        paragraphs = paragraphs_of(body)
        if not paragraphs:
            continue
        low = heading.lower()
        if "professional" in low or "career" == low:
            # Careers run long and oldest first, so the ending is the news.
            sections.append({"heading": "Lately", "text": trim(paragraphs[-2:])})
        elif any(word in low for word in BACKGROUND_SECTIONS):
            sections.append({"heading": heading, "text": trim(paragraphs)})
    return sections


def paragraphs_of(text: str) -> list[str]:
    """Paragraphs of a section, dropping any === subheadings ==="""
    lines = (line.strip() for line in text.split("\n"))
    return [ln for ln in lines if ln and not ln.startswith("=")]


def youtube_search_url(query: str) -> str:
    return "https://www.youtube.com/results?" + urllib.parse.urlencode(
        {"search_query": query}
    )


def parse_youtube_results(page: str, name: str, limit: int = 3) -> list[dict]:
    """Pull video ids and titles out of a results page's embedded JSON."""
    match = re.search(r"ytInitialData\s*=\s*(\{.*?\});</script>", page, re.S)
    if not match:
        return []
    last = surname(name)
    found: list[dict] = []
    seen: set[str] = set()

    def walk(node: object) -> None:
        if len(found) >= limit:
            return
        if isinstance(node, dict):
            video = node.get("videoRenderer")
            if isinstance(video, dict):
                vid = video.get("videoId")
                runs = (video.get("title") or {}).get("runs") or [{}]
                title = runs[0].get("text", "")
                if vid and vid not in seen and last in plain(title):
                    seen.add(vid)
                    found.append({"id": vid, "title": title})
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    try:
        walk(json.loads(match.group(1)))
    except json.JSONDecodeError:
        return []
    return found


def highlights(name: str, label: str) -> dict:
    query = f"{name} {label} highlights"
    url = youtube_search_url(query)
    try:
        videos = parse_youtube_results(get_text(url, ua=BROWSER_UA, retries=1), name)
    except Exception:
        videos = []
    return {"search_url": url, "videos": videos}
