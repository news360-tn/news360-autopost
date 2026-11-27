"""owner 26 Nov: Namakkal and Salem news ABOUT or NEAR Rasipuram invites Rasipuram 360 as collaborator (the owner accepts it)."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "poster"))
sys.path.insert(0, str(ROOT / "research_free"))
import post      # noqa: E402

CFG = json.loads((ROOT / "poster" / "config.json").read_text(encoding="utf-8"))


class CollabTest(unittest.TestCase):
    def row(self, ta="", en="", loc=""):
        return {"headline_ta": ta, "headline_en": en, "location": loc, "post_to": ""}

    def test_the_word_list_is_in_the_config(self):
        self.assertIn("rasipuram", CFG["collab_near_words"])
        self.assertIn("ராசிபுர", CFG["collab_near_words"])

    def test_news_about_or_near_rasipuram_invites_the_rasipuram_page(self):
        with mock.patch.object(post, "CONFIG", CFG):
            for ta, en, loc in (("ராசிபுரத்தில் சாலை விபத்து", "", ""), ("வெண்ணந்தூர் அருகே தீ விபத்து", "", ""), ("", "Fire near Namagiripettai", ""),
                                ("மின்தடை", "", "Rasipuram"), ("ஆத்தூர் அருகே லாரி கவிழ்ந்து விபத்து", "", "")):
                self.assertTrue(post.near_rasipuram(self.row(ta, en, loc)), (ta, en, loc))

    def test_other_news_does_not(self):
        with mock.patch.object(post, "CONFIG", CFG):
            for ta, en, loc in (("சேலத்தில் மழை", "", "Salem"), ("நாமக்கல் முட்டை விலை உயர்வு", "", "Namakkal"), ("", "", "")):
                self.assertFalse(post.near_rasipuram(self.row(ta, en, loc)), (ta, en, loc))

    def test_an_empty_word_list_switches_it_off(self):
        with mock.patch.object(post, "CONFIG", dict(CFG, collab_near_words=[])):
            self.assertFalse(post.near_rasipuram(self.row("ராசிபுரத்தில் விபத்து")))

    def test_collab_page_by_page(self):
        r = self.row("ராசிபுரத்தில் விபத்து")
        other = self.row("சேலத்தில் மழை")
        with mock.patch.object(post, "CONFIG", CFG):
            if post.PAGE == "namakkal":
                self.assertEqual(post.collab_page(r, "namakkal"), "rasipuram")
                self.assertEqual(post.collab_page(other, "namakkal"), "")
            else:
                self.assertEqual(post.PAGE, "salem")
                self.assertEqual(post.collab_page(r, "salem"), "rasipuram")
                self.assertEqual(post.collab_page(other, "salem"), "")
                with mock.patch.object(post, "COLLAB", "rasipuram"):
                    self.assertEqual(post.collab_user(), "rasipuram360.official")      # the account invited
        with mock.patch.object(post, "CONFIG", dict(CFG, collab_username="")):
            if post.PAGE == "salem":
                self.assertEqual(post.collab_page(r, "salem"), "")      # no collaborator account set: off


if __name__ == "__main__":
    unittest.main()
