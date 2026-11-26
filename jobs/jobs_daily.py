"""owner 26 Nov: DAILY DISTRICT JOBS REEL - one per page per day, only when a real, new/upcoming, still-open, district-only job exists.

  python jobs/jobs_daily.py                       pages = JOBS_PAGES (or jobs/config.json "enabled_pages")
  DRY_RUN=1 (default)     reads the official sources, applies every rule, builds the reel if something qualifies, posts NOTHING
                          and writes out/jobs/<page>/report.json (every candidate and why it was kept or rejected)
  LANE_POST=1 + DRY_RUN=0 posts - only for an enabled page, only from sources the owner confirmed, once a day per page.
Rules live in jobs/jobs_engine.py (official source, district match, every field + date + number found in the official text, open,
new or upcoming, not posted before). No match -> no post. A failure is only logged: it never touches news, rasipalan, gold or history."""
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "lanes"))
import lane_common as common  # noqa: E402
import jobs_engine as eng  # noqa: E402
import jobs_render  # noqa: E402
import lane_pages as pagecfg  # noqa: E402

LANE = "jobs"
CFG_PATH = HERE / "config.json"


def config():
    return common.load_json(CFG_PATH, {})


def seen_path(page):
    return common.state_dir(LANE) / f"seen_{page}.json"


def posted_map(page):
    return {r["key"]: r for r in common.load_json(common.state_dir(LANE) / f"keys_{page}.json", [])}


def remember_posted(page, job, day, link):
    rows = common.load_json(common.state_dir(LANE) / f"keys_{page}.json", [])
    rows.append({"key": eng.job_key(job), "date": day.isoformat(), "post": job["post"], "permalink": link})
    common.save_json(common.state_dir(LANE) / f"keys_{page}.json", rows[-500:])


def default_ask():
    sys.path.insert(0, str(ROOT / "research_free"))
    import llm

    def ask(system, user):
        try:
            return llm.ask_json(system, user)[0]      # free writers first
        except Exception:
            if llm.claude_available():
                return llm.ask_claude(system, user, max_tokens=3000)[0]      # Claude only as the backup
            raise
    return ask


def caption(p, job, left):
    last = job.get("last_date") or job.get("event_date")
    lines = [f"💼 {p['district_ta']} மாவட்ட வேலைவாய்ப்பு அறிவிப்பு", "",
             f"📌 பணி: {job['post']}"]
    if str(job.get("vacancies", "")).strip():
        lines.append(f"👥 காலிப்பணியிடங்கள்: {job['vacancies']}")
    lines += [f"🎓 தகுதி: {job['qualification']}",
              f"📅 {'கடைசி தேதி' if job.get('last_date') else 'நிகழ்ச்சி தேதி'}: {jobs_render.date_ta(__import__('datetime').date.fromisoformat(last))}"
              + ("" if left is None else f" (இன்னும் {left} நாட்கள்)"),
              f"📍 எங்கே: {job['apply_where']}", f"🔗 அதிகாரப்பூர்வ அறிவிப்பு: {job['link']}", "",
              "ℹ️ தகவல் அதிகாரப்பூர்வ அறிவிப்பின் அடிப்படையில் பகிரப்பட்டுள்ளது. விண்ணப்பிக்கும் முன் தகுதி, கடைசி தேதியை அதிகாரப்பூர்வ அறிவிப்பில் சரிபாருங்கள். "
              "வேலை தருவதாகச் சொல்லிப் பணம் கேட்பவர்களிடம் எச்சரிக்கையாக இருங்கள்.", "",
              f"🙏 {p['tag']} #வேலைவாய்ப்பு #{p['district_en'].replace(' ', '')}Jobs"]
    return "\n".join(lines)[:2150]


def collect(page_key, day, get, ask, allow_unconfirmed=False, log=common.log):
    """read every confirmed official source of the page -> (qualifying jobs, report rows). Never raises."""
    cfg = config()
    p = pagecfg.page(page_key)
    allowed = cfg.get("allowed_hosts", ["nic.in", "gov.in"])
    seen = common.load_json(seen_path(page_key), {})
    posted = posted_map(page_key)
    qualifying, report, all_gated = [], [], []
    for src in eng.load_sources(page_key, allow_unconfirmed):
        try:
            if not eng.official_host(src["url"], allowed):
                report.append({"source": src["url"], "result": "source host is not official - skipped"})
                continue
            text, _ = eng.fetch_source(src, get)
            cands = eng.extract(text, ask, p["district_en"])
            own_site = (urlparse(src["url"]).hostname or "").endswith(p["official_site"])
            for j in cands:
                probs = eng.gate(j, text, p, allowed, source_is_district_site=own_site)
                if probs:
                    report.append({"source": src["url"], "title": j.get("title"), "result": "rejected: " + "; ".join(probs)[:200]})
                    continue
                all_gated.append(j)
                why = eng.eligible(j, day, seen, posted, cfg)
                report.append({"source": src["url"], "title": j.get("title"), "result": "rejected: " + why if why else "QUALIFIES"})
                if not why:
                    qualifying.append(j)
        except Exception as e:
            report.append({"source": src.get("url"), "result": "source not read: " + str(e)[:150]})
    return qualifying, report, all_gated


def build(page_key, job, day, outdir, log=common.log):
    p = dict(pagecfg.page(page_key), logo=common.logo_data_uri(page_key))
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    left = eng.days_left(job, day)
    html = jobs_render.reel_page(p, job, left, day)
    (outdir / "reel.html").write_text(html, encoding="utf-8")
    from jobs_render import INTRO_S, STEP_S
    dur = INTRO_S + STEP_S * len(jobs_render.cards(job, left, day)) + 4.8
    music = common.soundtrack(dur, outdir / "music.wav", mood="bright", seed=11)
    mp4 = outdir / "reel.mp4"
    common.render_reel(outdir / "reel.html", mp4, music, log=log)
    common.screenshot_page(outdir / "reel.html", outdir / "cover.png", jobs_render.COVER_MS / 1000)
    cap = caption(p, job, left)
    (outdir / "caption.txt").write_text(cap, encoding="utf-8")
    return {"mp4": mp4, "caption": cap, "dur": dur, "cover_ms": jobs_render.COVER_MS}


def run_page(page_key, day, dry, get=None, ask=None, out_root=None, allow_unconfirmed=False, log=common.log):
    """-> a short status string. Never raises."""
    try:
        cfg = config()
        if not dry and page_key not in cfg.get("enabled_pages", []):
            return "page not enabled in jobs/config.json"
        if not dry and common.posted_today(LANE, page_key, day):
            return "already posted today"
        import requests
        get = get or requests.get
        ask = ask or default_ask()
        allow = allow_unconfirmed or (dry and os.environ.get("JOBS_ALLOW_UNCONFIRMED") == "1")
        qualifying, report, gated = collect(page_key, day, get, ask, allow, log)
        out = Path(out_root or ROOT / "out" / "jobs") / page_key
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        if not dry:      # remember what was seen (first run = baseline, nothing old ever counts as new)
            seen = eng.update_seen(common.load_json(seen_path(page_key), {}), gated, day)
            common.save_json(seen_path(page_key), seen)
        job = eng.pick(qualifying, day)
        if not job:
            return "no qualifying district job today - nothing posted"
        res = build(page_key, job, day, out, log=log)
        log(f"{page_key}: jobs reel built for '{job['post'][:50]}' ({res['dur']:.0f} s)")
        if dry:
            return f"DRY RUN: built {res['mp4']} - not posted"
        p = pagecfg.page(page_key)
        mid, link = common.post_reel(page_key, res["mp4"], res["caption"], LANE, day, tag=p["tag"], cover_ms=res["cover_ms"], logf=log)
        common.mark_posted(LANE, page_key, day, media_id=mid, permalink=link, post=job["post"])
        remember_posted(page_key, job, day, link)
        return f"POSTED {link}"
    except common.Paused as e:
        return f"paused: {e}"
    except Exception as e:
        return f"NOT POSTED - {str(e)[:300]}"


def main():
    cfg = config()
    dry = common.is_dry()
    pages = (os.environ.get("JOBS_PAGES", "").split() or cfg.get("enabled_pages", []) or (["namakkal"] if dry else []))
    day = common.today()
    common.log(f"jobs lane - {', '.join(pages) or 'no pages'} - {'DRY RUN' if dry else 'LIVE'}")
    for pg in pages:
        if pg not in pagecfg.PAGES:
            common.log(f"{pg}: unknown page")
            continue
        common.log(f"{pg}: {run_page(pg, day, dry)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
