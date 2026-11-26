"""owner 26 Nov: the read-only collector for the private team dashboard (dashboard/Code.gs + Index.html).

It changes NOTHING in the posting workflows: it only READS the numbers the pages already keep in their public repositories
  poster/insights/history.json   Instagram views / reach / saves / shares / interactions per post (written by each page's insights job)
  poster/yt_uploaded/<page>.json  the YouTube Shorts of the page
  poster/fb_posted/*-reel.json    the Facebook reels of the page
plus the public YouTube numbers (views / likes / comments) from the YouTube Data API (one free API key, YT_API_KEY), and sends one
combined file to the dashboard's private Apps Script store (DASH_URL + DASH_WRITE_KEY). Nothing private is read or stored here: the
comment / message TEXT of phase 2 never goes through a public repository.
Without DASH_URL / DASH_WRITE_KEY it prints a note and exits 0 (never a red run). Never prints a key."""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

OWNER = "news360-tn"
REPOS = {"news360-autopost": ["namakkal", "rasipuram"], "coimbatore360-autopost": ["coimbatore"], "erode360-autopost": ["erode"],
         "karur360-autopost": ["karur"], "salem360-autopost": ["salem"], "tirupur360-autopost": ["tirupur"], "trichy360-autopost": ["trichy"]}
NAMES = {"namakkal": ("Namakkal", "நாமக்கல்"), "rasipuram": ("Rasipuram", "இராசிபுரம்"), "coimbatore": ("Coimbatore", "கோவை"),
         "erode": ("Erode", "ஈரோடு"), "karur": ("Karur", "கரூர்"), "salem": ("Salem", "சேலம்"), "tirupur": ("Tiruppur", "திருப்பூர்"),
         "trichy": ("Trichy", "திருச்சி")}
DAYS = 14
IST = timezone(timedelta(hours=5, minutes=30))


def log(*a):
    print(*a, flush=True)


def raw(repo, path):
    """the file from the public repository's main branch, or None"""
    try:
        r = requests.get(f"https://raw.githubusercontent.com/{OWNER}/{repo}/main/{path}", timeout=60)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        log(f"{repo}/{path}: not read ({str(e)[:80]})")
        return None


def listing(repo, path):
    try:
        r = requests.get(f"https://api.github.com/repos/{OWNER}/{repo}/contents/{path}", timeout=60,
                         headers={"Accept": "application/vnd.github+json", **({"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"]}
                                                                              if os.environ.get("GITHUB_TOKEN") else {})})
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def when(s):
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00").replace("+0000", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def headline(caption):
    first = (caption or "").strip().split("\n")[0]
    return re.sub(r"^[^\w஀-௿]+", "", first).strip()[:140]


def instagram(repo, pages, cut):
    h = raw(repo, "poster/insights/history.json") or {}
    out = []
    for mid, v in h.items():
        t = when(v.get("t"))
        if not t or t < cut or v.get("page") not in pages:
            continue
        kind = "carousel" if v.get("type") == "FEED" else "reel"
        out.append({"platform": "instagram", "page": v["page"], "id": str(mid), "title": headline(v.get("caption")) or "(no caption)",
                    "t": t.isoformat(), "kind": kind, "views": v.get("views"), "reach": v.get("reach"), "saves": v.get("saved"),
                    "shares": v.get("shares"), "interactions": v.get("total_interactions"), "likes": None, "comments": None,
                    "topic": v.get("topic") or "", "url": str(v.get("permalink") or "")})      # owner 26 Nov: the post's own link (filled by the insights job)
    return out


def youtube(repo, pages, cut, key):
    out = []
    for pg in pages:
        d = raw(repo, f"poster/yt_uploaded/{pg}.json") or {}
        for u in d.get("uploads", []):
            t = when(u.get("at"))
            if not u.get("youtube") or not t or t < cut:
                continue
            out.append({"platform": "youtube", "page": pg, "id": u["youtube"], "title": (u.get("title") or "")[:140], "t": t.isoformat(),
                        "kind": "short", "views": None, "reach": None, "saves": None, "shares": None, "interactions": None, "likes": None,
                        "comments": None, "topic": "", "url": f"https://youtube.com/shorts/{u['youtube']}"})
    return out


def youtube_stats(items, key):
    """fills views / likes / comments from the public YouTube Data API (1 quota unit per 50 videos)"""
    if not key or not items:
        return False
    byid = {i["id"]: i for i in items}
    ids = list(byid)
    ok = True
    for n in range(0, len(ids), 50):
        try:
            r = requests.get("https://www.googleapis.com/youtube/v3/videos", timeout=60,
                             params={"part": "statistics", "id": ",".join(ids[n:n + 50]), "key": key})
            if r.status_code != 200:
                log("YouTube statistics not read:", r.status_code, r.text[:120])
                ok = False
                continue
            for v in r.json().get("items", []):
                s = v.get("statistics", {})
                it = byid.get(v["id"])
                if it:
                    it["views"] = int(s.get("viewCount", 0))
                    it["likes"] = int(s.get("likeCount", 0)) if "likeCount" in s else None
                    it["comments"] = int(s.get("commentCount", 0)) if "commentCount" in s else None
        except Exception as e:
            log("YouTube statistics failed:", str(e)[:100])
            ok = False
    return ok


def facebook(repo, pages, cut):
    out = []
    for f in listing(repo, "poster/fb_posted"):
        name = f.get("name", "")
        if name.startswith("_") or not name.endswith("-reel.json"):
            continue
        d = raw(repo, f"poster/fb_posted/{name}") or {}
        t = when(d.get("posted_at"))
        pg = d.get("page")
        if d.get("status") != "posted" or not t or t < cut or pg not in pages:
            continue
        story = str(d.get("story") or "")
        out.append({"platform": "facebook", "page": pg, "id": str(d.get("id") or name), "title": story, "t": t.isoformat(), "kind": "reel",
                    "views": None, "reach": None, "saves": None, "shares": None, "interactions": None, "likes": None, "comments": None,
                    "topic": "", "url": d.get("link") or ""})
    return out


def series(hist, page, key):
    """[(day, value)] of one page from a {day: {page: {key: n}}} history, oldest first, numbers only"""
    out = []
    for day in sorted(hist or {}):
        v = ((hist[day] or {}).get(page) or {}).get(key)
        if isinstance(v, (int, float)):
            out.append((day, int(v)))
    return out


def with_change(points):
    """latest value + the change against about 7 days earlier (None when there is not enough history yet)"""
    if not points:
        return None
    day, n = points[-1]
    d7 = None
    try:
        last = datetime.fromisoformat(day)
        gaps = [((last - datetime.fromisoformat(dd)).days, v) for dd, v in points[:-1]]
        older = [v for g, v in gaps if g >= 7] or [v for g, v in gaps if g >= 6]      # about a week back (6 days only when that is all there is)
        if older:
            d7 = n - older[-1]
    except Exception:
        pass
    return {"n": n, "d7": d7}


def youtube_subscribers(yt_items, key):
    """{page: {"n": subscribers or None, "hidden": bool, "videos": n}} from the public YouTube Data API. The channel of each page is found
    from one of its uploaded videos (no channel id to keep); 2 calls in all."""
    first = {}
    for it in yt_items:
        first.setdefault(it["page"], it["id"])
    if not key or not first:
        return {}
    try:
        r = requests.get("https://www.googleapis.com/youtube/v3/videos", timeout=60, params={"part": "snippet", "id": ",".join(first.values()), "key": key})
        chan_of = {v["id"]: v["snippet"]["channelId"] for v in r.json().get("items", [])} if r.status_code == 200 else {}
        ids = sorted(set(chan_of.values()))
        if not ids:
            return {}
        r = requests.get("https://www.googleapis.com/youtube/v3/channels", timeout=60, params={"part": "statistics", "id": ",".join(ids), "key": key})
        stats = {c["id"]: c.get("statistics", {}) for c in r.json().get("items", [])} if r.status_code == 200 else {}
    except Exception as e:
        log("YouTube subscribers not read:", str(e)[:100])
        return {}
    out = {}
    for pg, vid in first.items():
        st = stats.get(chan_of.get(vid), {})
        if not st:
            continue
        hidden = bool(st.get("hiddenSubscriberCount"))
        out[pg] = {"n": None if hidden or "subscriberCount" not in st else int(st["subscriberCount"]), "hidden": hidden,
                   "videos": int(st.get("videoCount", 0))}
    return out


def followers(yt_items, yt_key, raw_fn=None):
    """owner 26 Nov: followers / subscribers per page and platform:
    {page: {"instagram": {"n", "d7"}, "facebook": {"n", "d7"}, "youtube": {"n", "hidden", "videos"}}}
    Instagram: poster/insights/followers.json (daily, by the insights job). Facebook: poster/insights/fb_followers.json (same job, needs the
    page's Facebook secrets). YouTube: the public channel statistics. A missing platform is simply left out (the dashboard shows n/a)."""
    raw_fn = raw_fn or raw
    out = {}
    for repo, pages in REPOS.items():
        ig = raw_fn(repo, "poster/insights/followers.json") or {}
        fb = raw_fn(repo, "poster/insights/fb_followers.json") or {}
        for pg in pages:
            rec = {}
            i = with_change(series(ig, pg, "followers"))
            if i:
                rec["instagram"] = i
            f = with_change(series(fb, pg, "followers") or series(fb, pg, "fans"))
            if f:
                rec["facebook"] = f
            if rec:
                out[pg] = rec
    for pg, y in youtube_subscribers(yt_items, yt_key).items():
        out.setdefault(pg, {})["youtube"] = y
    return out


def build(now=None, yt_key=""):
    now = now or datetime.now(timezone.utc)
    cut = now - timedelta(days=DAYS)
    posts, notes = [], {}
    yt_all = []
    for repo, pages in REPOS.items():
        posts += instagram(repo, pages, cut)
        yt = youtube(repo, pages, cut, yt_key)
        yt_all += yt
        posts += yt
        posts += facebook(repo, pages, cut)
    if not youtube_stats(yt_all, yt_key):
        notes["youtube"] = "YouTube numbers need the YT_API_KEY secret" if not yt_key else "YouTube numbers could not be read this time"
    fol = followers(yt_all, yt_key)
    if not any("facebook" in v for v in fol.values()):
        notes["followers_facebook"] = "Facebook followers appear after the daily insights job has read them (the page's Facebook access may still need a Meta permission)"
    notes["facebook"] = "Facebook views / likes / comments need the Meta read_insights and pages_read_engagement permissions (phase 2)"
    notes["instagram"] = "Instagram likes and comment counts, comment text and messages arrive in phase 2"
    posts.sort(key=lambda p: p["t"], reverse=True)
    pages = {pg: {"name": NAMES[pg][0], "label": NAMES[pg][1]} for ps in REPOS.values() for pg in ps if pg != "rasipuram"}
    return {"updated": now.isoformat(timespec="seconds"), "days": DAYS, "pages": pages, "posts": posts, "notes": notes, "followers": fol}


def send(payload):
    url, key = os.environ.get("DASH_URL", "").strip(), os.environ.get("DASH_WRITE_KEY", "").strip()
    if not url or not key:
        log("dashboard not set up yet (DASH_URL / DASH_WRITE_KEY secrets) - nothing sent")
        return False
    r = requests.post(url, data=json.dumps({"action": "put", "key": key, "data": payload}, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, timeout=300)
    try:
        ok = bool(r.json().get("ok"))
    except Exception:
        ok = False
    log("dashboard data sent" if ok else f"dashboard store refused the data (HTTP {r.status_code}) - check DASH_URL / DASH_WRITE_KEY")
    return ok


def main():
    if not os.environ.get("DASH_URL") or not os.environ.get("DASH_WRITE_KEY"):
        log("dashboard not set up yet (DASH_URL / DASH_WRITE_KEY secrets) - nothing to do")
        return 0
    p = build(yt_key=os.environ.get("YT_API_KEY", "").strip())
    n = {k: sum(1 for x in p["posts"] if x["platform"] == k) for k in ("instagram", "facebook", "youtube")}
    log("posts collected:", n)
    send(p)
    return 0      # a dashboard problem never turns anything red


if __name__ == "__main__":
    sys.exit(main())
