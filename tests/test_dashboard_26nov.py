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
