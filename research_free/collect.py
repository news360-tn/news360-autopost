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
MAX_STORIES = int(os.environ.get("MAX_STORIES", "5"))
DRY = "--dry" in sys.argv
DEADLINE = time.time() + int(os.environ.get("BUDGET_MIN", "22")) * 60
llm.DEADLINE[0] = DEADLINE

TEMPLATE = ("Ultra-sharp photorealistic documentary-style news photo, tall vertical 9:16 portrait (1080x1920 or larger, highest resolution), "
            "4K photographic clarity, crisp fine detail, natural lighting, no blur, no plastic or over-smoothed look. {scene} "
            "Natural colours, realistic light, sharp detail, modern news-photography look. STRICT: no text, letters, numbers, signboard writing, logos or watermarks anywhere in the image; "
            "no recognisable real person, politician or celebrity face (show people only from behind, far away or blurred); no blood, injuries or dead bodies. "
            "Keep the top-right corner and the lower third of the image visually simple (sky, road, wall, field) because Tamil text will be placed there.")


def bridge(action, **kw):
    r = requests.get(BRIDGE_URL, params={"action": action, "key": BRIDGE_KEY, **kw}, timeout=120)
    r.raise_for_status()
    return r.json()


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
    for u in sources.candidate_links(20):
        if len(arts) >= MAX_STORIES + 2:
            break
        if u in seen_src:
            continue
        try:
            art = sources.article(u)
        except Exception as e:
            log.append(f"fetch failed {u}: {e}")
            continue
        if not fresh(art["published"]) or len(art["text"]) < 150:
            log.append(f"skip (old/short) {art['title'][:50]}")
            continue
        if any(difflib.SequenceMatcher(None, r.get("headline_ta", ""), art["title"]).ratio() > 0.72 for r in recent):
            log.append(f"skip (already filed) {art['title'][:50]}")
            continue
        arts.append(art)
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
        d, model, errors, att = res
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
