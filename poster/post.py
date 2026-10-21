"""News360 Instagram poster (runs in GitHub Actions) - photo flow.

Flow: the research task queues a story (text + image prompts) -> you reply to the email with the ChatGPT images ->
the Apps Script bridge saves the images and sets the story to "Queued" -> this job builds the photo carousel and the
photo reel and posts both to நாமக்கல் 360. Rasipuram-area stories also invite இராசிபுரம் 360 as a collaborator.

  python poster/post.py check   # prints ready=<n> (for the workflow); decides whether the heavy job must run
  python poster/post.py run     # posts the top ready story (carousel + reel); one story per run

Environment (GitHub Secrets): BRIDGE_URL, BRIDGE_KEY, CLOUDINARY_CLOUD, CLOUDINARY_PRESET.  DRY_RUN=1 -> render + upload, no publishing.
"""
import base64, json, os, re, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "kit"
REEL = ROOT / "reel"
OUT = ROOT / "out"
IST = timezone(timedelta(hours=5, minutes=30))
CONFIG = json.loads((Path(__file__).resolve().parent / "config.json").read_text())

BRIDGE_URL = os.environ.get("BRIDGE_URL", "")
BRIDGE_KEY = os.environ.get("BRIDGE_KEY", "")
CLOUD = os.environ.get("CLOUDINARY_CLOUD", "")
PRESET = os.environ.get("CLOUDINARY_PRESET", "")
DRY = os.environ.get("DRY_RUN", "") in ("1", "true", "yes")
IG_HOST = "https://graph.instagram.com"
IG_VER = os.environ.get("IG_API_VERSION", "")

PAGE = "namakkal"
LOGO = KIT / "logo_namakkal.png"
TAG = "#Namakkal360"
IMPORTANCE = {"High": 0, "Medium": 1, "Low": 2}
MAX_AGE_H = 48
AI_LINE = "📌 படங்கள் செய்தியை விளக்க AI மூலம் உருவாக்கப்பட்ட பிரதிநிதித்துவப் படங்கள்."

# news outlets must never appear on a post, a slide or in a reel
OUTLETS = ["தினமலர்", "தினத்தந்தி", "தினமணி", "மாலைமலர்", "தினகரன்", "இந்து தமிழ்", "தி இந்து", "புதிய தலைமுறை", "நியூஸ்18",
           "நியூஸ் 18", "பாலிமர்", "சன் நியூஸ்", "நியூஸ்7", "நியூஸ் 7", "கலைஞர் செய்திகள்", "விகடன்", "ஒன்இந்தியா", "வே2நியூஸ்",
           "டாப் தமிழ்", "தமிழ் மணி", "டைம்ஸ் ஆஃப் இந்தியா", "டி.டி. நெக்ஸ்ட்",
           "dinamalar", "dinamani", "dinathanthi", "daily thanthi", "maalaimalar", "dinakaran", "the hindu", "hindu tamil", "times of india",
           "toi", "dt next", "indian express", "news18", "polimer", "sun news", "news7", "vikatan", "oneindia", "way2news", "puthiya thalaimurai",
           "kalaignar", "toptamilnews", "tamil mani", "ஆதாரம்", "source:"]


def log(*a):
    print(datetime.now(IST).strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- bridge (Apps Script)
def bridge_get(action, **params):
    r = requests.get(BRIDGE_URL, params={"action": action, "key": BRIDGE_KEY, **params}, timeout=120)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"bridge {action}: {data.get('error')}")
    return data


def bridge_post(action, payload):
    r = requests.post(BRIDGE_URL, params={"key": BRIDGE_KEY},
                      data=json.dumps({"action": action, **payload}, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, timeout=120)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"bridge {action}: {data.get('error')}")
    return data


# ---------------------------------------------------------------- selection
def age_hours(row):
    for key in ("researched", "published"):
        v = (row.get(key) or "").lstrip("'").replace(" IST", "").strip()
        for fmt in ("%d %b %Y, %H:%M", "%d %b %Y %H:%M", "%d %b %Y"):
            try:
                t = datetime.strptime(v, fmt).replace(tzinfo=IST)
                return (datetime.now(IST) - t).total_seconds() / 3600
            except ValueError:
                pass
    return 0.0


def is_shutdown(row):
    return "மின் தடை" in (row.get("category") or "") or "shutdown" in (row.get("category") or "").lower()


def ready(row):
    if (row.get("review") or "").strip().lower() == "hold":
        return False
    if not row.get("images") or not row.get("slides_spec"):
        return False
    if row.get("namakkal_link") and row.get("reel_link"):
        return False
    return age_hours(row) <= MAX_AGE_H * (2 if is_shutdown(row) else 1)


def in_post_window():
    """Best-time posting: scheduled runs publish only inside the IST windows in config.json (manual runs ignore this)."""
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        return True
    try:
        cfg = json.loads((Path(__file__).parent / "config.json").read_text())
    except Exception:
        cfg = {}
    wins = cfg.get("post_windows_ist") or []
    if not wins:
        return True
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    m = now.hour * 60 + now.minute
    for w in wins:
        a, b = w.split("-")
        am = int(a[:2]) * 60 + int(a[3:]); bm = int(b[:2]) * 60 + int(b[3:])
        if am <= m <= bm:
            return True
    return False


def pick(rows):
    c = [r for r in rows if ready(r)]
    if not in_post_window():
        # outside the best-time windows only urgent items go out (high importance or power shutdowns)
        c = [r for r in c if is_shutdown(r) or (r.get("importance") or "").strip() == "High"]
    c.sort(key=lambda r: (IMPORTANCE.get((r.get("importance") or "").strip(), 1), -age_hours(r)))
    return c[0] if c else None


# ---------------------------------------------------------------- checks before posting
TAMIL_MONTHS = ["ஜனவரி", "பிப்ரவரி", "மார்ச்", "ஏப்ரல்", "மே", "ஜூன்", "ஜூலை", "ஆகஸ்ட்", "செப்டம்பர்", "அக்டோபர்", "நவம்பர்", "டிசம்பர்"]


def tamil_date_today():
    d = datetime.now(IST)
    return f"{d.day} {TAMIL_MONTHS[d.month - 1]} {d.year}"


def all_text(row, spec):
    parts = [row.get("caption") or "", row.get("reel_script") or "", spec.get("hl1", ""), spec.get("hl2", ""), spec.get("cat", ""), spec.get("loc", "")]
    for s in spec.get("slides", []):
        parts.append(s.get("title", ""))
        parts += s.get("lines", [])
    return "\n".join(parts)


def check_text(row, spec):
    cap = row.get("caption") or ""
    problems = []
    if not cap.strip():
        problems.append("empty caption")
    if len(cap) > 2150:
        problems.append(f"caption too long ({len(cap)})")
    if cap.count("#") > 30:
        problems.append("more than 30 hashtags")
    if re.search(r"https?://", cap):
        problems.append("caption contains a link")
    if "�" in cap:
        problems.append("broken characters in caption")
    low = all_text(row, spec).lower()
    hits = [o for o in OUTLETS if o.lower() in low]
    if hits:
        problems.append("a news source name appears in the post text: " + ", ".join(hits[:3]))
    if spec.get("v") != 3 or not spec.get("slides"):
        problems.append("slides spec is not the photo format (v3)")
    if not (row.get("reel_script") or "").strip():
        problems.append("empty reel script")
    return problems


def final_caption(row):
    cap = (row.get("caption") or "").strip()
    if TAG not in cap:
        cap += " " + TAG
    if CONFIG.get("ai_label", True) and "AI" not in cap.split("#")[0][-300:]:
        lines = cap.split("\n")
        idx = max([i for i, l in enumerate(lines) if l.strip().startswith("#")] or [len(lines)])
        if idx < len(lines):
            lines[idx:idx] = [AI_LINE, ""]
        else:
            lines += ["", AI_LINE]
        cap = "\n".join(lines)
    return cap


# ---------------------------------------------------------------- images
def fetch_images(row, work):
    urls = json.loads(row["images"])
    work.mkdir(parents=True, exist_ok=True)
    out = []
    for i, u in enumerate(urls, 1):
        r = requests.get(u, timeout=120)
        r.raise_for_status()
        raw = work / f"raw{i}"
        raw.write_bytes(r.content)
        im = Image.open(raw).convert("RGB")
        im.thumbnail((2000, 3000))
        dst = work / f"img{i}.jpg"
        im.save(dst, "JPEG", quality=93)
        raw.unlink()
        out.append(dst)
    return out


# ---------------------------------------------------------------- rendering
def render_carousel(row, spec, work):
    (work / "spec.json").write_text(json.dumps(spec, ensure_ascii=False))
    raw, final = work / "raw", work / "final"
    cmd = [sys.executable, str(KIT / "render_photo.py"), str(work / "spec.json"), str(work), str(raw)]
    if CONFIG.get("ai_label", True):
        cmd.append("--ai-label")
    subprocess.run(cmd, check=True)
    subprocess.run([sys.executable, str(KIT / "overlay_logo_v2.py"), str(LOGO), str(raw), str(final)], check=True)
    jpgs = []
    for png in sorted(final.glob("*.png"), key=lambda p: int(re.search(r"slide(\d+)", p.name).group(1))):
        jpg = png.with_suffix(".jpg")
        Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92, optimize=True)
        jpgs.append(jpg)
    if not 2 <= len(jpgs) <= 10:
        raise RuntimeError(f"{row['story_id']}: {len(jpgs)} slides (Instagram allows 2-10)")
    return jpgs


def reel_spec(row, spec, images):
    txt = (row.get("reel_script") or "").strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", txt) if s.strip()]
    if len(sentences) < 3:
        raise RuntimeError(f"{row['story_id']}: reel script needs at least 3 sentences")
    body, last = sentences[:-1], sentences[-1]
    n = len(images)
    scenes = []
    titles = [s.get("title", "") for s in spec["slides"]]
    for i, sent in enumerate(body):
        k = min(n - 1, round(i * (n - 1) / max(1, len(body) - 1))) if len(body) > 1 else 0
        sc = {"type": "photo", "image": str(images[k]), "say": sent, "caption": sent}
        if i == 0:
            sc["tag"] = (spec.get("cat") or "").strip()
            sc["big"] = spec.get("hl1", "")
        else:
            t = titles[min(i - 1, len(titles) - 1)] if titles else ""
            if t:
                sc["tag"] = t
        scenes.append(sc)
    scenes.append({"type": "outro", "say": last, "caption": "நாமக்கல் 360 – Follow செய்யுங்கள்"})
    return {"story": row["story_id"], "date": spec["date"], "location": (spec.get("loc") or "நாமக்கல்")[:30],
            "voice": "female", "ai_label": bool(CONFIG.get("ai_label", True)), "scenes": scenes}


def render_reel(row, spec, images, work, voice_file=None):
    rs = reel_spec(row, spec, images)
    (work / "reel.json").write_text(json.dumps(rs, ensure_ascii=False))
    env = dict(os.environ)
    if voice_file:
        env["VOICE_FILE"] = str(voice_file)
    mp4 = work / f"{row['story_id']}_reel.mp4"
    subprocess.run([sys.executable, str(REEL / "reel.py"), str(work / "reel.json"), str(mp4), PAGE], check=True, env=env)
    return mp4


# ---------------------------------------------------------------- hosting + Instagram
def upload(path, kind):
    url = f"https://api.cloudinary.com/v1_1/{CLOUD}/{'video' if kind == 'video' else 'image'}/upload"
    with open(path, "rb") as f:
        r = requests.post(url, data={"upload_preset": PRESET, "folder": "news360"}, files={"file": f}, timeout=600)
    r.raise_for_status()
    return r.json()["secure_url"]


def ig_url(path):
    return f"{IG_HOST}/{IG_VER + '/' if IG_VER else ''}{path}"


def ig(method, path, token, **params):
    params["access_token"] = token
    r = requests.request(method, ig_url(path), params=params if method == "GET" else None,
                         data=params if method == "POST" else None, timeout=120)
    try:
        data = r.json()
    except ValueError:
        r.raise_for_status()
        raise
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Instagram {path}: {data.get('error', data)}")
    return data


def wait_ready(cid, token, minutes=10):
    end = time.time() + minutes * 60
    while time.time() < end:
        st = ig("GET", cid, token, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container {cid} {st}")
        time.sleep(10)
    raise RuntimeError(f"Instagram container {cid} not ready after {minutes} min")


def ig_account(token):
    me = ig("GET", "me", token, fields="user_id,username")
    return me.get("user_id") or me.get("id"), me.get("username")


def create_with_collab(uid, token, params, collab):
    """Create the media container; if the collaborator invite is refused, create it without (and say so)."""
    if collab:
        try:
            return ig("POST", f"{uid}/media", token, collaborators=json.dumps([CONFIG["collab_username"]]), **params)["id"], True, ""
        except RuntimeError as e:
            log("collaborator invite refused, posting without it:", e)
            return ig("POST", f"{uid}/media", token, **params)["id"], False, str(e)[:300]
    return ig("POST", f"{uid}/media", token, **params)["id"], False, ""


def publish_carousel(token, urls, caption, collab):
    uid, _ = ig_account(token)
    kids = [ig("POST", f"{uid}/media", token, image_url=u, is_carousel_item="true")["id"] for u in urls]
    for k in kids:
        wait_ready(k, token, 5)
    cid, collab_ok, why = create_with_collab(uid, token, dict(media_type="CAROUSEL", children=",".join(kids), caption=caption), collab)
    wait_ready(cid, token, 5)
    mid = ig("POST", f"{uid}/media_publish", token, creation_id=cid)["id"]
    return mid, ig("GET", mid, token, fields="permalink").get("permalink", ""), collab_ok, why


def publish_reel(token, video_url, caption, collab):
    uid, _ = ig_account(token)
    cid, collab_ok, why = create_with_collab(uid, token, dict(media_type="REELS", video_url=video_url, caption=caption, share_to_feed="true"), collab)
    wait_ready(cid, token, 15)
    mid = ig("POST", f"{uid}/media_publish", token, creation_id=cid)["id"]
    return mid, ig("GET", mid, token, fields="permalink").get("permalink", ""), collab_ok, why


# ---------------------------------------------------------------- main flows
def fail(row, kind, msg):
    log("NOT POSTED -", row["story_id"], msg)
    bridge_post("error", {"row": row["row"], "page": PAGE, "kind": kind, "error": msg[:900]})


def run_story(row):
    """Build the carousel and the reel, run every check, and only then publish (carousel first, then reel)."""
    import verify
    sid = row["story_id"]
    spec = json.loads(row["slides_spec"])
    spec["date"] = tamil_date_today()  # date shown on poster/reel = actual posting date (IST)
    problems = check_text(row, spec) + verify.check_news(row)
    if problems:
        return fail(row, "carousel", "Checks failed: " + "; ".join(problems))
    collab = "rasipuram" in (row.get("post_to") or "").lower()
    caption = final_caption(row)
    work = OUT / sid
    images = fetch_images(row, work)
    need_carousel, need_reel = not row.get("namakkal_link"), not row.get("reel_link")
    jpgs = mp4 = None
    voice_file = None
    rs = None
    checks = []

    # 1. build everything (nothing is published yet)
    try:
        if need_reel:
            rs = reel_spec(row, spec, images)
        probs = verify.check_texts(spec, [sc.get("caption", "") for sc in (rs or {}).get("scenes", [])])
        if probs:
            return fail(row, "carousel", "Tamil text check failed: " + "; ".join(probs))
        checks.append("Tamil text and fonts OK")
        if need_carousel:
            jpgs = render_carousel(row, spec, work)
            checks.append(f"{len(jpgs)} slides rendered, no clipped text")
        if need_reel:
            try:
                v = bridge_get("voice", story=sid)
                if v.get("found"):
                    voice_file = work / f"voice{v.get('ext', '.m4a')}"
                    voice_file.write_bytes(base64.b64decode(v["data"]))
                    log("using recorded human voice", v.get("name"))
            except Exception as e:
                log("voice lookup failed, using the voice model:", e)
            mp4 = render_reel(row, spec, images, work, voice_file)
            probs = verify.check_reel(mp4, [sc["say"] for sc in rs["scenes"]])
            if probs:
                return fail(row, "reel", "Reel check failed: " + "; ".join(probs))
            checks.append("reel 1080x1920, 10-30 s, voice present and fully pronounceable")
    except subprocess.CalledProcessError as e:
        return fail(row, "carousel", f"Build failed ({e.cmd[1].split('/')[-1]}, exit {e.returncode})")
    except Exception as e:
        return fail(row, "carousel", f"Build failed: {e}")
    checks.append("news marked verified: " + (row.get("verification") or "")[:60])
    note = "; ".join(checks)
    log("all checks passed:", note)

    # 2. upload and publish
    done = []
    voice = "recorded" if voice_file else "voice model"
    if need_carousel:
        try:
            urls = [upload(j, "image") for j in jpgs]
            if DRY:
                log("DRY RUN carousel - not publishing", urls)
                bridge_post("posted", {"row": row["row"], "page": PAGE, "kind": "carousel", "dry_run": True, "permalink": "",
                                       "media_urls": urls, "caption": caption, "slides": len(urls), "collab": collab, "checks": note})
            else:
                token = bridge_get("token", page=PAGE)["token"]
                mid, link, collab_ok, why = publish_carousel(token, urls, caption, collab)
                log("carousel posted", sid, link)
                bridge_post("posted", {"row": row["row"], "page": PAGE, "kind": "carousel", "permalink": link, "media_id": mid,
                                       "media_urls": urls, "caption": caption, "slides": len(urls), "collab": collab_ok, "checks": note})
                done.append(("carousel", link))
        except Exception as e:
            log("ERROR carousel", sid, e)
            bridge_post("error", {"row": row["row"], "page": PAGE, "kind": "carousel", "error": str(e)[:900]})
    if need_reel:
        try:
            url = upload(mp4, "video")
            if DRY:
                log("DRY RUN reel - not publishing", url)
                bridge_post("posted", {"row": row["row"], "page": PAGE, "kind": "reel", "dry_run": True, "permalink": "",
                                       "media_urls": [url], "caption": caption, "voice": voice, "collab": collab, "checks": note})
            else:
                token = bridge_get("token", page=PAGE)["token"]
                mid, link, collab_ok, why = publish_reel(token, url, caption, collab)
                log("reel posted", sid, link)
                bridge_post("posted", {"row": row["row"], "page": PAGE, "kind": "reel", "permalink": link, "media_id": mid,
                                       "media_urls": [url], "caption": caption, "voice": voice, "collab": collab_ok, "checks": note})
                done.append(("reel", link))
        except Exception as e:
            log("ERROR reel", sid, e)
            bridge_post("error", {"row": row["row"], "page": PAGE, "kind": "reel", "error": str(e)[:900]})
    return done


def live_allowed():
    if DRY:
        return True
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and not (ROOT / "LIVE").exists():
        log("Not live yet (no LIVE file in the repository) - scheduled posting is switched off.")
        return False
    return True


def missing_setup():
    for name, val in (("BRIDGE_URL", BRIDGE_URL), ("BRIDGE_KEY", BRIDGE_KEY), ("CLOUDINARY_CLOUD", CLOUD), ("CLOUDINARY_PRESET", PRESET)):
        if not val:
            log(f"Setup not finished: secret {name} is missing - nothing to do.")
            return True
    return False


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if missing_setup() or not live_allowed():
        n = 0
        rows = []
    else:
        rows = bridge_get("queue")["rows"]
        n = 1 if pick(rows) else 0
    if mode == "check":
        log(f"{len(rows)} stories in the queue, ready to post: {n}")
        for r in rows:
            log("  ", r.get("story_id"), "review=", repr(r.get("review")), "images=", len(r.get("images") or ""),
                "spec=", len(r.get("slides_spec") or ""), "links=", repr(r.get("namakkal_link")), repr(r.get("reel_link")),
                "age_h=", round(age_hours(r), 1), "ready=", ready(r), "window=", in_post_window())
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write(f"ready={n}\n")
        return
    row = pick(rows)
    if not row:
        log("no story with images is waiting")
        return
    log("->", row["story_id"], row.get("headline_ta"))
    done = run_story(row)
    log("finished:", done or "nothing posted")


if __name__ == "__main__":
    main()
