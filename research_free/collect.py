"""Every-3-hours collector (free models). Fetch Namakkal news -> write posts -> validate -> send to the Apps Script bridge
(Sheet rows + ONE prompt file + ONE email). Usage: python research_free/collect.py [--dry]"""
import datetime, difflib, json, os, random, re, sys, time
from pathlib import Path
import requests
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import llm, sources, run, allnews

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
BRIDGE_URL, BRIDGE_KEY = os.environ.get("BRIDGE_URL", ""), os.environ.get("BRIDGE_KEY", "")
def _slot_count():
    """stories per round: no practical limit (owner 25 Oct: every news published today in the district is written and posted, priority first)"""
    return 200


SET_NEWS = int(os.environ.get("SET_NEWS_COUNT", "0") or 0) or _slot_count()
MAX_RASIPURAM = int(os.environ.get("MAX_RASIPURAM", "0") or 0) or SET_NEWS     # Rasipuram page: the same count per round, as far as local news exists
CAROUSEL_EVERY = int(os.environ.get("CAROUSEL_EVERY", "5"))   # 1 carousel (best story) per 5 stories, all others reel only
MAX_NAMAKKAL = int(os.environ.get("MAX_NAMAKKAL", "0") or 0) or SET_NEWS       # Namakkal page: district news, same count per round
ARCHIVE = HERE / "archive"
DRY = "--dry" in sys.argv
IMG_BUDGET = int(os.environ.get("IMG_BUDGET_MIN", "22")) * 60
IMG_MAX = int(os.environ.get("IMG_MAX_PER_RUN", "40"))     # credit guard: at most this many automatic images per run     # minutes spent on automatic images per send
DEADLINE = time.time() + int(os.environ.get("BUDGET_MIN", "22")) * 60
llm.DEADLINE[0] = DEADLINE

TEMPLATE = ("ONE single continuous photograph from one camera angle (not a collage, grid, strips or panels). Ultra-sharp photorealistic documentary-style news photo, tall vertical portrait (9:16 if possible, highest resolution), "
            "MAXIMUM CLARITY: 4K, tack-sharp focus across the whole frame, deep depth of field, shot like a professional full-frame camera with a 35mm lens at f/8, crisp fine detail and edges, clean noise-free image, balanced high dynamic range, natural lighting; no blur, no soft focus, no motion blur, no haze, no painterly, plastic or over-smoothed AI look. {scene} "
            "Natural colours, realistic light, sharp detail, modern news-photography look. STRICT: no text, letters, numbers, signboard writing, logos or watermarks anywhere in the image; "
            "no recognisable real person, politician or celebrity face (show people only from behind, far away or blurred); no blood, injuries or dead bodies. "
            "Keep the top-right corner and the lower third of the image visually simple (sky, road, wall, field) because Tamil text will be placed there.")


BRIEF_SYSTEM = """You write image-generation prompts for a Tamil local-news photo. You get the story facts: the English headline, the place, the category and the article text.
Write 3 different detailed prompts. Each one describes ONE real photograph of THIS story:
- the exact place from the article and its real type (road, bus stand, school, hospital, collectorate office, field, river, hill, market, house);
- the event itself as it looks (flood water on road, students with banners, police vehicle, damaged wall, crowd, rain, smoke) with the number of people and what they do;
- the time of day, weather and light mentioned in the article; the vehicles, objects and buildings named in it;
- people only from behind, far away or blurred; never a recognisable face.
Use only facts from the article. Do not invent details. Each prompt 60-120 words, English, one single photograph.
Never ask for text, letters, signboards with writing, logos or watermarks.
Return ONLY JSON: {"scenes": ["prompt 1", "prompt 2", "prompt 3"]}"""

IMG_TEMPLATE = ("Realistic news photograph, one single frame, tall vertical 9:16 composition, sharp focus, natural light, documentary press-photo look, no text, no letters, no logos. {scene} Keep the lower third plain (road, wall, sky).")


def image_scenes(art, d):
    """detailed image prompts built from the article itself (not a generic scene)"""
    user = f"HEADLINE: {d.get('english_headline', '')}\nPLACE: {d.get('location', '')}\nCATEGORY: {d.get('category', '')}\nARTICLE:\n{(art.get('text') or '')[:3000]}"
    try:
        data, _ = llm.ask_json(BRIEF_SYSTEM, user)
    except Exception:
        if not llm.claude_available():
            raise
        data, _ = llm.ask_claude(BRIEF_SYSTEM, user, max_tokens=1500)
    sc = [s.strip() for s in (data.get("scenes") or []) if isinstance(s, str) and len(s.strip()) > 40]
    return sc[:3]


def bridge(action, **kw):
    r = requests.get(BRIDGE_URL, params={"action": action, "key": BRIDGE_KEY, **kw}, timeout=120)
    r.raise_for_status()
    return r.json()


# what Namakkal readers care about most (higher = picked first, so it is never missed)
INTEREST = [
    (10, ("மின்தடை", "மின் தடை", "மின்நிறுத்த", "மின் நிறுத்த", "மின் வெட்டு", "மின்வெட்டு", "மின் விநியோகம் நிறுத்தம்")),
    (9, ("மழை", "வானிலை", "புயல்", "வெள்ளம்", "வெப்பம்", "பள்ளி விடுமுறை", "விடுமுறை")),
    (9, ("முட்டை விலை", "விலை", "காய்கறி", "தக்காளி", "கறிக்கோழி", "மஞ்சள்", "உழவர் சந்தை", "சந்தை")),
    (8, ("வேலைவாய்ப்பு", "வேலை வாய்ப்பு", "முகாம்", "தேர்வு", "ஆட்சேர்ப்பு", "பணியிடம்")),
    (7, ("பள்ளி", "கல்லூரி", "மாணவ", "தேர்வு முடிவு", "உதவித்தொகை", "சேர்க்கை")),
    (7, ("ரேஷன்", "மகளிர் உரிமை", "ஓய்வூதியம்", "திட்டம்", "மானியம்", "ஆட்சியர்", "அறிவிப்பு", "சிறப்பு முகாம்")),
    (6, ("பேருந்து", "சாலை", "போக்குவரத்து", "ரயில்", "பாலம்", "போக்குவரத்து மாற்றம்")),
    (6, ("குடிநீர்", "கொசு", "குப்பை", "சாக்கடை", "பாதாளச் சாக்கடை", "தண்ணீர்")),
    (5, ("திருவிழா", "கோவில்", "தேர்", "கொல்லிமலை", "சுற்றுலா")),
    (4, ("விபத்து", "மீட்பு", "தீ விபத்து", "கைது")),
]


def interest(art):
    t = art.get("title", "") + " " + art.get("text", "")[:600]
    head = art.get("title", "")
    best = 2
    for score, keys in INTEREST:
        for k in keys:
            if k in head:
                best = max(best, score + 1)
            elif k in t:
                best = max(best, score)
    return best


def _start_at():
    """the moment automatic collecting was last started (research_free/START_AT, UTC). News published before it is never collected."""
    try:
        return datetime.datetime.fromisoformat((HERE / "START_AT").read_text().strip().replace("Z", "+00:00"))
    except Exception:
        return None


def fresh(published):
    try:
        t = datetime.datetime.fromisoformat(published)
        d = t.astimezone(IST).date()
    except Exception:
        return True
    st = _start_at()
    if st is not None and t.tzinfo is not None and t < st:
        return False      # published before the automation was started: already covered by the posted/e-mailed news
    return d == datetime.datetime.now(IST).date()      # owner 25 Oct: only news published TODAY (IST, from 00:00); yesterday's news is never used


def _fr():
    sys.path.insert(0, str(HERE.parent / "poster"))
    import freshness
    return freshness


def is_dup(art, d, recent):
    for r in recent:
        if r.get("source") and r["source"] == art["url"]:
            return True
        if _fr().similar(r.get("headline_ta", ""), (d or {}).get("tamil_headline", art["title"]), 0.72, r.get("researched")):
            return True
    return False


def score(n):
    """how likely readers are to open / share it: topic interest + how many outlets carry it + how fresh it is"""
    s = interest({"title": n.get("title", ""), "text": n.get("snippet", "")})
    m = n.get("mentions", 1)
    s += 2 if m >= 3 else (1 if m == 2 else 0)
    try:
        import learned
        s += learned.boost(n.get("title", ""))        # topics our own Instagram insights show people watch / save / share
    except Exception:
        pass
    try:
        age_h = (datetime.datetime.now(IST) - datetime.datetime.fromisoformat(n["published"])).total_seconds() / 3600
        s += 1 if age_h < 6 else 0
    except Exception:
        pass
    return s


def load_state():
    try:
        st = json.loads((ARCHIVE / "state.json").read_text(encoding="utf-8"))
    except Exception:
        st = {}
    cut = (datetime.datetime.now(IST) - datetime.timedelta(days=5)).isoformat()
    return {k: v for k, v in st.items() if v.get("t", "") >= cut}


def save_state(st):
    ARCHIVE.mkdir(exist_ok=True)
    (ARCHIVE / "state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


PRIORITY_ONLY = [False]
EARLY_N = int(os.environ.get("EARLY_EMAIL_AFTER", "0"))   # the first email (images needed) goes out as soon as this many stories are written


def assign_carousel(group):
    """reels carry the reach; a carousel only for the most promising story in every CAROUSEL_EVERY per area (High importance always gets one)"""
    for a in ("R", "N"):
        grp = sorted([x for x in group if x.get("_area") == a], key=lambda x: -x["_score"])
        top = max(1, -(-len(grp) // CAROUSEL_EVERY)) if grp else 0
        for i, x in enumerate(grp):
            x["slides_spec"]["carousel"] = (i < top or str(x.get("importance", "")).strip() == "High") and os.environ.get("CAROUSEL_ON", "0") == "1"      # reels only for now


STYLE = ("Square image, the main subject exactly in the centre with empty space around it so a tall centre crop keeps it. Scroll-stopping, emotionally engaging, high-impact news photograph: one clear strong focal subject, dramatic natural light "
         "(golden hour, soft morning mist or storm-light as fits the story), rich saturated yet natural colours, cinematic composition with "
         "depth, professional photojournalism look, ultra-sharp, realistic textures. No vehicle number plates, no signboards, no writing on any object. ")


def _upload_image(data):
    cloud, preset = os.environ.get("CLOUDINARY_CLOUD"), os.environ.get("CLOUDINARY_PRESET")
    if not cloud or not preset:
        raise RuntimeError("Cloudinary secrets missing")
    r = requests.post(f"https://api.cloudinary.com/v1_1/{cloud}/image/upload", data={"upload_preset": preset, "folder": "news360"},
                      files={"file": ("img.jpg", data)}, timeout=300)
    r.raise_for_status()
    return r.json()["secure_url"]


_RECENT_IMG = []


def reuse_images(st, need):
    """earlier posted stories' pictures that fit this news: same category and place first, then same category (partial match).
    Returns `need` picture URLs, or [] when nothing suitable exists."""
    if os.environ.get("REUSE_IMAGES", "0") != "1":      # owner 25 Oct: never reuse earlier pictures, always make fresh ones
        return []
    if not _RECENT_IMG:
        try:
            _RECENT_IMG.extend(bridge("recent").get("rows", []))
        except Exception as e:
            print("recent pictures not available:", str(e)[:120]); _RECENT_IMG.append({})
    cat, loc = (st.get("category") or "").strip(), (st.get("location") or "").strip()
    best, best_score = None, 0
    for r in _RECENT_IMG:
        if not r.get("story_id") or not str(r.get("post_status", "")).lower().startswith(("posted", "partly")):
            continue
        try:
            imgs = json.loads(r.get("images") or "[]")
        except Exception:
            continue
        if len(imgs) < need or "NOIMAGE" in str(imgs):
            continue
        score = (2 if cat and r.get("category") == cat else 0) + (2 if loc and loc.split(",")[0].strip() and loc.split(",")[0].strip() in str(r.get("location", "")) else 0)
        if score >= 2 and score > best_score:
            best, best_score = imgs, score
    return list(best[:need]) if best else []


def make_images(group, log=None):
    """AUTO images: every scene prompt -> NVIDIA image API -> Cloudinary. A story gets story["images"] only when ALL its images were made;
    the bridge then queues it for posting at once and leaves it out of the images-needed email. Any failure -> the e-mail flow as before."""
    if os.environ.get("AUTO_IMAGES", "0") != "1" or not (os.environ.get("FAL_KEY") or os.environ.get("NVIDIA_API_KEY") or os.environ.get("CLOUDFLARE_API_TOKEN")) or DRY:
        return
    try:
        import imagegen
    except Exception as e:
        print("imagegen import failed:", e)
        return
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time()
    for st in group:
        if time.time() - t0 > IMG_BUDGET:
            msg = "image budget used up: the remaining stories go to the images-needed email"
            print(msg); log is not None and log.append(msg)
            break
        prompts = [p.strip() for p in str(st.get("prompts", "")).split("\n---\n") if p.strip()]
        if not prompts:
            continue
        sid = st.get("english_headline", "")[:40]
        if IMG_MAX and sum(imagegen.USED.values()) + len(prompts) > IMG_MAX:
            msg = f"image cap {IMG_MAX} per run reached (credit guard): the remaining stories go to the images-needed email"
            print(msg); log is not None and log.append(msg)
            break
        reused = reuse_images(st, len(prompts))
        if reused:
            st["images"] = reused
            print(f"earlier pictures reused for '{sid}'")
            if log is not None:
                log.append(f"earlier picture reused for '{sid}' (matching news)")
            continue
        try:
            def one(ip):
                i, pr = ip
                data = imagegen.generate((STYLE + pr)[:1800], seed=random.randint(1, 10**6))
                return _upload_image(data)
            # credit guard: the first image is made alone; if it fails, the rest of this story is NOT attempted (no credits wasted on half a story)
            first = one((0, prompts[0]))
            rest = []
            if len(prompts) > 1:
                with ThreadPoolExecutor(max_workers=2) as ex:
                    rest = list(ex.map(one, list(enumerate(prompts))[1:]))
            urls = [first] + rest
            st["images"] = urls
            print(f"images made: {len(urls)} for '{sid}'")
        except Exception as e:
            print(f"images NOT made for '{sid}': {str(e)[:200]}")
            if log is not None:
                log.append(f"auto images failed for '{sid}': {str(e)[:120]} -> images-needed email")
            # last check: earlier pictures again (a partial match is accepted); otherwise this story waits for the owner's e-mail
            again = reuse_images(st, len(prompts))
            if again:
                st["images"] = again
                if log is not None:
                    log.append(f"earlier picture reused (second check) for '{sid}'")
                continue
            if "all image models failed" in str(e):
                break          # no image model works right now (credits/limit): do not waste time on the other stories
    if log is not None:
        log.append(f"auto images: {sum(1 for x in group if x.get('images'))} of {len(group)} stories ({imagegen.USED})")


def pending_ids(max_hours=2):
    """stories of earlier rounds still waiting for the owner's images (not older than a day): they are listed again in this round's e-mail"""
    if not BRIDGE_URL or DRY:
        return []
    try:
        rows = bridge("recent").get("rows", [])
    except Exception as e:
        print("pending list not available:", e)
        return []
    out, now = [], datetime.datetime.now(IST)
    TODAY[0] = 0
    mon = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    for r in rows:
        m = re.search(r"(\d{1,2}) (\w{3}) (\d{4}), (\d{1,2}):(\d{2})", str(r.get("researched", "")))
        if not m or m.group(2).lower() not in mon:
            continue
        t = datetime.datetime(int(m.group(3)), mon.index(m.group(2).lower()) + 1, int(m.group(1)), int(m.group(4)), int(m.group(5)), tzinfo=IST)
        if t.date() == now.date() and not str(r.get("post_status", "")).lower().startswith("skipped"):
            TODAY[0] += 1          # stories written today (each one is one reel per page it goes to)
        if str(r.get("post_status", "")).strip() != "Awaiting images":
            continue
        if (now - t).total_seconds() <= max_hours * 3600:
            out.append(r["story_id"])
    return out


REOFFER = []
TODAY = [0]
DAILY_CAP = int(os.environ.get("DAILY_CAP", "1000"))      # owner: after 40 posts in a day only the main / important news is written and posted


def send_batch(group, log=None):
    """write these stories to the Sheet and send ONE images-needed email for them; returns True when the bridge accepted them"""
    if not group or not BRIDGE_URL or DRY:
        return False
    assign_carousel(group)
    make_images(group, log)           # free AI image API; stories whose images could not all be made stay on the images-needed email
    clean = [{k: v for k, v in x.items() if not k.startswith("_")} for x in group]
    try:
        r = requests.post(BRIDGE_URL, params={"key": BRIDGE_KEY}, data=json.dumps({"action": "addStories", "stories": clean, "reoffer_ids": REOFFER}), timeout=180)
        print("bridge:", r.status_code, r.text[:300])
        r.raise_for_status()
        return True
    except Exception as e:
        print("bridge failed:", e)
        if log is not None:
            log.append(f"addStories failed: {e}")
        return False


def file_story(art, res, errors_log, recent):
    """quality gate for one written story; returns the story dict, or (None, reason)"""
    if isinstance(res, Exception):
        return None, f"all free models failed: {str(res)[:80]}"
    try:
        d, model, errors, att = res
        d["scenes"], d["tamil_headline"]
    except Exception as e:
        return None, f"bad draft: {e}"
    HARD = ("not grounded", "numbers not found", "fact-check", "source/outlet", "not a JSON", "missing key")
    # owner 25 Oct: a draft is NOT rejected for length, word count or validator problems. It is rewritten by the models (free, then Claude),
    # and whatever is left goes out with the problems written in its verification note for the owner to see.
    hard = list(errors)
    try:
        sys.path.insert(0, str(HERE.parent / "poster"))
        import freshness
        why = freshness.stale_reason(d.get("tamil_headline", ""), d.get("english_headline", ""), d.get("category", ""), art.get("published", ""))
        if why:
            return None, "stale: " + why
    except ImportError:
        pass
    if is_dup(art, d, recent):
        return None, "duplicate after write"
    if isinstance(d.get("slides_spec"), dict):
        d["slides_spec"]["v"] = 3          # the poster only reads format v3; a model writing v4 made RN-48 unpostable
    try:
        scenes = image_scenes(art, d)
    except Exception as e:
        print("image brief failed, using the writer's scenes:", str(e)[:120], flush=True)
        scenes = d["scenes"]
    prompts = "\n---\n".join(IMG_TEMPLATE.format(scene=s.strip()) for s in scenes)
    ver = f"FREE-MODEL DRAFT ({model}) - not checked by Claude yet" + (f"; validator problems: {'; '.join(errors)}" if errors else "")
    return {"tamil_headline": d["tamil_headline"], "english_headline": d["english_headline"], "category": d["category"], "location": d["location"],
            "importance": d["importance"], "post_to": d["post_to"], "slides_spec": d["slides_spec"], "reel_script": d["reel_script"],
            "caption": d["caption"], "prompts": prompts, "source": art["url"], "published": art["published"], "verification": ver,
            "note": f"free-model draft {model}, {att} attempt(s), {len(errors)} validator problem(s)",
            "post_time": "right after your reply, same day"}, ""


def instagram_recent(log=None):
    """headlines of what both Instagram pages ALREADY show (last 50 posts each), as sheet-like rows, so nothing already posted is written or posted again"""
    rows = []
    try:
        sys.path.insert(0, str(HERE.parent / "poster"))
        import post
        for page in ("rasipuram", "namakkal"):
            try:
                tok = post.bridge_get("token", page=page)["token"]
                uid, _ = post.ig_account(tok)
                for m in post.ig("GET", f"{uid}/media", tok, fields="caption,timestamp", limit=50).get("data", []):
                    head = re.sub(r"^[^\w]+", "", (m.get("caption") or "").strip().split("\n")[0]).strip()
                    if head:
                        rows.append({"story_id": "IG-" + page, "headline_ta": head, "headline_en": "", "researched": m.get("timestamp"), "source": "", "post_status": "posted"})
            except Exception as e:
                if log is not None:
                    log.append(f"instagram check {page} failed: {str(e)[:120]}")
    except Exception as e:
        if log is not None:
            log.append(f"instagram check unavailable: {str(e)[:120]}")
    if log is not None:
        log.append(f"instagram check: {len(rows)} recent posts read from both pages")
    return rows


def main():
    recent = []
    if BRIDGE_URL:
        rr = bridge("recent")
        if rr.get("ok"):
            recent = rr["rows"]
        elif DRY:
            print("bridge 'recent' not available yet (Apps Script not updated):", rr)
        else:
            raise SystemExit(f"bridge 'recent' failed: {rr}")
    seen_src = {r.get("source") for r in recent}
    ig_log = []
    if BRIDGE_URL and not DRY:
        recent += instagram_recent(ig_log)
    today = datetime.datetime.now(IST).strftime("%A %d %B %Y")
    out, log = [], []
    sent_n = [0]      # stories already sent in the early email
    state = load_state()
    REOFFER[:] = pending_ids()
    log.append(f"earlier stories still waiting for images: {REOFFER}")
    log += ig_log
    news = allnews.collect(log)                                   # EVERY item from every source
    for n in news:
        n["score"] = score(n)
        n["status"] = "collected"
        n["story"] = ""
    for r in recent:   # already posted/filed earlier: never write them twice
        for n in news:
            if r.get("source") and (r["source"] == n["url"] or r["source"] in n["alts"]):
                n["status"] = "already filed"
            elif n["title"] and _fr().similar(r.get("headline_ta", ""), n["title"], 0.6, r.get("researched")):
                n["status"] = "already filed"
    for n in news:
        st = state.get(n["key"], {})
        if st.get("s") in ("filed", "dup", "notext", "old", "notdistrict") or st.get("n", 0) >= 10:
            n["status"] = n["status"] if n["status"] != "collected" else "checked earlier: " + st.get("s", "failed")
    manual_links = [u.strip() for u in re.split(r"[\s,]+", os.environ.get("MANUAL_URL", "")) if u.strip().startswith("http")]
    for mu in manual_links:     # owner 26 Oct: links given by hand are written whatever their date; still skipped if already filed or no article text
        news.insert(0, {"key": mu, "url": mu, "title": "", "source": "manual", "published": "", "via": "dinamalar-list",
                        "query": "manual", "snippet": "", "outlets": ["manual link"], "alts": [mu], "mentions": 3,
                        "area": "N", "score": 999, "status": "collected", "story": "", "manual": True})
        log.append(f"manual link added: {mu}")
    queues = {"R": [], "N": []}
    rechecks = 0
    for n in sorted(news, key=lambda x: -x["score"]):
        if n["status"] == "collected" and n["area"] == "N" and allnews.outside_district(n["title"], n.get("via", "")):
            n["status"] = "not Namakkal district news (state-wide / other district)"
            continue
        if n["status"] == "collected" and fresh(n["published"]):
            queues[n["area"]].append(n)
        elif n["status"] == "collected" and any(w in (n.get("source") or "") for w in ("தினமணி", "தினமலர்")) and rechecks < 60:
            # the feed date of a Dinamani / Dinamalar item can be older than the story: open the article and use ITS date (checked when opened)
            rechecks += 1
            queues[n["area"]].append(n)
        elif n["status"] == "collected":
            n["status"] = "old"
    for a_ in ("R", "N"):      # links given by hand go first, before any time is used up
        queues[a_] = [q for q in queues[a_] if q.get("manual")] + [q for q in queues[a_] if not q.get("manual")]
    if not PRIORITY_ONLY[0] and len(queues["R"]) < MAX_RASIPURAM:      # too little Rasipuram news: the Rasipuram page also takes news from the places next to it
        have = {q["key"] for q in queues["R"]}
        near = [q for q in queues["N"] if q["key"] not in have and any(w in q["title"] for w in allnews.RASI_NEAR)]
        queues["R"] += near[:MAX_RASIPURAM - len(queues["R"])]
        log.append(f"Rasipuram short of news: {len(near[:MAX_RASIPURAM])} items from nearby places added to its list")
    from collections import Counter
    log.append("candidate filter: " + ", ".join(f"{k.split(':')[0][:40]}={v}" for k, v in Counter(n["status"] for n in news).most_common()))
    log.append(f"to write: {len(queues['R'])} Rasipuram + {len(queues['N'])} other district candidates (max {MAX_RASIPURAM} + {MAX_NAMAKKAL} stories)")
    target, done, tried = {"R": MAX_RASIPURAM, "N": MAX_NAMAKKAL}, {"R": 0, "N": 0}, {"R": 0, "N": 0}
    if TODAY[0] >= DAILY_CAP:
        log.append(f"daily cap: {TODAY[0]} stories already written today (cap {DAILY_CAP}) - only main / important news is written now")
    if os.environ.get("WRITE_STORIES", "1") == "0" or TODAY[0] >= DAILY_CAP:      # archive-only round: collect and store everything, write nothing, send no email
        # priority scan: only a really urgent local story (accident / death / fire / blast / murder / flood / power shutdown, or reported by 3+
        # outlets) is written between the three normal rounds; if the writer rates it High it is filed and its images-needed email goes at once
        PRIO = ("பலி", "உயிரிழ", "விபத்து", "வெடி", "கொலை", "தீப்பிடி", "தீ விபத்து", "மின்தடை", "மின் தடை", "வெள்ளம்", "தற்கொலை", "கைது")
        target = {"R": 1, "N": 2}
        for a_ in ("R", "N"):
            queues[a_] = [q for q in queues[a_] if q["mentions"] >= 3 or any(w in q["title"] for w in PRIO)][:4]
        PRIORITY_ONLY[0] = True
        log.append("archive round: priority scan only (urgent local news, if any)")
    # Namakkal 360 = top news of the whole district (Rasipuram included), Rasipuram 360 = Rasipuram only; each page posts on its own.
    # A Rasipuram story that is among the district's top MAX_NAMAKKAL by score also goes to Namakkal 360 (and uses one of its slots).
    all_sc = sorted([x["score"] for a_ in ("R", "N") for x in queues[a_]], reverse=True)
    district_cut = all_sc[MAX_NAMAKKAL - 1] if len(all_sc) >= MAX_NAMAKKAL else (all_sc[-1] if all_sc else 0)
    tries_cap = {"R": MAX_RASIPURAM * 10, "N": MAX_NAMAKKAL * 10}
    log.append(f"candidates waiting: {len(queues['R'])} Rasipuram, {len(queues['N'])} Namakkal; time left {int((DEADLINE - time.time()) / 60)} min")
    while time.time() < DEADLINE - 120:
        progressed = False
        for area in ("R", "N"):
            if done[area] >= target[area] or not queues[area] or tried[area] >= tries_cap[area]:
                continue
            n = queues[area].pop(0)
            progressed = True
            tried[area] += 1
            log.append(f"try ({area}) manual={bool(n.get('manual'))}: {(n.get('title') or n.get('url') or '')[:60]}")
            stt = state.setdefault(n["key"], {"n": 0})
            stt["n"] = stt.get("n", 0) + 1
            stt["t"] = datetime.datetime.now(IST).isoformat()
            try:
                url = allnews.resolve(n["url"])
                art = allnews.article_any(url)
                art["url"] = url
                for k in ("text", "title"):      # some outlets type ூ as ு+ா (ப.வேலுார்): normalise so the writer copies the correct spelling
                    if art.get(k):
                        art[k] = art[k].replace("\u0bc1\u0bbe", "\u0bc2")
                art["title"] = art.get("title") or n["title"]
                art["published"] = art.get("published") or n["published"]
            except Exception as e:
                n["status"] = f"could not open the article: {str(e)[:60]}"
                log.append(f"skip ({area}) could not open: {n['title'][:50]} [{n['url'][:60]}] {str(e)[:80]}")
                continue
            if url in seen_src or any(r.get("source") == url for r in recent):
                n["status"], stt["s"] = "already filed", "dup"
                log.append(f"skip ({area}) already filed: {art['title'][:50]}")
                continue
            if len(art["text"]) < 20:      # owner 25 Oct: only an empty article is skipped, never by length
                n["status"], stt["s"] = "article text too short / blocked", "notext"
                log.append(f"skip ({area}) no article text ({len(art['text'])} chars): {art['title'][:50]} [{url[:60]}]")
                continue
            if not fresh(art["published"]) and not n.get("manual"):      # a link the owner gives by hand is written whatever its date
                n["status"], stt["s"] = "old", "old"
                log.append(f"skip ({area}) not today ({art['published'] or 'no date'}): {art['title'][:50]}")
                continue
            if not (allnews.has_place(n["title"]) or allnews.has_place(art["title"]) or allnews.has_place(art["text"][:1500])) and n.get("via", "") != "dinamalar-list":
                n["status"], stt["s"] = "not Namakkal district news (article names no Namakkal place)", "notdistrict"
                log.append(f"skip ({area}) no Namakkal place in article: {art['title'][:50]}")
                continue
            if any(_fr().similar(r.get("headline_ta", ""), art["title"], 0.55, r.get("researched")) for r in recent):
                n["status"], stt["s"] = "already filed", "dup"
                continue
            art["interest"] = interest(art)
            print(f"writing [{area}]: {art['title'][:60]}", flush=True)
            try:
                res = run.write(art, today)
            except Exception as e:
                res = e
            story, why = file_story(art, res, log, recent)
            if not story:
                n["status"] = "not filed: " + why
                log.append(f"NOT filed ({area}) {art['title'][:50]}: {why}")
                continue
            if PRIORITY_ONLY[0] and str(story.get("importance", "")).strip() != "High":
                n["status"] = "checked: not urgent, left for the next normal round"
                log.append(f"not urgent ({area}) {art['title'][:50]}")
                continue
            both = area == "R" and n["score"] >= district_cut
            story["post_to"] = ("Rasipuram 360 + Namakkal 360" if both else "Rasipuram 360") if area == "R" else "Namakkal 360"
            if both:
                target["N"] = max(0, target["N"] - 1)
            story["_area"], story["_score"] = area, n["score"]
            out.append(story)
            if EARLY_N and not sent_n[0] and len(out) >= EARLY_N and send_batch(out, log):
                sent_n[0] = len(out)
                log.append(f"early email: first {sent_n[0]} stories sent, the rest follow in a second email")
            recent.append({"headline_ta": story["tamil_headline"], "source": art["url"]})
            n["status"], n["story"], stt["s"] = "filed", story["tamil_headline"], "filed"
            done[area] += 1
            for a in ("R", "N"):    # same event from another outlet / wording: never write it a second time
                keep = []
                for q in queues[a]:
                    if difflib.SequenceMatcher(None, q["title"], art["title"]).ratio() > 0.8:      # owner 25 Oct: only the same event, not similar wording
                        q["status"] = "duplicate of a story filed this round"
                    else:
                        keep.append(q)
                queues[a] = keep
        if not progressed:
            break
    log.append(f"candidate loop ended: left R={len(queues['R'])} N={len(queues['N'])}, tried={tried}, done={done}, time left {int((DEADLINE - time.time()) / 60)} min")
    rest = out[sent_n[0]:]
    assign_carousel(rest)
    log.append(f"carousel for {sum(1 for x in out if x['slides_spec'].get('carousel'))} of {len(out)} stories, the rest reel only")
    log.append(f"filed: {done['R']} Rasipuram + {done['N']} Namakkal (targets {MAX_RASIPURAM} + {MAX_NAMAKKAL})")
    for n in news:
        if n["status"] == "collected":
            n["status"] = "collected (not in this round's top)"
    # --- the full list of every news item, for the owner to analyse (Sheet tab "All News" + a CSV in the repository)
    rows = [{"source": ", ".join(n["outlets"])[:80], "area": "Rasipuram" if n["area"] == "R" else "Namakkal district", "url": n["url"], "title": n["title"],
             "published": n["published"][:16].replace("T", " "), "mentions": n["mentions"], "score": n["score"], "status": n["status"], "story": n["story"]} for n in news]
    try:
        import csv
        ARCHIVE.mkdir(exist_ok=True)
        f = ARCHIVE / (datetime.datetime.now(IST).strftime("%Y-%m") + ".csv")
        new = not f.exists()
        with open(f, "a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["collected_ist", "source", "area", "url", "title", "published", "mentions", "score", "status", "story"])
            stamp = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
            for r in rows:
                w.writerow([stamp, r["source"], r["area"], r["url"], r["title"], r["published"], r["mentions"], r["score"], r["status"], r["story"]])
        save_state(state)
    except Exception as e:
        log.append(f"archive file not written: {e}")
    if BRIDGE_URL and not DRY and rows:
        try:
            for i in range(0, len(rows), 60):
                rr = requests.post(BRIDGE_URL, params={"key": BRIDGE_KEY}, data=json.dumps({"action": "archiveNews", "rows": rows[i:i + 60]}), timeout=180)
                log.append(f"All News sheet: {rr.text[:100]}")
        except Exception as e:
            log.append(f"All News sheet not updated: {e}")
    Path(HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "collect.json").write_text(json.dumps({"log": log, "llm": llm.LOG, "stories": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(log), f"\nstories: {len(out)}")
    if rest and not DRY:
        if not send_batch(rest, log):
            raise RuntimeError("addStories failed for the final batch")
    elif not out and REOFFER and not DRY:
        try:      # no new story, but earlier stories still wait for images: ask for those again
            rr = requests.post(BRIDGE_URL, params={"key": BRIDGE_KEY}, data=json.dumps({"action": "reoffer", "ids": REOFFER}), timeout=180)
            print("reoffer:", rr.status_code, rr.text[:200])
        except Exception as e:
            print("reoffer failed:", e)
    elif not out and not DRY and os.environ.get("NO_NEWS_EMAIL", "") in ("1", "true", "yes"):
        # tell the owner why there is no email with prompts this time (never fails the run)
        try:
            why = "\n".join("- " + x[:170] for x in log if not x.startswith("source ")) or "- no new story this round"
            requests.post(BRIDGE_URL, params={"key": BRIDGE_KEY}, data=json.dumps({"action": "addStories", "stories": [], "no_news": why[:1500]}), timeout=120)
        except Exception as e:
            print("no-news email not sent:", e)


if __name__ == "__main__":
    main()
