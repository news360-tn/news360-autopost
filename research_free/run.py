"""Test runner. python research_free/run.py URL [URL...]   -> writes research_free/results/<n>.json (+ report). Never touches the live Sheet."""
import json, sys, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import llm, sources
from validate import validate

SYSTEM = (HERE / "rules.md").read_text(encoding="utf-8")
EX = json.loads((HERE / "examples.json").read_text(encoding="utf-8"))
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def prompt(art, today, errors=None):
    shots = "\n\n".join(f"EXAMPLE ARTICLE:\n{e['article']}\nEXAMPLE OUTPUT:\n{json.dumps(e['output'], ensure_ascii=False)}" for e in EX)
    u = f"{shots}\n\nTODAY (IST): {today}\n\nNOW WRITE THE OUTPUT FOR THIS ARTICLE (facts only from this text):\nHEADLINE: {art['title']}\nPUBLISHED: {art['published']}\nARTICLE:\n{art['text'][:6000]}"
    try:
        import learned
        h = learned.hints()
        if h:
            u += "\n\nLEARNED FROM OUR INSTAGRAM INSIGHTS (style only; facts still only from the article):\n" + h
    except Exception:
        pass
    if errors:
        u += "\n\nYOUR PREVIOUS ANSWER HAD THESE PROBLEMS. Fix all of them and return the full JSON again:\n- " + "\n- ".join(errors)
    return u


def _obj(d):
    """some free models wrap the answer in a list; accept [ {...} ], reject anything that is not an object"""
    if isinstance(d, list) and d and isinstance(d[0], dict):
        d = d[0]
    if not isinstance(d, dict):
        raise ValueError("model answer was not a JSON object")
    return d


MAX_ATTEMPTS = 10      # owner: a wrong draft is rewritten up to 10 times (with the exact problems listed) before the story is dropped; the round time budget still applies


def write(art, today):
    errors, best = None, None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        d, model = llm.ask_json(SYSTEM, prompt(art, today, errors))
        try:
            d = _obj(d)
        except ValueError as e:
            errors = [str(e)]
            print(f"attempt {attempt} {model}: {e}")
            continue
        errors = validate(d, art["text"] + " " + art["title"])
        if not errors:
            errors = factcheck(d, art)
        print(f"attempt {attempt} {model}: {len(errors)} problems", *errors, sep="\n  ")
        if best is None or len(errors) <= len(best[2]):      # keep the draft with the fewest problems
            best = (d, model, errors, attempt)
        if not errors:
            break
    if best is None:
        raise RuntimeError("no usable answer from the free models")
    return proofread(best, art)


CHECK = """You are a strict fact-checker for a Tamil local-news page. You get an ARTICLE and a DRAFT (JSON with Tamil text).
Check EVERY claim in the draft's tamil_headline, reel_script, slides_spec and caption against the ARTICLE.
Report a problem for each of these: a place, person role, number, amount, date, time or cause that is NOT in the article or differs from it; an invented detail; a sentence that is ungrammatical or has no clear meaning in Tamil; two different facts mixed into one sentence; an important fact of the article (who did what, where, result such as an arrest) that is missing from the reel_script.
Return ONLY JSON: {"ok": true or false, "problems": ["short English description of each problem"]}. ok is true ONLY when the problems list is empty."""


def factcheck(d, art):
    """independent second call: compares the draft with the article. Returns a list of problems."""
    try:
        r, m = llm.ask_json(CHECK, "ARTICLE:\n" + art["title"] + "\n" + art["text"][:6000] + "\n\nDRAFT:\n" + json.dumps(
            {k: d.get(k) for k in ("tamil_headline", "reel_script", "slides_spec", "caption")}, ensure_ascii=False))
        r = _obj(r)
        probs = [str(x) for x in (r.get("problems") or [])]
        if r.get("ok") is False and not probs:
            probs = ["fact-checker rejected the draft"]
        print(f"factcheck by {m}: {len(probs)} problems", *probs, sep="\n  ")
        return ["fact-check: " + x for x in probs]
    except Exception as e:
        print("factcheck unavailable:", e)
        return ["fact-check: could not be run"]


PROOF = """You are a senior Tamil news editor and proofreader for the Instagram page "நாமக்கல் 360".
You get a JSON draft. Return the SAME JSON object (same keys, same structure, same facts, same numbers) with ONLY these fixes:
1. Correct Tamil spelling, sandhi (புணர்ச்சி), grammar and place names in every Tamil text.
2. reel_script: make it read like ONE continuous story by a professional Tamil TV news reader: smooth connecting words between sentences (மேலும், இதனால், இதையடுத்து, இந்நிலையில்), no abrupt jumps, no repeated facts, first sentence = the hook. Keep it 4-6 sentences, 38-55 words, numbers as Tamil words, no digits, no English letters. English words that people say in Tamil must be written in Tamil script so a Tamil voice pronounces them (மொபைல், ஆன்லைன், பஸ்). Keep the last sentence exactly: மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.
3. slides_spec texts and caption: natural modern Tamil, no half-English sentences except fixed words (Follow, Share, Save). Keep the character limits (hl1 40, hl2 28, title 18, lines 60).
Never add facts. Never remove the follow line or hashtags. Output ONLY the JSON object."""


def proofread(best, art):
    """second free-model pass: Tamil grammar/spelling, smooth news-reader flow. Kept only if it still passes every check."""
    d, model, errors, att = best
    try:
        fixed, m2 = llm.ask_json(PROOF, json.dumps(d, ensure_ascii=False))
        fixed = _obj(fixed)
        e2 = validate(fixed, art["text"] + " " + art["title"])
        if not e2 and not errors:
            e2 = factcheck(fixed, art)
        if len(e2) <= len(errors) and set(fixed) >= set(d):
            print(f"proofread by {m2}: {len(e2)} problems")
            return fixed, model + " + proofread " + m2, e2, att
        print(f"proofread rejected ({len(e2)} problems)", *e2, sep="\n  ")
    except Exception as e:
        print("proofread skipped:", e)
    return best


def main(urls):
    today = datetime.datetime.now(IST).strftime("%A %d %B %Y")
    rep = []
    for n, u in enumerate(urls, 1):
        try:
            art = sources.article(u)
            d, model, errors, att = write(art, today)
        except Exception as e:
            rep.append(f"{n}. FAILED {u}: {type(e).__name__}: {str(e)[:300]}")
            continue
        (HERE / "results" / f"{n}.json").write_text(json.dumps({"url": u, "article": art, "model": model, "attempts": att, "problems": errors, "draft": d}, ensure_ascii=False, indent=1), encoding="utf-8")
        rep.append(f"{n}. {art['title'][:70]} | {model} | attempts {att} | problems {len(errors)}")
    (HERE / "results" / "report.txt").write_text("\n".join(rep) + "\n\n" + "\n".join(llm.LOG), encoding="utf-8")
    print("\n".join(rep))


if __name__ == "__main__":
    main(sys.argv[1:])
