"""owner 26 Nov: puts each news story's Facebook and YouTube links on the public website (news360.pages.dev).

READ-ONLY towards posting: it only reads the records the pages already keep in their public repositories
  poster/fb_posted/<facebook page>-<story>-reel.json   the Facebook reel of a story (link, status)
  poster/yt_uploaded/<page>.json + poster/posted/*.json  the YouTube Short of a story (the upload knows the Instagram post id, the
                                                          posted record knows which story that post was)
and sends  [{"id": "<website story id>", "fb_url": ..., "yt_url": ...}]  to the website's protected /api/links door
(WEBSITE_INGEST_KEY, the same secret the pages already use to send news). The website changes only those two columns.
The Instagram link is sent with the story itself, so it is not handled here.
A problem here never turns the run red and never touches posting: it logs and exits 0.   python dashboard/link_sync.py [--days 3] [--dry]
Never prints a key."""
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dash_collect as dc      # noqa: E402  (raw / listing helpers and the repo list)

URL = (os.environ.get("WEBSITE_URL") or "https://www.namakkal360.workers.dev").rstrip("/")
# website story id = <district code>-<story id>; Namakkal (the first site) has no code (website geo.ts rowId)
CODES = {"namakkal": "", "coimbatore": "CBE", "salem": "SLM", "erode": "ERD", "karur": "KRR", "tirupur": "TPR", "trichy": "TRY"}
REPO_DISTRICT = {"news360-autopost": "namakkal", "coimbatore360-autopost": "coimbatore", "erode360-autopost": "erode",
                 "karur360-autopost": "karur", "salem360-autopost": "salem", "tirupur360-autopost": "tirupur", "trichy360-autopost": "trichy"}
STORY = re.compile(r"^[A-Z]{1,4}-\d{1,7}$")      # a news story (rasipalan / gold reels have dated ids and are not news)
FB_NAME = re.compile(r"^([a-z]+)-([A-Z]{1,4}-\d{1,7})-reel\.json$")


def log(*a):
    print(*a, flush=True)


def row_id(district, story):
    code = CODES.get(district, "")
    return f"{code}-{story}" if code else story


def _fetch_all(raw, repo, paths):
    """{path: file} read 12 at a time (a page keeps hundreds of small records; one by one would take minutes)"""
    with ThreadPoolExecutor(max_workers=12) as ex:
        return dict(zip(paths, ex.map(lambda p: raw(repo, p) or {}, paths)))


def _recent(ts, days, now):
    t = dc.when(ts)
    return bool(t) and now - t <= timedelta(days=days)


def fb_links(repo, district, days, now, raw=None, listing=None):
    """{story: facebook link} of the stories posted on Facebook in the last `days` days (the district's own Facebook page first)"""
    raw, listing = raw or dc.raw, listing or dc.listing
    named = []
    for f in listing(repo, "poster/fb_posted"):
        m = FB_NAME.match(str(f.get("name", "")))
        if m:
            named.append((int(re.sub(r"\D", "", m.group(2))), m.group(1), m.group(2), f["name"]))
    named.sort(reverse=True)      # story numbers grow with time: only the newest ones can have been posted in the last `days` days
    named = named[:max(60, days * 30)]
    files = _fetch_all(raw, repo, [f"poster/fb_posted/{n[3]}" for n in named])
    best = {}
    for _, page, story, name in named:
        d = files.get(f"poster/fb_posted/{name}") or {}
        link = str(d.get("link") or "")
        if d.get("status") != "posted" or not link.startswith("https://") or not _recent(d.get("posted_at") or d.get("updated"), days, now):
            continue
        if story not in best or page == district:
            best[story] = link
    return best


def yt_links(repo, district, days, now, raw=None, listing=None):
    """{story: YouTube Shorts link}: the page's uploads (Instagram post id -> video) joined with the posted records (post id -> story)"""
    raw, listing = raw or dc.raw, listing or dc.listing
    uploads = {u["ig"]: u["youtube"] for u in ((raw(repo, f"poster/yt_uploaded/{district}.json") or {}).get("uploads") or [])
               if u.get("ig") and u.get("youtube")}
    if not uploads:
        return {}
    cut = (now - timedelta(days=days + 1)).strftime("%Y%m%d")
    names = [str(f.get("name", "")) for f in listing(repo, "poster/posted")]
    names = [n for n in names if n.endswith(".json") and n[:8] >= cut]
    files = _fetch_all(raw, repo, [f"poster/posted/{n}" for n in names])
    out = {}
    for n in names:
        rec = files.get(f"poster/posted/{n}") or {}
        vid = uploads.get(str(rec.get("media_id") or ""))
        if vid and STORY.match(str(rec.get("story") or "")):
            out[rec["story"]] = f"https://youtube.com/shorts/{vid}"
    return out


def collect(days=3, now=None, raw=None, listing=None):
    """[{id, fb_url?, yt_url?}] for every story of every page that has at least one link"""
    now = now or datetime.now(timezone.utc)
    items = []
    for repo, district in REPO_DISTRICT.items():
        fb = fb_links(repo, district, days, now, raw, listing)
        yt = yt_links(repo, district, days, now, raw, listing)
        for story in sorted(set(fb) | set(yt)):
            it = {"id": row_id(district, story)}
            if story in fb:
                it["fb_url"] = fb[story]
            if story in yt:
                it["yt_url"] = yt[story]
            items.append(it)
        log(f"{district}: {len(fb)} Facebook, {len(yt)} YouTube link(s)")
    return items


def send(items, key, post=requests.post):
    """in groups of 100; returns (saved, not_on_site_yet). A failed group is logged, the next run sends it again."""
    saved = skipped = 0
    for i in range(0, len(items), 100):
        group = items[i:i + 100]
        for attempt in range(3):
            try:
                r = post(URL + "/api/links", json=group, timeout=60, headers={"authorization": "Bearer " + key, "user-agent": "news360-link-sync"})
                if r.status_code == 200:
                    j = r.json()
                    saved += len(j.get("saved", []))
                    skipped += len(j.get("skipped", []))
                    break
                log("website answered", r.status_code, r.text[:120])
                if r.status_code in (400, 401, 403):
                    return saved, skipped      # a wrong key / bad request never gets better by trying again
            except Exception as e:
                log("website not reachable:", str(e)[:120])
            time.sleep(5 * (attempt + 1))
    return saved, skipped


def main(argv):
    days = int(argv[argv.index("--days") + 1]) if "--days" in argv else 3
    items = collect(days)
    log(f"{len(items)} story link(s) found")
    key = os.environ.get("WEBSITE_INGEST_KEY", "")
    if "--dry" in argv or not items:
        return 0
    if not key:
        log("WEBSITE_INGEST_KEY not set - nothing sent")
        return 0
    saved, skipped = send(items, key)
    log(f"sent: {saved} saved on the website, {skipped} not on the website (yet or no valid link)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:      # never red
        log("link sync stopped:", str(e)[:200])
        sys.exit(0)
