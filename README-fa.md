# welt-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/welt-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای **[WELT](https://www.welt.de)** — یکی از بزرگ‌ترین روزنامه‌های روزانهٔ آلمان — از طریق فید رسمی RSS در [www.welt.de/feeds/latest.rss](https://www.welt.de/feeds/latest.rss) و صفحات مقالات که متن کامل آن‌ها از `articleBody` در JSON-LD خوانده می‌شود. تیترهای برتر، اخبار بر اساس موضوع (Deutschland، Ausland، Fußball، Kultur و …)، جست‌وجوی کلیدواژه، تازه‌ترین ویدیوها و متن کامل مقالات. بدون کلید، بدون ورود.

> ساختهٔ محمد عباسی در چارچوب «کارخانهٔ MCP آلمان» (خط تولیدی به سبک سپهر). وابسته به WELT یا Axel Springer نیست.

## برای ایجنت‌های هوش مصنوعی

در پیکربندی کلاینت MCP اضافه کنید (stdio):

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

یا اجرای محلی: `python -m welt_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------|
| `welt_headlines` | تیترهای برتر (فید رسمی RSS، ۳۰ مورد)، تازه‌ترین اول — `limit` ۱ تا ۵۰ |
| `welt_news_by_topic` | تازه‌ترین اخبار یک موضوع — `topic`: ‏«Deutschland»، ‏«Ausland»، ‏«Fußball»، ‏«Kultur»، ‏«Film»، ‏«Debatte»، ‏«Eishockey» و … (تطبیق زیررشته‌ای، بدون حساسیت به بزرگی/کوچکی حروف)، `limit` ۱ تا ۵۰ |
| `welt_search_news` | جست‌وجوی اخبار با کلیدواژه (عنوان + تیزر) — `query` (مثلاً «Bundestag»)، `limit` ۱ تا ۵۰ |
| `welt_latest_videos` | تازه‌ترین ویدیوها از فید (subtype برابر video)، تازه‌ترین اول — `limit` ۱ تا ۵۰ |
| `welt_get_article` | متن کامل یک مقالهٔ WELT (‏`articleBody` در JSON-LD‏) — `url`: آدرس مقاله در www.welt.de (شامل /article). مقالات WELT+ فقط تیزر را برمی‌گردانند (`paywalled: true`) |
| `welt_health` | بررسی دسترسی به فید (ok / blocked / error) — یک درخواست مؤدبانه |

نمونهٔ خروجی (`welt_headlines` با `limit` برابر ۲):

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

نکته‌ها:
- سرور **فید رسمی RSS** را می‌خواند (۳۰ مورد، تأیید زنده در ۲۰۲۶-۱۱-۱۸). جست‌وجو و فیلتر موضوعی روی فیدِ دریافت‌شده انجام می‌شود. هر مورد پرچم `<welt:premium>` و `<welt:subType>` (news / video / opinion) را از خود فید دارد.
- **صداقت دربارهٔ پی‌وال:** مقالات WELT+ (پریمیوم) در JSON-LD فقط تیزر را نشان می‌دهند — `articleBody` برابر توضیحات است (حدود ۲۰۰ کاراکتر، روی ۳ مقالهٔ پریمیوم تأیید شد). `welt_get_article` برای این مقالات `paywalled: true` و تیزر را برمی‌گرداند و هرگز متن نمی‌سازد. مقالات رایگان متن کامل دارند (در نمونه‌ها ۱۵۰۰ تا ۳۹۰۰ کاراکتر). خبرهای کوتاه خبرگزاری‌ها هم ممکن است فقط تیزر باشند (`teaser_only: true` و `paywalled: false`) — تیزر در آن صورت کل متنِ در دسترسِ رایگان است.
- فید بخش‌ها وجود ندارد: `/feeds/<section>.rss` برای همهٔ بخش‌های آزمایش‌شده (politik، wirtschaft، sport، kultur و …) ۴۰۴ می‌دهد؛ تنها فید `latest.rss` است و موضوع‌ها همان مقادیر `<category>` آن‌اند.
- داده‌ها: فید عمومی RSS و صفحات مقالات WELT — بدون کلید، بدون ورود، فقط‌خواندنی.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — آفلاین؛ فید واقعیِ ذخیره‌شده و یک مقالهٔ رایگان و یک مقالهٔ WELT+ را تجزیه می‌کند
- `tests/test_live.py` — درخواست‌های زندهٔ محتاطانه به www.welt.de

تست‌ها: ۴۱/۴۱ سبز (۳۴ آفلاین + ۷ زنده، ۲۰۲۶-۱۱-۱۸).

## مجوز

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — رایگان برای استفادهٔ شخصی و غیرتجاری؛ استفادهٔ تجاری نیازمند مجوز جداگانه است (به LICENSE نگاه کنید).

---

ساختهٔ [محمد عباسی](https://github.com/mohammad-abbasi-sh) — [آلمانی‌باما](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
