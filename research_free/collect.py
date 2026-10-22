"""Every-3-hours collector (free models). Fetch Namakkal news -> write posts -> validate -> send to the Apps Script bridge
(Sheet rows + ONE prompt file + ONE email). Usage: python research_free/collect.py [--dry]"""
import datetime, difflib, json, os, re, sys, time
from pathlib import Path
import requests
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import llm, sources, run

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
BRIDGE_URL, BRIDGE_KEY = os.environ.get("BRIDGE_URL", ""), os.environ.get("BRIDGE_KEY", "")
MAX_STORIES = int(os.environ.get("MAX_STORIES", "8"))
DRY = "--dry" in sys.argv
DEADLINE = time.time() + int(os.environ.get("BUDGET_MIN", "22")) * 60
llm.DEADLINE[0] = DEADLINE

TEMPLATE = ("ONE single continuous photograph from one camera angle (not a collage, grid, strips or panels). Ultra-sharp photorealistic documentary-style news photo, tall vertical portrait (9:16 if possible, highest resolution), "
            "MAXIMUM CLARITY: 4K, tack-sharp focus across the whole frame, deep depth of field, shot like a professional full-frame camera with a 35mm lens at f/8, crisp fine detail and edges, clean noise-free image, balanced high dynamic range, natural lighting; no blur, no soft focus, no motion blur, no haze, no painterly, plastic or over-smoothed AI look. {scene} "
            "Natural colours, realistic light, sharp detail, modern news-photography look. STRICT: no text, letters, numbers, signboard writing, logos or watermarks anywhere in the image; "
            "no recognisable real person, politician or celebrity face (show people only from behind, far away or blurred); no blood, injuries or dead bodies. "
            "Keep the top-right corner and the lower third of the image visually simple (sky, road, wall, field) because Tamil text will be placed there.")


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


def fresh(published):
    try:
        d = datetime.datetime.fromisoformat(published).astimezone(IST).date()
    except Exception:
        return True
    return d >= (datetime.datetime.now(IST).date() - datetime.timedelta(days=1))


def is_dup(art, d, recent):
    for r in recent:
        if r.get("source") and r["source"] == art["url"]:
            return True
        if difflib.SequenceMatcher(None, r.get("headline_ta", ""), (d or {}).get("tamil_headline", art["title"])).ratio() > 0.72:
            return True
    return False


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
    today = datetime.datetime.now(IST).strftime("%A %d %B %Y")
    out, log = [], []
    arts = []
    arts = []
    all_links = sources.candidate_links(40)
    links = [u for u in all_links if u not in seen_src]
    log.append(f"links on the news list: {len(all_links)}, not yet filed: {len(links)}")
    from concurrent.futures import ThreadPoolExecutor as _TPE

    def _fetch(u):
        try:
            return u, sources.article(u), None
        except Exception as e:
            return u, None, e
    with _TPE(max_workers=6) as ex0:
        fetched = list(ex0.map(_fetch, links))
    for u, art, e in fetched:
        if e is not None:
            log.append(f"fetch failed {u}: {e}")
            continue
        if not fresh(art["published"]) or len(art["text"]) < 150:
            log.append(f"skip (old/short) {art['title'][:50]}")
            continue
        if any(difflib.SequenceMatcher(None, r.get("headline_ta", ""), art["title"]).ratio() > 0.72 for r in recent):
            log.append(f"skip (already filed) {art['title'][:50]}")
            continue
        art["interest"] = interest(art)
        arts.append(art)
    arts.sort(key=lambda a: -a["interest"])            # stable: site order (newest first) inside the same score
    log.append("picked by interest: " + "; ".join(f"{a['interest']}:{a['title'][:30]}" for a in arts[:MAX_STORIES]))
    arts = arts[:MAX_STORIES]

    def work(art):
        print(f"writing: {art['title'][:60]}", flush=True)
        try:
            return art, run.write(art, today)
        except Exception as e:
            return art, e
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(work, arts))
    for art, res in results:
        if isinstance(res, Exception):
            log.append(f"all free models failed for {art['title'][:50]}: {res}")
            continue
        try:
            d, model, errors, att = res
            d["scenes"], d["tamil_headline"]
        except Exception as e:
            log.append(f"bad draft skipped for {art['title'][:50]}: {e}")
            continue
        if is_dup(art, d, recent):
            log.append(f"skip (duplicate after write) {art['title'][:50]}")
            continue
        scenes = d["scenes"]
        prompts = "\n---\n".join(TEMPLATE.format(scene=s.strip()) for s in scenes)
        ver = f"FREE-MODEL DRAFT ({model}) - not checked by Claude yet" + (f"; validator problems: {'; '.join(errors)}" if errors else "")
        out.append({"tamil_headline": d["tamil_headline"], "english_headline": d["english_headline"], "category": d["category"], "location": d["location"],
                    "importance": d["importance"], "post_to": d["post_to"], "slides_spec": d["slides_spec"], "reel_script": d["reel_script"],
                    "caption": d["caption"], "prompts": prompts, "source": art["url"], "published": art["published"], "verification": ver,
                    "note": f"free-model draft {model}, {att} attempt(s), {len(errors)} validator problem(s)",
                    "post_time": "right after your reply, same day"})
        recent.append({"headline_ta": d["tamil_headline"], "source": art["url"]})
    Path(HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "collect.json").write_text(json.dumps({"log": log, "llm": llm.LOG, "stories": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(log), f"\nstories: {len(out)}")
    if out and not DRY:
        r = requests.post(BRIDGE_URL, params={"key": BRIDGE_KEY}, data=json.dumps({"action": "addStories", "stories": out}), timeout=180)
        print("bridge:", r.status_code, r.text[:300])
        r.raise_for_status()


if __name__ == "__main__":
    main()
