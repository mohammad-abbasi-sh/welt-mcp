"""MCP server: unofficial read-only access to WELT (welt.de) — one of
Germany's biggest daily newspapers — via its official RSS feed at
www.welt.de/feeds/latest.rss and article pages (JSON-LD articleBody).
No key, no login."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import domain as _dom
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for WELT (welt.de) — one of Germany's
biggest daily newspapers — via its official RSS feed
(www.welt.de/feeds/latest.rss, no key, no login) and article pages,
whose full text is read from the JSON-LD articleBody. Top headlines,
news by topic (Deutschland, Ausland, Fußball, Kultur, …), keyword
search, the latest video items, and full article text. NOTE: WELT+
(premium) articles expose only their teaser — get_article returns
paywalled=true with the teaser for those, never fabricated text;
short agency flashes can also be teaser-only (teaser_only=true).
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · \
https://mabbasi.ir — Germany MCP factory.\
"""


_SOURCE = "www.welt.de"
_DISCLAIMER = "Unofficial read-only data from WELT's public RSS feed and article pages; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


mcp = FastMCP("welt-mcp", instructions=INSTRUCTIONS)


def _feed(limit: int) -> dict:
    """Fetch the WELT RSS feed and return its items, newest first, capped."""
    parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
    items = parsed["items"][:limit]
    return {
        "feed_title": parsed["feed_title"],
        "total_results": parsed["count"],
        "count": len(items),
        "items": items,
    }


@mcp.tool()
def welt_headlines(limit: int = 10) -> str:
    """Top headlines from WELT (official RSS feed, 30 items), newest first.
limit: 1..50 (default 10). Items carry title, link, teaser, author,
category, topic, premium flag (WELT+), subtype (news/video/opinion),
image URL and publish time."""
    try:
        lim = _dom.validate_limit(limit)
        out = _feed(lim)
    except (_http.WeltError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def welt_news_by_topic(topic: str, limit: int = 10) -> str:
    """Newest WELT news of one topic, in feed order. topic: a feed
category such as "Deutschland", "Ausland", "Fußball", "Kultur",
"Film", "Debatte" or "Eishockey" (case-insensitive substring match;
any category string works). limit: 1..50 (default 10)."""
    try:
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
        found = _dom.filter_by_topic(parsed["items"], topic)
        out = {
            "topic": topic.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.WeltError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def welt_search_news(query: str, limit: int = 10) -> str:
    """Search WELT news by keyword (title + teaser) in the RSS feed.
query: free text, e.g. "Bundestag" or "Stromsteuer". limit: 1..50
(default 10). Searches the 30-item feed client-side, newest first,
de-duplicated by link."""
    try:
        if not (query or "").strip():
            return _ok({"error": "query must not be empty"})
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
        found = _dom.dedupe_sort(_dom.search_items(parsed["items"], query.strip()))
        out = {
            "query": query.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.WeltError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def welt_latest_videos(limit: int = 10) -> str:
    """Latest WELT video items from the RSS feed (subtype "video"),
newest first. limit: 1..50 (default 10)."""
    try:
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
        found = _dom.filter_videos(parsed["items"])
        out = {
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.WeltError, ValueError) as e:
        return _err(e)
    return _ok(out)


def _premium_flag_for(url: str) -> bool | None:
    """The feed's own <welt:premium> flag for this article URL, or
    None when the URL is not in the current 30-item feed. Best effort:
    a feed fetch failure must not block the article fetch."""
    try:
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
    except (_http.WeltError, ValueError):
        return None
    want = url.rstrip("/")
    for it in parsed["items"]:
        if (it.get("link") or "").rstrip("/") == want:
            return bool(it.get("premium"))
    return None


@mcp.tool()
def welt_get_article(url: str) -> str:
    """Full text of one WELT article page (JSON-LD articleBody).
url: a www.welt.de article URL (containing /article or /plus), e.g. from
welt_headlines. Returns title, author, publish time, the body text
and its word count. For WELT+ (premium) articles only the teaser is
freely available: paywalled=true and body holds the teaser. Short
agency flashes can be teaser-only too (teaser_only=true,
paywalled=false) — the teaser is then the whole freely available
text. Nothing is ever fabricated."""
    try:
        if not (url or "").strip():
            return _ok({"error": "url must not be empty"})
        url = url.strip()
        article = _dom.parse_article(_http.fetch_article(url))
        premium = _premium_flag_for(url)
        paywalled = premium if premium is not None else article["teaser_only"]
        note = ""
        if paywalled:
            note = (
                "WELT+ (premium) article: only the teaser is freely "
                "available; the full text is behind the paywall."
            )
        elif article["teaser_only"]:
            note = (
                "Only the teaser is available for this item (short news "
                "flash); the teaser is the whole freely available text."
            )
        out = {
            "url": url,
            "title": article["title"],
            "author": article["author"],
            "published": article["published"],
            "paywalled": paywalled,
            "teaser_only": article["teaser_only"],
            "word_count": article["word_count"],
            "body": article["body"],
            "description": article["description"],
            "note": note,
        }
    except (_http.WeltError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def welt_health() -> str:
    """Check whether the WELT RSS feed is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
