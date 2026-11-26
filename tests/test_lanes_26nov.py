"""owner 26 Nov: the two daily lanes (history/, jobs/) - safety first: nothing posts by accident, nothing unsourced is ever said."""
import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
for d in ("lanes", "history", "jobs"):
    sys.path.insert(0, str(ROOT / d))
import lane_common as common          # noqa: E402
import lane_factgate as factgate        # noqa: E402
import lane_pages as pages           # noqa: E402
import history_writer as hw      # noqa: E402
import history_render as hr      # noqa: E402
import history_voice as hv       # noqa: E402
import history_daily as hd       # noqa: E402
import jobs_engine as je         # noqa: E402
import jobs_render as jr         # noqa: E402
import jobs_daily as jd          # noqa: E402

TOPIC = {"id": "t1", "order": 1, "verified": True, "sources": [{"url": "https://example.gov.in/a"}], "title_ta": "திருச்செங்கோடு கோயில்", "town_ta": "திருச்செங்கோடு",
         "facts": [{"id": "f1", "ta": "மலைமேல் கோயில் உள்ளது.", "kind": "fact"}, {"id": "f2", "ta": "சுமார் 1,200 படிகள் உள்ளன.", "kind": "fact"},
                   {"id": "f3", "ta": "இரண்டு தேவர்களின் போட்டி என்பது நம்பிக்கை.", "kind": "tradition"}],
         "avoid_regex": ["\\d[\\d,]*\\s*ஆண்டு"], "people": ["Tipu Sultan"], "scene_hints": ["a hill temple"]}


class SwitchTest(unittest.TestCase):
    def test_nothing_posts_unless_both_switches_say_so(self):
        for env, want in (({"DRY_RUN": "", "LANE_POST": ""}, True), ({"DRY_RUN": "1", "LANE_POST": "1"}, True), ({"DRY_RUN": "", "LANE_POST": "1"}, False),
                          ({"DRY_RUN": "0", "LANE_POST": "1"}, False), ({"DRY_RUN": "true", "LANE_POST": "1"}, True)):
            with mock.patch.dict(os.environ, env):
                self.assertEqual(common.is_dry(), want, env)

    def test_no_page_is_enabled_yet_and_every_page_is_configured(self):
        self.assertEqual(json.loads((ROOT / "history" / "config.json").read_text(encoding="utf-8"))["enabled_pages"], [])
        self.assertEqual(json.loads((ROOT / "jobs" / "config.json").read_text(encoding="utf-8"))["enabled_pages"], [])
        for k, p in pages.PAGES.items():
            self.assertTrue(all(p.get(f) for f in ("town", "district_ta", "district_en", "handle", "tag", "official_site", "aliases")), k)
            self.assertTrue((ROOT / "history" / "topics" / f"{k}.json").exists() and (ROOT / "jobs" / "sources" / f"{k}.json").exists(), k)

    def test_job_sources_start_unconfirmed(self):
        for k in pages.PAGES:
            d = json.loads((ROOT / "jobs" / "sources" / f"{k}.json").read_text(encoding="utf-8"))
            self.assertTrue(d["sources"] and not any(s["confirmed"] for s in d["sources"]), k)
            self.assertEqual(je.load_sources(k), [])      # the lane ignores a source until the owner confirms it
            self.assertTrue(je.load_sources(k, allow_unconfirmed=True))


class FactGateTest(unittest.TestCase):
    def test_numbers_and_number_words(self):
        self.assertEqual(factgate.unsupported_numbers("சுமார் 1,200 படிகள்", "1200 படிகள்"), [])
        self.assertEqual(factgate.unsupported_numbers("1,500 படிகள்", "1200 படிகள்"), ["1500"])
        self.assertEqual(factgate.unsupported_numbers("ஆயிரம் படிகள்", "படிகள் உள்ளன"), ["ஆயிரம்"])
        self.assertEqual(factgate.unsupported_numbers("௧௨௦௦ படிகள்", "1,200 படிகள்"), [])      # Tamil digits

    def test_dates_in_the_ways_notices_write_them(self):
        d = date(2026, 12, 5)
        for txt in ("last date 05/12/2026", "5.12.2026 வரை", "05-12-2026", "5 December 2026", "5 டிசம்பர் 2026", "Dec 5, 2026", "2026-12-05"):
            self.assertTrue(factgate.date_in_text(d, txt), txt)
        self.assertFalse(factgate.date_in_text(d, "last date 06/12/2026"))
        self.assertTrue(factgate.value_in_text("Junior  Assistant", "post: junior assistant (office)"))

    def test_history_gate(self):
        ok = [{"text": "மலைமேல் கோயில் உள்ளது.", "facts": ["f1"]}, {"text": "சுமார் 1,200 படிகள் உள்ளன.", "facts": ["f2"]},
              {"text": "இரண்டு தேவர்களின் போட்டி என்பது நம்பிக்கை.", "facts": ["f3"]}]
        self.assertEqual(factgate.check_history_lines(ok, TOPIC), [])
        bad = factgate.check_history_lines([{"text": "சுமார் 1,500 படிகள் உள்ளன.", "facts": ["f2"]}], TOPIC)
        self.assertTrue(any("1500" in x for x in bad))
        bad = factgate.check_history_lines([{"text": "இரண்டு தேவர்கள் போட்டியிட்டனர்.", "facts": ["f3"]}], TOPIC)
        self.assertTrue(any("legend" in x for x in bad))      # a legend told as a fact
        self.assertTrue(any("ஆண்டு" in x or "disagree" in x for x in factgate.check_history_lines([{"text": "இது 1,300 ஆண்டு பழமை.", "facts": ["f1"]}], TOPIC)))
        self.assertTrue(any("not on the sheet" in x for x in factgate.check_history_lines([{"text": "மலைமேல் கோயில்.", "facts": ["f9"]}], TOPIC)))
        self.assertTrue(any("not based" in x for x in factgate.check_history_lines([{"text": "மலைமேல் கோயில்.", "facts": []}], TOPIC)))
        self.assertEqual(factgate.check_history_lines([{"text": "தெரியுமா?", "facts": [], "frame": True}], TOPIC), [])      # a frame line


class HistoryWriterTest(unittest.TestCase):
    def test_only_verified_sourced_topics_can_post(self):
        self.assertEqual(hw.eligible(TOPIC), "")
        self.assertIn("verified", hw.eligible(dict(TOPIC, verified=False)))
        self.assertIn("source", hw.eligible(dict(TOPIC, sources=[])))
        self.assertIn("facts", hw.eligible(dict(TOPIC, facts=TOPIC["facts"][:2])))
        self.assertEqual(hw.eligible(dict(TOPIC, verified=False), allow_unverified=True), "")      # previews only
        for k in pages.PAGES:      # the shipped banks: nothing is verified yet, and no topic is verified without sources
            for t in hw.load_bank(k):
                self.assertFalse(t.get("verified"), f"{k}/{t['id']} must not be verified before sources are added")

    def test_pick_goes_in_order_and_cycles(self):
        a, b = dict(TOPIC, id="a", order=2), dict(TOPIC, id="b", order=1)
        self.assertEqual(hw.pick_topic("x", [], bank=[a, b])["id"], "b")
        self.assertEqual(hw.pick_topic("x", ["b"], bank=[a, b])["id"], "a")
        self.assertEqual(hw.pick_topic("x", ["a", "b"], bank=[a, b])["id"], "b")      # every topic told: the cycle starts again
        self.assertIsNone(hw.pick_topic("x", [], bank=[dict(TOPIC, verified=False)]))

    def test_plain_script_always_passes_and_a_bad_model_script_is_dropped(self):
        lines, how = hw.write(TOPIC)
        self.assertEqual(how, "plain")
        self.assertEqual(hw.gate(lines, TOPIC), [])
        liar = lambda s, u: {"lines": [{"text": "இது 1,300 ஆண்டு பழமையான கோயில்.", "facts": ["f1"]}]}      # invents an age
        lines, how = hw.write(TOPIC, ask=liar, log=lambda *a: None)
        self.assertEqual(how, "plain")
        honest = lambda s, u: {"lines": [{"text": "தெரியுமா?", "facts": [], "frame": True}, {"text": "மலைமேல் கோயில் உள்ளது.", "facts": ["f1"]},
                                         {"text": "சுமார் 1,200 படிகள் உள்ளன.", "facts": ["f2"]}]}
        self.assertEqual(hw.write(TOPIC, ask=honest)[1], "model")
        self.assertEqual(hw.write(TOPIC, ask=mock.Mock(side_effect=RuntimeError("down")), log=lambda *a: None)[1], "plain")

    def test_pictures_never_name_a_real_person(self):
        self.assertEqual(len(hw.scene_prompts(TOPIC)), 6)
        with self.assertRaises(ValueError):
            hw.scene_prompts(dict(TOPIC, scene_hints=["Tipu Sultan on a horse"]))


class HistoryRenderAndDailyTest(unittest.TestCase):
    def test_reel_page_is_a_seek_page_with_logo_top_right_and_no_news_bar(self):
        lines, _ = hw.write(TOPIC)
        p = dict(pages.page("namakkal"), logo="data:image/png;base64,AAAA")
        html = hr.reel_page(p, TOPIC, lines, ["data:image/jpeg;base64,AAAA"] * 3, hr.estimate_times(lines))
        self.assertIn("window.seek", html)
        self.assertIn("window.DUR", html)
        self.assertIn("நம்ம ஊர் வரலாறு", html)
        self.assertRegex(html, r"#logo\{position:absolute;top:\d+px;right:\d+px")
        self.assertNotIn("ticker", html.lower())
        self.assertIn("AI மூலம்", hr.reel_page(p, TOPIC, lines, ["x"], hr.estimate_times(lines), ai=True))
        self.assertNotIn("AI மூலம்", hr.reel_page(p, TOPIC, lines, ["x"], hr.estimate_times(lines), ai=False))
        self.assertLess(hr.fit_size("x" * 120), hr.fit_size("x" * 30))

    def test_caption_discloses_ai_pictures_and_names_the_sources(self):
        lines, _ = hw.write(TOPIC)
        cap = hd.caption(pages.page("namakkal"), TOPIC, lines, True)
        self.assertIn("AI மூலம் உருவாக்கப்பட்டவை", cap)
        self.assertIn("example.gov.in", cap)
        self.assertNotIn("AI மூலம்", hd.caption(pages.page("namakkal"), TOPIC, lines, False))

    def test_live_run_needs_an_enabled_page_and_posts_once_a_day_and_holds_for_approval(self):
        day = date(2026, 12, 1)
        self.assertIn("not enabled", hd.run_page("namakkal", day, dry=False))
        cfg = {"enabled_pages": ["namakkal"], "hold_until": "2026-12-14"}
        self.assertTrue(hd.hold_active(cfg, "namakkal", day))
        self.assertFalse(hd.hold_active(cfg, "namakkal", date(2026, 12, 15)))
        self.assertFalse(hd.hold_active({"enabled_pages": ["namakkal"]}, "namakkal", day))
        with tempfile.TemporaryDirectory() as t, mock.patch.object(common, "ROOT", Path(t)), mock.patch.object(hd, "config", return_value=cfg):
            common.mark_posted("history", "namakkal", day, topic="x")
            self.assertEqual(hd.run_page("namakkal", day, dry=False), "already posted today")

    def test_with_no_verified_topic_nothing_is_built(self):
        with mock.patch.object(hd, "config", return_value={"enabled_pages": ["namakkal"]}):
            self.assertIn("no verified topic", hd.run_page("salem", date(2026, 12, 1), dry=True))

    def test_voice_timing_and_providers(self):
        self.assertEqual(hv.line_times([2.0, 5.0]), [(0.0, 3.0), (3.0, 8.85)])
        self.assertEqual(hv.synth([{"text": "x"}], "none", tempfile.gettempdir()), [])
        post = mock.Mock(return_value=mock.Mock(status_code=200, json=lambda: {"audios": ["QUJD"]}))
        self.assertEqual(hv.sarvam_say("வணக்கம்", key="K", post=post), b"ABC")
        self.assertEqual(post.call_args.kwargs["headers"]["api-subscription-key"], "K")
        with self.assertRaises(RuntimeError):
            hv.sarvam_say("x", key="")


class ApprovalTest(unittest.TestCase):
    def test_only_real_topics_can_be_approved_and_they_are_remembered(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.object(common, "ROOT", Path(t)):
            got = hd.approve(["namakkal:namakkal-anjaneyar", "namakkal:made-up", "mars:x", "garbage"])
            self.assertEqual(got, ["namakkal:namakkal-anjaneyar"])
            self.assertIn("namakkal:namakkal-anjaneyar", hd.approvals())
            self.assertNotIn("namakkal:made-up", hd.approvals())


# ---- jobs ----
PAGE = pages.page("namakkal")
NOTICE = ("Namakkal District Collectorate Recruitment. Post: Junior Assistant. Vacancies: 12. Qualification: Any Degree. "
          "Last date for applications 15/12/2026. Apply at: District Employment Office, Namakkal. Notice published 1/12/2026.")
JOB = {"post": "Junior Assistant", "vacancies": "12", "qualification": "Any Degree", "last_date": "2026-12-15", "event_date": "",
       "apply_where": "District Employment Office, Namakkal", "link": "https://namakkal.nic.in/notice/1.pdf", "published": "2026-12-01"}
CFG = {"new_within_days": 2, "upcoming_event_days": 14}
HOSTS = ["nic.in", "gov.in"]


class JobsEngineTest(unittest.TestCase):
    def test_html_to_text_and_pdf_links(self):
        text, links = je.html_to_text('<html><script>x=1</script><body><p>Junior <b>Assistant</b></p><a href="/a.pdf">Notice</a></body></html>', "https://x.nic.in/r/")
        self.assertEqual(text, "Junior Assistant Notice")
        self.assertEqual(links, [("https://x.nic.in/a.pdf", "Notice")])

    def test_a_job_backed_by_the_official_text_passes(self):
        self.assertEqual(je.gate(JOB, NOTICE, PAGE, HOSTS), [])

    def test_every_missing_or_unbacked_field_blocks_the_post(self):
        for field in ("post", "qualification", "apply_where", "link"):
            self.assertTrue(any("missing" in x for x in je.gate(dict(JOB, **{field: ""}), NOTICE, PAGE, HOSTS)), field)
        self.assertTrue(any("last date" in x for x in je.gate(dict(JOB, last_date="", event_date=""), NOTICE, PAGE, HOSTS)))
        self.assertTrue(any("2026-12-20" in x for x in je.gate(dict(JOB, last_date="2026-12-20"), NOTICE, PAGE, HOSTS)))      # a date the notice does not contain
        self.assertTrue(any("vacancies" in x for x in je.gate(dict(JOB, vacancies="40"), NOTICE, PAGE, HOSTS)))
        self.assertTrue(any("qualification" in x for x in je.gate(dict(JOB, qualification="B.E. only"), NOTICE, PAGE, HOSTS)))
        self.assertTrue(any("official" in x for x in je.gate(dict(JOB, link="https://jobs-fake.com/x"), NOTICE, PAGE, HOSTS)))
        self.assertTrue(any("official" in x for x in je.gate(dict(JOB, link="http://namakkal.nic.in/x"), NOTICE, PAGE, HOSTS)))

    def test_other_district_jobs_are_refused(self):
        other = NOTICE.replace("Namakkal", "Chennai")
        job = dict(JOB, apply_where="District Employment Office, Chennai")
        self.assertTrue(any("district" in x for x in je.gate(job, other, PAGE, HOSTS)))
        self.assertEqual(je.gate(job, other, PAGE, HOSTS, source_is_district_site=True), [])      # the district's own site is always its district

    def test_eligibility_rules(self):
        day, seen, posted = date(2026, 12, 2), {}, {}
        self.assertEqual(je.eligible(JOB, day, seen, posted, CFG), "")      # published yesterday, open
        self.assertEqual(je.eligible(JOB, date(2026, 12, 16), seen, posted, CFG), "expired")
        self.assertIn("old", je.eligible(dict(JOB, published="2026-11-20"), day, seen, posted, CFG))      # published long ago
        self.assertIn("old", je.eligible(dict(JOB, published=""), day, {je.job_key(JOB): "2026-10-01"}, {}, CFG))      # first seen long ago
        self.assertEqual(je.eligible(dict(JOB, published=""), day, {je.job_key(JOB): "2026-12-01"}, {}, CFG), "")      # first seen yesterday
        self.assertEqual(je.eligible(dict(JOB, published="2026-10-01", last_date="", event_date="2026-12-10"), day, seen, posted, CFG), "")      # upcoming camp
        self.assertIn("old", je.eligible(dict(JOB, published="2026-10-01", last_date="", event_date="2027-03-01"), day, seen, posted, CFG))      # too far away
        self.assertEqual(je.eligible(JOB, day, seen, {je.job_key(JOB): {}}, CFG), "already posted")

    def test_first_run_is_a_baseline_so_old_notices_never_count_as_new(self):
        seen = je.update_seen({}, [dict(JOB, published="")], date(2026, 12, 2))
        self.assertIn("old", je.eligible(dict(JOB, published=""), date(2026, 12, 2), seen, {}, CFG))
        seen2 = je.update_seen(dict(seen), [dict(JOB, post="Typist", published="")], date(2026, 12, 3))      # a later run: a new notice is first seen today
        self.assertEqual(seen2[je.job_key(dict(JOB, post="Typist"))], "2026-12-03")

    def test_the_soonest_closing_job_is_picked(self):
        a, b = dict(JOB, last_date="2026-12-20"), dict(JOB, last_date="2026-12-10", post="B")
        self.assertEqual(je.pick([a, b], date(2026, 12, 2))["post"], "B")
        self.assertIsNone(je.pick([], date(2026, 12, 2)))


class JobsDailyTest(unittest.TestCase):
    def _run(self, text, ask_jobs, dry=True, day=date(2026, 12, 2), enabled=("namakkal",)):
        get = lambda url, **k: mock.Mock(status_code=200, text=f"<html><body>{text}</body></html>", content=b"")
        ask = lambda s, u: {"jobs": ask_jobs}
        with tempfile.TemporaryDirectory() as t, mock.patch.object(common, "ROOT", Path(t)), \
                mock.patch.object(jd, "config", return_value={"enabled_pages": list(enabled), "allowed_hosts": HOSTS, "new_within_days": 2, "upcoming_event_days": 14}), \
                mock.patch.object(jd, "build", return_value={"mp4": Path(t) / "r.mp4", "caption": "c", "dur": 20, "cover_ms": 1}) as b:
            out = Path(t) / "out"
            st = jd.run_page("namakkal", day, dry, get=get, ask=ask, out_root=out, allow_unconfirmed=True)
            rep = json.loads((out / "namakkal" / "report.json").read_text(encoding="utf-8")) if (out / "namakkal" / "report.json").exists() else []
            return st, rep, b.called

    def test_a_qualifying_job_builds_a_reel_in_a_dry_run_and_posts_nothing(self):
        st, rep, built = self._run(NOTICE, [JOB])
        self.assertTrue(st.startswith("DRY RUN: built"))
        self.assertTrue(built)
        self.assertEqual(rep[0]["result"], "QUALIFIES")

    def test_no_match_no_post(self):
        st, rep, built = self._run(NOTICE, [dict(JOB, last_date="2026-12-20")])
        self.assertIn("no qualifying", st)
        self.assertFalse(built)
        self.assertIn("not found in the official text", rep[0]["result"])
        st, rep, built = self._run(NOTICE, [])
        self.assertIn("no qualifying", st)

    def test_old_and_expired_jobs_are_not_posted(self):
        st, rep, built = self._run(NOTICE, [dict(JOB, published="2026-11-01")])
        self.assertFalse(built)
        self.assertIn("old notice", rep[0]["result"])
        st, rep, built = self._run(NOTICE, [JOB], day=date(2026, 12, 16))
        self.assertFalse(built)
        self.assertIn("expired", rep[0]["result"])

    def test_a_live_run_for_a_page_that_is_not_enabled_does_nothing(self):
        st, rep, built = self._run(NOTICE, [JOB], dry=False, enabled=())
        self.assertIn("not enabled", st)
        self.assertFalse(built)

    def test_caption_has_the_official_link_the_facts_and_the_fraud_warning(self):
        cap = jd.caption(PAGE, JOB, 13)
        for part in ("Junior Assistant", "Any Degree", "15 டிசம்பர் 2026", "இன்னும் 13 நாட்கள்", "https://namakkal.nic.in/notice/1.pdf", "பணம் கேட்பவர்களிடம்"):
            self.assertIn(part, cap)

    def test_job_reel_page(self):
        p = dict(PAGE, logo="data:image/png;base64,AAAA")
        html = jr.reel_page(p, JOB, 13, date(2026, 12, 2))
        self.assertIn("window.seek", html)
        self.assertIn("window.DUR", html)
        self.assertRegex(html, r"#logo\{position:absolute;top:\d+px;right:\d+px")
        self.assertIn("namakkal.nic.in", html)
        self.assertEqual([c[0] for c in jr.cards(JOB, 13, date(2026, 12, 2))], ["post", "vac", "edu", "cal", "pin"])
        self.assertEqual([c[0] for c in jr.cards(dict(JOB, vacancies=""), 13, date(2026, 12, 2))], ["post", "edu", "cal", "pin"])


if __name__ == "__main__":
    unittest.main()
