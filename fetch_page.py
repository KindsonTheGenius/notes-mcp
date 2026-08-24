"""
fetch_page helper for notes-mcp — copy into notes-mcp/fetch_page.py during filming.

Fetches a URL (allowlisted), strips HTML to text, truncates for the LLM.
For demos: also serve demo/fixtures with `python -m http.server 8765`.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Keep the demo safe — expand only when you understand the risk.
ALLOWED_HOSTS = {
    "127.0.0.1",
    "localhost",
    "example.com",
    "www.example.com",
}

MAX_CHARS = 6000
TIMEOUT_SEC = 10
USER_AGENT = "AlkademyNotesMCP/0.1 (+educational demo)"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        joined = " ".join(self._chunks)
        return re.sub(r"\s+", " ", joined).strip()


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ALLOWED_HOSTS


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Fallback: crude strip
        return re.sub(r"<[^>]+>", " ", html)
    return parser.text()


def fetch_page(url: str) -> str:
    """Fetch an allowlisted URL and return truncated plain text."""
    url = (url or "").strip()
    if not url:
        return "fetch_page failed: empty url"

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "fetch_page failed: only http/https allowed"

    if not _host_allowed(url):
        allowed = ", ".join(sorted(ALLOWED_HOSTS))
        return (
            f"fetch_page failed: host not allowlisted ({parsed.hostname}). "
            f"Allowed: {allowed}"
        )

    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=TIMEOUT_SEC) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            html = raw.decode(charset, errors="replace")
    except HTTPError as exc:
        return f"fetch_page failed: HTTP {exc.code} for {url}"
    except URLError as exc:
        return f"fetch_page failed: {exc.reason}"
    except Exception as exc:
        return f"fetch_page failed: {exc}"

    text = _html_to_text(html)
    if not text:
        return f"fetch_page: no readable text from {url}"

    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 1] + "…"

    return f"source={url}\n\n{text}"
