"""owner 23 Nov: every Namakkal-district news is posted by Namakkal 360; only a Rasipuram-area news invites Rasipuram 360 as
collaborator; Rasipuram 360 never posts on its own (news, rasipalan, gold); Facebook only on the Namakkal page."""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "poster"))
sys.path.insert(0, str(ROOT / "rasipalan"))
import post      # noqa: E402


class NamakkalPostsAll(unittest.TestCase):
    def test_every_news_is_namakkals(self):
        for pt in ("Rasipuram 360 (collab: Namakkal 360)", "Namakkal 360 (collab: Rasipuram 360)", "Namakkal 360", "", "Rasipuram 360 + Namakkal 360"):
            self.assertEqual(post.pages_of({"post_to": pt}), ["namakkal"], pt)

    def test_only_rasipuram_news_invites_rasipuram(self):
        self.assertEqual(post.collab_page({"post_to": "Rasipuram 360 (collab: Namakkal 360)"}, "namakkal"), "rasipuram")
        self.assertEqual(post.collab_page({"post_to": "Namakkal 360 (collab: Rasipuram 360)"}, "namakkal"), "")
        self.assertEqual(post.collab_page({"post_to": "Namakkal 360"}, "namakkal"), "")

    def test_accept_never_raises(self):
        with mock.patch.object(post, "bridge_get", side_effect=RuntimeError("down")):
            post.accept_collab("rasipuram", "123")

    def test_rasipalan_and_gold_on_namakkal(self):
        wf = (ROOT / ".github" / "workflows" / "rasipalan.yml").read_text(encoding="utf-8")
        self.assertIn("PAGE: namakkal", wf)
        self.assertNotIn("out/rasipalan/rasipuram", wf)
        self.assertIn('GOLD_PAGES: "namakkal"', (ROOT / ".github" / "workflows" / "goldrate.yml").read_text(encoding="utf-8"))
        import rasi_daily
        self.assertEqual(rasi_daily.PAGES["namakkal"]["logo"], "logo_namakkal.png")
        self.assertEqual(rasi_daily.PAGES["namakkal"]["collab"], "")
        self.assertTrue((ROOT / "kit" / "logo_namakkal.png").exists())

    def test_watchdog_waits_only_for_namakkal(self):
        import watchdog
        with mock.patch.object(watchdog, "REPO", "news360-tn/news360-autopost"):
            self.assertEqual(watchdog.page_names(), ("namakkal",))


if __name__ == "__main__":
    unittest.main()
