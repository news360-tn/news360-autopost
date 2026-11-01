import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "poster"))
import post


class HoldBeforePosting(unittest.TestCase):
    """owner 2 Nov (RN-272): a draft with fact-check problems, or an unknown location, is never posted"""

    def row(self, **kw):
        base = dict(verification="DRAFT (m) - fact-check: no problems found", location="Namakkal district", caption="x", reel_script="y",
                    source="", published="", headline_ta="", category="", notes="", batch="", review="Auto")
        base.update(kw)
        return base

    def test_fact_check_problem_is_held(self):
        r = self.row(verification="DRAFT (m) - NOT CLEAN, held from posting - problems: fact-check: wrong vehicle")
        self.assertTrue(post.skip_reason(r).startswith("held: fact-check problems"))

    def test_unknown_location_is_held(self):
        self.assertEqual(post.skip_reason(self.row(caption="இடம்: தெரியவில்லை")), "held: location unknown")
        self.assertEqual(post.skip_reason(self.row(location="unknown")), "held: location unknown")

    def test_clean_row_is_not_held_by_the_new_rules(self):
        self.assertNotIn("held:", post.skip_reason(self.row()))


if __name__ == "__main__":
    unittest.main()
