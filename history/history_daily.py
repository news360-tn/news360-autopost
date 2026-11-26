"""owner 26 Nov: DAILY DISTRICT HISTORY / TEMPLE STORY REEL - one per page per day, separate from news, rasipalan and gold.

  python history/history_daily.py                 pages = HISTORY_PAGES (or history/config.json "enabled_pages")
  DRY_RUN=1 (default)      builds the reel into out/history/<page>/ and posts NOTHING
  LANE_POST=1 + DRY_RUN=0  posts - only for a page listed in config "enabled_pages", only a verified + sourced topic, only after the
                           owner's approval during the first hold_days (history/state/approvals.json), and only once a day per page.
Flow per page: pick topic -> script (writer model, fact gate, else plain facts) -> scene pictures -> voice (config "voice") -> reel
(heritage parchment design, history_render.py) -> caption (AI-visuals line + source names) -> [hold for approval] -> post.
A failure is only logged: it never touches news, rasipalan or gold posts."""
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "lanes"))
import lane_common as common  # noqa: E402
import history_images  # noqa: E402
import history_render  # noqa: E402
import history_voice  # noqa: E402
import history_writer as writer  # noqa: E402
import lane_pages as pagecfg  # noqa: E402

LANE = "history"
CFG_PATH = HERE / "config.json"


def config():
    return common.load_json(CFG_PATH, {})


def approvals():
    return common.load_json(common.state_dir(LANE) / "approvals.json", {})


def hold_active(cfg, page, day):
    """the first hold_days days after the page's first story: every story waits for approval (hold_until is set at the first build)"""
    until = cfg.get("hold_until") or ""
    return bool(until) and day.isoformat() <= until


def used_ids(page):
    return common.load_json(common.state_dir(LANE) / f"used_{page}.json", [])


def mark_used(page, tid):
    ids = used_ids(page)
    if tid not in ids:
        ids.append(tid)
    common.save_json(common.state_dir(LANE) / f"used_{page}.json", ids)


def caption(p, topic, lines, ai):
    src = sorted({urlparse(s["url"]).hostname.replace("www.", "") for s in topic.get("sources", []) if s.get("url")})
    hook = lines[0]["text"] if lines else topic["title_ta"]
    parts = [f"🏛️ நம்ம ஊர் வரலாறு | {topic['title_ta']}", "", hook, ""]
    if ai:
        parts += ["🎨 படங்கள் AI மூலம் உருவாக்கப்பட்டவை - உண்மையான இடத்தின் புகைப்படங்கள் அல்ல.", ""]
    if src:
        parts += ["📚 தகவல் மூலங்கள்: " + ", ".join(src), ""]
    parts += ["🙏 நம்ம ஊர் வரலாறு தினமும் - " + p["tag"] + " #நம்மஊர்வரலாறு #வரலாறு"]
    return "\n".join(parts)[:2150]


def default_ask():
    """the writer model when keys exist (free writers first, Claude only as the backup); None = the plain fact script"""
    try:
        sys.path.insert(0, str(ROOT / "research_free"))
        import llm
        if not llm.chain() and not llm.claude_available():
            return None

        def ask(system, user):
            try:
                return llm.ask_json(system, user)[0]
            except Exception:
                if llm.claude_available():
                    return llm.ask_claude(system, user, max_tokens=2500)[0]
                raise
        return ask
    except Exception:
        return None


def build(page_key, topic, outdir, cfg=None, ask=None, generate=None, voice=None, log=common.log):
    """make the reel for one topic -> dict(mp4, caption, ai, dur, lines, how, cover_ms). Raises on a real problem."""
    cfg = cfg or config()
    p = dict(pagecfg.page(page_key), logo=common.logo_data_uri(page_key))
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    lines, how = writer.write(topic, ask=ask, log=log)
    prompts = writer.scene_prompts(topic, n=len(lines))
    uris, ai = history_images.make_scenes(prompts, outdir / "scenes", seed=sum(map(ord, topic["id"])) % 9973, generate=generate, log=log)
    provider = voice if voice is not None else cfg.get("voice", "none")
    clips, voiced = [], False
    if provider and provider != "none":
        try:
            clips = history_voice.synth(lines, provider, outdir / "voice", log=log)
            voiced = bool(clips)
        except Exception as e:      # a voice problem never blocks the story: subtitles + music
            log("voice not used:", str(e)[:150])
    if clips:
        times = history_voice.line_times([history_voice.wav_seconds(c) for c in clips])
    else:
        times = history_render.estimate_times(lines)
    html = history_render.reel_page(p, topic, lines, uris, times, ai=bool(ai))
    (outdir / "reel.html").write_text(html, encoding="utf-8")
    scenes, dur = history_render.timeline(times)
    music = common.soundtrack(dur, outdir / "music.wav", mood=cfg.get("music_mood", "soft"))
    audio = music
    if clips and music:
        starts = [(a, c) for (a, b), c in zip(scenes, clips)]
        audio = common.mix_audio(music, [(a + 0.25, c) for a, c in starts], outdir / "mix.wav", dur)
    mp4 = outdir / "reel.mp4"
    common.render_reel(outdir / "reel.html", mp4, audio, log=log)
    common.screenshot_page(outdir / "reel.html", outdir / "cover.png", history_render.COVER_MS / 1000)
    cap = caption(p, topic, lines, bool(ai))
    (outdir / "caption.txt").write_text(cap, encoding="utf-8")
    return {"mp4": mp4, "caption": cap, "ai": ai, "dur": dur, "lines": lines, "how": how, "voiced": voiced,
            "cover_ms": history_render.COVER_MS, "topic": topic["id"]}


def run_page(page_key, day, dry, allow_unverified=False, out_root=None, ask=None, generate=None, log=common.log):
    """-> a short status string. Never raises."""
    try:
        cfg = config()
        if not dry and page_key not in cfg.get("enabled_pages", []):
            return "page not enabled in history/config.json"
        if not dry and common.posted_today(LANE, page_key, day):
            return "already posted today"
        used = used_ids(page_key)
        topic = writer.pick_topic(page_key, used, allow_unverified=allow_unverified or (dry and os.environ.get("HISTORY_ALLOW_UNVERIFIED") == "1"))
        if not topic:
            return "no verified topic with sources + facts available - nothing built"
        out = Path(out_root or ROOT / "out" / "history") / page_key
        res = build(page_key, topic, out, cfg=cfg, ask=ask if ask is not None else default_ask(), generate=generate, log=log)
        log(f"{page_key}: reel built for '{topic['id']}' ({res['dur']:.0f} s, script {res['how']}, {res['ai']} AI pictures, voice {'yes' if res['voiced'] else 'no'})")
        if dry:
            return f"DRY RUN: built {res['mp4']} - not posted"
        key = f"{page_key}:{topic['id']}"
        if hold_active(cfg, page_key, day) and not approvals().get(key):
            common.save_json(common.state_dir(LANE) / f"pending_{page_key}.json",
                             {"topic": topic["id"], "date": day.isoformat(), "preview": str(res["mp4"]), "caption": res["caption"]})
            return f"HELD for the owner's approval ({key})"
        p = pagecfg.page(page_key)
        mid, link = common.post_reel(page_key, res["mp4"], res["caption"], LANE, day, tag=p["tag"], cover_ms=res["cover_ms"], logf=log)
        common.mark_posted(LANE, page_key, day, topic=topic["id"], media_id=mid, permalink=link)
        mark_used(page_key, topic["id"])
        return f"POSTED {link}"
    except common.Paused as e:
        return f"paused: {e}"
    except Exception as e:
        return f"NOT POSTED - {str(e)[:300]}"


def approve(keys):
    """the owner's go-ahead for held stories: keys like "namakkal:tiruchengode-ardhanareeswarar" -> history/state/approvals.json.
    Only ids that exist in that page's topic bank are accepted. Returns the list of keys recorded."""
    done = approvals()
    ok = []
    for k in keys:
        page, _, tid = k.strip().partition(":")
        if page in pagecfg.PAGES and any(t["id"] == tid for t in writer.load_bank(page)):
            done[f"{page}:{tid}"] = datetime_now_iso()
            ok.append(f"{page}:{tid}")
        else:
            common.log(f"approval ignored (unknown page or topic): {k[:80]}")
    common.save_json(common.state_dir(LANE) / "approvals.json", done)
    return ok


def datetime_now_iso():
    from datetime import datetime
    return datetime.now(common.IST).isoformat(timespec="seconds")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "approve":
        got = approve(sys.argv[2:])
        common.log(f"approved: {', '.join(got) or 'nothing'}")
        return 0
    cfg = config()
    dry = common.is_dry()
    pages = (os.environ.get("HISTORY_PAGES", "").split() or cfg.get("enabled_pages", []) or (["namakkal"] if dry else []))
    day = common.today()
    common.log(f"history lane - {', '.join(pages) or 'no pages'} - {'DRY RUN' if dry else 'LIVE'}")
    out = 0
    for pg in pages:
        if pg not in pagecfg.PAGES:
            common.log(f"{pg}: unknown page")
            continue
        status = run_page(pg, day, dry)
        common.log(f"{pg}: {status}")
        out += status.startswith("NOT POSTED")
    return 0      # a lane problem is logged, never a red run that could alarm the news pipeline


if __name__ == "__main__":
    sys.exit(main())
