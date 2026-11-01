"""owner 1 Nov (Namakkal 360 / Rasipuram 360): power-shutdown news is posted at once - never twice, never after the cut; the normal
collection is not touched."""
import datetime, json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_free"))
import powercut      # noqa: E402

IST = powercut.IST


class PowerCutLane(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.old = (powercut.STATE, powercut.URLS, powercut.DRY)
        powercut.STATE = Path(self.d.name) / "s.json"
        powercut.URLS = Path(self.d.name) / "u.txt"
        powercut.DRY = False

    def tearDown(self):
        powercut.STATE, powercut.URLS, powercut.DRY = self.old
        self.d.cleanup()

    def run_find(self, now, arts, recent=()):
        links = [{"url": u, "title": "", "published": ""} for u in arts]
        real_dt = datetime.datetime

        class FakeDT(real_dt):
            @classmethod
            def now(cls, tz=None):
                return now
        with mock.patch.object(powercut, "links", return_value=links), \
                mock.patch.object(powercut.allnews, "article_any", side_effect=lambda u: dict(arts[u], url=u)), \
                mock.patch.object(powercut, "recent_rows", return_value=list(recent)), \
                mock.patch.object(powercut.datetime, "datetime", FakeDT):
            powercut.cmd_find()
        return [l for l in powercut.URLS.read_text().split("\n") if l]

    def test_new_cut_once_and_never_late(self):
        now = datetime.datetime(2026, 11, 1, 15, 0, tzinfo=IST)
        dm = "https://www.dinamani.com/all-editions/edition-dharmapuri/namakkal/2026/Nov/01/kalappanaickenpatti"
        cm = "https://www.dinamalar.com/news/tamil-nadu-district-news-namakkal/kalappanaickenpatti-power-cut/9"
        old = "https://www.dinamalar.com/news/tamil-nadu-district-news-namakkal/old-cut/1"
        other = "https://www.dinamalar.com/news/tamil-nadu-district-news-namakkal/other-news/2"
        arts = {
            dm: {"title": "நாளைய மின்தடை: காளப்பநாயக்கன்பட்டி துணை மின் நிலையம்", "text": "காளப்பநாயக்கன்பட்டி துணை மின் நிலையத்தில் பராமரிப்புப் பணி",
                 "published": "2026-11-01T14:00:00+05:30"},
            cm: {"title": "நாளை காளப்பநாயக்கன்பட்டி பகுதியில் மின்தடை", "text": "நாமக்கல் காளப்பநாயக்கன்பட்டி", "published": "2026-11-01T14:30:00+05:30"},
            old: {"title": "சூலூர் பகுதியில் 30.10.2026 மின்தடை", "text": "", "published": "2026-10-29T18:00:00+05:30"},
            other: {"title": "நாமக்கல்லில் சாலை பணி தொடக்கம்", "text": "", "published": "2026-11-01T10:00:00+05:30"},
        }
        got = self.run_find(now, arts)
        self.assertEqual(got, [dm])      # Dinamani first; Dinamalar's copy of the same cut and the past cut are not written
        self.assertEqual(self.run_find(now, arts), [])      # next hour: never twice
        st = json.loads(powercut.STATE.read_text())
        self.assertIn(powercut.pid(dm), st["done"])

    def test_already_in_the_sheet_is_skipped(self):
        now = datetime.datetime(2026, 11, 1, 15, 0, tzinfo=IST)
        dm = "https://www.dinamani.com/all-editions/edition-dharmapuri/namakkal/2026/Nov/01/kalappanaickenpatti"
        arts = {dm: {"title": "நாளைய மின்தடை: காளப்பநாயக்கன்பட்டி துணை மின் நிலையம்", "text": "", "published": "2026-11-01T14:00:00+05:30"}}
        recent = [{"source": "https://x/y", "headline_ta": "காளப்பநாயக்கன்பட்டி பகுதியில் நாளை மின்தடை", "published": "2026-11-01T12:00:00+05:30"}]
        self.assertEqual(self.run_find(now, arts, recent), [])

    def test_poster_posts_it_without_other_checks(self):
        sys.path.insert(0, str(ROOT / "poster"))
        import post
        url = "https://www.dinamani.com/all-editions/edition-dharmapuri/namakkal/2026/Nov/01/kalappanaickenpatti"
        post._LANE = {powercut.pid(url)}
        try:
            self.assertTrue(post.owner_picked({"source": url}))
            self.assertFalse(post.owner_picked({"source": "https://www.dinamalar.com/news/other/1"}))      # every other story: checks as before
        finally:
            post._LANE = None
        src = (ROOT / "poster" / "post.py").read_text(encoding="utf-8")
        self.assertIn("powercut_state.json", src)

    def test_workflow(self):
        wf = (ROOT / ".github" / "workflows" / "powercut.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "20 0-16 * * *"', wf)
        self.assertIn("powercut.py find", wf)
        self.assertIn("powercut.py verify", wf)
        self.assertIn('PICK_ONLY: "1"', wf)
        src = (ROOT / "research_free" / "collect.py").read_text(encoding="utf-8")
        self.assertIn("elif PICK_ONLY:", src)                       # the lane writes only its own links
        self.assertIn("news = allnews.collect(log)", src)            # the normal collection is unchanged
        self.assertIn('[] if PICK_ONLY else ["collect"]', src)       # and the lane never counts as a collection round
        for line in wf.splitlines():
            if "post.yml/dispatches" in line:
                self.assertIn("inputs[dry_run]=false", line)


if __name__ == "__main__":
    unittest.main()
