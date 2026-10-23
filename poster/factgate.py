"""Last gate before a reel is built and posted: re-read the story's SOURCE article and fact-check the spoken script, headline and caption
against it with a model (independent of the writer's own check). Returns blocking problems; '' list = fine / could not check."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "research_free"))

SOFT = ("missing", "misses", "omit", "not mentioned in the draft", "could not be run")      # an omission is not a false statement: never blocks


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
        return [p for p in probs if not any(w in p.lower() for w in SOFT)]
    except Exception as e:
        print("factgate unavailable - not blocking:", str(e)[:150])
        return []
