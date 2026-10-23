"""Re-write stories whose first version was wrong/deleted, from the SOURCE article, with the current quality gates (10 tries + fact-check + proofread).
The images already exist, so the story must fit exactly that many images (slides = images - 1, scenes = images). Output: results/rewrite.json (only clean drafts)."""
import json, sys, pathlib, datetime
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "poster"))
import allnews, run, freshness

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
today = datetime.datetime.now(IST).strftime("%A %d %B %Y")
out = {}
for it in json.load(open(HERE / "rewrite_input.json", encoding="utf-8")):
    sid, n = it["id"], int(it["images"])
    try:
        a = allnews.article_any(it["url"])
        art = a if isinstance(a, dict) else {"title": "", "text": str(a)}
        art.setdefault("published", it.get("published", ""))
        run.EXTRA[0] = (f"IMPORTANT: this story already has exactly {n} images. slides_spec.slides must have exactly {n - 1} items and scenes must have exactly {n} items. "
                        "Use ONLY facts that are in the article; copy every place name, number and amount exactly as written there.")
        d, model, errors, att = run.write(art, today)
        why = freshness.stale_reason(d.get("tamil_headline", ""), d.get("english_headline", ""), d.get("category", ""), art.get("published", ""))
        if why:
            errors = errors + ["stale: " + why]
        if len((d.get("slides_spec") or {}).get("slides", [])) != n - 1:
            errors = errors + [f"slides must be {n - 1}"]
        d["slides_spec"]["v"] = 3
        out[sid] = {"ok": not errors, "problems": errors, "model": model, "attempts": att, "draft": d}
        print(sid, "OK" if not errors else "REJECTED", errors, flush=True)
    except Exception as e:
        out[sid] = {"ok": False, "problems": ["failed: " + str(e)[:200]]}
        print(sid, "FAILED", e, flush=True)
(HERE / "results").mkdir(exist_ok=True)
json.dump(out, open(HERE / "results" / "rewrite.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
