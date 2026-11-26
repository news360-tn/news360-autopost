"""owner 26 Nov: the dashboard collector only reads public numbers, builds one file, never fails the run."""
import sys, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import dash_collect as collect      # noqa: E402

NOW = datetime(2026, 11, 26, 6, 0, tzinfo=timezone.utc)
HIST = {"111": {"page": "namakkal", "t": "2026-11-26T03:00:00+0000", "caption": "🔴 நாமக்கல்லில் நாளை மின் தடை\n\nவிவரம்", "topic": "power_cut",
                "reach": 100, "views": 250, "saved": 3, "shares": 2, "total_interactions": 9},
        "222": {"page": "namakkal", "t": "2026-10-01T03:00:00+0000", "caption": "old", "views": 1},
        "333": {"page": "rasipuram", "t": "2026-11-25T03:00:00+0000", "caption": "x", "views": 5, "type": "FEED"}}
YT = {"uploads": [{"youtube": "vid1", "at": "2026-11-26T04:00:00+00:00", "title": "T1 | Namakkal power cut", "day": "2026-11-26"},
                  {"youtube": "", "at": "2026-11-26T04:05:00+00:00", "title": "limit"}]}


def fake_raw(repo, path):
    if path.endswith("history.json"):
        return HIST if repo == "news360-autopost" else {}
    if path.endswith("namakkal.json"):
        return YT
    return None


class Collect(unittest.TestCase):
    def test_build_reads_only_public_numbers(self):
        with mock.patch.object(collect, "raw", side_effect=fake_raw), mock.patch.object(collect, "listing", return_value=[]), \
                mock.patch.object(collect, "youtube_stats", return_value=True):
            p = collect.build(NOW, "KEY")
        ig = [x for x in p["posts"] if x["platform"] == "instagram"]
        yt = [x for x in p["posts"] if x["platform"] == "youtube"]
        self.assertEqual(sorted(x["id"] for x in ig), ["111", "333"])      # the 2-month-old post is left out
        self.assertEqual(ig[-1]["title"] if ig[-1]["id"] == "111" else ig[0]["title"], "நாமக்கல்லில் நாளை மின் தடை")
        self.assertEqual([x["id"] for x in yt], ["vid1"])      # the "limit" placeholder is not a video
        self.assertEqual(yt[0]["url"], "https://youtube.com/shorts/vid1")
        self.assertNotIn("rasipuram", p["pages"])
        self.assertIn("namakkal", p["pages"])
        text = str(p)
        self.assertNotIn("KEY", text)

    def test_youtube_statistics(self):
        items = [{"id": "a", "views": None, "likes": None, "comments": None}, {"id": "b", "views": None, "likes": None, "comments": None}]
        resp = mock.Mock(status_code=200)
        resp.json.return_value = {"items": [{"id": "a", "statistics": {"viewCount": "10", "likeCount": "2", "commentCount": "1"}},
                                            {"id": "b", "statistics": {"viewCount": "5"}}]}
        with mock.patch.object(collect.requests, "get", return_value=resp):
            self.assertTrue(collect.youtube_stats(items, "K"))
        self.assertEqual((items[0]["views"], items[0]["likes"], items[0]["comments"]), (10, 2, 1))
        self.assertEqual((items[1]["views"], items[1]["likes"], items[1]["comments"]), (5, None, None))
        self.assertFalse(collect.youtube_stats(items, ""))

    def test_never_fails_and_never_sends_without_setup(self):
        with mock.patch.dict("os.environ", {"DASH_URL": "", "DASH_WRITE_KEY": ""}), mock.patch.object(collect.requests, "post") as post:
            self.assertEqual(collect.main(), 0)
        post.assert_not_called()

    def test_send_posts_the_key_only_in_the_body(self):
        resp = mock.Mock(status_code=200)
        resp.json.return_value = {"ok": True}
        with mock.patch.dict("os.environ", {"DASH_URL": "https://script.example/exec", "DASH_WRITE_KEY": "SECRETKEY"}), \
                mock.patch.object(collect.requests, "post", return_value=resp) as post:
            self.assertTrue(collect.send({"posts": []}))
        self.assertNotIn("SECRETKEY", post.call_args.args[0])
        self.assertIn(b"SECRETKEY", post.call_args.kwargs["data"])

    def test_workflow_is_read_only_and_separate(self):
        wf = (ROOT / ".github" / "workflows" / "dashboard.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", wf)
        self.assertNotIn("git push", wf)
        self.assertNotIn("git commit", wf)


if __name__ == "__main__":
    unittest.main()


class InstagramLinkTest(unittest.TestCase):
    def test_collector_passes_the_post_link_through(self):
        import dash_collect as dc
        from datetime import datetime, timezone
        hist = {"111": {"page": "namakkal", "t": "2026-11-26T05:00:00+0000", "caption": "செய்தி", "views": 5, "permalink": "https://www.instagram.com/reel/AbC/"},
                "222": {"page": "namakkal", "t": "2026-11-26T05:10:00+0000", "caption": "பழையது", "views": 1}}
        with __import__("unittest.mock", fromlist=["patch"]).patch.object(dc, "raw", return_value=hist):
            out = dc.instagram("news360-autopost", ["namakkal"], datetime(2026, 11, 1, tzinfo=timezone.utc))
        urls = {o["id"]: o["url"] for o in out}
        self.assertEqual(urls, {"111": "https://www.instagram.com/reel/AbC/", "222": ""})


class FollowersTest(unittest.TestCase):
    def test_series_and_the_weekly_change(self):
        import dash_collect as dc
        hist = {f"2026-11-{d:02d}": {"namakkal": {"followers": 10000 + d * 10}, "other": {"followers": 1}} for d in range(10, 27)}
        hist["2026-11-26"]["namakkal"]["followers"] = None      # a day without a number is skipped
        pts = dc.series(hist, "namakkal", "followers")
        self.assertEqual(pts[-1], ("2026-11-25", 10250))
        self.assertEqual(dc.with_change(pts), {"n": 10250, "d7": 70})      # against 25 - 7 days = 18 Nov, the newest day at least 6 days older
        self.assertIsNone(dc.with_change([]))
        self.assertEqual(dc.with_change([("2026-11-26", 5)]), {"n": 5, "d7": None})      # not enough history yet

    def test_followers_from_the_repositories_and_youtube(self):
        import dash_collect as dc
        files = {("news360-autopost", "poster/insights/followers.json"): {"2026-11-19": {"namakkal": {"followers": 100}, "rasipuram": {"followers": 50}},
                                                                        "2026-11-26": {"namakkal": {"followers": 130}, "rasipuram": {"followers": 55}}},
                 ("news360-autopost", "poster/insights/fb_followers.json"): {"2026-11-26": {"namakkal": {"followers": 900, "fans": 880}}},
                 ("salem360-autopost", "poster/insights/followers.json"): {"2026-11-26": {"salem": {"followers": 7830}}}}

        def fake_get(url, **k):
            if url.endswith("/videos"):
                return mock.Mock(status_code=200, json=lambda: {"items": [{"id": "v1", "snippet": {"channelId": "C1"}}]})
            return mock.Mock(status_code=200, json=lambda: {"items": [{"id": "C1", "statistics": {"subscriberCount": "321", "videoCount": "40"}}]})
        with mock.patch.object(dc.requests, "get", side_effect=fake_get):
            out = dc.followers([{"page": "salem", "id": "v1"}], "KEY", raw_fn=lambda repo, path: files.get((repo, path)))
        self.assertEqual(out["namakkal"]["instagram"], {"n": 130, "d7": 30})
        self.assertEqual(out["namakkal"]["facebook"], {"n": 900, "d7": None})
        self.assertEqual(out["rasipuram"]["instagram"]["n"], 55)
        self.assertEqual(out["salem"]["instagram"]["n"], 7830)
        self.assertEqual(out["salem"]["youtube"], {"n": 321, "hidden": False, "videos": 40})
        self.assertNotIn("facebook", out["salem"])      # not read yet: the dashboard shows n/a

    def test_hidden_subscriber_counts_and_no_key(self):
        import dash_collect as dc
        self.assertEqual(dc.youtube_subscribers([{"page": "salem", "id": "v1"}], ""), {})
        def fake_get(url, **k):
            if url.endswith("/videos"):
                return mock.Mock(status_code=200, json=lambda: {"items": [{"id": "v1", "snippet": {"channelId": "C1"}}]})
            return mock.Mock(status_code=200, json=lambda: {"items": [{"id": "C1", "statistics": {"hiddenSubscriberCount": True, "videoCount": "3"}}]})
        with mock.patch.object(dc.requests, "get", side_effect=fake_get):
            self.assertEqual(dc.youtube_subscribers([{"page": "salem", "id": "v1"}], "K")["salem"], {"n": None, "hidden": True, "videos": 3})
