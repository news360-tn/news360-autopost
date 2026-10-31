"""Daily rasipalan carousel (owner 31 Oct): panchangam values, festival days, writer checks, caption rules."""
import sys, unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rasipalan"))
import importlib.util
HAVE_SWE = importlib.util.find_spec("swisseph") is not None


@unittest.skipUnless(HAVE_SWE, "pyswisseph is installed by tests.yml")
class Panchangam(unittest.TestCase):
    def test_31_october_2026_matches_published_panchangam(self):
        import rasi_panchang as P
        p = P.compute(date(2026, 10, 31))
        self.assertEqual((p["tamil_month"], p["tamil_day"], p["weekday"]), ("ஐப்பசி", 14, "சனி"))
        self.assertEqual((p["tithi"], p["paksha"], p["nakshatra"]), ("சஷ்டி", "தேய்பிறை", "திருவாதிரை"))
        self.assertIn("4:5", p["tithi_end"])          # published: 4:57 PM
        self.assertIn("7:1", p["nakshatra_end"])      # published: 7:11 AM
        self.assertEqual(p["chandrashtamam"], "விருச்சிகம்")
        self.assertEqual(p["rahu"], "9:00 – 10:30")

    def test_tamil_month_starts(self):
        import rasi_panchang as P
        self.assertEqual((P.compute(date(2027, 1, 15))["tamil_month"], P.compute(date(2027, 1, 15))["tamil_day"]), ("தை", 1))
        self.assertEqual(P.compute(date(2027, 4, 14))["tamil_month"], "சித்திரை")


class Festivals(unittest.TestCase):
    P = {"tithi_idx": 20, "nakshatra_idx": 5}

    def test_official_day_gets_its_theme(self):
        import rasi_festivals as festivals
        f, _, _ = festivals.today(date(2026, 11, 8), self.P)
        self.assertEqual((f["name"], f["theme"]), ("தீபாவளி", "diwali"))

    def test_moon_festival_needs_the_article(self):
        import rasi_festivals as festivals
        f, _, why = festivals.today(date(2027, 3, 10), self.P, "இன்றைய பஞ்சாங்கம் ...")
        self.assertIsNone(f)
        f, _, _ = festivals.today(date(2027, 3, 10), self.P, "இன்று ரம்ஜான் பண்டிகை கொண்டாட்டம்")
        self.assertEqual(f["theme"], "islamic")

    def test_normal_day(self):
        import rasi_festivals as festivals
        f, notes, _ = festivals.today(date(2026, 11, 2), {"tithi_idx": 14, "nakshatra_idx": 2})
        self.assertIsNone(f)
        self.assertEqual(notes, ["பௌர்ணமி", "கிருத்திகை"])

    def test_table_is_not_running_out(self):
        import rasi_festivals as festivals
        self.assertFalse(festivals.table_runs_out_soon(date.today()), "add next year's Tamil Nadu Government holiday list to festivals.OFFICIAL")


class WriterChecks(unittest.TestCase):
    def good(self):
        import rasi_writer as writer
        return {"rasis": [{"rasi": r, "stars": 4, "work": "பணியில் முன்னேற்றம் உண்டு", "money": "வருமானம் சீராக இருக்கும்",
                           "family": "குடும்பத்தில் மகிழ்ச்சி", "health": "உடல்நலம் சீராக இருக்கும்"} for r in writer.RASI]}

    def test_clean_draft_passes_and_chandrashtamam_is_capped(self):
        import rasi_writer as writer
        d = self.good()
        self.assertEqual(writer.check(d, [{"rasis": {"மேஷம்": "வேறு வார்த்தைகள்"}}], "விருச்சிகம்"), [])
        self.assertEqual(d["rasis"][7]["stars"], 2)

    def test_copied_words_english_and_fear_are_caught(self):
        import rasi_writer as writer
        d = self.good()
        d["rasis"][0]["work"] = "புதிய திட்டங்கள் நல்ல பலன் தரும்"
        d["rasis"][1]["money"] = "money வரும்"
        d["rasis"][2]["health"] = "ஆபத்து உண்டு"
        src = [{"rasis": {"மேஷம்": "இன்று புதிய திட்டங்கள் நல்ல பலன் தரும் நாள்"}}]
        errs = " ".join(writer.check(d, src, "விருச்சிகம்"))
        self.assertIn("copied", errs)
        self.assertIn("English", errs)
        self.assertIn("fear", errs)

    def test_missing_rasi(self):
        import rasi_writer as writer
        d = self.good()
        d["rasis"].pop()
        self.assertTrue(writer.check(d, [], "மேஷம்"))


class Sources(unittest.TestCase):
    def test_split_twelve_rasis(self):
        import rasi_sources as sources
        text = "\n".join(f"{r}\nஇன்று உங்களுக்கு நல்ல நாள். பணியில் முன்னேற்றம் உண்டு." for r in sources.RASI)
        rs = sources.split_rasis(text)
        self.assertEqual(len(rs), 12)
        self.assertTrue(all(v.startswith("இன்று") for v in rs.values()))

    def test_date_tokens_match_real_urls(self):
        import rasi_sources as sources
        toks = sources.date_tokens(date(2026, 10, 31))
        for u in ("today-rasi-palan-in-tamil-daily-horoscope-october-31-2026-predictions-116738.html",
                  "today-rasi-palan-in-tamil-31-october-2026", "rasipalan-on-31st-october-2026-saturday-tns26103100481",
                  "todays-rasipalan-in-tamil-31102026"):
            self.assertTrue(any(t in u for t in toks), u)


class CaptionRules(unittest.TestCase):
    def test_caption(self):
        import rasi_daily as run, rasi_writer as writer
        p = {"date": "2026-10-31", "date_ta": "31 அக்டோபர் 2026", "weekday": "சனி", "tamil_month": "ஐப்பசி", "tamil_day": 14,
             "chandrashtamam": "விருச்சிகம்", "rahu": "9:00 – 10:30", "emagandam": "1:30 – 3:00", "kuligai": "6:00 – 7:30"}
        rs = [{"rasi": r, "stars": 5 if r == "சிம்மம்" else 3, "work": "பணியில் முன்னேற்றம்"} for r in writer.RASI]
        for page in ("rasipuram", "coimbatore"):
            cap = run.caption(run.PAGES[page], p, {"name": "தீபாவளி", "theme": "diwali"}, ["பிரதோஷம்"], rs)
            tags = [w for w in cap.split() if w.startswith("#")]
            self.assertLessEqual(len(tags), 5)
            self.assertEqual(tags[-1], "#Rasipuram360" if page == "rasipuram" else "#Coimbatore360")
            self.assertIn("#Deepavali", tags)
            self.assertIn("தீபாவளி நல்வாழ்த்துகள்", cap)
            self.assertIn("சிம்மம்", cap.split("\n")[2])
            self.assertNotIn("கமெண்ட்", cap)
            self.assertLess(len(cap), 2200)


if __name__ == "__main__":
    unittest.main()
