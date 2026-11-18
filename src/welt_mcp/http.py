"""HTTP layer for welt_mcp — plain httpx GETs against www.welt.de.

Two endpoints, both public, no key, no login:
- the official RSS feed: https://www.welt.de/feeds/latest.rss
- article pages: https://www.welt.de/.../article<hex>/... (free) or
  /plus<hex>/... (WELT+ premium) — the full text is in the JSON-LD
  articleBody; see domain.parse_article.

Only www.welt.de is ever fetched, and article fetches are restricted
to /article<hex>/ URLs from the feed or passed by the caller.
"""
from __future__ import annotations

import os
import ssl
import time
from urllib.parse import urlparse

import httpx

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 25.0
ALLOWED_HOST = "www.welt.de"


class WeltError(RuntimeError):
    pass


def _verify():
    """TLS trust store: the OS bundle when present, else httpx/certifi.

    The OS bundle matters behind MITM egress proxies (their CA is in the
    system store, not in certifi) and is the right default on Linux
    anyway; on systems without it we fall back to certifi.
    """
    for path in (
        "/etc/ssl/certs/ca-certificates.crt",
        ssl.get_default_verify_paths().openssl_cafile,
    ):
        if path and os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return True


def _client(accept: str) -> httpx.Client:
    # NOTE: we read the proxy URL from the environment but never log it.
    # trust_env=False because httpx fails to parse bracketed IPv6 entries
    # (e.g. [::1]) that some environments put in no_proxy.
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    return httpx.Client(
        headers={"User-Agent": UA, "Accept": accept},
        timeout=TIMEOUT,
        proxy=proxy or None,
        trust_env=False,
        verify=_verify(),
        follow_redirects=True,
    )


def _check_host(url: str) -> None:
    host = (urlparse(url).netloc or "").lower()
    if host != ALLOWED_HOST:
        raise WeltError(
            f"only {ALLOWED_HOST} pages are fetched (got {host or url!r})"
        )


def _get(url: str, accept: str) -> str:
    """GET with one retry on 429/5xx and on transient network errors."""
    _check_host(url)
    last_exc: Exception | None = None
    r: httpx.Response | None = None
    for attempt in range(2):
        try:
            with _client(accept) as c:
                r = c.get(url)
        except httpx.HTTPError as e:
            last_exc = e
            if attempt == 0:
                time.sleep(1.0)
                continue
            raise WeltError(f"network error fetching {url}: {e}") from e
        if r.status_code in (429, 500, 502, 503):
            if attempt == 0:
                time.sleep(1.0)
                continue
        break
    assert r is not None  # loop always assigns r or raises
    if r.status_code == 403:
        raise WeltError(
            f"www.welt.de returned HTTP 403 for {url} (bot wall) — try again later"
        )
    if r.status_code == 429:
        raise WeltError(
            "www.welt.de rate-limited the request (HTTP 429) — try again later"
        )
    if r.status_code != 200:
        raise WeltError(f"www.welt.de returned HTTP {r.status_code} for {url}")
    return r.text


def fetch_feed(url: str) -> str:
    """GET the official WELT RSS feed; returns the raw XML text."""
    if not urlparse(url).path.startswith("/feeds/"):
        raise WeltError(f"only /feeds/*.rss feeds are fetched (got {url!r})")
    return _get(url, "application/rss+xml, application/xml, text/xml, */*")


def fetch_article(url: str) -> str:
    """GET one www.welt.de article page; returns the raw HTML text.

    Article URLs contain "/article<hex>/" (free) or "/plus<hex>/"
    (WELT+ premium); anything else is refused so the tool cannot be
    pointed at arbitrary welt.de pages.
    """
    path = urlparse(url).path
    if "/article" not in path and "/plus" not in path:
        raise WeltError(
            "only www.welt.de article URLs (containing /article or /plus) "
            f"are fetched (got {url!r})"
        )
    return _get(url, "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")


def health_check() -> dict:
    """One polite probe of the source feed.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `welt_health` tool
    and the daily smoke CI.
    """
    url = "https://www.welt.de/feeds/latest.rss"
    try:
        fetch_feed(url)
    except WeltError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
