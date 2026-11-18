# welt-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/welt-mcp

Unofficial **read-only** MCP server for **[WELT](https://www.welt.de)** — one of Germany's biggest daily newspapers — via its official RSS feed at [www.welt.de/feeds/latest.rss](https://www.welt.de/feeds/latest.rss) and article pages, whose full text is read from the JSON-LD `articleBody`. Top headlines, news by topic (Deutschland, Ausland, Fußball, Kultur, …), keyword search, the latest video items, and full article text. No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory" (Sepehr-style pipeline). Not affiliated with WELT or Axel Springer.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "welt": {
      "command": "uvx",
      "args": ["welt-mcp==0.1.0"]
    }
  }
}
```

Or run locally: `python -m welt_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `welt_headlines` | Top headlines (official RSS feed, 30 items), newest first — `limit` 1..50 |
| `welt_news_by_topic` | Newest news of one topic — `topic`: "Deutschland", "Ausland", "Fußball", "Kultur", "Film", "Debatte", "Eishockey", … (case-insensitive substring match), `limit` 1..50 |
| `welt_search_news` | Search news by keyword (title + teaser) in the feed — `query` (e.g. "Bundestag"), `limit` 1..50 |
| `welt_latest_videos` | Latest video items from the feed (subtype "video"), newest first — `limit` 1..50 |
| `welt_get_article` | Full text of one WELT article page (JSON-LD `articleBody`) — `url`: a www.welt.de article URL (containing /article or /plus). WELT+ articles return `paywalled: true` with the teaser only |
| `welt_health` | Reachability probe (ok / blocked / error) — one polite request |

Example output (`welt_headlines`, `limit` 2):

```json
{"feed_title": "Nachrichten - WELT", "total_results": 30, "count": 2,
 "items": [
  {"title": "Baugenehmigungen in Deutschland brechen im September deutlich ein – doch Jahresbilanz bleibt positiv",
   "link": "https://www.welt.de/politik/deutschland/article6afd6d12fc384ca056385c40/baugenehmigungen-in-deutschland-brechen-im-september-deutlich-ein-doch-jahresbilanz-bleibt-positiv.html",
   "description": "Der Aufwärtstrend im deutschen Wohnungsbau ist gestoppt: Die Zahl der genehmigten Wohnungen sank im September um knapp 15 Prozent. Höhere Zinsen und Baukosten belasten die Branche.",
   "author": "Till Henniges", "published": "2026-11-18T10:10:03+00:00", "category": "Deutschland",
   "topic": "Jahresvergleich", "premium": false, "subtype": "news",
   "image": "https://images.welt.de/6afd6d12fc384ca056385c40/771566a806d7370faa5b330a76bd385b-master/ci23x11-w1200/dpa-com-261030-935-1707967-jpg"},
  ...]}
```

Notes:
- The server reads the **official RSS feed** (30 items, verified live 2026-11-18). Search and topic filters run client-side over the fetched feed. Each item carries the feed's own `<welt:premium>` flag and `<welt:subType>` (news / video / opinion).
- **Paywall honesty:** WELT+ (premium) articles expose only their teaser in the JSON-LD — `articleBody` equals the description (~200 chars, verified on 3 premium items). `welt_get_article` returns `paywalled: true` with the teaser for those, never fabricated text. Free articles return the full body (1,500–3,900 chars in the sampled items). Short agency flashes can also be teaser-only (`teaser_only: true`, `paywalled: false`) — the teaser is then the whole freely available text.
- Section feeds do not exist: `/feeds/<section>.rss` is 404 for every section tried (politik, wirtschaft, sport, kultur, …); the single `latest.rss` feed is the only feed, and topics are its `<category>` values.
- Data: WELT public RSS feed and article pages — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parses the real captured RSS feed + one free and one WELT+ article page
- `tests/test_live.py` — cautious live requests against www.welt.de

Tests: 41/41 green (34 offline + 7 live, 2026-11-18).

## License

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — free for personal and non-commercial use; commercial use needs a separate license (see LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
