"""owner 26 Nov: the website keeps its OWN small copy of each story's pictures.

The pipeline's picture links (Cloudflare R2) are deleted after 24 hours ("clean every 24 hrs"), so a story on the website would lose
its picture the next day. This job runs every 2 hours: it asks the website which recent stories have no copy yet (thumbs = 0),
downloads their pictures while the links still work, makes each one small (720 px WebP, about 40 KB) and sends it to the website's
protected /api/thumbs door (WEBSITE_INGEST_KEY, the secret the pages already use). Free: nothing is generated, only resized.

READ-ONLY towards posting; never turns the run red; never prints a key.      python dashboard/thumb_sync.py [--max 40] [--dry]"""
import base64
import io
import os
import sys
import time

import requests

URL = (os.environ.get("WEBSITE_URL") or "https://www.namakkal360.workers.dev").rstrip("/")
MAX_PICS = 3          # pictures kept per story
MAX_SIDE = 720        # pixels, longest side
MAX_CHARS = 150_000   # one picture as base64 must stay below this (the website accepts 200 000)
LOOKBACK_PAGES = 4    # newest 60 stories are enough: the job runs every 2 hours


def log(*a):
    print(*a, flush=True)


def shrink(data, side=MAX_SIDE):
    """image bytes -> base64 of a small WebP, or None (not an image / too big even when small)"""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        return None
    im = im.convert("RGB")
    im.thumbnail((side, side))
    for q in (72, 60, 48):
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=q, method=4)
        b64 = base64.b64encode(buf.getvalue()).decode()
        if len(b64) <= MAX_CHARS:
            return b64
    return None


def fetch_image(url, get=requests.get):
    try:
        r = get(url, timeout=25)
        ok = r.status_code == 200 and str(r.headers.get("content-type", "")).startswith("image/") and len(r.content) < 15_000_000
        return r.content if ok else None
    except Exception:
        return None


def stories_without_copy(pages=LOOKBACK_PAGES, get=requests.get):
    """newest stories whose website row has no stored picture yet but does have picture links"""
    out = []
    for pg in range(pages):
        try:
            r = get(f"{URL}/api/news", params={"page": pg}, timeout=40)
            items = r.json().get("items", []) if r.status_code == 200 else []
        except Exception as e:
            log("website not reachable:", str(e)[:100])
            break
        for n in items:
            if not int(n.get("thumbs") or 0) and [u for u in n.get("images", []) if str(u).startswith("https://")]:
                out.append({"id": n["id"], "images": n["images"][:MAX_PICS]})
        if len(items) < 15:
            break
    return out


def build(stories, fetch=fetch_image, limit=40):
    """[{id, thumbs: [base64...]}] - stories none of whose pictures can be fetched any more are left out (nothing to keep)"""
    items = []
    for s in stories[:limit]:
        pics = []
        for u in s["images"]:
            data = fetch(u)
            b64 = shrink(data) if data else None
            if b64:
                pics.append(b64)
        if pics:
            items.append({"id": s["id"], "thumbs": pics})
        else:
            log(f"{s['id']}: no picture could be fetched (link already gone)")
    return items


def send(items, key, post=requests.post):
    """in small groups (a group is about 100-400 KB); returns (saved, skipped)"""
    saved = skipped = 0
    for i in range(0, len(items), 5):
        group = items[i:i + 5]
        for attempt in range(3):
            try:
                r = post(URL + "/api/thumbs", json=group, timeout=90, headers={"authorization": "Bearer " + key, "user-agent": "news360-thumb-sync"})
                if r.status_code == 200:
                    j = r.json()
                    saved += len(j.get("saved", []))
                    skipped += len(j.get("skipped", []))
                    break
                log("website answered", r.status_code, r.text[:120])
                if r.status_code in (400, 401, 403, 404):
                    return saved, skipped
            except Exception as e:
                log("website not reachable:", str(e)[:100])
            time.sleep(5 * (attempt + 1))
    return saved, skipped


def main(argv):
    limit = int(argv[argv.index("--max") + 1]) if "--max" in argv else 40
    stories = stories_without_copy()
    log(f"{len(stories)} recent stor{'y' if len(stories) == 1 else 'ies'} without a stored picture")
    if not stories:
        return 0
    items = build(stories, limit=limit)
    log(f"{len(items)} with a picture to store")
    key = os.environ.get("WEBSITE_INGEST_KEY", "")
    if "--dry" in argv or not items:
        return 0
    if not key:
        log("WEBSITE_INGEST_KEY not set - nothing sent")
        return 0
    saved, skipped = send(items, key)
    log(f"stored: {saved} stories, {skipped} skipped")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:      # never red
        log("picture sync stopped:", str(e)[:200])
        sys.exit(0)
