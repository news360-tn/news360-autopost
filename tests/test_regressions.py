"""Regression tests built from real cases the pipeline got wrong (26-27 Oct 2026). Run before every push:

    python3 -m unittest discover -s tests -v

Each test names the real story that broke, so a failure says which old problem has come back."""
import ast, datetime, json, os, re, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for d in ("poster", "research_free", "reel"):
    sys.path.insert(0, str(ROOT / d))

import freshness as fr          # noqa: E402
import allnews                  # noqa: E402
import collect                  # noqa: E402
import post                     # noqa: E402

IST = fr.IST
TODAY = datetime.datetime.now(IST).date()


def from_file(path, names, extra=None):
    """load only some top-level functions/assignments of a file (reel4.py needs a browser library to import as a whole)"""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in names)]
    ns = {"os": os, "sys": sys, "json": json, "re": re, "Path": Path, "__file__": str(path), "html": __import__("html")}
    ns.update(extra or {})
    exec(compile(ast.Module(body, []), str(path), "exec"), ns)
    return ns


class DuplicateCheck(unittest.TestCase):
    def test_prisoner_is_not_the_rss_march(self):      # 27 Oct: the escaped-prisoner news was skipped as a 'duplicate'
        self.assertFalse(fr.similar("நாமக்கல்லில் நீதிமன்ற உத்தரவுப்படி ஆர்எஸ்எஸ் அணிவகுப்பு ஊர்வலம்",
                                    "நாமக்கல் நீதிமன்றத்திலிருந்து  தப்பியோடிய கைதி பிடிப்பு", 0.55))

    def test_bus_death_is_not_roof_fall(self):
        self.assertFalse(fr.similar("வேலகவுண்டம்பட்டி அருகே தனியார் பேருந்து மோதி தொழிலாளி உயிரிழப்பு",
                                    "வீட்டின் கூரை மேலிருந்து விழுந்த தொழிலாளி உயிரிழப்பு", 0.55))

    def test_same_news_other_words_still_duplicate(self):
        self.assertTrue(fr.similar("100 ஆண்டுகளான புளியமரம் சாலையின் குறுக்கே சாய்ந்தது",
                                   "சேந்தமங்கலம் அருகே 100 ஆண்டு புளியமரம் சாலையில் சாய்ந்தது", 0.55))
        self.assertTrue(fr.similar("நாமக்கல்லில் நீதிமன்ற உத்தரவுப்படி ஆர்எஸ்எஸ் அணிவகுப்பு ஊர்வலம்",
                                   "நாமக்கல்லில் ஆா்எஸ்எஸ் அணிவகுப்பு ஊா்வலம்", 0.55))      # old print form ா் = ர்

    def test_different_numbers_are_different_events(self):      # 26 Oct: RN-111 vs RN-62
        self.assertTrue(fr.different_numbers("சூதாடிய 8 பேர் கைது", "சூதாடிய 6 பேர் கைது"))

    def test_power_cut_other_place_not_duplicate(self):      # 27 Oct: RN-131 skipped as a 'duplicate' of an older power cut
        a = "காளப்பநாயக்கன்பட்டி துணை மின் நிலையப் பராமரிப்பு: நாளை காலை 9 முதல் மதியம் 2 வரை மின் தடை"
        b = "பூளவாடி துணை மின் நிலையப் பராமரிப்பு: நாளை காலை 9 முதல் மதியம் 2 வரை மின் தடை"
        self.assertFalse(fr.similar(b, a, 0.62, f"{TODAY:%d %b %Y}, 02:00"))
        self.assertTrue(fr.similar(a, a, 0.62, f"{TODAY:%d %b %Y}, 02:00"))
        old = TODAY - datetime.timedelta(days=15)
        self.assertFalse(fr.similar(a, a, 0.62, f"{old:%d %b %Y}, 10:00"))      # same substation, an older notice

    def test_writer_same_news(self):
        self.assertTrue(collect.same_news("மழையால் நாமக்கல் கலெக்டர் குடியிருப்பின் சுற்றுச்சுவர் இடிந்தது",
                                          "கனமழை: நாமக்கல் ஆட்சியர் பங்களா சுவர் இடிந்து விழுந்தது"))

    def test_writer_other_news_not_duplicate(self):      # 28 Oct: three new stories were skipped as 'similar to a filed story'
        now = f"{TODAY:%d %b %Y}, 06:00"
        old = f"{TODAY - datetime.timedelta(days=6):%d %b %Y}, 06:00"
        self.assertFalse(collect.same_news("நாமக்கல்லில் மரவள்ளி விவசாயிகள் பிரச்னை: அக். 30-ல் முத்தரப்புக் கூட்டம்",
                                           "30ல் விவசாயிகள் குறைதீர் கூட்டம்", now))      # RN-140: two shared words only
        self.assertFalse(collect.same_news("🗑️ குப்பையுடன் தேங்கிய மழைநீர் – சுகாதார சீர்கேடு",
                                           "சர்வீஸ் சாலையில் குவிக்கும் குப்பையால் சுகாதார சீர்கேடு", old))      # RN-69: days older
        self.assertTrue(collect.same_news("கலெக்டர் அலுவலகத்தில் முதியவர் தீக்குளிக்க முயற்சி: நிலத் தகராறு",
                                          "முதியவர் தீக்குளிக்க முயற்சி கலெக்டர் ஆபீசில் பரபரப்பு", now))      # RN-146: real repeat


class LearnedPriority(unittest.TestCase):
    """28 Oct: power cuts and jobs (our most watched news) were scored -0.5 as 'civic' / 'education_jobs'"""

    def test_power_cut_and_jobs_have_own_topic(self):
        import learned
        self.assertEqual("power_cut", learned.topic("நாளை காளப்பநாயக்கன்பட்டி உள்ளிட்ட 9 பகுதிகளில் மின் தடை: சாலை பணி"))
        self.assertEqual("jobs", learned.topic("நாமக்கல்லில் 23ஆம் தேதி தனியார் வேலைவாய்ப்பு முகாம்"))
        self.assertEqual("education", learned.topic("TNPSC குரூப் 4 தேர்வுக்கு இலவசப் பயிற்சி"))      # 'தேர்' (chariot) is not temple
        real = learned.load
        learned.load = lambda: {"topic_weight": {"civic": -0.5, "education": -0.5}}      # not measured yet: the starting weight is used
        try:
            self.assertGreater(learned.boost("நாளை 9 பகுதிகளில் மின் தடை"), 0)
            self.assertGreater(learned.boost("தனியார் வேலைவாய்ப்பு முகாம்"), 0)
        finally:
            learned.load = real


class PowerCutTiming(unittest.TestCase):
    A = "காளப்பநாயக்கன்பட்டி துணை மின் நிலையப் பராமரிப்பு: நாளை காலை 9 முதல் மதியம் 2 வரை மின் தடை"

    def at(self, h, m=0):
        return datetime.datetime.combine(TODAY, datetime.time(h, m), IST)

    def test_late_notice_not_posted(self):      # 27 Oct: RN-131 (cut until 2 pm) went out at 13:42
        y = TODAY - datetime.timedelta(days=1)
        self.assertIn("too late", fr.power_cut_over(self.A, "", f"{y} 18:33", self.at(13, 35)))
        self.assertEqual("", fr.power_cut_over(self.A, "", f"{y} 18:33", self.at(10, 0)))

    def test_tomorrow_cut_posted_today(self):
        self.assertEqual("", fr.power_cut_over(self.A, "", f"{TODAY} 18:33", self.at(21, 0)))

    def test_english_and_evening_end(self):
        y = TODAY - datetime.timedelta(days=1)
        self.assertIn("14:00", fr.power_cut_over("Power cut in Rasipuram tomorrow", "Power cut from 9 am to 2 pm", f"{y}", self.at(13, 45)))
        self.assertIn("17:00", fr.power_cut_over("நாமக்கல்லில் இன்று காலை 9 முதல் மாலை 5 வரை மின்தடை", "", f"{TODAY}", self.at(16, 45)))


class NewsDate(unittest.TestCase):
    def test_date_from_link(self):      # 27 Oct: the Sheet had no publish date for RN-131
        self.assertEqual(datetime.date(2026, 10, 26), fr.news_date("", "https://www.dinamani.com/all-editions/edition-dharmapuri/namakkal/2026/Oct/26/x"))
        self.assertEqual(datetime.date(2026, 10, 23), fr.news_date("", "https://www.dinakaran.com/district/namakkal-231026-3/"))
        self.assertEqual(datetime.date(2026, 10, 25), fr.news_date("2026-10-25T09:00:00Z", ""))


class PostingGate(unittest.TestCase):
    def setUp(self):
        post.ALL_ROWS = []

    def row(self, **k):
        r = {"story_id": "RN-T1", "headline_ta": "மோகனூரில் தடை செய்யப்பட்ட புகையிலை விற்ற 2 பேர் கைது", "headline_en": "Two held for selling banned tobacco in Mohanur",
             "category": "குற்றம்", "location": "மோகனூர், நாமக்கல்", "caption": "மோகனூரில் புகையிலை விற்ற இருவர் கைது",
             "published": f"{TODAY}", "source": "https://www.dinamalar.com/news/tamil-nadu-district-news-namakkal/x/1",
             "researched": f"{TODAY:%d %b %Y}, 06:25", "post_status": "", "notes": "", "batch": "", "review": "Auto"}
        r.update(k)
        return r

    def test_today_news_posts(self):
        self.assertEqual("", post.skip_reason(self.row()))

    def test_two_day_old_news_not_posted(self):      # 27 Oct: RN-103 (25 Oct RSS march) went out two days late
        old = TODAY - datetime.timedelta(days=2)
        self.assertIn("older than yesterday", post.skip_reason(self.row(published=f"{old}", researched=f"{old:%d %b %Y}, 01:50")))

    def test_old_news_by_link_date(self):
        old = TODAY - datetime.timedelta(days=3)
        self.assertIn("older than yesterday", post.skip_reason(self.row(
            published="", source=f"https://www.dinamani.com/all-editions/edition-dharmapuri/namakkal/{old:%Y/%b/%d}/x")))

    def test_other_district_not_posted(self):      # 26 Oct: Attur / Salem stories slipped through
        self.assertTrue(post.skip_reason(self.row(headline_ta="ஆத்தூரில் பேருந்து விபத்து: 5 பேர் காயம்", location="ஆத்தூர், சேலம்",
                                                  caption="ஆத்தூர் அருகே விபத்து")))


class DistrictFilter(unittest.TestCase):
    def test_link_district(self):
        self.assertEqual("namakkal", allnews.url_district("https://www.dinamalar.com/news/tamil-nadu-district-news-namakkal/central-media-crowds/4360211"))
        self.assertEqual("namakkal", allnews.url_district("https://www.dinamani.com/all-editions/edition-dharmapuri/namakkal/2026/Oct/26/x"))
        self.assertEqual("virudhunagar", allnews.url_district("https://www.dinamani.com/all-editions/edition-madurai/virudhunagar/2026/Oct/26/x"))

    def test_places(self):
        for t in ("இராசிபுரத்தில்", "மல்லசமுத்திரத்தில் தீ", "Kolli Hills rain", "வேலகவுண்டம்பட்டியில்"):
            self.assertTrue(allnews.has_place(t), t)
        self.assertTrue(allnews.other_district("சேலத்தில் கனமழை"))


class Recheck(unittest.TestCase):
    URL = "https://www.dinamalar.com/news/tamil-nadu-district-news-namakkal/central-media-crowds/4360211"

    def test_rejected_district_page_story_checked_again_once(self):      # 27 Oct: centre-median / Star 3.0 stayed 'checked earlier'
        st = {"s": "notdistrict", "n": 0}
        self.assertTrue(collect.recheck_once(st, self.URL))
        self.assertNotIn("s", st)      # the writer must not see the old verdict
        st["s"] = "notdistrict"
        self.assertFalse(collect.recheck_once(st, self.URL))      # only once

    def test_old_duplicate_checked_again(self):      # the escaped-prisoner news
        st = {"s": "dup", "n": 0}
        self.assertTrue(collect.recheck_once(st, "https://news.google.com/x"))

    def test_other_district_not_rechecked(self):
        self.assertFalse(collect.recheck_once({"s": "notdistrict"}, "https://www.dinamani.com/all-editions/edition-madurai/virudhunagar/2026/Oct/26/x"))


class DinamalarList(unittest.TestCase):
    def test_reads_whole_list(self):      # 27 Oct: only the first 8 stories were read; the 140 mm rain report was missed
        import sources
        page = ('<a href="/news/tamil-nadu-district-news-namakkal/2-held-for-selling-tobacco/4360215">x</a>'
                '{"url":"/news/tamil-nadu-district-news-namakkal/4360205/140--rain-recorded-in-district-people-rejoice"}')
        old = sources._get
        sources._get = lambda u: page
        try:
            links = sources.candidate_links(60)
        finally:
            sources._get = old
        self.assertEqual(2, len(links))
        self.assertTrue(any(l.endswith("/140--rain-recorded-in-district-people-rejoice/4360205") for l in links))


class Reel(unittest.TestCase):
    def test_no_b_tags_on_screen(self):      # 27 Oct: '<b>90,703</b>' showed in a reel
        E = from_file(ROOT / "reel" / "reel4.py", {"E"})["E"]
        self.assertEqual("90,703", E("<b>90,703</b>"))
        self.assertEqual("5 &lt; 7", E("5 < 7"))

    def test_google_voice_free_only(self):      # owner 27 Oct: Google voice only inside the free allowance, else Valluvar
        ns = from_file(ROOT / "reel" / "reel4.py", {"voice_setting", "pick_voice", "google_used_this_month", "google_record", "_gv_dir", "_GV"})
        with tempfile.TemporaryDirectory() as tmp:
            ns["_gv_dir"] = lambda: Path(tmp)
            os.environ["GOOGLE_TTS_API_KEY"] = "test"
            try:
                spec = {"story": "RN-142", "sentences": [{"say": "அ" * 1300}]}
                self.assertEqual("google", ns["pick_voice"](spec)[0].get("engine"))
                self.assertEqual("google", ns["pick_voice"]({"story": "RN-143", "sentences": spec["sentences"]})[0].get("engine"))      # every reel, odd numbers too
                month = datetime.datetime.now(IST).strftime("%Y-%m")
                (Path(tmp) / f"RN-2_gvoice_{month}.json").write_text(json.dumps({"chars": 699500}))
                self.assertEqual("edge", ns["pick_voice"]({"story": "RN-144", "sentences": spec["sentences"]})[0].get("engine"))
                cfg = json.loads((ROOT / "poster" / "config.json").read_text())
                self.assertLessEqual(cfg["reel_voice_alt"]["free_chars_per_month"], 1000000, "never above Google's free tier")
            finally:
                os.environ.pop("GOOGLE_TTS_API_KEY", None)
        os.environ.pop("GOOGLE_TTS_API_KEY", None)
        self.assertEqual("edge", ns["pick_voice"]({"story": "RN-146", "sentences": [{"say": "அ"}]})[0].get("engine"))      # no key -> Valluvar


class Images(unittest.TestCase):
    def test_cover_dev_scenes_schnell(self):      # owner 27 Oct: cost saving, every picture still made for this news
        import imagegen
        calls = []
        old_fal, old_size, old_key = imagegen._fal, imagegen.to_story_size, os.environ.get("FAL_KEY")
        imagegen._fal = lambda p, s, k, model=None: calls.append(model) or b"img"
        imagegen.to_story_size = lambda b: b
        os.environ["FAL_KEY"] = "test"
        try:
            imagegen.generate("p", 1); imagegen.generate("p", 1, cheap=True)
        finally:
            imagegen._fal, imagegen.to_story_size = old_fal, old_size
            if old_key is None:
                os.environ.pop("FAL_KEY", None)
            else:
                os.environ["FAL_KEY"] = old_key
        self.assertEqual(["fal-ai/flux/dev", "fal-ai/flux/schnell"], calls)
        self.assertNotEqual("1", os.environ.get("REUSE_IMAGES"), "older pictures are never reused")


class PrimeTime(unittest.TestCase):
    """owner 27 Oct: non-urgent reels wait for 9-12 / 18-21:30; urgent news never waits; nothing is ever dropped"""
    def at(self, h, m=0):
        return datetime.datetime.combine(TODAY, datetime.time(h, m), IST)

    def row(self, title, filed_h_ago=1):
        t = datetime.datetime.now(IST) - datetime.timedelta(hours=filed_h_ago)
        return {"story_id": "RN-T", "headline_ta": title, "headline_en": "", "category": "", "researched": t.strftime("%d %b %Y, %H:%M")}

    def test_urgent_never_waits(self):
        for title in ("காளப்பநாயக்கன்பட்டி பகுதியில் நாளை மின் தடை", "தனியார் பேருந்து மோதி தொழிலாளி உயிரிழப்பு",
                      "நாமக்கல் மாவட்டத்தில் கனமழை எச்சரிக்கை", "ஆட்சியர் அறிவிப்பு: சிறப்பு முகாம்"):
            self.assertEqual("", post.prime_wait(self.row(title), self.at(14)), title)

    def test_other_news_waits_outside_prime_time(self):
        self.assertIn("prime time", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா"), self.at(14)))
        self.assertIn("18:00", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா"), self.at(14)))
        self.assertIn("09:00", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா"), self.at(23)))

    def test_posts_inside_prime_time(self):
        self.assertEqual("", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா"), self.at(10)))
        self.assertEqual("", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா"), self.at(19, 30)))

    def test_never_dropped_after_long_wait(self):      # a reel that has waited 12 hours goes out whatever the hour
        self.assertEqual("", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா", filed_h_ago=13), self.at(3)))


class ReelOpening(unittest.TestCase):
    """owner 27 Oct (change 1): the most striking fact is spoken first"""
    def test_punch_line(self):
        ns = from_file(ROOT / "reel" / "reel4.py", {"punch_line", "punch_on"})
        self.assertEqual("90,703 குழந்தைகளுக்கு வைட்டமின் ஏ முகாம்!", ns["punch_line"]({"hook": ["குழந்தைகளுக்கு வைட்டமின் ஏ முகாம்", "<b>90,703</b>"]}))
        self.assertEqual("நாளை மின் தடை!", ns["punch_line"]({"hook": ["நாளை மின் தடை", "9 பகுதிகளில் மின் தடை - முழுப் பட்டியல் கீழே பாருங்கள்"]}))
        self.assertEqual("எழுத்தாளர் வரி", ns["punch_line"]({"punch": "<b>எழுத்தாளர்</b> வரி", "hook": ["x", "1"]}))
        # owner 28 Oct: the reel opens with the one-line story itself (first 2-3 s), not a separate punch line
        self.assertFalse(json.loads((ROOT / "poster" / "config.json").read_text()).get("reel_punch"))


class ReelWords(unittest.TestCase):
    """owner 27 Oct: no double reading, full dates, everyday Tamil Nadu words in voice, subtitles and cards"""
    ns = None

    @classmethod
    def setUpClass(cls):
        cls.ns = from_file(ROOT / "reel" / "reel4.py", {"everyday", "everyday_on", "EVERYDAY", "fix_dates", "MONTHS_TA", "repeats", "_words", "punch_line"})

    def test_everyday_words(self):
        e = self.ns["everyday"]
        self.assertEqual("தனியார் பஸ் மோதி டூவீலரில் சென்ற", e("தனியார் பேருந்து மோதி இருசக்கர வாகனத்தில் சென்ற"))
        self.assertEqual("மாவட்ட கலெக்டர் மதுபாலன், கலெக்டரிடம் மனு", e("மாவட்ட ஆட்சியர் மதுபாலன், ஆட்சியரிடம் மனு"))
        self.assertEqual("போலீசார் விசாரணை", e("காவல்துறையினர் விசாரணை"))
        self.assertEqual("திமுக ஆட்சியில்", e("திமுக ஆட்சியில்"))      # 'in rule' is not 'Collector'

    def test_full_dates(self):
        f, T = self.ns["fix_dates"], datetime.date(2026, 10, 27)
        self.assertEqual("முகாம் அக்டோபர் 30ஆம் தேதி வரை நடைபெறும்.", f("முகாம் <b>30</b> வரை நடைபெறும்.", T))
        self.assertEqual("அக்டோபர் 22ஆம் தேதி மணிகட்டிபுதூர்", f("22-ஆம் தேதி மணிகட்டிபுதூர்", T))
        for keep in ("அக்டோபர் 28 அன்று", "மாலை 4:30 வரை", "10.30 வரை", "5 வயது வரையுள்ள"):
            self.assertEqual(keep, f(keep, T))

    def test_no_double_reading(self):
        self.assertTrue(self.ns["repeats"]("தனியார் பஸ் மோதி தொழிலாளி பலி!", "வேலகவுண்டம்பட்டி அருகே தனியார் பஸ் மோதி ஒரு கூலித் தொழிலாளி உயிரிழந்தார்."))
        self.assertFalse(self.ns["repeats"]("நாளை மின் தடை!", "ராசிபுரம் துணை மின் நிலையத்தில் பராமரிப்பு பணி நடைபெறுகிறது."))
        self.assertEqual("தனியார் பேருந்து மோதி தொழிலாளி பலி!", self.ns["punch_line"]({"hook": ["தனியார் பேருந்து மோதி தொழிலாளி பலி", "22 விபத்து, ஞாயிறு"]}))


class Website(unittest.TestCase):
    """owner 27 Oct: every posted story goes to the website with all its details; a website problem never stops posting"""
    def test_payload_has_everything(self):
        import website
        row = {"story_id": "RN-140", "researched": "27 Oct 2026, 10:14", "published": "2026-10-27", "headline_ta": "மரவள்ளி கூட்டம்",
               "headline_en": "Tapioca meeting", "category": "Government & Services", "location": "நாமக்கல்", "source": "https://www.dinamalar.com/x/1",
               "caption": "📰 முழு விவரம்:\n🕘 நேரம்: மாலை 4:30", "reel_script": "கூட்டம் நடைபெறும்.",
               "images": '["https://res.cloudinary.com/a.jpg", "NOIMAGE", "http://insecure.jpg"]', "reel_link": "நாமக்கல் 360: https://www.instagram.com/reel/De_Cu6Pj3zR/"}
        p = website.payload(row, "", {"title_en": "Collector calls meeting", "story_en": "A meeting will be held."})
        self.assertEqual("2026-10-27T10:14:00+05:30", p["filed_at"])      # exact India time, not 12:00
        self.assertEqual(["https://res.cloudinary.com/a.jpg"], p["images"])
        self.assertEqual("Collector calls meeting", p["headline_en"])
        self.assertIn("instagram.com/reel/", p["reel_link"])
        for k in ("location", "category", "source", "caption", "reel_script"):
            self.assertTrue(p[k], k)

    def test_never_raises_without_key(self):
        import website
        os.environ.pop("WEBSITE_INGEST_KEY", None)
        self.assertFalse(website.send({"story_id": "RN-1", "headline_ta": "x", "_en": {"title_en": "x", "story_en": "y" * 50}}, ""))


class FullDetail(unittest.TestCase):
    """28 Oct: reels were 50-90 words while the source article had more detail; owner: full detail, at most 90 seconds"""

    def length_problems(self, words, article_words):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[1]["output"])
        d["reel_script"] = " ".join(["தகவல்"] * words) + " " + validate.LAST
        art = " ".join(f"சொல்{i}" for i in range(article_words))
        return [x for x in validate.validate(d, art) if x.startswith("reel_script has")]

    def test_short_reel_of_long_article_is_rewritten(self):
        self.assertTrue(self.length_problems(70, 300))
        self.assertFalse(self.length_problems(150, 300))

    def test_short_article_keeps_a_short_reel(self):
        self.assertFalse(self.length_problems(70, 80))

    def test_never_more_words_than_90_seconds(self):
        self.assertTrue(self.length_problems(200, 400))

    def test_examples_are_full_detail(self):
        for e in json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8")):
            self.assertGreaterEqual(len(e["output"]["reel_script"].split()), 80)

    def test_reel_max_seconds(self):
        self.assertEqual(json.loads((ROOT / "poster" / "config.json").read_text())["reel_max_seconds"], 90)
        self.assertIn("fit_max(work, len(texts), lead, gap)", (ROOT / "reel" / "reel4.py").read_text(encoding="utf-8"))

class Proofread(unittest.TestCase):
    """28 Oct: the last Tamil proofread damaged posted reels (RN-158 'செல்லாமல் சென்றனர் செல்லாமல்', RN-155 நம்மக்கல்,
    RN-145 'வர வேண்டிய' -> 'வரத் தேவையற்ற', RN-150 மீட்டப்பட்டனர், RN-157 follow line 'மூன்று அறுபது')"""

    def setUp(self):
        import tamilcheck
        self.T = tamilcheck

    def test_bad_fixes_are_refused(self):
        art = "மனைப்பட்டா கேட்டு மனு. சிறுவர்கள் மீட்கப்பட்டனர்."
        for w, ok in [("நாமக்கல்", "நம்மக்கல்"), ("வர வேண்டிய", "வரத் தேவையற்ற"), ("த்ரீ சிக்ஸ்டி", "மூன்று அறுபது"),
                      ("Follow", "பின்தொடருங்கள்"), ("கடுமையாக", ""), ("செல்லாமல்", "செல்லாமல் சென்றனர் செல்லாமல்"),
                      ("மீட்கப்பட்டனர்.", "மீட்டப்பட்டனர்."), ("மனைப்பட்டா,", "மனப்பெட்டா,"), ("பரமத்தி வேலூர்", "ப.வேலுார்")]:
            self.assertTrue(self.T.unsafe(w, ok, art), f"{w} -> {ok} must be refused")

    def test_verb_not_turned_into_noun(self):      # 29 Oct Coimbatore RN-1: 'அரசு நிர்வாகிக்க' -> 'அரசு நிர்வாகம்'
        self.assertTrue(self.T.unsafe("அரசு நிர்வாகிக்க", "அரசு நிர்வாகம்", ""))
        self.assertEqual(self.T.unsafe("அரசு நிர்வாகிக்க", "அரசு நிர்வகிக்க", ""), "")      # the real spelling fix still goes in

    def test_real_spelling_fixes_still_go_in(self):
        for w, ok in [("வெளியிட்டுுள்ளார்.", "வெளியிட்டுள்ளார்."), ("இயக்குனர்", "இயக்குநர்"), ("கீழ்கண்ட", "கீழ்க்கண்ட")]:
            self.assertEqual(self.T.unsafe(w, ok, ""), "")

    def test_rn158_no_word_inside_a_word(self):
        import llm
        row = {"headline_ta": "x", "caption": "பள்ளிக்குச் செல்லாமல்", "slides_spec": "{}",
               "reel_script": "பள்ளிக்குச் செல்லாமல் பிறந்த நாள். ராஜா பள்ளிக்குச் செல்லவில்லை. " + self.T.LAST}
        before = dict(row)
        old = llm.ask_json
        llm.ask_json = lambda *a, **k: ({"fixes": [{"wrong": "செல்ல", "right": "செல்லாமல் சென்ற"}]}, "test")
        try:
            self.T.proofread(row, log=lambda *a: None, article="")
        finally:
            llm.ask_json = old
        self.assertEqual(row, before)

    def test_age_shorthand_sent_back(self):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[1]["output"])
        d["reel_script"] = "வீராச்சாமி தனது மகன் ராஜா, 12, பள்ளிக்குச் செல்லவில்லை. " + validate.LAST
        self.assertTrue([p for p in validate.validate(d, "") if "ages" in p])


class ClearReading(unittest.TestCase):
    """owner 28 Oct: one-line story in the first 2-3 seconds; every number heard with its meaning (age, count, date with month)"""

    def problems(self, script):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[0]["output"])
        d["reel_script"] = script + " " + validate.LAST
        return validate.validate(d, "")

    def test_long_opening_sent_back(self):
        self.assertTrue([p for p in self.problems("பள்ளிக்குச் செல்லாமல் பிறந்த நாள் கொண்டாடச் சென்ற மூன்று மாணவர்கள் குமாரபாளையம் பஸ் நிலையத்தில் போலீசாரால் மீட்கப்பட்டனர்.") if p.startswith("sentence 1")])
        self.assertFalse([p for p in self.problems("குமாரபாளையத்தில் மூன்று மாணவர்கள் மீட்பு.") if p.startswith("sentence 1")])

    def test_bare_numbers_sent_back(self):
        self.assertTrue([p for p in self.problems("மாணவர்கள் மீட்பு. கவுசிக், 14, ஸ்ரீதர், 15, காணவில்லை.") if "without their meaning" in p])
        for ok in ("மாணவர்கள் மீட்பு. 14 வயது கவுசிக் காணவில்லை.", "மாணவர்கள் மீட்பு. அக்டோபர் 28, 2026 அன்று கூட்டம்.",
                   "மாணவர்கள் மீட்பு. 30 பாட்டில்கள், ரூ.5,000 பறிமுதல்.", "மாணவர்கள் மீட்பு. விலை 5.70 ரூபாய்."):
            self.assertFalse([p for p in self.problems(ok) if "without their meaning" in p], ok)


class FollowUpAndPage(unittest.TestCase):
    """28 Oct: RN-159 (3 arrested for the laptop theft) was blocked as a duplicate of RN-42 (the theft, 6 days earlier);
    RN-161 (the district Collector's Diwali sweets notice on the paper's Namakkal page) was blocked as not Namakkal news"""

    def test_arrest_after_the_theft_is_new_news(self):
        old = {"story_id": "RN-42", "researched": "22 Oct 2026, 10:26", "headline_en": "Four laptops and a phone stolen from students' room near Thiruchengode",
               "headline_ta": "மாணவர்களின் லேப்டாப் திருட்டு: 4 லேப்டாப், செல்போன் மாயம்"}
        new = {"story_id": "RN-159", "researched": "28 Oct 2026, 06:39", "headline_en": "Three arrested for stealing laptops and mobile phones from student rooms near Tiruchengode",
               "headline_ta": "திருச்செங்கோடு அருகே மடிக்கணினி, கைப்பேசி திருட்டு: 3 பேர் கைது"}
        self.assertTrue(fr.follow_up(old, new))

    def test_same_day_report_stays_a_duplicate(self):
        a = {"researched": "27 Oct 2026, 17:10", "headline_ta": "ஓமலூரில் காணாமல் போன 4 பள்ளி சிறுவர்கள் குமாரபாளையத்தில் மீட்பு"}
        b = {"researched": "28 Oct 2026, 05:46", "headline_ta": "பள்ளி செல்லாமல் பிறந்த நாள் கொண்டாடிய 3 மாணவர்கள் குமாரபாளையத்தில் மீட்பு"}
        self.assertFalse(fr.follow_up(a, b))

    def test_paper_namakkal_page_is_namakkal_news(self):
        row = {"source": "https://www.dinamani.com/all-editions/edition-dharmapuri/namakkal/2026/Oct/27/தீபாவளி-இனிப்பு-காரம்-விற்பனைக்கு-உரிமம்-பெறுவது-கட்டாயம்",
               "headline_ta": "தீபாவளி இனிப்பு, காரம் விற்பனைக்கு உரிமம் கட்டாயம்", "caption": "உரிமம் கட்டாயம்", "location": "Tamil Nadu"}
        self.assertEqual(post.not_namakkal(row), "")
        row["headline_ta"] = "சேலத்தில் இனிப்பு விற்பனைக்கு உரிமம் கட்டாயம்"
        self.assertTrue(post.not_namakkal(row))


class Ages(unittest.TestCase):
    """28 Oct RN-156: 'செல்வம், 47,' / 'செல்வம் (47)' was heard as a bare number - the age is said with வயது, also for stories written earlier"""

    def test_newspaper_ages(self):
        import names
        self.assertEqual(names.ages("வசிக்கும் செல்வம், 47, நிதி"), "வசிக்கும் செல்வம் (47 வயது), நிதி")
        self.assertEqual(names.ages("உரிமையாளர் செல்வம் (47), செவ்வாய்"), "உரிமையாளர் செல்வம் (47 வயது), செவ்வாய்")
        self.assertEqual(names.ages("கவுசிக், 14, ஸ்ரீதர், 15, ஆகியோரும்"), "கவுசிக் (14 வயது), ஸ்ரீதர் (15 வயது), ஆகியோரும்")
        for same in ("அக்டோபர் 13, 14, 15ஆம் தேதிகளில்", "அக்டோபர், 12, கூட்டம்", "செல்வம் (47 வயது) வந்தார்", "ரூ.5,000 அபராதம்"):
            self.assertEqual(names.ages(same), same)
        self.assertIn("(47 வயது)", names.spoken("வசிக்கும் செல்வம், 47, நிதி"))


if __name__ == "__main__":
    unittest.main()


class ReelTooLong(unittest.TestCase):
    """owner 28 Oct (RN-153): a reel over 90 s is shortened automatically, never held"""
    SCRIPT = ("பொத்தனூர் சந்தையில் இரண்டு வாரங்களாக தேங்காய் ஏலம் நடைபெறவில்லை. விவசாயிகள் பாதிக்கப்பட்டுள்ளனர். "
              "வாரந்தோறும் செவ்வாய், வியாழக்கிழமைகளில் ஏலம் நடைபெறுவது வழக்கம். பல ஊர்களைச் சேர்ந்த விவசாயிகள் இங்கு வருகின்றனர். "
              "வியாபாரிகள் ஏலத்தில் பங்கேற்க மறுத்தனர். வெளிச் சந்தைகளில் குறைந்த விலையே கிடைக்கும். "
              "மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.")

    def test_shorter_keeps_first_and_follow_line(self):
        out = post.shorten_script(self.SCRIPT, 0.5)
        self.assertLess(len(out), len(self.SCRIPT))
        self.assertTrue(out.startswith("பொத்தனூர் சந்தையில்"))
        self.assertTrue(out.endswith("பின்தொடருங்கள்."))
        self.assertGreaterEqual(len(re.split(r"(?<=[.!?])\s+", out)), 3)

    def test_short_script_unchanged(self):
        s = "ஒன்று. இரண்டு. மேலும் செய்திகளுக்கு பின்தொடருங்கள்."
        self.assertEqual(post.shorten_script(s, 0.5), s)


class NotNews(unittest.TestCase):
    """owner 29 Oct (RN-189 egg price): a story that only says the article has no details is never filed or posted;
    a real story with one such sentence keeps its facts and loses only that sentence (RN-112)"""
    EMPTY = ("முட்டை விலை நிலவரம் குறித்த விவரம் இந்தக் கட்டுரையில் வெளியிடப்படவில்லை. கட்டுரையில் முட்டை விலை எவ்வளவு என்ற எண்ணோ தகவலோ இல்லை. "
             "வேறு ஒரு செய்தி உள்ளது. அந்தச் செய்தி முட்டை விலையுடன் தொடர்புடையது அல்ல. முட்டை விலை விவரம் தெரியவந்ததும் பகிரப்படும். "
             "மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.")
    REAL = ("நாமக்கல்லில் ஓய்வு பெற்றோர் நலச்சங்கக் கூட்டம் நடைபெற்றது. அகவிலைப்படியுடன் ஓய்வூதியம் வழங்க வேண்டும் என கோரிக்கை விடுக்கப்பட்டது. "
            "மாவட்டத் தலைவர் தலைமை வகித்தார். 2003க்குப் பின் பணியில் சேர்ந்தோர் இக்கோரிக்கையின் கீழ் வருகின்றனர். "
            "மொத்தப் பண பலன்கள் குறித்த முழு விவரம் இன்னும் தெரியவரவில்லை. மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.")

    def setUp(self):
        import freshness
        self.f = freshness

    def test_empty_story_rejected(self):
        self.assertTrue(self.f.no_news("முட்டை விலை நிலவரம்", self.EMPTY, "").startswith("not news"))

    def test_headline_saying_no_detail_rejected(self):
        self.assertTrue(self.f.no_news("முட்டை விலை - விவரம் இன்னும் தெரியவில்லை", "", ""))

    def test_real_story_kept_and_cleaned(self):
        self.assertEqual(self.f.no_news("ஓய்வு பெற்றோர் நலச்சங்கக் கூட்டம்", self.REAL, ""), "")
        out = self.f.strip_no_news(self.REAL)
        self.assertNotIn("தெரியவரவில்லை", out)
        self.assertIn("அகவிலைப்படியுடன்", out)
        self.assertTrue(out.endswith("பின்தொடருங்கள்."))

    def test_posting_gate_blocks_it(self):
        row = {"story_id": "RN-189", "headline_ta": "முட்டை விலை நிலவரம்", "headline_en": "Egg price update", "category": "Business & Prices",
               "published": post.datetime.now(post.IST).isoformat(), "researched": post.datetime.now(post.IST).strftime("%d %b %Y, %H:%M"),
               "reel_script": self.EMPTY, "caption": "", "slides_spec": "{}"}
        self.assertTrue(post.skip_reason(row).startswith("not news"))


class OwnerFixes29Oct(unittest.TestCase):
    """29 Oct: RN-189 (deleted by the owner) wrote about the article; RN-188 + RN-189 were both today's egg price; Claude backup model id"""

    def test_script_about_the_article_refused(self):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[0]["output"])
        d["reel_script"] = ("முட்டை விலை நிலவரம் குறித்த விவரம் இந்தக் கட்டுரையில் வெளியிடப்படவில்லை. "
                            "முட்டை விலை விவரம் தெரியவந்ததும் பகிரப்படும். " + validate.LAST)
        self.assertTrue([x for x in validate.validate(d, "") if "talks about the article" in x])
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[0]["output"])
        self.assertFalse([x for x in validate.validate(d, "") if "talks about the article" in x])

    def test_one_egg_price_a_day(self):
        now = f"{TODAY:%d %b %Y}, 06:40"
        a = {"story_id": "RN-188", "researched": now, "headline_ta": "நாமக்கல் மண்டலத்தில் முட்டை விலை ரூ.5.70-ஆக நீடிப்பு", "headline_en": "Egg price stays"}
        b = {"story_id": "RN-189", "researched": now, "headline_ta": "முட்டை விலை நிலவரம்", "headline_en": ""}
        self.assertEqual("egg", fr.same_day_recurring(a, b))
        y = dict(a, researched=f"{TODAY - datetime.timedelta(days=1):%d %b %Y}, 06:40")
        self.assertEqual("", fr.same_day_recurring(y, b))      # tomorrow's price is a new post
        self.assertEqual("", fr.same_day_recurring(a, {"researched": now, "headline_ta": "ராசிபுரத்தில் பைக் திருட்டு"}))
        post.ALL_ROWS = [dict(a, post_status="Posted")]
        try:
            self.assertIn("one egg price post a day", post.skip_reason(dict(b, source="", category="", published=f"{TODAY}", notes="", batch="", review="Auto")))
        finally:
            post.ALL_ROWS = []

    def test_claude_model_exists(self):
        self.assertIn('os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")', (ROOT / "research_free" / "llm.py").read_text())


class FreeImagesFirst(unittest.TestCase):
    """owner 29 Oct: Cloudflare and NVIDIA (free) first; FAL only when they fail (cover dev, scenes schnell)"""

    def order(self, fail, cheap=False):
        import imagegen
        calls = []
        def src(name):
            def f(*a, **k):
                calls.append(name)
                if name in fail:
                    raise RuntimeError(name + " 429: daily free allocation used")
                return b"img"
            return f
        saved = {k: getattr(imagegen, k) for k in ("_cf", "generate_nvidia", "_fal", "to_story_size")}
        env = {k: os.environ.get(k) for k in ("FAL_KEY", "NVIDIA_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")}
        imagegen._cf, imagegen.generate_nvidia, imagegen.to_story_size = src("cloudflare"), src("nvidia"), (lambda b: b)
        imagegen._fal = lambda p, s, k, model=None: src(model)()
        os.environ.update({k: "test" for k in env})
        imagegen.DEAD.clear()
        try:
            imagegen.generate("p", 1, cheap=cheap)
        finally:
            for k, v in saved.items():
                setattr(imagegen, k, v)
            for k, v in env.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
            imagegen.DEAD.clear()
        return calls

    def test_free_first_then_fal(self):
        self.assertEqual(["cloudflare"], self.order(set()))
        self.assertEqual(["cloudflare", "nvidia"], self.order({"cloudflare"}))
        self.assertEqual(["cloudflare", "nvidia", "fal-ai/flux/dev"], self.order({"cloudflare", "nvidia"}))      # cover
        self.assertEqual(["cloudflare", "nvidia", "fal-ai/flux/schnell"], self.order({"cloudflare", "nvidia"}, cheap=True))      # scenes 2-3


class NewsImagePrompt(unittest.TestCase):
    """owner 29 Oct: a clean, detailed prompt so the picture shows THIS news - the scene first, generic covers sent back"""
    GOOD = ("Two police constables in khaki unload seized liquor bottles from a white mini lorry onto a long table outside the Pallipalayam "
            "police station while four men in shirts and veshti stand in a line nearby; the bottles are stacked in cartons, a police jeep is "
            "parked behind, neem trees shade the station compound, late morning sunlight, light clouds, eye-level 35 mm wide shot showing the "
            "table, the lorry and the station gate.")

    def test_scene_first(self):
        p = collect.IMG_TEMPLATE.format(scene=self.GOOD)
        self.assertTrue(p.startswith("Two police constables"))
        self.assertIn("No text", p)

    def test_generic_cover_sent_back(self):
        head = "Police seize 120 liquor bottles from a mini lorry near Pallipalayam"
        self.assertTrue(collect.scene_ok(self.GOOD, head))
        self.assertFalse(collect.scene_ok("A quiet village road in Tamil Nadu with trees and houses in daylight. " * 4, head))
        self.assertFalse(collect.scene_ok("Police seize liquor bottles from a lorry.", head))      # too short



class HeadlineOnlyAndMadeUp(unittest.TestCase):
    """owner 29 Oct (RN-12 Coimbatore, K.N. Nehru raid): a page that is only a headline is not written (the writer invented
    the rest), and a draft whose words mostly do not come from a Tamil article is not filed. Short real briefs still pass."""
    def test_headline_only_page_has_no_body(self):
        a = {"title": "KN Nehru Raid| எதிர்பாரா ட்விஸ்ட்டாக கோவையிலும்.. அதிரும் சிங்காநல்லூர்",
             "text": "KN Nehru Raid| எதிர்பாரா ட்விஸ்ட்டாக கோவையிலும்.. அதிரும் சிங்காநல்லூர் எதிர்பாரா ட்விஸ்ட்டாக கோவையிலும்"}
        self.assertLess(len(collect.body_words(a)), collect.HEADLINE_ONLY_MIN)

    def test_short_real_brief_passes(self):
        a = {"title": "சூதாட்டம் ஆடிய 6 பேருக்கு காப்பு",
             "text": "சூதாட்டம் ஆடிய 6 பேருக்கு காப்பு. பரமத்தி வேலூர் போலீசார் ரோந்து சென்றபோது பணம் வைத்து சூதாடிய ஆறு பேரை கைது செய்து ரூ.11,600 பறிமுதல் செய்தனர். அனைவரும் ஜாமீனில் விடுவிக்கப்பட்டனர்."}
        self.assertGreaterEqual(len(collect.body_words(a)), collect.HEADLINE_ONLY_MIN)

    def test_made_up_draft_rejected(self):
        art = {"url": "https://example.com/a", "title": "t", "published": collect.datetime.datetime.now(collect.IST).isoformat(),
               "text": " ".join(["நாமக்கல்லில்", "போலீசார்", "விசாரணை", "நடத்தினர்", "பொதுமக்கள்", "கோரிக்கை"] * 15)}
        d = {"tamil_headline": "நாமக்கல் செய்தி", "english_headline": "x", "category": "c", "location": "l", "scenes": ["s"],
             "reel_script": "", "caption": "", "slides_spec": {}}
        story, why = collect.file_story(art, (d, "test", ["not grounded: only 37% of the words come from the article"], 1), [], [])
        self.assertIsNone(story)
        self.assertIn("likely made up", why)
