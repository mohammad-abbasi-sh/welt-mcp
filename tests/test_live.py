"""Live tests — hit the real www.welt.de RSS feed and article pages.
Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set WELT_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from welt_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("WELT_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="WELT_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_headlines_live(self):
        out = json.loads(srv.welt_headlines(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["link"] for i in out["items"]))
        print(f"\nLIVE headlines: {out['count']} items, first: {out['items'][0]['title']}")

    def test_by_topic_live(self):
        out = json.loads(srv.welt_news_by_topic("Deutschland", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(
            "deutschland" in (i["category"] or "").casefold()
            for i in out["items"]
        ))
        print(f"\nLIVE Deutschland: {out['total_results']} items")

    def test_search_live(self):
        out = json.loads(srv.welt_search_news("Deutschland", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(
            "deutschland" in (i["title"] + i["description"]).casefold()
            for i in out["items"]
        ))
        print(f"\nLIVE search 'Deutschland': {out['total_results']} hits")

    def test_videos_live(self):
        out = json.loads(srv.welt_latest_videos(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["subtype"] == "video" for i in out["items"]))
        print(f"\nLIVE videos: {out['total_results']} items")

    def test_get_article_free_live(self):
        # A free article from the current feed: full body expected.
        feed = json.loads(srv.welt_headlines(limit=30))
        free = [i for i in feed["items"] if not i["premium"] and i["subtype"] == "news"]
        self.assertGreater(len(free), 0)
        out = json.loads(srv.welt_get_article(free[0]["link"]))
        self.assertNotIn("error", out)
        self.assertFalse(out["paywalled"])
        self.assertGreater(out["word_count"], 100)
        print(f"\nLIVE article: {out['word_count']} words, {out['title'][:60]}")

    def test_get_article_plus_live(self):
        # A WELT+ article from the current feed: teaser only expected.
        feed = json.loads(srv.welt_headlines(limit=30))
        plus = [i for i in feed["items"] if i["premium"]]
        if not plus:
            self.skipTest("no WELT+ item in the current feed")
        out = json.loads(srv.welt_get_article(plus[0]["link"]))
        self.assertNotIn("error", out)
        self.assertTrue(out["paywalled"])
        self.assertTrue(out["teaser_only"])
        print(f"\nLIVE WELT+ article: paywalled, {out['word_count']} words (teaser)")

    def test_health_live(self):
        out = json.loads(srv.welt_health())
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["http_status"], 200)


if __name__ == "__main__":
    unittest.main()
