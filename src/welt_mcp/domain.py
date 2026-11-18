"""Domain logic: shape welt.de's official RSS feed and article pages
into compact dicts (stdlib only).

Data source: the official WELT RSS feed at www.welt.de/feeds/latest.rss
(30 items, no key, no login) + article pages, whose full text lives
in the JSON-LD NewsArticle/VideoObject block as "articleBody".

Honest limitation (verified live 2026-11-18): WELT+ (premium) articles
expose ONLY their teaser in the JSON-LD — articleBody == description
(~200 chars) — while free articles carry the full body (1,500-3,900
chars in the sampled items). The feed marks premium items with
<welt:premium>true</welt:premium>. get_article returns paywalled=true
+ the teaser for those, never fabricated text. Short agency flashes
(premium=false) can also have body == description: those are returned
with teaser_only=true and paywalled=false, i.e. the teaser IS the
whole freely available text.
"""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime

BASE = "https://www.welt.de"
HEADLINES_FEED = f"{BASE}/feeds/latest.rss"

_DC_NS = "{http://purl.org/dc/elements/1.1/}"
_WELT_NS = "{https://www.welt.de/spec}"
_MEDIA_NS = "{http://search.yahoo.com/mrss/}"

# Categories seen in the live feed (2026-11-18) — the feed is the
# authority; any other category string works as a topic filter too.
KNOWN_TOPICS = [
    "Deutschland", "Ausland", "Fußball", "Kultur", "Film", "Debatte",
    "Eishockey", "Wirtschaft", "Sport", "Politik", "Panorama",
    "Wissen", "Gesundheit", "Reise", "Auto", "Technik", "Meinung",
]


def validate_limit(limit: int) -> int:
    """Clamp/validate the page size (the feed carries 30 items)."""
    if not 1 <= limit <= 50:
        raise ValueError(f"limit out of range: {limit} (expected 1..50)")
    return limit


def _text(elem, tag: str) -> str:
    child = elem.find(tag)
    if child is None or child.text is None:
        return ""
    return html.unescape(child.text).strip()


def _iso(date_text: str) -> str | None:
    if not date_text:
        return None
    try:
        dt = parsedate_to_datetime(date_text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(raw: str) -> str:
    text = _TAG_RE.sub("", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def compact_item(item: ET.Element) -> dict:
    """One RSS <item>: title, link, teaser, author, category, topic,
    premium flag, subtype (news/video/opinion), image URL, publish time.

    <welt:premium> is the feed's own paywall flag. <welt:subType>
    distinguishes news / video / opinion items. The first
    media:content URL is the lead image.
    """
    premium_raw = _text(item, f"{_WELT_NS}premium").casefold()
    image_url = ""
    media = item.find(f"{_MEDIA_NS}content")
    if media is not None:
        image_url = (media.get("url") or "").strip()
    return {
        "title": _text(item, "title"),
        "link": _text(item, "link"),
        "description": _text(item, "description"),
        "author": _text(item, f"{_DC_NS}creator"),
        "published": _iso(_text(item, "pubDate")),
        "category": _text(item, "category"),
        "topic": _text(item, f"{_WELT_NS}topic"),
        "premium": premium_raw == "true",
        "subtype": _text(item, f"{_WELT_NS}subType"),
        "image": image_url,
    }


def parse_rss(xml_text: str) -> dict:
    """Parse the www.welt.de/feeds/latest.rss feed into
    {feed_title, count, items}.

    Raises ValueError on malformed XML or a non-RSS document (e.g. a
    404 error page saved as text).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"invalid RSS XML: {e}") from e
    channel = root.find("channel")
    if channel is None:
        raise ValueError("unexpected RSS shape: no <channel> element")
    items = [compact_item(it) for it in channel.findall("item")]
    return {
        "feed_title": _text(channel, "title"),
        "count": len(items),
        "items": items,
    }


_LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    re.S | re.I,
)


def _author_name(raw) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return str(raw.get("name") or "").strip()
    if isinstance(raw, list):
        names = [_author_name(a) for a in raw]
        return ", ".join(n for n in names if n)
    return ""


def parse_article(html_text: str) -> dict:
    """Extract the article from a www.welt.de article page.

    The full text lives in a JSON-LD block (NewsArticle or VideoObject)
    as "articleBody". Returns {title, description, body, author,
    published, word_count, teaser_only}. Raises ValueError when no
    JSON-LD block carries an articleBody (JS-only or error page).
    """
    for match in _LD_JSON_RE.finditer(html_text):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict) or "articleBody" not in data:
            continue
        body = (data.get("articleBody") or "").strip()
        description = _strip_tags(str(data.get("description") or ""))
        return {
            "title": _strip_tags(str(data.get("headline") or "")),
            "description": description,
            "body": body,
            "author": _author_name(data.get("author")),
            "published": str(data.get("datePublished") or "") or None,
            "word_count": len(body.split()),
            "teaser_only": bool(body) and body == description,
        }
    raise ValueError(
        "no article text found on this page (no JSON-LD articleBody) — "
        "the article may be JS-rendered or the page may be an error page"
    )


def search_items(items: list, query: str) -> list:
    """Case-insensitive substring match over title + description."""
    q = (query or "").strip().casefold()
    if not q:
        raise ValueError("query must not be empty")
    return [
        it for it in items
        if q in (it.get("title") or "").casefold()
        or q in (it.get("description") or "").casefold()
    ]


def filter_by_topic(items: list, topic: str) -> list:
    """Items whose category matches the topic (case-insensitive
    substring, so "deutschland" matches "Deutschland")."""
    t = (topic or "").strip().casefold()
    if not t:
        raise ValueError("topic must not be empty")
    return [it for it in items if t in (it.get("category") or "").casefold()]


def filter_videos(items: list) -> list:
    """Items whose subtype is "video"."""
    return [it for it in items if (it.get("subtype") or "").casefold() == "video"]


def list_topics(items: list) -> list[dict]:
    """Distinct categories in the feed with item counts, most first."""
    counts: dict[str, int] = {}
    for it in items:
        cat = (it.get("category") or "").strip()
        if cat:
            counts[cat] = counts.get(cat, 0) + 1
    return [
        {"topic": cat, "count": n}
        for cat, n in sorted(counts.items(), key=lambda kv: -kv[1])
    ]


def dedupe_sort(items: list) -> list:
    """De-duplicate by link, newest first (empty publish time sorts last)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for it in items:
        if it["link"] in seen:
            continue
        seen.add(it["link"])
        unique.append(it)
    unique.sort(key=lambda it: it.get("published") or "", reverse=True)
    return unique
