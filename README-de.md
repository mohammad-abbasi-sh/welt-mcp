# welt-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/welt-mcp

Inoffizieller **Read-only**-MCP-Server für **[WELT](https://www.welt.de)** — eine der größten Tageszeitungen Deutschlands — über den offiziellen RSS-Feed auf [www.welt.de/feeds/latest.rss](https://www.welt.de/feeds/latest.rss) und Artikelseiten, deren Volltext aus dem JSON-LD-`articleBody` gelesen wird. Top-Schlagzeilen, Nachrichten nach Thema (Deutschland, Ausland, Fußball, Kultur, …), Stichwortsuche, die neuesten Video-Beiträge und Volltexte von Artikeln. Kein Schlüssel, kein Login.

> Gebaut von Mohammad Abbasi als Teil der "Germany MCP factory" (Sepehr-ähnliche Pipeline). Nicht mit WELT oder Axel Springer verbunden.

## Für KI-Agenten

In die MCP-Client-Konfiguration eintragen (stdio):

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

Oder lokal starten: `python -m welt_mcp.server` (benötigt `mcp<2`, `httpx`).

## Tools

| Tool | Beschreibung |
|------|-------------|
| `welt_headlines` | Top-Schlagzeilen (offizieller RSS-Feed, 30 Einträge), neueste zuerst — `limit` 1..50 |
| `welt_news_by_topic` | Neueste Nachrichten zu einem Thema — `topic`: "Deutschland", "Ausland", "Fußball", "Kultur", "Film", "Debatte", "Eishockey", … (Teilstring, Groß-/Kleinschreibung egal), `limit` 1..50 |
| `welt_search_news` | Stichwortsuche in den Nachrichten (Titel + Teaser) — `query` (z. B. "Bundestag"), `limit` 1..50 |
| `welt_latest_videos` | Neueste Video-Beiträge aus dem Feed (subtype "video"), neueste zuerst — `limit` 1..50 |
| `welt_get_article` | Volltext einer WELT-Artikelseite (JSON-LD `articleBody`) — `url`: eine www.welt.de-Artikel-URL (mit /article). WELT+-Artikel liefern `paywalled: true` und nur den Teaser |
| `welt_health` | Erreichbarkeitsprüfung (ok / blocked / error) — eine höfliche Anfrage |

Beispielausgabe (`welt_headlines`, `limit` 2):

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

Hinweise:
- Der Server liest den **offiziellen RSS-Feed** (30 Einträge, live verifiziert 2026-11-18). Suche und Themenfilter laufen clientseitig über den geladenen Feed. Jeder Eintrag trägt das `<welt:premium>`-Flag des Feeds und den `<welt:subType>` (news / video / opinion).
- **Ehrlichkeit zur Paywall:** WELT+-Artikel (Premium) zeigen im JSON-LD nur ihren Teaser — `articleBody` entspricht der Beschreibung (ca. 200 Zeichen, an 3 Premium-Artikeln verifiziert). `welt_get_article` liefert für diese `paywalled: true` mit dem Teaser, niemals erfundenen Text. Kostenlose Artikel liefern den Volltext (1.500–3.900 Zeichen in den Stichproben). Kurze Agenturmeldungen können ebenfalls nur aus dem Teaser bestehen (`teaser_only: true`, `paywalled: false`) — der Teaser ist dann der gesamte frei verfügbare Text.
- Ressort-Feeds gibt es nicht: `/feeds/<ressort>.rss` liefert 404 für jedes getestete Ressort (politik, wirtschaft, sport, kultur, …); der einzige Feed ist `latest.rss`, und Themen sind dessen `<category>`-Werte.
- Daten: öffentlicher WELT-RSS-Feed und Artikelseiten — kein Schlüssel, kein Login, nur lesend.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parst den echten, gespeicherten RSS-Feed sowie eine kostenlose und eine WELT+-Artikelseite
- `tests/test_live.py` — vorsichtige Live-Anfragen an www.welt.de

Tests: 41/41 grün (34 offline + 7 live, 2026-11-18).

## Lizenz

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — frei für private und nicht-kommerzielle Nutzung; kommerzielle Nutzung braucht eine separate Lizenz (siehe LICENSE).

---

Gebaut von [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
