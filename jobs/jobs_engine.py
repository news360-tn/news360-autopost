"""owner 26 Nov: the DISTRICT JOBS lane - what may be posted. Pure rules + the official-source fetch + the extractor; no posting here.

The lane posts a job ONLY when ALL of these hold (owner decisions 26 Nov):
  1. it comes from an OFFICIAL source the owner confirmed for that district (jobs/sources/<page>.json, confirmed:true, official host)
  2. it is for THIS district (the notice names the district / one of its towns, or the source is the district's own site)
  3. it has every required field: post name, qualification, last date (or event date), where to apply, official link - and each of them,
     and every date and number, is found in the fetched official text (fact gate)
  4. it is still OPEN (last date not passed)
  5. it is NEW (published / first seen within new_within_days) or UPCOMING (recruitment / exam / job camp within upcoming_event_days)
  6. it was not posted before (one "last date near" reminder is allowed only for a notice this lane already posted, and only while open)
No match -> no post that day. Never old jobs, never other districts, never filler."""
import hashlib
import json
import re
import sys
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lanes"))
import lane_factgate as factgate  # noqa: E402

REQUIRED = ("post", "qualification", "apply_where", "link")
UA = {"User-Agent": "Mozilla/5.0 (compatible; News360-jobs/1.0)"}


# ---------- sources ----------
def load_sources(page, allow_unconfirmed=False, root=ROOT):
    try:
        d = json.loads((Path(root) / "jobs" / "sources" / f"{page}.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    return [s for s in d.get("sources", []) if s.get("confirmed") or allow_unconfirmed]


def official_host(url, allowed):
    host = (urlparse(url).hostname or "").lower()
    return any(host == a or host.endswith("." + a) for a in allowed)


class _Text(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base, self.out, self.skip, self.links, self._href = base, [], 0, [], None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        if tag == "a":
            self._href = dict(attrs).get("href")
        if tag in ("br", "p", "tr", "li", "div", "h1", "h2", "h3", "td", "th", "a", "span", "dt", "dd"):
            self.out.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)
        if tag in ("a", "td", "th", "span"):
            self.out.append(" ")
        if tag == "a":
            self._href = None

    def handle_data(self, data):
        if self.skip:
            return
        self.out.append(data)
        if self._href:
            self.links.append((urljoin(self.base, self._href), data.strip()))


def html_to_text(html, base=""):
    """-> (visible text, [(absolute link, anchor text)])"""
    p = _Text(base)
    p.feed(html or "")
    return re.sub(r"\s+", " ", "".join(p.out)).strip(), p.links


def fetch_source(src, get, max_chars=60000, max_pdfs=3):
    """-> (text, links) of the page + the text of up to max_pdfs linked PDF notices (when pypdf exists). `get` = requests.get-like."""
    r = get(src["url"], headers=UA, timeout=40)
    if getattr(r, "status_code", 200) != 200:
        raise RuntimeError(f"{src['url']} answered {r.status_code}")
    text, links = html_to_text(r.text, src["url"])
    pdfs = [u for u, _ in links if u.lower().split("?")[0].endswith(".pdf")][:max_pdfs]
    for u in pdfs:
        try:
            pr = get(u, headers=UA, timeout=60)
            if pr.status_code == 200 and len(pr.content) < 8_000_000:
                import io
                from pypdf import PdfReader
                txt = " ".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(pr.content)).pages[:6])
                text += f" [PDF {u}] " + re.sub(r"\s+", " ", txt)
        except Exception:
            continue
    return text[:max_chars], links


# ---------- extraction (writer model) ----------
SYSTEM = """You read the text of an OFFICIAL Tamil Nadu government web page and list job / recruitment / job-camp notices.
Return ONLY JSON: {"jobs": [{"title": "...", "post": "name of the post(s), copied exactly", "vacancies": "number or empty",
"qualification": "copied exactly", "last_date": "YYYY-MM-DD or empty", "event_date": "YYYY-MM-DD or empty (job camp / exam day)",
"apply_where": "where / how to apply, copied exactly (office address or website)", "link": "the official notice link", "published": "YYYY-MM-DD or empty"}]}
Rules: use ONLY what is written in the text; never guess a date, a number or a post; copy names and qualifications exactly as written;
leave a field empty if it is not in the text; skip anything that is not a job / recruitment / employment camp notice."""


def extract(text, ask, district_hint=""):
    """the writer model's candidate list. ask(system, user) -> parsed JSON. Candidates still have to pass the fact gate."""
    data = ask(SYSTEM, f"District: {district_hint}\n\nPAGE TEXT:\n{text[:30000]}")
    return [j for j in (data or {}).get("jobs", []) if isinstance(j, dict)]


# ---------- the gate ----------
def _d(s):
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def job_key(job):
    base = (job.get("link") or "") + "|" + factgate.norm(job.get("post", "")) + "|" + str(job.get("last_date") or job.get("event_date") or "")
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def gate(job, text, page, allowed_hosts, source_is_district_site=False):
    """-> [problems] (empty = every field is backed by the official text)"""
    problems = []
    for f in REQUIRED:
        if not str(job.get(f, "")).strip():
            problems.append(f"missing {f}")
    if not (_d(job.get("last_date")) or _d(job.get("event_date"))):
        problems.append("missing last date / event date")
    if problems:
        return problems
    if not str(job["link"]).startswith("https://") or not official_host(job["link"], allowed_hosts):
        problems.append("link is not an official https address")
    for f in ("post", "qualification", "apply_where"):
        if not factgate.value_in_text(job[f], text):
            problems.append(f"{f} not found in the official text")
    for f in ("last_date", "event_date"):
        d = _d(job.get(f))
        if d and not factgate.date_in_text(d, text):
            problems.append(f"{f} {d.isoformat()} not found in the official text")
    if str(job.get("vacancies", "")).strip():
        bad = factgate.numbers_in(job["vacancies"]) - factgate.numbers_in(text)
        if bad:
            problems.append("vacancies number not in the official text")
    aliases = page.get("aliases", [])
    if not source_is_district_site and not any(factgate.norm(a) in factgate.norm(text) for a in aliases):
        problems.append("district not named in the notice")
    return problems


def eligible(job, day, seen, posted, cfg):
    """why a gated job cannot be posted today ('' = it can). seen: {key: first_seen iso}; posted: {key: {...}}"""
    key = job_key(job)
    last, event = _d(job.get("last_date")), _d(job.get("event_date"))
    if key in posted:
        return "already posted"
    close = last or event
    if close and close < day:
        return "expired"
    if last and last < day:
        return "expired"
    new_days = int(cfg.get("new_within_days", 2))
    up_days = int(cfg.get("upcoming_event_days", 14))
    pub = _d(job.get("published")) or _d(seen.get(key))
    is_new = bool(pub) and (day - pub).days <= new_days
    is_upcoming = bool(event) and 0 <= (event - day).days <= up_days
    if not (is_new or is_upcoming):
        return "old notice (not new, not upcoming)"
    return ""


def update_seen(seen, jobs, day):
    """remember when each notice was first seen. FIRST RUN of a page (empty seen): the notices already on the site are the baseline
    - marked as seen 30 days ago, so they never count as new (only upcoming events can still qualify)."""
    baseline = not seen
    for j in jobs:
        k = job_key(j)
        if k not in seen:
            seen[k] = (day - timedelta(days=30)).isoformat() if baseline else day.isoformat()
    return seen


def pick(candidates, day):
    """the one job to post today: the soonest closing date first"""
    def close(j):
        return _d(j.get("last_date")) or _d(j.get("event_date")) or date.max
    return sorted(candidates, key=close)[0] if candidates else None


def days_left(job, day):
    close = _d(job.get("last_date")) or _d(job.get("event_date"))
    return (close - day).days if close else None
