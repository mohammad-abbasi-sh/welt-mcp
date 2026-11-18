"""Offline tests — parse the real captured www.welt.de RSS feed and
two real article pages (one free, one WELT+), no network."""
import json
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from welt_mcp import domain as dom
from welt_mcp import http as http_mod
from welt_mcp import server as srv

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"

FREE_URL = (
    "https://www.welt.de/politik/deutschland/"
    "article6afd6d12fc384ca056385c40/baugenehmigungen-in-deutschland-"
    "brechen-im-september-deutlich-ein-doch-jahresbilanz-bleibt-positiv.html"
)
PLUS_URL = (
    "https://www.welt.de/debatte/"
    "plus6afd64ba4e6cd4bac15cec70/bundesregierung-die-union-muss-die-"
    "spd-jetzt-aus-der-koalition-werfen.html"
)


def _rss(name):
    return dom.parse_rss((FIX / name).read_text(encoding="utf-8"))


class TestHeadlinesFixture(unittest.TestCase):
    def test_headlines_shape(self):
        out = _rss("headlines.xml")
        self.assertEqual(out["feed_title"], "Nachrichten - WELT")
        self.assertEqual(out["count"], 30)
        self.assertEqual(len(out["items"]), 30)

    def test_headlines_first_item(self):
        item = _rss("headlines.xml")["items"][0]
        self.assertEqual(
            item["title"],
            "Baugenehmigungen in Deutschland brechen im September deutlich "
            "ein – doch Jahresbilanz bleibt positiv",
        )
        self.assertEqual(item["link"], FREE_URL)
        self.assertEqual(item["published"], "2026-11-18T10:10:03+00:00")
        self.assertEqual(item["category"], "Deutschland")
        self.assertEqual(item["author"], "Till Henniges")
        self.assertEqual(item["topic"], "Jahresvergleich")
        self.assertFalse(item["premium"])
        self.assertEqual(item["subtype"], "news")
        self.assertTrue(item["image"].startswith("https://images.welt.de/"))

    def test_headlines_all_items_complete(self):
        items = _rss("headlines.xml")["items"]
        self.assertTrue(all(i["title"] and i["link"] and i["published"] for i in items))
        self.assertTrue(all(i["link"].startswith("https://www.welt.de/") for i in items))

    def test_premium_and_video_counts(self):
        items = _rss("headlines.xml")["items"]
        self.assertEqual(sum(1 for i in items if i["premium"]), 4)
        self.assertEqual(sum(1 for i in items if i["subtype"] == "video"), 10)
        self.assertEqual(sum(1 for i in items if i["subtype"] == "news"), 19)

    def test_categories(self):
        items = _rss("headlines.xml")["items"]
        topics = dom.list_topics(items)
        self.assertEqual(topics[0], {"topic": "Deutschland", "count": 15})
        self.assertEqual(topics[1], {"topic": "Ausland", "count": 6})
        self.assertEqual(topics[2], {"topic": "Fußball", "count": 3})


class TestArticleFixtures(unittest.TestCase):
    def test_free_article_full_body(self):
        html_text = (FIX / "article-free.html").read_text(encoding="utf-8")
        out = dom.parse_article(html_text)
        self.assertEqual(
            out["title"],
            "Baugenehmigungen in Deutschland brechen im September deutlich "
            "ein – doch Jahresbilanz bleibt positiv",
        )
        self.assertEqual(out["author"], "Till Henniges")
        self.assertEqual(out["published"], "2026-11-18T10:10:03.799Z")
        self.assertEqual(len(out["body"]), 3855)
        self.assertTrue(out["body"].startswith(
            "Der deutsche Wohnungsbau hat einen Rückschlag erlitten."))
        self.assertFalse(out["teaser_only"])
        self.assertGreater(out["word_count"], 500)

    def test_plus_article_teaser_only(self):
        html_text = (FIX / "article-plus.html").read_text(encoding="utf-8")
        out = dom.parse_article(html_text)
        self.assertEqual(
            out["title"],
            "Bundesregierung: Die Union muss die SPD jetzt aus der "
            "Koalition werfen",
        )
        self.assertEqual(out["author"], "Ulf Poschardt")
        self.assertEqual(out["published"], "2026-11-18T09:38:31.114Z")
        self.assertEqual(len(out["body"]), 222)
        self.assertTrue(out["teaser_only"])
        self.assertEqual(out["body"], out["description"])

    def test_article_without_json_ld_raises(self):
        with self.assertRaises(ValueError):
            dom.parse_article("<html><body>no ld+json here</body></html>")


class TestParseErrors(unittest.TestCase):
    def test_malformed_xml(self):
        with self.assertRaises(ValueError):
            dom.parse_rss("<rss><channel><item>oops")

    def test_non_rss_document(self):
        with self.assertRaises(ValueError):
            dom.parse_rss("<html><head><title>404</title></head></html>")

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            dom.parse_rss("")


class TestValidation(unittest.TestCase):
    def test_limit_bounds(self):
        self.assertEqual(dom.validate_limit(1), 1)
        self.assertEqual(dom.validate_limit(50), 50)
        with self.assertRaises(ValueError):
            dom.validate_limit(0)
        with self.assertRaises(ValueError):
            dom.validate_limit(51)


class TestSearchAndFilters(unittest.TestCase):
    def test_search_case_insensitive(self):
        items = _rss("headlines.xml")["items"]
        self.assertEqual(len(dom.search_items(items, "Merz")), 3)
        self.assertEqual(len(dom.search_items(items, "merz")), 3)

    def test_search_no_hits(self):
        items = _rss("headlines.xml")["items"]
        self.assertEqual(dom.search_items(items, "zzzzqqq"), [])

    def test_search_empty_raises(self):
        with self.assertRaises(ValueError):
            dom.search_items([], "  ")

    def test_filter_by_topic(self):
        items = _rss("headlines.xml")["items"]
        self.assertEqual(len(dom.filter_by_topic(items, "Deutschland")), 15)
        self.assertEqual(len(dom.filter_by_topic(items, "deutschland")), 15)
        self.assertEqual(len(dom.filter_by_topic(items, "Ausland")), 6)
        self.assertEqual(dom.filter_by_topic(items, "zzzz"), [])

    def test_filter_by_topic_empty_raises(self):
        with self.assertRaises(ValueError):
            dom.filter_by_topic([], "  ")

    def test_filter_videos(self):
        items = _rss("headlines.xml")["items"]
        videos = dom.filter_videos(items)
        self.assertEqual(len(videos), 10)
        self.assertTrue(all(v["subtype"] == "video" for v in videos))

    def test_dedupe_sort(self):
        items = _rss("headlines.xml")["items"]
        merged = dom.dedupe_sort(items + items[:5])
        links = [i["link"] for i in merged]
        self.assertEqual(len(links), len(set(links)))
        self.assertEqual(len(merged), 30)
        dates = [i["published"] for i in merged]
        self.assertEqual(dates, sorted(dates, reverse=True))


class TestHttpGuards(unittest.TestCase):
    def test_fetch_feed_rejects_non_feed_path(self):
        with self.assertRaises(http_mod.WeltError):
            http_mod.fetch_feed("https://www.welt.de/politik/")

    def test_fetch_feed_rejects_other_host(self):
        with self.assertRaises(http_mod.WeltError):
            http_mod.fetch_feed("https://example.com/feeds/latest.rss")

    def test_fetch_article_rejects_non_article_url(self):
        with self.assertRaises(http_mod.WeltError):
            http_mod.fetch_article("https://www.welt.de/politik/")


class TestServerOffline(unittest.TestCase):
    """Tool functions with the HTTP layer mocked to the fixtures."""

    def test_headlines_tool(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.welt_headlines(limit=3))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["total_results"], 30)
        self.assertEqual(out["source"], "www.welt.de")
        self.assertIn("fetched_at", out)

    def test_headlines_tool_limit_error(self):
        out = json.loads(srv.welt_headlines(limit=0))
        self.assertIn("error", out)

    def test_by_topic_tool(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.welt_news_by_topic("Deutschland", limit=2))
        self.assertNotIn("error", out)
        self.assertEqual(out["topic"], "Deutschland")
        self.assertEqual(out["total_results"], 15)
        self.assertEqual(out["count"], 2)

    def test_by_topic_tool_empty(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.welt_news_by_topic("zzzz", limit=2))
        self.assertNotIn("error", out)
        self.assertEqual(out["total_results"], 0)

    def test_search_tool(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.welt_search_news("Merz", limit=10))
        self.assertNotIn("error", out)
        self.assertEqual(out["query"], "Merz")
        self.assertEqual(out["total_results"], 3)

    def test_search_tool_empty_query(self):
        out = json.loads(srv.welt_search_news("   "))
        self.assertIn("error", out)

    def test_videos_tool(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.welt_latest_videos(limit=5))
        self.assertNotIn("error", out)
        self.assertEqual(out["total_results"], 10)
        self.assertEqual(out["count"], 5)

    def test_get_article_free(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        html_text = (FIX / "article-free.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml), \
                mock.patch.object(srv._http, "fetch_article", return_value=html_text):
            out = json.loads(srv.welt_get_article(FREE_URL))
        self.assertNotIn("error", out)
        self.assertFalse(out["paywalled"])
        self.assertFalse(out["teaser_only"])
        self.assertGreater(out["word_count"], 500)
        self.assertEqual(out["author"], "Till Henniges")

    def test_get_article_plus(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        html_text = (FIX / "article-plus.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml), \
                mock.patch.object(srv._http, "fetch_article", return_value=html_text):
            out = json.loads(srv.welt_get_article(PLUS_URL))
        self.assertNotIn("error", out)
        self.assertTrue(out["paywalled"])
        self.assertTrue(out["teaser_only"])
        self.assertEqual(out["word_count"], len(out["body"].split()))
        self.assertIn("WELT+", out["note"])

    def test_get_article_empty_url(self):
        out = json.loads(srv.welt_get_article("   "))
        self.assertIn("error", out)

    def test_get_article_non_article_url(self):
        out = json.loads(srv.welt_get_article("https://www.welt.de/politik/"))
        self.assertIn("error", out)

    def test_health_tool(self):
        with mock.patch.object(srv._http, "health_check", return_value={"status": "ok", "http_status": 200, "url": dom.HEADLINES_FEED}):
            out = json.loads(srv.welt_health())
        self.assertEqual(out["status"], "ok")


if __name__ == "__main__":
    unittest.main()
