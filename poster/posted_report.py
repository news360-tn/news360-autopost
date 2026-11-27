"""owner 21 Nov ("news posted e-mail not received - I don't know whether news is posted"): ONE e-mail for ALL 8 pages, 4 times a
day (posted_report.yml: 9 AM, 1 PM, 6 PM, 10 PM IST; the watchdog starts it when GitHub skips it), through the Promo Hub - so
Gmail's daily sending limit (about 100) is never reached. For every page:
  the news posted since the last report (time, headline, Instagram link) and today's count,
  what is ready / waiting now (from the page's latest posting check),
  today's gold rate and rasipalan posts,
  any problem: Instagram paused the page, posting runs that failed.
It reads only public files of the 7 repositories (poster/posted/*.json - one tiny record per posted news, .last_check,
goldrate/state, rasipalan/state) and the posting runs list. Never prints a token.
owner 24 Nov: and ONCE a day (00:10 IST) a DAILY summary - every news posted on all pages the day before (--day).
Usage: python poster/posted_report.py [--dry] [--day]      (--dry prints the e-mail instead of sending it)"""
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
IST = timezone(timedelta(hours=5, minutes=30))
OWNER = "news360-tn"
REPOS = (("news360-autopost", ("namakkal", "rasipuram")), ("coimbatore360-autopost", ("coimbatore",)), ("salem360-autopost", ("salem",)),
         ("erode360-autopost", ("erode",)), ("karur360-autopost", ("karur",)), ("tirupur360-autopost", ("tirupur",)),
         ("trichy360-autopost", ("trichy",)))
LABEL = {"namakkal": "Namakkal 360", "rasipuram": "Rasipuram 360", "coimbatore": "Coimbatore 360", "salem": "Salem 360",
         "erode": "Erode 360", "karur": "Karur 360", "tirupur": "Tiruppur 360", "trichy": "Trichy 360"}
STATE = HERE / "report_state.json"      # when the last report was sent (committed by posted_report.yml)
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
E = html.escape


def log(*a):
    print("report:", *a, flush=True)


def _headers():
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    h = {"Accept": "application/vnd.github+json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    return h


def api(path, **params):
    r = requests.get(f"{API}/{path}", headers=_headers(), params=params, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def raw(repo, path):
    r = requests.get(f"{RAW}/{OWNER}/{repo}/main/{path}", timeout=60)
    return r.text if r.status_code == 200 else None


def ist_time(ts):
    """'09:41 PM' (IST) from an ISO time"""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(IST).strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return ts


def window(now):
    """(since, until): from the last report (at most 26 hours back) until now"""
    try:
        last = datetime.fromisoformat(json.loads(STATE.read_text(encoding="utf-8"))["last"])
        if now - last < timedelta(hours=26):
            return last, now
    except Exception:
        pass
    return now - timedelta(hours=4), now


def posted_records(repo, since, until, day_start):
    """(records in the window, {page: count today}) from poster/posted/ - a file's name starts with its UTC time"""
    items = api(f"repos/{OWNER}/{repo}/contents/poster/posted") or []
    lo, hi = since.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S"), until.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
    day = day_start.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
    got, today = [], {}
    for it in items if isinstance(items, list) else []:
        n = str(it.get("name") or "")
        parts = n.split("-")
        if not n.endswith(".json") or len(parts) < 4:
            continue
        stamp, page = n[:15], parts[2]
        if day <= stamp < hi:
            today[page] = today.get(page, 0) + 1
        if lo <= stamp < hi:
            try:
                got.append(json.loads(raw(repo, f"poster/posted/{n}") or "{}"))
            except ValueError:
                pass
    return sorted(got, key=lambda x: x.get("at", "")), today


def check_status(repo, pages):
    """what the page's latest posting check said: ready now, why news waits, Instagram pause"""
    t = raw(repo, ".last_check") or ""
    m = re.search(r"(\d+) stories in the queue, ready to post: (\d+)", t)
    ready = int(m.group(2)) if m else None
    dups = len(re.findall(r"skipped: already on Instagram", t))
    out = {"ready": None if ready is None else max(0, ready - dups), "waits": {}, "paused": {}, "quota": {}}
    for w in re.findall(r"RN-\d+ waits(?: for)?:? ([^\n]*)", t):
        k = re.sub(r"\s+on \[.*$", "", w).strip()[:60]
        out["waits"][k] = out["waits"].get(k, 0) + 1
    for pg in pages:
        p = re.search(rf"([^\n]*?) on {pg} - paused until (\S+) UTC", t)
        if p:
            why = re.sub(r"^\d\d:\d\d:\d\d\s+", "", p.group(1)).replace("story catch-up " + pg + " waits: ", "").strip()
            out["paused"][pg] = f"{why} - paused until {ist_time(p.group(2) + '+00:00')}"
        q = re.search(rf"publishing quota {pg}: (\d+)/(\d+)", t)
        if q:
            out["quota"][pg] = f"{q.group(1)}/{q.group(2)}"
    return out


def daily_jobs(repo, pg, today):
    """today's gold rate and rasipalan post: 'posted' / 'not yet' / '' (the page has no such post)"""
    res = {}
    for key, path in (("gold", f"goldrate/state/posted_{pg}.json"), ("rasipalan", f"rasipalan/state/{pg}.json")):
        t = raw(repo, path)
        if t is None:
            res[key] = ""
            continue
        try:
            res[key] = "posted" if json.loads(t).get("date") == today else "not yet"
        except ValueError:
            res[key] = "?"
    return res


def failed_runs(repo, since, until=None):
    f = "%Y-%m-%dT%H:%M:%SZ"
    try:
        created = (since.astimezone(timezone.utc).strftime(f) + ".." + until.astimezone(timezone.utc).strftime(f)) if until \
            else ">=" + since.astimezone(timezone.utc).strftime(f)      # owner 24 Nov: the daily summary counts only that day
        d = api(f"repos/{OWNER}/{repo}/actions/workflows/post.yml/runs", status="failure", created=created, per_page=1) or {}
        return int(d.get("total_count") or 0)
    except Exception as e:
        log(repo, "runs not read:", str(e)[:120])
        return 0


def day_window(now):
    """owner 24 Nov: (since, until) = the whole IST day before now (00:00 - 24:00)"""
    end = now.astimezone(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    return end - timedelta(days=1), end


def collect(now, span=None):
    since, until = span or window(now)
    day_start = (until - timedelta(seconds=1)).astimezone(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    today = day_start.strftime("%Y-%m-%d")
    pages = []
    for repo, pgs in REPOS:
        try:
            recs, counts = posted_records(repo, since, until, day_start)
        except Exception as e:
            log(repo, "posted news not read:", str(e)[:150])
            recs, counts = None, {}
        st = check_status(repo, pgs)
        fails = failed_runs(repo, since, until if span else None)
        for i, pg in enumerate(pgs):
            problems = []
            if st["paused"].get(pg):
                problems.append(st["paused"][pg])
            if fails and i == 0:
                problems.append(f"{fails} posting run(s) failed")
            if recs is None:
                problems.append("posted list not readable")
            pages.append({"page": pg, "label": LABEL.get(pg, pg), "posted": [r for r in recs or [] if r.get("page") == pg],
                          "today": counts.get(pg, 0), "ready": st["ready"] if i == 0 else None, "waits": st["waits"] if i == 0 else {},
                          "quota": st["quota"].get(pg, ""), "problems": problems,
                          **(daily_jobs(repo, pg, today) if not span else {"gold": "", "rasipalan": ""}),      # the state files keep only the latest day
                          "shared": len(pgs) > 1})
    return since, until, pages


def email(since, until, pages, daily=False):
    total = sum(len(p["posted"]) for p in pages)
    day_total = sum(p["today"] for p in pages)
    problems = [(p["label"], x) for p in pages for x in p["problems"]]
    span = f"{since.astimezone(IST):%I:%M %p}".lstrip("0") + " - " + f"{until.astimezone(IST):%I:%M %p}".lstrip("0")
    subject = (f"[News 360 REPORT] {until.astimezone(IST):%d %b %I:%M %p} - {total} news posted since the last report"
               + (f" - {len(problems)} problem(s)" if problems else ""))
    if daily:      # owner 24 Nov: one e-mail with the whole day
        subject = f"[News 360 DAILY] {since.astimezone(IST):%d %b %Y} - {total} news posted on all pages"
        span = f"{since.astimezone(IST):%d %b %Y} (whole day)"
    text = [subject, f"{span}: {total} news posted. Today so far: {day_total} on all pages.", ""]
    rows, blocks = [], []
    for p in pages:
        ready = "-" if p["ready"] is None else str(p["ready"]) + (" (both pages)" if p["shared"] else "")
        waits = "; ".join(f"{n} {k}" for k, n in sorted(p["waits"].items(), key=lambda kv: -kv[1])[:2])
        prob = "; ".join(p["problems"]) or "OK"
        colour = "#c62828" if p["problems"] else "#2e7d32"
        rows.append(f"<tr><td style='padding:6px;border:1px solid #ddd'><b>{E(p['label'])}</b></td>"
                    f"<td style='padding:6px;border:1px solid #ddd;text-align:center'><b>{len(p['posted'])}</b></td>"
                    f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{p['today']}</td>"
                    f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{E(ready)}"
                    f"{'<br><small>' + E(waits) + '</small>' if waits else ''}</td>"
                    f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{E(p['gold'] or '-')}</td>"
                    f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{E(p['rasipalan'] or '-')}</td>"
                    f"<td style='padding:6px;border:1px solid #ddd;color:{colour}'>{E(prob)}</td></tr>")
        text.append(f"{p['label']}: {len(p['posted'])} posted now, {p['today']} today, ready {ready}"
                    f"{' (' + waits + ')' if waits else ''}, gold {p['gold'] or '-'}, rasipalan {p['rasipalan'] or '-'} - {prob}")
        if p["posted"]:
            items = "".join(f"<li style='margin:4px 0'>{E(ist_time(r.get('at', '')))} - {E(r.get('headline') or r.get('story') or '')}"
                            f"{' - <a href=' + chr(39) + E(r['link']) + chr(39) + '>Instagram</a>' if r.get('link') else ''}</li>"
                            for r in p["posted"])
            blocks.append(f"<h3 style='margin:16px 0 4px'>{E(p['label'])} - {len(p['posted'])} posted</h3><ul style='margin:0'>{items}</ul>")
            text += [f"   {ist_time(r.get('at', ''))}  {r.get('headline') or r.get('story')}  {r.get('link') or ''}" for r in p["posted"]]
    head = ("<tr>" + "".join(f"<th style='padding:6px;border:1px solid #ddd;background:#f3f3f3'>{h}</th>" for h in
                             ("Page", "Posted now", "Today", "Ready now", "Gold rate", "Rasipalan", "Problem")) + "</tr>")
    probs = ("<div style='background:#fdecea;border:1px solid #f5c2c0;border-radius:8px;padding:10px;margin:10px 0'><b>Problems:</b><br>"
             + "<br>".join(f"{E(a)}: {E(b)}" for a, b in problems) + "</div>") if problems else ""
    html_body = (f"<div style='font-family:Arial,sans-serif'><h2 style='margin:0'>News 360 - posted report</h2>"
                 f"<p style='margin:6px 0'>{E(span)}: <b>{total}</b> news posted. Today so far: <b>{day_total}</b> on all pages.</p>{probs}"
                 f"<table style='border-collapse:collapse;font-size:14px'>{head}{''.join(rows)}</table>{''.join(blocks)}"
                 + ("<p style='color:#888;font-size:12px'>Daily summary: every news posted that day on all pages. 'Posted now' and "
                    "'Today' = that day. 'Ready now' = news waiting in the page's latest posting check.</p></div>" if daily else
                    "<p style='color:#888;font-size:12px'>One report for all pages at 9 AM, 1 PM, 6 PM and 10 PM. 'Posted now' = since the "
                    "last report. 'Ready now' = news ready in the page's latest posting check.</p></div>"))
    return subject, "\n".join(text), html_body


def main(dry=False, daily=False):
    now = datetime.now(timezone.utc)
    since, until, pages = collect(now, day_window(now) if daily else None)
    subject, text, html_body = email(since, until, pages, daily)
    if dry:
        print(subject + "\n" + text)
        return
    import promo
    if not promo.enabled():
        log("not sent (PROMO_URL / PROMO_KEY not set)\n" + text)
        return
    promo.hub_post("digest", {"subject": subject, "text": text, "html": html_body})
    if daily:      # the daily summary never moves the 4-a-day report's window
        log("sent:", subject)
        return
    STATE.write_text(json.dumps({"last": until.isoformat(timespec="seconds")}, indent=1), encoding="utf-8")
    log("sent:", subject)


if __name__ == "__main__":
    main("--dry" in sys.argv, "--day" in sys.argv)
