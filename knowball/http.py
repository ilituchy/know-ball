"""Small stdlib JSON/text fetcher with retries."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

UA = "know-ball/0.1 (https://github.com/ilituchy/know-ball)"


def get_text(url: str, ua: str = UA, retries: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"giving up on {url}: {last}")


def get_json(url: str) -> dict:
    return json.loads(get_text(url))
