"""Every-3-hours collector (free models). Fetch Namakkal news -> write posts -> validate -> send to the Apps Script bridge
(Sheet rows + ONE prompt file + ONE email). Usage: python research_free/collect.py [--dry]"""
import datetime, difflib, json, os, re, sys, time
from pathlib import Path
import requests
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import llm, sources, run, allnews

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
BRIDGE_URL, BRIDGE_KEY = os.environ.get("BRIDGE_URL", ""), os.environ.get("BRIDGE_KEY", "")
MAX_RASIPURAM = int(os.environ.get("MAX_RASIPURAM", "5"))     # Rasipuram page: up to 5 stories per round
MAX_NAMAKKAL = int(os.environ.get("MAX_NAMAKKAL", "6"))       # Namakkal page: up to 6 other district stories per round
ARCHIVE = HERE / "archive"
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


def score(n):
    """how likely readers are to open / share it: topic interest + how many outlets carry it + how fresh it is"""
    s = interest({"title": n.get("title", ""), "text": n.get("snippet", "")})
    m = n.get("mentions", 1)
    s += 2 if m >= 3 else (1 if m == 2 else 0)
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
    hard = [e for e in errors if any(h in e for h in HARD)]
    if hard:
        return None, "would be wrong/unclear: " + "; ".join(hard)[:150]
    if is_dup(art, d, recent):
        return None, "duplicate after write"
    prompts = "\n---\n".join(TEMPLATE.format(scene=s.strip()) for s in d["scenes"])
    ver = f"FREE-MODEL DRAFT ({model}) - not checked by Claude yet" + (f"; validator problems: {'; '.join(errors)}" if errors else "")
    return {"tamil_headline": d["tamil_headline"], "english_headline": d["english_headline"], "category": d["category"], "location": d["location"],
            "importance": d["importance"], "post_to": d["post_to"], "slides_spec": d["slides_spec"], "reel_script": d["reel_script"],
            "caption": d["caption"], "prompts": prompts, "source": art["url"], "published": art["published"], "verification": ver,
            "note": f"free-model draft {model}, {att} attempt(s), {len(errors)} validator problem(s)",
            "post_time": "right after your reply, same day"}, ""


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
    state = load_state()
    news = allnews.collect(log)                                   # EVERY item from every source
    for n in news:
        n["score"] = score(n)
        n["status"] = "collected"
        n["story"] = ""
    for r in recent:   # already posted/filed earlier: never write them twice
        for n in news:
            if r.get("source") and (r["source"] == n["url"] or r["source"] in n["alts"]):
                n["status"] = "already filed"
            elif n["title"] and difflib.SequenceMatcher(None, r.get("headline_ta", ""), n["title"]).ratio() > 0.6:
                n["status"] = "already filed"
    for n in news:
        st = state.get(n["key"], {})
        if st.get("s") in ("filed", "dup", "notext", "old") or st.get("n", 0) >= 3:
            n["status"] = n["status"] if n["status"] != "collected" else "checked earlier: " + st.get("s", "failed")
    queues = {"R": [], "N": []}
    for n in sorted(news, key=lambda x: -x["score"]):
        if n["status"] == "collected" and fresh(n["published"]):
            queues[n["area"]].append(n)
        elif n["status"] == "collected":
            n["status"] = "old"
    log.append(f"to write: {len(queues['R'])} Rasipuram + {len(queues['N'])} other district candidates (max {MAX_RASIPURAM} + {MAX_NAMAKKAL} stories)")
    target, done, tried = {"R": MAX_RASIPURAM, "N": MAX_NAMAKKAL}, {"R": 0, "N": 0}, {"R": 0, "N": 0}
    tries_cap = {"R": MAX_RASIPURAM * 3, "N": MAX_NAMAKKAL * 3}
    while time.time() < DEADLINE - 120:
        progressed = False
        for area in ("R", "N"):
            if done[area] >= target[area] or not queues[area] or tried[area] >= tries_cap[area]:
                continue
            n = queues[area].pop(0)
            progressed = True
            tried[area] += 1
            stt = state.setdefault(n["key"], {"n": 0})
            stt["n"] = stt.get("n", 0) + 1
            stt["t"] = datetime.datetime.now(IST).isoformat()
            try:
                url = allnews.resolve(n["url"])
                art = allnews.article_any(url)
                art["url"] = url
                art["title"] = art.get("title") or n["title"]
                art["published"] = art.get("published") or n["published"]
            except Exception as e:
                n["status"] = f"could not open the article: {str(e)[:60]}"
                continue
            if url in seen_src or any(r.get("source") == url for r in recent):
                n["status"], stt["s"] = "already filed", "dup"
                continue
            if len(art["text"]) < 150:
                n["status"], stt["s"] = "article text too short / blocked", "notext"
                continue
            if not fresh(art["published"]):
                n["status"], stt["s"] = "old", "old"
                continue
            if any(difflib.SequenceMatcher(None, r.get("headline_ta", ""), art["title"]).ratio() > 0.55 for r in recent):
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
            story["post_to"] = "Namakkal 360 + Rasipuram 360 (collab)" if area == "R" else "Namakkal 360"
            out.append(story)
            recent.append({"headline_ta": story["tamil_headline"], "source": art["url"]})
            n["status"], n["story"], stt["s"] = "filed", story["tamil_headline"], "filed"
            done[area] += 1
            for a in ("R", "N"):    # same event from another outlet / wording: never write it a second time
                keep = []
                for q in queues[a]:
                    if difflib.SequenceMatcher(None, q["title"], art["title"]).ratio() > 0.5:
                        q["status"] = "duplicate of a story filed this round"
                    else:
                        keep.append(q)
                queues[a] = keep
        if not progressed:
            break
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
    if out and not DRY:
        r = requests.post(BRIDGE_URL, params={"key": BRIDGE_KEY}, data=json.dumps({"action": "addStories", "stories": out}), timeout=180)
        print("bridge:", r.status_code, r.text[:300])
        r.raise_for_status()
    elif not out and not DRY and os.environ.get("NO_NEWS_EMAIL", "") in ("1", "true", "yes"):
        # tell the owner why there is no email with prompts this time (never fails the run)
        try:
            why = "\n".join("- " + x[:170] for x in log if not x.startswith("source ")) or "- no new story this round"
            requests.post(BRIDGE_URL, params={"key": BRIDGE_KEY}, data=json.dumps({"action": "addStories", "stories": [], "no_news": why[:1500]}), timeout=120)
        except Exception as e:
            print("no-news email not sent:", e)


if __name__ == "__main__":
    main()
