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
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

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
START = time.time()
DRY = os.environ.get("DRY_RUN", "") in ("1", "true", "yes")
PREBUILD = os.environ.get("PREBUILD", "") in ("1", "true", "yes")   # build + upload only; the posting run then publishes at once
CACHE = ROOT / "poster" / "prebuilt"
IG_HOST = "https://graph.instagram.com"
IG_VER = os.environ.get("IG_API_VERSION", "")

PAGE = "namakkal"
ALL_ROWS = []      # every row of the queue (set in main) - used to spot the same news posted before
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


LABEL = {"rasipuram": "இராசிபுரம் 360", "namakkal": "நாமக்கல் 360"}


def pages_of(row):
    """the pages that post this story, each on its own (no collaboration): Namakkal 360 = top news of the whole district (Rasipuram
    included), Rasipuram 360 = Rasipuram news only. post_to names them; a story can go to both, as two separate posts."""
    t = (row.get("post_to") or "").lower()
    pg = [p for p in ("namakkal", "rasipuram") if p in t]
    return pg or ["namakkal"]


def page_done(row, page):
    car_ok = bool(row.get(page + "_link")) or not spec_has_carousel(row)
    reel_ok = LABEL[page] in (row.get("reel_link") or "")
    return car_ok and reel_ok


def spec_has_carousel(row):
    """stories written in the reel-first plan carry "carousel": false in slides_spec when only a reel is wanted (older stories: both)"""
    if CONFIG.get("carousel") is False:      # reels only for now (config.json "carousel": false); the poster/carousel comes back when the owner says so
        return False
    try:
        return json.loads(row.get("slides_spec") or "{}").get("carousel", True) is not False
    except Exception:
        return True


_SKIPPED = set()


def skip_reason(row):
    """'' = fine to post. Otherwise why this story must not go out: its announced date has passed (power cut, job fair, 'today' news ...),
    or the same news was already posted under another story id."""
    import difflib, freshness
    f = filed_at(row)
    same_day = bool(f and f.date() == datetime.now(IST).date())      # filed today: it goes out today, whatever the clock says
    why = "" if same_day else freshness.stale_reason(row.get("headline_ta") or "", row.get("headline_en") or "", row.get("category") or "", row.get("published") or "")
    if why:
        return "stale: " + why
    for o in ALL_ROWS:
        went_out = o.get("rasipuram_link") or o.get("namakkal_link") or o.get("reel_link") or str(o.get("post_status") or "").lower().startswith(("posted", "partly"))
        if o.get("story_id") == row.get("story_id") or not went_out:
            continue
        if (freshness.similar(o.get("headline_ta") or "", row.get("headline_ta") or "", 0.62, o.get("researched"))
                or freshness.similar((o.get("headline_en") or "").lower(), (row.get("headline_en") or "").lower(), 0.65, o.get("researched"))):
            return f"duplicate of {o.get('story_id')}"
    return ""


def ready(row):
    if (row.get("review") or "").strip().lower() == "hold":
        return False
    if not row.get("images") or not row.get("slides_spec"):
        return False
    pg = pages_of(row)
    if all(page_done(row, p) for p in pg):
        return False
    why = skip_reason(row)
    if why:
        if row.get("story_id") not in _SKIPPED:
            _SKIPPED.add(row.get("story_id"))
            log("SKIP", row.get("story_id"), why)
        return False
    # a story that already went out on one page is only carried over to its other page while it is still fresh (same day);
    # an older one is never posted again later (stale news, e.g. yesterday's power cut)
    if any(page_done(row, p) or row.get(p + "_link") for p in pg) and age_hours(row) > 20:
        return False
    return True      # a story with its images is never dropped for age or time of day: it posts as soon as its set has started


def _starts():
    """the three daily posting start times (IST minutes after midnight) from config.json post_windows_ist ("06:30-09:30" -> 06:30)"""
    try:
        cfg = json.loads((Path(__file__).parent / "config.json").read_text())
    except Exception:
        cfg = {}
    out = []
    for w in cfg.get("post_windows_ist") or []:
        a = w.split("-")[0]
        out.append(int(a[:2]) * 60 + int(a[3:5]))
    return sorted(out)


def filed_at(row):
    """IST datetime the story was filed ('22 Oct 2026, 10:26' in the researched column), or None"""
    import re as _re
    from datetime import datetime, timedelta, timezone
    m = _re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4}),?\s+(\d{1,2}):(\d{2})", str(row.get("researched") or ""))
    if not m:
        return None
    mon = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(m.group(2).lower()) + 1
    return datetime(int(m.group(3)), mon, int(m.group(1)), int(m.group(4)), int(m.group(5)), tzinfo=timezone(timedelta(hours=5, minutes=30)))


def set_started(row, now=None):
    """Every story belongs to the posting set (morning / afternoon / evening) it was written for: the first start time that is not
    earlier than 90 min before it was filed. From that start time on it posts as soon as it is ready - a late image reply is posted at
    once, it never waits for (or is pushed into) the next set. Manual runs ignore this."""
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        return True
    from datetime import datetime, timedelta, timezone
    starts = _starts()
    f = filed_at(row)
    if not starts or f is None:
        return True
    now = now or datetime.now(timezone(timedelta(hours=5, minutes=30)))
    # the set of a story = the latest start time that is not later than 2 h after it was filed (a round that runs late still belongs to the set
    # whose start has already passed, so its stories post as soon as their images are in; a round before a start waits for that start)
    hi = f + timedelta(minutes=120)
    best = None
    for day in (-1, 0):
        for st in starts:
            cand = datetime(hi.year, hi.month, hi.day, st // 60, st % 60, tzinfo=hi.tzinfo) + timedelta(days=day)
            if cand <= hi and (best is None or cand > best):
                best = cand
    return True if best is None else now >= best


def is_urgent(row):
    return is_shutdown(row) or (row.get("importance") or "").strip() == "High"


def pick_all(rows):
    """every ready story whose set has started (urgent ones always), urgent first, then the rest oldest first"""
    c = [r for r in rows if ready(r) and (set_started(r) or is_urgent(r))]
    c.sort(key=lambda r: (IMPORTANCE.get((r.get("importance") or "").strip(), 1), -age_hours(r)))
    return c


def pick(rows):
    c = pick_all(rows)
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


def _digits_in_spec(spec):
    """numbers/times/dates shown as digits (10 மணி, 11ஆம் தேதி), never as Tamil words"""
    sys.path.insert(0, str(REEL))
    from digits import to_digits
    for k in ("hl1", "hl2", "cat", "loc"):
        if spec.get(k):
            spec[k] = to_digits(spec[k])
    for sl in spec.get("slides", []):
        sl["title"] = to_digits(sl.get("title", ""))
        sl["lines"] = [to_digits(x) for x in sl.get("lines", [])]


def final_caption(row):
    sys.path.insert(0, str(REEL))
    from digits import to_digits
    cap = to_digits((row.get("caption") or "").strip())
    # Instagram allows at most 5 hashtags: keep #Namakkal360 + the first 4 others, as ONE line at the end
    tags, seen = [], set()
    for t in [TAG] + re.findall(r"#[^\s#]+", cap):
        k = t.lower().rstrip(".,!")
        if k not in seen:
            seen.add(k); tags.append(t.rstrip(".,!"))
    tags = [TAG] + [t for t in tags if t != TAG][:4]
    body = "\n".join(re.sub(r"#[^\s#]+", "", l).rstrip() for l in cap.split("\n")).rstrip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    cap = body + "\n\n" + " ".join(tags[1:] + [TAG])
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
        if im.width < 2160:  # upscale small AI images so zooming and cropping stay sharp
            f = 2160 / im.width
            im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
        # enhance: gentle denoise, local contrast, colour, sharpening (keeps the look natural)
        im = im.filter(ImageFilter.MedianFilter(3)) if im.width * im.height < 6_000_000 else im
        im = ImageOps.autocontrast(im, cutoff=0.4)
        im = ImageEnhance.Contrast(im).enhance(1.06)
        im = ImageEnhance.Color(im).enhance(1.08)
        im = im.filter(ImageFilter.UnsharpMask(radius=2.0, percent=60, threshold=2))
        im = im.filter(ImageFilter.UnsharpMask(radius=0.8, percent=45, threshold=2))
        im.thumbnail((2600, 4000))
        dst = work / f"img{i}.jpg"
        im.save(dst, "JPEG", quality=96, subsampling=0)
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
    # every reel ends with the same follow line (spoken in English by the system)
    STD = "மேலும் செய்திகளுக்கு " + ("இராசிபுரம்" if PAGE == "rasipuram" else "நாமக்கல்") + " த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்."
    if "பின்தொடரு" in sentences[-1] or "Follow" in sentences[-1]:
        sentences = sentences[:-1]
    sentences.append(STD)
    body, last = sentences[:-1], sentences[-1]
    # an on-screen fact is shown ONLY while the sentence it matches is spoken (matched by shared word stems);
    # the old code cycled slide lines in order, so the chip often showed a different fact than the voice said.
    def _stems(t):
        return {w[:4] for w in re.findall(r"[\u0B80-\u0BFF]{4,}", re.sub(r"<[^>]+>", "", t))}
    pool = [re.sub(r"<[^>]+>", "", ln) for sl in spec.get("slides", []) for ln in sl.get("lines", [])]
    used, sents = set(), []
    for i, sent in enumerate(body):
        best, bs = "", 1
        st = _stems(sent)
        for j, ln in enumerate(pool):
            sc = len(st & _stems(ln))
            if j not in used and sc > bs and len(ln) <= 48:
                best, bs, bj = ln, sc, j
        if best and i >= 1:
            used.add(bj)
        sents.append({"say": sent, "caption": sent, "fact": best if i >= 1 else ""})
    hook = [(spec.get("hl1") or "").strip(), (spec.get("hl2") or "").strip()]
    return {"v": 3, "story": row["story_id"], "date": spec["date"], "cat": (spec.get("cat") or "").strip(),
            "location": (spec.get("loc") or "நாமக்கல்")[:30], "voice": "male", "hook": hook,
            "images": [str(p) for p in images], "sentences": sents, "outro": {"say": last},
            "scenes": [{"caption": x["caption"]} for x in sents] + [{"caption": last}]}


def render_reel(row, spec, images, work, voice_file=None):
    rs = reel_spec(row, spec, images)
    (work / "reel.json").write_text(json.dumps(rs, ensure_ascii=False))
    env = dict(os.environ)
    if voice_file:
        env["VOICE_FILE"] = str(voice_file)
    mp4 = work / f"{row['story_id']}_reel.mp4"
    subprocess.run([sys.executable, str(REEL / "reel3.py"), str(work / "reel.json"), str(mp4), PAGE], check=True, env=env)
    return mp4


# ---------------------------------------------------------------- hosting + Instagram
def upload(path, kind):
    url = f"https://api.cloudinary.com/v1_1/{CLOUD}/{'video' if kind == 'video' else 'image'}/upload"
    with open(path, "rb") as f:
        r = requests.post(url, data={"upload_preset": PRESET, "folder": "news360"}, files={"file": f}, timeout=600)
    r.raise_for_status()
    return r.json()["secure_url"]


def cache_key(row, spec, caption):
    import hashlib
    raw = json.dumps([row.get("reel_script"), row.get("slides_spec"), caption, row.get("images"), spec.get("date"), row.get("post_to")] + (["rasipuram"] if PAGE == "rasipuram" else []), ensure_ascii=False)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def cache_path(sid, page=None):
    page = page or PAGE
    return CACHE / (f"{sid}.json" if page == "namakkal" else f"{sid}_{page}.json")


def load_cache(sid, key):
    try:
        d = json.loads(cache_path(sid).read_text(encoding="utf-8"))
        if d.get("key") == key and d.get("reel") and (d.get("carousel") or d.get("reel_only")):
            return d
    except Exception:
        pass
    return None


def save_cache(sid, key, media, checks):
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        cache_path(sid).write_text(json.dumps(dict(media, key=key, checks=checks, reel_only=not media.get("carousel")), ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        log("cache not saved:", e)


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


LOC_ID = ""   # Instagram location (place) id for the story being posted; set in run_story


def pick_location(row, spec):
    """Instagram place id from config.json "locations" (keyword -> id).
    The place named FIRST in the Tamil headline wins, then the English headline, then the story's location fields;
    the district-wide 'namakkal' tags are used only when no town, temple or hill is named."""
    locs = CONFIG.get("locations") or {}
    generic = {"namakkal", "நாமக்கல்"}
    fields = [row.get("headline_ta", ""), row.get("headline_en", ""), spec.get("loc", ""), row.get("location", "")]
    for specific_only in (True, False):
        for f in fields:
            low = (f or "").lower()
            best = None
            for key, pid in locs.items():
                if key == "default" or not str(pid).strip().isdigit():
                    continue
                if specific_only and key in generic:
                    continue
                i = low.find(key.lower())
                if i >= 0 and (best is None or (i, -len(key)) < best[0]):
                    best = ((i, -len(key)), str(pid).strip())
            if best:
                return best[1]
    d = str(locs.get("default", "")).strip()
    return d if d.isdigit() else ""


def create_with_collab(uid, token, params, collab):
    """Create the media container with the location tag and the collaborator invite; if either is refused, retry without it (and say so)."""
    base = dict(params)
    if LOC_ID:
        base["location_id"] = LOC_ID

    def attempt(extra, p):
        return ig("POST", f"{uid}/media", token, **extra, **p)["id"]

    for use_loc in ([True, False] if LOC_ID else [False]):
        p = dict(base) if use_loc else dict(params)
        if collab:
            try:
                return attempt(dict(collaborators=json.dumps([CONFIG["collab_username"]])), p), True, ("" if use_loc or not LOC_ID else "location refused")
            except RuntimeError as e:
                log("container refused with collaborator" + (" + location" if use_loc and LOC_ID else "") + ":", e)
                try:
                    return attempt({}, p), False, str(e)[:300]
                except RuntimeError as e2:
                    log("container refused:", e2)
                    if not (use_loc and LOC_ID):
                        raise
                    continue
        try:
            return attempt({}, p), False, ""
        except RuntimeError as e:
            log("container refused:", e)
            if not (use_loc and LOC_ID):
                raise
    raise RuntimeError("could not create the media container")


def publish_carousel(token, urls, caption, collab, alt=""):
    uid, _ = ig_account(token)

    def kid(u, i):
        # alt text helps Instagram understand the picture (search / accessibility); dropped if the API refuses it
        if alt:
            try:
                return ig("POST", f"{uid}/media", token, image_url=u, is_carousel_item="true", alt_text=f"{alt} - slide {i}")["id"]
            except Exception as e:
                log("alt text refused, posting without it:", e)
        return ig("POST", f"{uid}/media", token, image_url=u, is_carousel_item="true")["id"]
    kids = [kid(u, i) for i, u in enumerate(urls, 1)]
    for k in kids:
        wait_ready(k, token, 5)
    cid, collab_ok, why = create_with_collab(uid, token, dict(media_type="CAROUSEL", children=",".join(kids), caption=caption), collab)
    wait_ready(cid, token, 5)
    mid = ig("POST", f"{uid}/media_publish", token, creation_id=cid)["id"]
    return mid, ig("GET", mid, token, fields="permalink").get("permalink", ""), collab_ok, why


def publish_reel(token, video_url, caption, collab, cover_url=""):
    uid, _ = ig_account(token)
    prm = dict(media_type="REELS", video_url=video_url, caption=caption, share_to_feed="true")
    if cover_url:
        prm["cover_url"] = cover_url   # chosen cover photo (sharp frame with the hook headline)
    try:
        cid, collab_ok, why = create_with_collab(uid, token, prm, collab)
    except RuntimeError as e:
        if not cover_url:
            raise
        log("reel refused with the cover, posting with Instagram's own cover:", e)
        prm.pop("cover_url", None)
        cid, collab_ok, why = create_with_collab(uid, token, prm, collab)
    wait_ready(cid, token, 15)
    mid = ig("POST", f"{uid}/media_publish", token, creation_id=cid)["id"]
    return mid, ig("GET", mid, token, fields="permalink").get("permalink", ""), collab_ok, why


FIRST_COMMENTS = [
    "இந்த செய்தி உங்களுக்கு பயனுள்ளதா? தேவைப்படும் நண்பர்களுக்கு Share செய்யுங்கள் 🙏",
    "உங்கள் பகுதியில் இதன் நிலை என்ன? கமெண்டில் சொல்லுங்கள் 👇",
    "நாமக்கல் செய்திகளைத் தவறவிடாமல் இருக்க Save செய்து Follow செய்யுங்கள் 📌",
]


def first_comment(token, media_id, sid, k=0):
    """the page's own first comment (a question / share prompt, no hashtags) to start the conversation. Never raises."""
    try:
        if not CONFIG.get("first_comment", True) or not media_id:
            return
        msg = FIRST_COMMENTS[(sum(map(ord, sid)) + k) % len(FIRST_COMMENTS)]
        ig("POST", f"{media_id}/comments", token, message=msg)
        log("first comment added", media_id)
    except Exception as e:
        log("first comment not added (post itself is fine):", e)


def publish_story(token, media_url, kind):
    """Instagram Story (image or video) on the same account. Never raises: a story problem must not undo the post."""
    try:
        if not CONFIG.get("post_stories", True):
            return ""
        uid, _ = ig_account(token)
        prm = dict(media_type="STORIES")
        prm["video_url" if kind == "video" else "image_url"] = media_url
        cid = ig("POST", f"{uid}/media", token, **prm)["id"]
        wait_ready(cid, token, 10)
        mid = ig("POST", f"{uid}/media_publish", token, creation_id=cid)["id"]
        log("story posted", kind, mid)
        return mid
    except Exception as e:
        log("story not posted (post itself is fine):", e)
        return ""


def story_image(jpg, dst):
    """9:16 story frame from a carousel slide: slide centred on a blurred, darkened copy of itself"""
    im = Image.open(jpg).convert("RGB")
    bg = im.resize((1080, 1920), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    w = 1080
    h = round(im.height * w / im.width)
    if h > 1920:
        h = 1920
        w = round(im.width * h / im.height)
    fg = im.resize((w, h), Image.LANCZOS)
    bg.paste(fg, ((1080 - w) // 2, (1920 - h) // 2))
    bg.save(dst, "JPEG", quality=94)
    return dst


# ---------------------------------------------------------------- main flows
def fail(row, kind, msg):
    log("NOT POSTED -", row["story_id"], msg)
    bridge_post("error", {"row": row["row"], "page": PAGE, "kind": kind, "error": msg[:900]})


def still_needed(sid, page, kind):
    """last check right before publishing: the sheet may have changed while this slow job was building (row marked skipped / already posted)"""
    try:
        r = next((x for x in bridge_get("queue")["rows"] if x.get("story_id") == sid), None)
    except Exception:
        return True
    if r is None:
        return False
    if (r.get("review") or "").strip().lower() == "hold":
        return False
    if kind == "carousel":
        return not r.get(page + "_link")
    return LABEL[page] not in (r.get("reel_link") or "")


LIMIT = {}      # page -> True once Instagram's 24-hour publishing limit (50 posts per account) is reached


def is_limit_error(e):
    t = str(e).lower()
    return "2207042" in t or "publish limit" in t or "publishing limit" in t or "maximum number of" in t and "posts" in t


def limit_reached(page):
    """True when this page already used its 50 API posts of the last 24 h. The only reason a prepared story is held back (it is posted later,
    nothing is marked failed)."""
    if page in LIMIT:
        return LIMIT[page]
    LIMIT[page] = False
    if DRY:
        return False
    try:
        token = bridge_get("token", page=page)["token"]
        uid, _ = ig_account(token)
        d = ig("GET", f"{uid}/content_publishing_limit", token, fields="quota_usage,config")
        row = (d.get("data") or [{}])[0]
        used, total = int(row.get("quota_usage", 0)), int((row.get("config") or {}).get("quota_total", 50) or 50)
        log(f"publishing quota {page}: {used}/{total}")
        LIMIT[page] = used >= total
    except Exception as e:
        log("quota check failed (posting goes on):", e)
    return LIMIT[page]


def run_story(row):
    """every page named in post_to gets its own carousel + reel (own logo and follow line), one page after the other"""
    done = []
    for pg in pages_of(row):
        if page_done(row, pg):
            continue
        if limit_reached(pg):
            log("LIMIT: 24-hour Instagram post limit reached for", pg, "- ", row.get("story_id"), "waits")
            continue
        done += run_story_page(row, pg) or []
    return done


def run_story_page(row, page):
    """Build the carousel and the reel, run every check, and only then publish (carousel first, then reel)."""
    import verify
    sid = row["story_id"]
    spec = json.loads(row["slides_spec"])
    _digits_in_spec(spec)
    spec["date"] = tamil_date_today()  # date shown on poster/reel = actual posting date (IST)
    global LOC_ID
    LOC_ID = pick_location(row, spec)
    if LOC_ID:
        log("location tag:", LOC_ID)
    problems = check_text(row, spec) + verify.check_news(row)
    if problems:
        return fail(row, "carousel", "Checks failed: " + "; ".join(problems))
    global PAGE, LOGO, TAG
    PAGE = page
    LOGO = KIT / f"logo_{PAGE}.png"
    TAG = "#Rasipuram360" if PAGE == "rasipuram" else "#Namakkal360"
    os.environ["PAGE_KEY"] = PAGE
    collab = False      # no collaboration: every page posts its own news separately (Rasipuram 360 = Rasipuram only, Namakkal 360 = the rest of the district)
    caption = final_caption(row)
    work = OUT / sid
    key = cache_key(row, spec, caption)
    cached = None if PREBUILD else load_cache(sid, key)
    if cached:
        log("prebuilt carousel + reel found - publishing without rebuilding")
    images = [] if cached else fetch_images(row, work)
    need_carousel, need_reel = not row.get(PAGE + "_link") and spec.get("carousel", True) is not False and CONFIG.get("carousel") is not False, LABEL[PAGE] not in (row.get("reel_link") or "")
    jpgs = mp4 = None
    reel_cover = None
    voice_file = None
    rs = None
    checks = []

    # 1. build everything (nothing is published yet)
    if cached:
        checks = list(cached.get('checks') or [])
    else:
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
                probs = verify.check_reel(mp4, [x["say"] for x in rs["sentences"]] + [rs["outro"]["say"]])
                if probs:
                    return fail(row, "reel", "Reel check failed: " + "; ".join(probs))
                checks.append("reel 1080x1920, 10-30 s, voice present and fully pronounceable")
                cov = mp4.with_name(mp4.stem + "_cover.jpg")
                reel_cover = cov if cov.exists() else None
                if not reel_cover:
                    log("no cover image made, Instagram will pick a frame")
        except subprocess.CalledProcessError as e:
            return fail(row, "carousel", f"Build failed ({e.cmd[1].split('/')[-1]}, exit {e.returncode})")
        except Exception as e:
            return fail(row, "carousel", f"Build failed: {e}")
    checks.append("news marked verified: " + (row.get("verification") or "")[:60])
    note = "; ".join(checks)
    log("all checks passed:", note)

    # 1b. upload the finished files once and remember the links (a later run, or a retry after an Instagram error, publishes at once)
    if cached:
        media = cached
    else:
        media = {"carousel": [], "reel": "", "cover": "", "story": ""}
        try:
            if need_carousel and jpgs:
                media["carousel"] = [upload(j, "image") for j in jpgs]
                try:
                    media["story"] = upload(story_image(jpgs[0], work / "story_cover.jpg"), "image")
                except Exception as e:
                    log("story image not made (post itself is fine):", e)
            if need_reel and mp4:
                media["reel"] = upload(mp4, "video")
                try:
                    media["cover"] = upload(reel_cover, "image") if reel_cover else ""
                except Exception as e:
                    log("cover upload failed:", e)
            if media["reel"] and (media["carousel"] or spec.get("carousel", True) is False):
                save_cache(sid, key, media, checks)
        except Exception as e:
            return fail(row, "carousel", f"Upload failed: {e}")
    if PREBUILD:
        log("PREBUILT (not posted):", sid, "carousel", len(media["carousel"]), "slides, reel", bool(media["reel"]))
        return [("prebuilt", sid)]

    # stagger: stories of one run are published SLOT_MIN minutes apart (account reach is better than a burst of posts)
    try:
        slot = float(os.environ.get("SLOT_MIN", "0") or 0)
    except ValueError:
        slot = 0
    wait_s = START + slot * 60 - time.time()
    if slot and not DRY and wait_s > 0:
        log(f"waiting {wait_s / 60:.0f} min for this story's posting slot")
        time.sleep(wait_s)

    # 2. upload and publish
    done = []
    voice = "recorded" if voice_file else "voice model"
    if need_carousel:
        try:
            urls = media["carousel"]
            if DRY:
                log("DRY RUN carousel - not publishing", urls)
                bridge_post("posted", {"row": row["row"], "page": PAGE, "kind": "carousel", "dry_run": True, "permalink": "",
                                       "media_urls": urls, "caption": caption, "slides": len(urls), "collab": collab, "checks": note})
            elif not still_needed(sid, PAGE, "carousel"):
                log("carousel no longer needed (sheet changed) - not publishing", sid, PAGE)
            else:
                token = bridge_get("token", page=PAGE)["token"]
                mid, link, collab_ok, why = publish_carousel(token, urls, caption, collab, (row.get('headline_en') or '')[:200] + (' - Rasipuram 360 news' if PAGE == 'rasipuram' else ' - Namakkal 360 news'))
                log("carousel posted", sid, link)
                first_comment(token, mid, sid, 0)
                bridge_post("posted", {"row": row["row"], "page": PAGE, "kind": "carousel", "permalink": link, "media_id": mid,
                                       "media_urls": urls, "caption": caption, "slides": len(urls), "collab": collab_ok, "checks": note})
                done.append(("carousel", link))
                try:
                    if media.get("story"):
                        publish_story(token, media["story"], "image")
                except Exception as e:
                    log("story image not made (post itself is fine):", e)
        except Exception as e:
            if is_limit_error(e):
                LIMIT[PAGE] = True
                log("LIMIT: Instagram post limit hit while posting carousel", sid, "- waits, not a failure")
            else:
                log("ERROR carousel", sid, e)
                bridge_post("error", {"row": row["row"], "page": PAGE, "kind": "carousel", "error": str(e)[:900]})
    if need_reel:
        try:
            url = media["reel"]
            if DRY:
                log("DRY RUN reel - not publishing", url)
                bridge_post("posted", {"row": row["row"], "page": PAGE, "kind": "reel", "dry_run": True, "permalink": "",
                                       "media_urls": [url], "caption": caption, "voice": voice, "collab": collab, "checks": note})
            elif not still_needed(sid, PAGE, "reel"):
                log("reel no longer needed (sheet changed) - not publishing", sid, PAGE)
            else:
                token = bridge_get("token", page=PAGE)["token"]
                cover_url = media.get("cover") or ""
                mid, link, collab_ok, why = publish_reel(token, url, caption, collab, cover_url)
                log("reel posted", sid, link)
                first_comment(token, mid, sid, 1)
                publish_story(token, url, "video")
                bridge_post("posted", {"row": row["row"], "page": PAGE, "kind": "reel", "permalink": link, "media_id": mid,
                                       "media_urls": [url], "caption": caption, "voice": voice, "collab": collab_ok, "checks": note})
                done.append(("reel", link))
        except Exception as e:
            if is_limit_error(e):
                LIMIT[PAGE] = True
                log("LIMIT: Instagram post limit hit while posting reel", sid, "- waits, not a failure")
            else:
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
        global ALL_ROWS
        ALL_ROWS = list(rows)
        try:      # recent rows of the Sheet (already posted ones included) so the same news is never posted twice
            ALL_ROWS += [r for r in bridge_get("recent").get("rows", []) if r.get("story_id") not in {x.get("story_id") for x in rows}]
        except Exception as e:
            log("recent rows not available (duplicate check uses the queue only):", e)
        n = len(pick_all(rows))
    if mode == "check":
        log(f"{len(rows)} stories in the queue, ready to post: {n}")
        if rows:
            log("  keys:", sorted(rows[0].keys()))
        for r in rows:
            log("  ", r.get("story_id"), "review=", repr(r.get("review")), "images=", len(r.get("images") or ""),
                "spec=", len(r.get("slides_spec") or ""), "pages=", pages_of(r), "links=", repr(r.get("namakkal_link")), repr(r.get("rasipuram_link")), repr(r.get("reel_link")),
                "age_h=", round(age_hours(r), 1), "ready=", ready(r), "set_started=", set_started(r))
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                if PREBUILD:   # prebuild: every waiting story, built at once, nothing published
                    ids = [r["story_id"] for r in pick_all(rows)] if n else []
                    f.write(f"ready={1 if n else 0}\n")
                    f.write("matrix=" + json.dumps({"include": [{"story": i, "slot": 0} for i in ids]}) + "\n")
                else:
                    ids = [r["story_id"] for r in pick_all(rows)][:6] if n else []   # 6 stories per run, 6 min apart (was 3 per run, 25 min apart: far too slow for 24 stories per round)
                    inc = [{"story": i, "slot": k * 6, "prebuild": ""} for k, i in enumerate(ids)]
                    # stories whose set has not started yet: make the carousel/reel ahead, so they go out the moment it starts
                    urgent = set(ids)
                    pre = [r["story_id"] for r in rows if ready(r) and r["story_id"] not in urgent and not set_started(r) and not all(cache_path(r["story_id"], p).exists() for p in pages_of(r) if not page_done(r, p))][:3]
                    inc += [{"story": i, "slot": 0, "prebuild": "1"} for i in pre]
                    if pre:
                        log("prebuilding ahead of the set start:", pre)
                    f.write(f"ready={1 if inc else 0}\n")
                    f.write("matrix=" + json.dumps({"include": inc}) + "\n")
        return
    want = sys.argv[2] if len(sys.argv) > 2 else ""
    row = next((r for r in (rows if PREBUILD else pick_all(rows)) if r.get("story_id") == want and (not PREBUILD or ready(r))), None) if want else pick(rows)
    if not row:
        log("no story with images is waiting")
        return
    log("->", row["story_id"], row.get("headline_ta"))
    done = run_story(row)
    log("finished:", done or "nothing posted")


if __name__ == "__main__":
    main()
