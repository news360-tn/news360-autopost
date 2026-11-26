"""owner 26 Nov: what the two daily lanes (history/, jobs/) share. Everything here is about SAFETY and plumbing, not content:

  is_dry()          True unless LANE_POST=1 and DRY_RUN is not 1  -> a lane never posts by accident
  posted_today / mark_posted / state files           once a day per page and lane, kept in <lane>/state/
  render_reel(html, mp4, ...)                        the page's window.seek(t) -> frames -> H.264 (+ music / voice), like goldrate/gold_reel.py
  mix_audio(...)                                     music bed + narration clips placed at their start times
  post_reel(...)                                     Instagram reel (+ the page's Facebook page), reusing goldrate/gold_daily.py's calls
A lane's failure is only logged: it never touches news, rasipalan or gold posts. Never prints a key."""
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))
FPS = 30
W, H = 1080, 1920
for _p in (ROOT / "lanes", ROOT / "reel", ROOT / "goldrate", ROOT / "poster", ROOT / "research_free"):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))      # appended: the news pipeline has modules with generic names (factgate, ...) - ours are all lane_*


def log(*a):
    print(datetime.now(IST).strftime("%H:%M:%S"), *a, flush=True)


def today():
    return datetime.now(IST).date()


def is_dry():
    """posting needs BOTH switches: LANE_POST=1 (set in the workflow by the owner) and DRY_RUN not 1"""
    if os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "yes"):
        return True
    return os.environ.get("LANE_POST", "").strip() != "1"


# ---------- state ----------
def state_dir(lane):
    d = ROOT / lane / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def posted_path(lane, page):
    return state_dir(lane) / f"posted_{page}.json"


def posted_today(lane, page, day):
    """the record of today's post of this lane on this page, or None"""
    for r in load_json(posted_path(lane, page), []):
        if r.get("date") == day.isoformat():
            return r
    return None


def mark_posted(lane, page, day, **meta):
    rows = [r for r in load_json(posted_path(lane, page), []) if r.get("date") != day.isoformat()]
    rows.append({"date": day.isoformat(), "at": datetime.now(IST).isoformat(timespec="seconds"), **meta})
    save_json(posted_path(lane, page), rows[-400:])


# ---------- reel from a seek(t) page ----------
def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def soundtrack(dur, path, mood="soft", seed=7):
    """our own original music bed (reel/music.py) -> wav, or None"""
    try:
        import music
        music.main(str(path), dur, seed=seed, mood=mood)
        return Path(path)
    except Exception as e:
        log("music skipped:", str(e)[:150])
        return None


def mix_audio(music_wav, clips, out_wav, dur, music_gain=0.28):
    """music bed + narration clips [(start_seconds, wav path)] -> one wav of `dur` seconds. Without clips the music is used as it is."""
    if not clips:
        return music_wav
    cmd = [ffmpeg(), "-y", "-loglevel", "error"]
    cmd += ["-i", str(music_wav)] if music_wav else ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=44100:cl=mono"]
    for _, wav in clips:
        cmd += ["-i", str(wav)]
    parts = [f"[0:a]volume={music_gain},atrim=0:{dur:.2f}[m]"]
    for i, (start, _) in enumerate(clips, 1):
        parts.append(f"[{i}:a]adelay={int(start * 1000)}|{int(start * 1000)},aresample=44100[v{i}]")
    ins = "[m]" + "".join(f"[v{i}]" for i in range(1, len(clips) + 1))
    parts.append(f"{ins}amix=inputs={len(clips) + 1}:normalize=0:duration=first,atrim=0:{dur:.2f}[a]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[a]", "-ar", "44100", str(out_wav)]
    subprocess.run(cmd, check=True)
    return out_wav


def _browser(pw):
    exe = os.environ.get("PW_CHROMIUM", "").strip()      # local test machines only; Actions use the installed Chromium
    return pw.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe else pw.chromium.launch()


def render_reel(html_path, mp4_path, audio_path=None, fps=FPS, log=log):
    """a 1080x1920 page whose every frame is window.seek(t) (and window.DUR seconds long) -> H.264 mp4 with `audio_path` (or silence).
    Returns the duration in seconds."""
    from playwright.sync_api import sync_playwright
    html_path, mp4_path = Path(html_path), Path(mp4_path)
    with sync_playwright() as pw:
        b = _browser(pw)
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto(f"file://{html_path.resolve()}")
        pg.evaluate("document.fonts.ready.then(() => 1)")
        pg.wait_for_timeout(500)
        dur = float(pg.evaluate("window.DUR"))
        cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-"]
        cmd += ["-i", str(audio_path)] if audio_path else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"]      # never a reel without a sound track
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
                "-shortest", "-movflags", "+faststart", str(mp4_path)]
        enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for i in range(int(round(dur * fps))):
                pg.evaluate(f"window.seek({i / fps:.4f})")
                enc.stdin.write(pg.screenshot(type="jpeg", quality=90))
        finally:
            enc.stdin.close()
            enc.wait()
        b.close()
    if enc.returncode:
        raise RuntimeError("ffmpeg could not make the reel")
    log(f"reel {mp4_path.name}: {dur:.1f} s")
    return dur


def screenshot_page(html_path, png_path, t, size=(W, H)):
    """one frame of a seek(t) page at time t (for the owner's preview / the tests)"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = _browser(pw)
        pg = b.new_page(viewport={"width": size[0], "height": size[1]})
        pg.goto(f"file://{Path(html_path).resolve()}")
        pg.evaluate("document.fonts.ready.then(() => 1)")
        pg.wait_for_timeout(400)
        pg.evaluate(f"window.seek({t})")
        pg.screenshot(path=str(png_path))
        b.close()


def font_css():
    """the Tamil / Latin fonts the other reels use (goldrate/fonts), as @font-face with file:// addresses"""
    fd = ROOT / "goldrate" / "fonts"
    rules = []
    for f in sorted(fd.glob("noto-sans-tamil-*.woff2")):
        script = "tamil" if "-tamil-" in f.name else "latin"
        weight = f.name.split("-")[-2]
        rng = "U+0B80-0BFF,U+200C-200D,U+25CC" if script == "tamil" else "U+0000-00FF,U+0131,U+0152-0153,U+2000-206F,U+20AC,U+2122"
        rules.append(f"@font-face{{font-family:'NST';font-weight:{weight};src:url('file://{f.as_posix()}') format('woff2');unicode-range:{rng}}}")
    return "\n".join(rules)


def logo_data_uri(page_key):
    import base64
    p = ROOT / "kit" / f"logo_{page_key}.png"
    if not p.exists():
        p = ROOT / "kit" / "logo_namakkal.png"
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


# ---------- posting ----------
class Paused(RuntimeError):
    pass


def post_reel(page_key, mp4, caption, lane, day, tag="", cover_ms=0, logf=log):
    """Instagram reel for the page, then the page's Facebook page (when set up). Returns (media id, permalink). Raises on a problem."""
    import gold_daily as gd
    if gd.ig_paused_page(page_key):
        raise Paused(f"Instagram posting is paused on {page_key} (a block / limit) - not tried")
    token = gd.bridge_get("token", page=page_key)["token"]
    url = gd.upload_video(mp4)
    uid = gd.ig("GET", "me", token, fields="user_id")["user_id"]
    cid = gd.ig("POST", f"{uid}/media", token, media_type="REELS", video_url=url, caption=caption, share_to_feed="true",
                thumb_offset=str(int(cover_ms)))["id"]
    gd.wait_ready(cid, token, 15)
    mid = gd.ig("POST", f"{uid}/media_publish", token, creation_id=cid)["id"]
    link = gd.ig("GET", mid, token, fields="permalink").get("permalink", "")
    logf(f"{page_key}: {lane} REEL POSTED {link}")
    try:
        import facebook
        facebook.share(page_key, f"{lane}-reel-{day.isoformat()}", "reel", [url], caption, tag, always=True, story=False)
    except Exception as e:
        logf("Facebook step skipped:", str(e)[:150])
    return mid, link
