"""owner 26 Nov: the link sync puts Facebook / YouTube links on the website's stories (read-only towards posting)."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
import link_sync as ls      # noqa: E402

NOW = datetime(2026, 11, 26, 9, 0, tzinfo=timezone.utc)


class FakeRepo:
    """files of one repository: {path: json}"""
    def __init__(self, files):
        self.files = files

    def raw(self, repo, path):
        return self.files.get((repo, path))

    def listing(self, repo, path):
        pre = path.rstrip("/") + "/"
        return [{"name": p[len(pre):]} for (r, p) in self.files if r == repo and p.startswith(pre)]


def fb(page, story, link, at="2026-11-26T05:00:00+00:00", status="posted"):
    return {("coimbatore360-autopost", f"poster/fb_posted/{page}-{story}-reel.json"): {"status": status, "link": link, "posted_at": at}}


class LinkSyncTest(unittest.TestCase):
    def test_website_ids_follow_the_district_code(self):
        self.assertEqual(ls.row_id("namakkal", "RN-12"), "RN-12")
        self.assertEqual(ls.row_id("coimbatore", "RN-77"), "CBE-RN-77")
        self.assertEqual(ls.row_id("trichy", "RN-9"), "TRY-RN-9")

    def test_facebook_only_posted_recent_news_stories(self):
        f = {}
        f.update(fb("coimbatore", "RN-1", "https://www.facebook.com/reel/1/"))
        f.update(fb("coimbatore", "RN-2", "https://www.facebook.com/reel/2/", status="failed"))
        f.update(fb("coimbatore", "RN-3", "https://www.facebook.com/reel/3/", at="2026-11-01T05:00:00+00:00"))      # too old
        f.update(fb("coimbatore", "rasipalan-2026-11-26", "https://www.facebook.com/reel/4/"))      # not a news story
        r = FakeRepo(f)
        got = ls.fb_links("coimbatore360-autopost", "coimbatore", 3, NOW, r.raw, r.listing)
        self.assertEqual(got, {"RN-1": "https://www.facebook.com/reel/1/"})

    def test_district_own_facebook_page_wins(self):
        f = {}
        f.update(fb("rasipuram", "RN-5", "https://www.facebook.com/reel/R/"))
        f.update(fb("namakkal", "RN-5", "https://www.facebook.com/reel/N/"))
        r = FakeRepo({(k[0].replace("coimbatore360", "news360"), k[1]): v for k, v in f.items()})
        got = ls.fb_links("news360-autopost", "namakkal", 3, NOW, r.raw, r.listing)
        self.assertEqual(got["RN-5"], "https://www.facebook.com/reel/N/")

    def test_youtube_joins_the_upload_with_the_posted_record(self):
        repo = "coimbatore360-autopost"
        r = FakeRepo({
            (repo, "poster/yt_uploaded/coimbatore.json"): {"uploads": [{"ig": "111", "youtube": "abcDEF12345"}, {"ig": "", "youtube": ""}, {"ig": "222", "youtube": "zzzAAA11122"}]},
            (repo, "poster/posted/20261126-070000-coimbatore-RN-7.json"): {"story": "RN-7", "media_id": "111"},
            (repo, "poster/posted/20261126-080000-coimbatore-rasipalan-2026-11-26.json"): {"story": "rasipalan-2026-11-26", "media_id": "222"},
            (repo, "poster/posted/20261101-080000-coimbatore-RN-1.json"): {"story": "RN-1", "media_id": "111"},      # too old a file
        })
        got = ls.yt_links(repo, "coimbatore", 3, NOW, r.raw, r.listing)
        self.assertEqual(got, {"RN-7": "https://youtube.com/shorts/abcDEF12345"})

    def test_collect_builds_website_ids_with_both_links(self):
        repo = "coimbatore360-autopost"
        f = fb("coimbatore", "RN-7", "https://www.facebook.com/reel/7/")
        f[(repo, "poster/yt_uploaded/coimbatore.json")] = {"uploads": [{"ig": "111", "youtube": "abcDEF12345"}]}
        f[(repo, "poster/posted/20261126-070000-coimbatore-RN-7.json")] = {"story": "RN-7", "media_id": "111"}
        r = FakeRepo(f)
        items = ls.collect(3, NOW, r.raw, r.listing)
        self.assertEqual(items, [{"id": "CBE-RN-7", "fb_url": "https://www.facebook.com/reel/7/", "yt_url": "https://youtube.com/shorts/abcDEF12345"}])

    def test_send_groups_of_100_and_a_wrong_key_stops(self):
        items = [{"id": f"CBE-RN-{i}", "fb_url": "https://www.facebook.com/reel/1/"} for i in range(150)]
        calls = []

        def ok(url, json, **k):
            calls.append((url, len(json), k["headers"]["authorization"] != ""))
            return mock.Mock(status_code=200, json=lambda: {"saved": [x["id"] for x in json[:-1]], "skipped": [{"id": "x"}]})
        self.assertEqual(ls.send(items, "KEY", post=ok), (148, 2))
        self.assertEqual([c[1] for c in calls], [100, 50])
        self.assertTrue(calls[0][0].endswith("/api/links"))
        bad = mock.Mock(side_effect=lambda *a, **k: mock.Mock(status_code=401, text="unauthorized"))
        self.assertEqual(ls.send(items, "BAD", post=bad), (0, 0))
        self.assertEqual(bad.call_count, 1)      # not retried, not continued

    def test_no_key_sends_nothing_and_never_fails(self):
        with mock.patch.object(ls, "collect", return_value=[{"id": "RN-1", "fb_url": "https://www.facebook.com/reel/1/"}]), \
                mock.patch.dict("os.environ", {"WEBSITE_INGEST_KEY": ""}), mock.patch.object(ls, "send") as s:
            self.assertEqual(ls.main([]), 0)
        s.assert_not_called()


if __name__ == "__main__":
    unittest.main()
