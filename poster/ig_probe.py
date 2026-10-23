"""One-off probe: can the stored Instagram tokens (1) read the page's recent posts and (2) read reel insights? Writes poster/probe/ig_probe.json."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import post

out = {}
METRICS = ["reach", "views", "saved", "shares", "likes", "comments", "total_interactions", "ig_reels_avg_watch_time", "ig_reels_video_view_total_time", "plays"]
for page in ("rasipuram", "namakkal"):
    r = out[page] = {}
    try:
        tok = post.bridge_get("token", page=page)["token"]
        uid, name = post.ig_account(tok)
        r["account"] = name
        m = post.ig("GET", f"{uid}/media", tok, fields="id,caption,timestamp,media_product_type,permalink,like_count,comments_count", limit=12)
        items = m.get("data", [])
        r["media_ok"] = len(items)
        r["recent"] = [{"t": i.get("timestamp"), "type": i.get("media_product_type"), "likes": i.get("like_count"), "comments": i.get("comments_count"),
                        "caption": (i.get("caption") or "")[:60].replace("\n", " ")} for i in items]
        reel = next((i for i in items if i.get("media_product_type") == "REELS"), None)
        r["insights"] = {}
        if reel:
            for met in METRICS:
                try:
                    d = post.ig("GET", f"{reel['id']}/insights", tok, metric=met)
                    r["insights"][met] = (d.get("data") or [{}])[0].get("values")
                except Exception as e:
                    r["insights"][met] = "ERR " + str(e)[:160]
        try:
            d = post.ig("GET", f"{uid}/insights", tok, metric="reach", period="day")
            r["account_reach"] = (d.get("data") or [{}])[0].get("values")
        except Exception as e:
            r["account_reach"] = "ERR " + str(e)[:160]
    except Exception as e:
        r["error"] = str(e)[:300]
os.makedirs(os.path.join(os.path.dirname(__file__), "probe"), exist_ok=True)
json.dump(out, open(os.path.join(os.path.dirname(__file__), "probe", "ig_probe.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:1500])
