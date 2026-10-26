"""Last Tamil proofread before a reel is built: spelling, sandhi (புணர்ச்சி), grammar and unclear sentences in everything that goes out
(headline, slide texts shown in the reel, the spoken script, the caption). Free models first, Claude only when they are not available.
Only exact, small corrections are applied; a correction that changes a number, or makes broken Tamil, is ignored."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "research_free"))

PROOF = """You are a senior Tamil news editor and proofreader. You get the texts of ONE Tamil news post as JSON.
Find every real mistake: wrong spelling, wrong sandhi (புணர்ச்சி, e.g. missing க்/ச்/த்/ப் doubling), wrong case ending, wrong verb or
plural agreement, a word that does not exist, a broken or unclear sentence, a sentence that mixes two facts, spoken/colloquial forms in the
news text (இருக்கு -> உள்ளது), and English words written in English letters inside Tamil text.
For each mistake give the EXACT wrong text as it appears (a few words, copied character by character) and the corrected text.
STRICT: never change a number, date, time, amount, name, place or fact; never add information; do not rewrite text that is already correct;
keep the closing follow line and hashtags as they are. If everything is correct, return an empty list.
Return ONLY JSON: {"fixes": [{"wrong": "exact text", "right": "corrected text", "why": "short reason"}]}"""

FIELDS = ("headline_ta", "reel_script", "caption")


def _texts(row):
    spec = json.loads(row.get("slides_spec") or "{}")
    slides = [{"title": s.get("title", ""), "lines": s.get("lines", [])} for s in spec.get("slides", [])]
    return {"headline_ta": row.get("headline_ta", ""), "hl1": spec.get("hl1", ""), "hl2": spec.get("hl2", ""), "slides": slides,
            "reel_script": row.get("reel_script", ""), "caption": (row.get("caption") or "").split("#")[0].strip()}


def _digits(t):
    return re.findall(r"\d+", t or "")


def proofread(row, log=print):
    """corrects row in place; returns the number of corrections applied"""
    import llm, verify
    user = json.dumps(_texts(row), ensure_ascii=False)
    try:
        try:
            r, m = llm.ask_json(PROOF, user)
        except Exception:
            if not llm.claude_available():
                raise
            r, m = llm.ask_claude(PROOF, user, max_tokens=3000)
    except Exception as e:
        log("Tamil proofread unavailable (posting goes on):", str(e)[:150])
        return 0
    fixes = (r or {}).get("fixes") if isinstance(r, dict) else None
    if not fixes:
        log(f"Tamil proofread by {m}: no mistakes found")
        return 0
    spec = row.get("slides_spec") or ""
    done = 0
    for f in fixes[:25]:
        w, ok = str(f.get("wrong") or ""), str(f.get("right") or "")
        if not w or not ok or w == ok or len(w) < 2:
            continue
        if _digits(w) != _digits(ok) or len(ok) > 2 * len(w) + 12:      # a number changed, or a rewrite instead of a correction
            log("proofread fix ignored (would change a number / too big):", w[:40], "->", ok[:40])
            continue
        if verify.tamil_sequence_problems(ok):
            continue
        hit = False
        for k in FIELDS:
            if w in (row.get(k) or ""):
                row[k] = row[k].replace(w, ok)
                hit = True
        if w in spec:
            spec = spec.replace(json.dumps(w, ensure_ascii=False)[1:-1], json.dumps(ok, ensure_ascii=False)[1:-1])
            hit = True
        if hit:
            done += 1
            log(f"Tamil fix: «{w}» -> «{ok}» ({str(f.get('why', ''))[:60]})")
    try:
        json.loads(spec)
        row["slides_spec"] = spec
    except Exception:
        log("proofread fixes in the slide texts skipped (would break the format)")
    log(f"Tamil proofread by {m}: {done} of {len(fixes)} corrections applied")
    return done
