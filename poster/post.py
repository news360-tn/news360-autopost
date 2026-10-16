"""News360 Instagram poster (runs in GitHub Actions).

Modes:
  python poster/post.py carousel   # every hour: post the top queued story to each page (max 1 per page per run)
  python poster/post.py reel       # every 2 hours: post the top reel-worthy story as a 10-30 s reel

Environment (GitHub Secrets):
  BRIDGE_URL, BRIDGE_KEY           Google Apps Script web app (Sheet, Doc, Drive, Gmail, Instagram tokens)
  CLOUDINARY_CLOUD, CLOUDINARY_PRESET   free image/video hosting (unsigned upload preset)
  DRY_RUN=1                        render + upload but do not publish (for testing)
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

BRIDGE_URL = os.environ.get("BRIDGE_URL", "")
BRIDGE_KEY = os.environ.get("BRIDGE_KEY", "")
CLOUD = os.environ.get("CLOUDINARY_CLOUD", "")
PRESET = os.environ.get("CLOUDINARY_PRESET", "")
DRY = os.environ.get("DRY_RUN", "") in ("1", "true", "yes")
IG_HOST = "https://graph.instagram.com"
IG_VER = os.environ.get("IG_API_VERSION", "")  # e.g. "v23.0"; empty = default version

PAGES = {
    "rasipuram": {"label": "Rasipuram 360", "link_col": "rasipuram_link", "logo": "logo_rasipuram.png",
                  "example": "example_slides_rasipuram.json", "tag": "#Rasipuram360"},
    "namakkal": {"label": "Namakkal 360", "link_col": "namakkal_link", "logo": "logo_namakkal.png",
                 "example": "example_slides_namakkal.json", "tag": "#Namakkal360"},
}
IMPORTANCE = {"High": 0, "Medium": 1, "Low": 2}
MAX_AGE_H = {"carousel": 36, "reel": 24}


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
def targets(row):
    s = (row.get("post_to") or "").lower()
    out = []
    if "rasipuram" in s:
        out.append("rasipuram")
    if "namakkal" in s or not out:
        out.append("namakkal")
    return out


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


def pick(rows, page, kind):
    cands = []
    for r in rows:
        if (r.get("review") or "").strip().lower() == "hold":
            continue
        if page not in targets(r):
            continue
        if kind == "carousel" and r.get(PAGES[page]["link_col"]):
            continue
        if kind == "reel":
            if (r.get("reel") or "").strip().lower() != "yes" or r.get("reel_link"):
                continue
        limit = MAX_AGE_H[kind] * (2 if is_shutdown(r) else 1)
        if age_hours(r) > limit:
            continue
        cands.append(r)
    cands.sort(key=lambda r: (IMPORTANCE.get((r.get("importance") or "").strip(), 1), -age_hours(r)))
    return cands[0] if cands else None


# ---------------------------------------------------------------- rendering
def page_spec(spec, page):
    """Same slides, but the follow slide (last) comes from the page's example, with the story's date."""
    ex = json.loads((KIT / PAGES[page]["example"]).read_text())
    follow = ex["slides"][-1]["html"]
    m = re.search(r'<i data-ic="calendar-days"></i>([^<]+)</div>', spec["slides"][0]["html"])
    if m:
        follow = re.sub(r'(<i data-ic="calendar-days"></i>)[^<]+(</div>)', lambda mm: mm.group(1) + m.group(1) + mm.group(2), follow, count=1)
    out = json.loads(json.dumps(spec))
    last = out["slides"][-1]
    if "இணைந்திருங்கள்" in last["html"] or "follow" in last.get("file", ""):
        last["html"] = follow
    else:
        out["slides"].append({"file": f"{spec.get('story', 'X')}_slide{len(out['slides']) + 1}_follow.png", "html": follow})
    return out


def render_carousel(row, page):
    sid = row["story_id"]
    spec = json.loads(row["slides_spec"])
    spec = page_spec(spec, page)
    work = OUT / f"{sid}_{page}"
    work.mkdir(parents=True, exist_ok=True)
    (work / "spec.json").write_text(json.dumps(spec, ensure_ascii=False))
    raw, final = work / "raw", work / "final"
    subprocess.run([sys.executable, str(KIT / "render_v2.py"), str(work / "spec.json"), str(raw)], check=True)
    subprocess.run([sys.executable, str(KIT / "overlay_logo_v2.py"), str(KIT / PAGES[page]["logo"]), str(raw), str(final)], check=True)
    jpgs = []
    for png in sorted(final.glob("*.png"), key=lambda p: int(re.search(r"slide(\d+)", p.name).group(1)) if re.search(r"slide(\d+)", p.name) else 0):
        jpg = png.with_suffix(".jpg")
        Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92, optimize=True)
        jpgs.append(jpg)
    if not 1 <= len(jpgs) <= 10:
        raise RuntimeError(f"{sid}: {len(jpgs)} slides (Instagram allows 1-10)")
    return jpgs


def reel_spec_from_row(row):
    """Column U may hold a JSON reel spec (scenes) or a plain spoken script."""
    txt = (row.get("reel_script") or "").strip()
    try:
        spec = json.loads(txt)
        if isinstance(spec, dict) and spec.get("scenes"):
            return spec
    except ValueError:
        pass
    sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", txt) if s.strip()]
    if not sentences:
        raise RuntimeError(f"{row['story_id']}: empty reel script")
    date = ""
    try:
        m = re.search(r'<i data-ic="calendar-days"></i>([^<]+)</div>', json.loads(row["slides_spec"])["slides"][0]["html"])
        date = m.group(1) if m else ""
    except Exception:
        pass
    headline = (row.get("headline_ta") or "").split(":")[0].strip()
    scenes = [{"type": "title", "kicker": (row.get("category") or "முக்கியச் செய்தி").strip(), "line1": headline, "line2": "",
               "icon": "bullhorn", "say": sentences[0], "caption": sentences[0]}]
    icons = ["circle-info", "location-dot", "clock", "bell", "shield-halved"]
    for i, s in enumerate(sentences[1:-1]):
        scenes.append({"type": "advice", "icon": icons[i % len(icons)], "title": "", "text": s, "say": s, "caption": s})
    if len(sentences) > 1:
        scenes.append({"type": "outro", "say": sentences[-1], "caption": "உள்ளூர் செய்திகளுக்கு Follow செய்யுங்கள்"})
    return {"story": row["story_id"], "date": date, "location": (row.get("location") or "").split(",")[0][:30],
            "voice": "female", "scenes": scenes}


def render_reel(row, page, voice_file=None):
    sid = row["story_id"]
    work = OUT / f"{sid}_{page}_reel"
    work.mkdir(parents=True, exist_ok=True)
    spec = reel_spec_from_row(row)
    (work / "reel.json").write_text(json.dumps(spec, ensure_ascii=False))
    env = dict(os.environ)
    if voice_file:
        env["VOICE_FILE"] = str(voice_file)
    mp4 = work / f"{sid}_{page}_reel.mp4"
    subprocess.run([sys.executable, str(REEL / "reel.py"), str(work / "reel.json"), str(mp4), page], check=True, env=env)
    return mp4


# ---------------------------------------------------------------- checks before posting
def check_text(row):
    cap = row.get("caption") or ""
    problems = []
    if not cap.strip():
        problems.append("empty caption")
    if len(cap) > 2200:
        problems.append(f"caption too long ({len(cap)} > 2200)")
    if cap.count("#") > 30:
        problems.append("more than 30 hashtags")
    if re.search(r"ஆதாரம்|https?://", cap):
        problems.append("caption contains a source or link")
    if re.search(r"[�]", cap):
        problems.append("broken characters in caption")
    return problems


def page_caption(row, page):
    cap = (row.get("caption") or "").strip()
    tag = PAGES[page]["tag"]
    if tag not in cap:
        cap += " " + tag
    return cap


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


def publish_carousel(token, urls, caption):
    uid, _ = ig_account(token)
    if len(urls) == 1:
        cid = ig("POST", f"{uid}/media", token, image_url=urls[0], caption=caption)["id"]
    else:
        kids = [ig("POST", f"{uid}/media", token, image_url=u, is_carousel_item="true")["id"] for u in urls]
        for k in kids:
            wait_ready(k, token, 5)
        cid = ig("POST", f"{uid}/media", token, media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    wait_ready(cid, token, 5)
    mid = ig("POST", f"{uid}/media_publish", token, creation_id=cid)["id"]
    return mid, ig("GET", mid, token, fields="permalink").get("permalink", "")


def publish_reel(token, video_url, caption):
    uid, _ = ig_account(token)
    cid = ig("POST", f"{uid}/media", token, media_type="REELS", video_url=video_url, caption=caption, share_to_feed="true")["id"]
    wait_ready(cid, token, 15)
    mid = ig("POST", f"{uid}/media_publish", token, creation_id=cid)["id"]
    return mid, ig("GET", mid, token, fields="permalink").get("permalink", "")


# ---------------------------------------------------------------- main flows
def run_carousel(rows):
    done = []
    for page in ("rasipuram", "namakkal"):
        row = pick(rows, page, "carousel")
        if not row:
            log(page, "nothing queued")
            continue
        sid = row["story_id"]
        log(page, "->", sid, row.get("headline_ta"))
        try:
            problems = check_text(row)
            if problems:
                raise RuntimeError("; ".join(problems))
            jpgs = render_carousel(row, page)
            urls = [upload(j, "image") for j in jpgs]
            caption = page_caption(row, page)
            if DRY:
                log("DRY RUN - not publishing", urls)
                bridge_post("posted", {"row": row["row"], "page": page, "kind": "carousel", "dry_run": True,
                                       "permalink": "", "media_urls": urls, "caption": caption, "slides": len(urls)})
                continue
            token = bridge_get("token", page=page)["token"]
            mid, link = publish_carousel(token, urls, caption)
            log("posted", page, sid, link)
            bridge_post("posted", {"row": row["row"], "page": page, "kind": "carousel", "permalink": link, "media_id": mid,
                                   "media_urls": urls, "caption": caption, "slides": len(urls)})
            row[PAGES[page]["link_col"]] = link
            done.append((page, sid, link))
        except Exception as e:  # report and continue with the other page
            log("ERROR", page, sid, e)
            bridge_post("error", {"row": row["row"], "page": page, "kind": "carousel", "error": str(e)[:900]})
    return done


def run_reel(rows):
    row = None
    for page in ("rasipuram", "namakkal"):
        row = row or pick(rows, page, "reel")
    if not row:
        log("no reel-worthy story waiting")
        return []
    sid = row["story_id"]
    voice_file = None
    try:
        v = bridge_get("voice", story=sid)
        if v.get("found"):
            voice_file = OUT / f"{sid}_voice{v.get('ext', '.m4a')}"
            OUT.mkdir(exist_ok=True)
            voice_file.write_bytes(base64.b64decode(v["data"]))
            log("using recorded human voice", v.get("name"))
    except Exception as e:
        log("voice lookup failed, using voice model:", e)
    done = []
    for page in targets(row):
        try:
            mp4 = render_reel(row, page, voice_file)
            url = upload(mp4, "video")
            caption = page_caption(row, page)
            if DRY:
                log("DRY RUN - not publishing", url)
                bridge_post("posted", {"row": row["row"], "page": page, "kind": "reel", "dry_run": True, "permalink": "",
                                       "media_urls": [url], "caption": caption, "voice": "recorded" if voice_file else "voice model"})
                continue
            token = bridge_get("token", page=page)["token"]
            mid, link = publish_reel(token, url, caption)
            log("reel posted", page, sid, link)
            bridge_post("posted", {"row": row["row"], "page": page, "kind": "reel", "permalink": link, "media_id": mid,
                                   "media_urls": [url], "caption": caption, "voice": "recorded" if voice_file else "voice model"})
            done.append((page, sid, link))
        except Exception as e:
            log("ERROR reel", page, sid, e)
            bridge_post("error", {"row": row["row"], "page": page, "kind": "reel", "error": str(e)[:900]})
    return done


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "carousel"
    for name, val in (("BRIDGE_URL", BRIDGE_URL), ("BRIDGE_KEY", BRIDGE_KEY), ("CLOUDINARY_CLOUD", CLOUD), ("CLOUDINARY_PRESET", PRESET)):
        if not val:
            log(f"Setup not finished: secret {name} is missing - nothing to do.")
            return
    if not DRY and os.environ.get("GITHUB_EVENT_NAME") == "schedule" and not (ROOT / "LIVE").exists():
        log("Not live yet (no LIVE file in the repository) - scheduled posting is switched off.")
        return
    rows = bridge_get("queue")["rows"]
    log(f"{len(rows)} stories waiting")
    done = run_carousel(rows) if mode == "carousel" else run_reel(rows)
    log("finished:", done or "nothing posted")


if __name__ == "__main__":
    main()
