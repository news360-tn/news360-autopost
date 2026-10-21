"""Test runner. python research_free/run.py URL [URL...]   -> writes research_free/out/<n>.json (+ report). Never touches the live Sheet."""
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
    if errors:
        u += "\n\nYOUR PREVIOUS ANSWER HAD THESE PROBLEMS. Fix all of them and return the full JSON again:\n- " + "\n- ".join(errors)
    return u


def write(art, today):
    errors, best = None, None
    for attempt in range(1, 4):
        d, model = llm.ask_json(SYSTEM, prompt(art, today, errors))
        errors = validate(d, art["text"] + " " + art["title"])
        print(f"attempt {attempt} {model}: {len(errors)} problems", *errors, sep="\n  ")
        best = (d, model, errors, attempt)
        if not errors:
            break
    return best


def main(urls):
    today = datetime.datetime.now(IST).strftime("%A %d %B %Y")
    rep = []
    for n, u in enumerate(urls, 1):
        art = sources.article(u)
        d, model, errors, att = write(art, today)
        (HERE / "out" / f"{n}.json").write_text(json.dumps({"url": u, "article": art, "model": model, "attempts": att, "problems": errors, "draft": d}, ensure_ascii=False, indent=1), encoding="utf-8")
        rep.append(f"{n}. {art['title'][:70]} | {model} | attempts {att} | problems {len(errors)}")
    (HERE / "out" / "report.txt").write_text("\n".join(rep) + "\n\n" + "\n".join(llm.LOG), encoding="utf-8")
    print("\n".join(rep))


if __name__ == "__main__":
    main(sys.argv[1:])
