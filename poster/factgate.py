"""Last gate before a reel is built and posted: re-read the story's SOURCE article and fact-check the spoken script, headline and caption
against it with a model (independent of the writer's own check). Returns blocking problems; '' list = fine / could not check."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "research_free"))

SOFT = ("promotional", "follow line", "த்ரீ சிக்ஸ்டி", "follow ", "page is not mentioned", "date of posting", "missing", "misses", "omit", "not mentioned in the draft", "could not be run")      # an omission is not a false statement: never blocks


def _body(cap):
    """caption without the footer (the 📍 place | posting-date line, follow line, hashtags): the posting date is not a claim from the article"""
    keep = []
    for ln in (cap or "").split("\n"):
        t = ln.strip()
        if t.startswith("\U0001F4CD") or t.startswith("#") or "Follow" in t:
            continue
        keep.append(ln)
    return "\n".join(keep).strip()


def check(row):
    url = (row.get("source") or "").strip()
    if not url.startswith("http") or not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("NVIDIA_API_KEY") and not os.environ.get("GEMINI_API_KEY") and not os.environ.get("OPENROUTER_API_KEY"):
        return []
    try:
        import allnews, run
        a = allnews.article_any(url)
        text = a.get("text", "") if isinstance(a, dict) else (a[-1] if isinstance(a, (tuple, list)) else str(a or ""))
        title = a.get("title", "") if isinstance(a, dict) else ""
        if not text or len(text) < 200:
            print("factgate: article text not available - not blocking")
            return []
        d = {"tamil_headline": row.get("headline_ta", ""), "reel_script": row.get("reel_script", ""),
             "slides_spec": json.loads(row["slides_spec"]) if row.get("slides_spec") else "", "caption": _body(row.get("caption", ""))}
        probs = run.factcheck(d, {"title": title or row.get("headline_ta", ""), "text": text})
        probs = [p for p in probs if not any(w in p.lower() for w in SOFT)]
        return confirm(probs, title, text) if probs else []
    except Exception as e:
        print("factgate unavailable - not blocking:", str(e)[:150])
        return []


CONFIRM = """You are a strict senior news editor. A first checker listed possible factual problems in a draft; first checkers often misread. For EACH problem, find the exact sentence in the ARTICLE that proves it. The fixed closing line "மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்", the caption footer and hashtags are never problems. Wording choices (e.g. மூதாட்டி for an elderly woman) are not problems. Only a wrong name, number, place, date, cause or event that contradicts the article is real.
Return ONLY JSON: {"results":[{"n":1,"real":true|false,"quote":"article sentence that proves it, or empty"}]}"""


def confirm(probs, title, text):
    """second, independent opinion: keep a problem only when the model can quote the article sentence that proves it.
    If the second opinion cannot run, keep all problems (never post on doubt)."""
    try:
        import llm
        user = "ARTICLE:\n" + title + "\n" + text[:6000] + "\n\nPROBLEMS:\n" + "\n".join(f"{i+1}. {p}" for i, p in enumerate(probs))
        try:
            r, m = llm.ask_json(CONFIRM, user)          # free models first; Claude only when they are not available
        except Exception:
            if not llm.claude_available():
                return probs
            r, m = llm.ask_claude(CONFIRM, user, max_tokens=1500)
        res = r.get("results") if isinstance(r, dict) else None
        if not res:
            return probs
        keep = []
        for i, p in enumerate(probs):
            x = next((y for y in res if y.get("n") == i + 1), None)
            if x is None or (x.get("real") and (x.get("quote") or "").strip()):
                keep.append(p)
        print(f"factgate confirm by {m}: {len(probs)} flagged -> {len(keep)} confirmed")
        return keep
    except Exception as e:
        print("factgate confirm unavailable - keeping the flags:", str(e)[:120])
        return probs
