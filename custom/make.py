"""SAMPLE only (owner 16 Nov): today's posted Rasipuram 360 news reel (RN-606, 05:24) rebuilt + a sponsored promotion strip
(JCOM Rasipuram 2.0 meeting) at the bottom. python custom/make.py <out.mp4>  (repo root; never posts)"""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path.cwd()
sys.path[:0] = [str(ROOT / "reel"), str(ROOT / "poster"), str(ROOT / "research_free")]
os.environ["REEL_PUNCH"] = "0"
C = ROOT / "custom"
story = json.loads((C / "story.json").read_text())

img = C / "img" / "01.jpg"      # the news picture: made from the SAME prompt the posting job used for RN-606
if not img.exists():
    try:
        import imagegen
        data = imagegen.generate(story["image_prompt"], seed=606)
        try:
            data = imagegen.to_story_size(data)
        except Exception:
            pass
        img.write_bytes(data)
    except Exception as e:      # free picture allowance used up: the plain branded background (same as the posting job's fallback)
        print("picture not made:", str(e)[:150], "- plain branded background")
        from PIL import Image, ImageDraw
        bg = Image.new("RGB", (1152, 2048), (10, 24, 52)); d = ImageDraw.Draw(bg)
        for y in range(2048):
            d.line([(0, y), (1152, y)], fill=(10 + y // 80, 24 + y // 60, 52 + y // 30))
        logo = Image.open(ROOT / "kit" / "logo_rasipuram.png").convert("RGBA"); logo.thumbnail((620, 620))
        bg.paste(logo, ((1152 - logo.width) // 2, 560), logo); bg.save(img, quality=92)
story["images"] = [str(img)] * len(story["sentences"])
spec = C / "story_run.json"
spec.write_text(json.dumps(story, ensure_ascii=False))

import reel4
R, V3 = reel4.R, reel4.V3
STARTS = []
_mvt = R.make_voice_track
MOVES = [(1.0, 1.15, .5, .45, 0, 0), (1.15, 1.25, .35, .5, 20, 0), (1.12, 1.25, .65, .5, -20, 0), (1.05, 1.2, .5, .55, 0, 0)]


def grab(work, texts, starts, total):
    STARTS[:] = starts
    return _mvt(work, texts, starts, total)


def per_sentence(n_img, content_end, snaps):
    cuts = [0.0] + [STARTS[i] - 0.15 for i in range(1, n_img)] + [content_end + 5]
    return [{"a": round(cuts[i], 3), "b": round(cuts[i + 1], 3), "img": i, "z0": min(m[0], V3.MAX_ZOOM), "z1": min(m[1], V3.MAX_ZOOM),
             "fx": m[2], "fy": m[3], "px": m[4], "py": m[5]} for i, m in ((i, MOVES[i % len(MOVES)]) for i in range(n_img))]


R.make_voice_track = grab
V3_plan = V3.plan_shots
V3.plan_shots = lambda n, e, s: per_sentence(n, e, s) if STARTS else V3_plan(n, e, s)
out = Path(sys.argv[1])
base = out.with_name("base.mp4")
reel4.main(str(spec), str(base), "rasipuram")

# ---- the promotion strip (1000 x 196 px, labelled விளம்பரம்) ----
F = (ROOT / "goldrate" / "fonts").resolve()
thumb = (C / "img" / "promo_thumb.jpg").resolve()
html = f"""<html><head><style>
@font-face{{font-family:NT;src:url(file://{F}/noto-sans-tamil-tamil-800-normal.woff2)}}
@font-face{{font-family:NL;src:url(file://{F}/noto-sans-tamil-latin-800-normal.woff2)}}
@font-face{{font-family:NT6;src:url(file://{F}/noto-sans-tamil-tamil-600-normal.woff2)}}
@font-face{{font-family:NL6;src:url(file://{F}/noto-sans-tamil-latin-600-normal.woff2)}}
body{{margin:0;background:transparent}}
#p{{width:1040px;height:320px;box-sizing:border-box;display:flex;align-items:center;gap:24px;padding:18px 24px 18px 18px;
 background:linear-gradient(100deg,#fffaf0,#fff3d6);border-radius:22px;border:4px solid #b3121b;box-shadow:0 10px 30px rgba(0,0,0,.45);font-family:NL,NT}}
#p img{{width:330px;height:278px;object-fit:contain;background:#fff;border-radius:12px;border:2px solid #d9c9a3}}
.tag{{display:inline-block;background:#b3121b;color:#fff;font:800 28px NL,NT;padding:4px 18px;border-radius:30px;margin-bottom:8px}}
.t1{{font:800 44px/1.15 NL,NT;color:#7a0d12}}
.t2{{font:600 31px/1.35 NL6,NT6;color:#222;margin-top:6px;white-space:nowrap}}
.t3{{font:800 38px/1.3 NL,NT;color:#0b6b3a;margin-top:4px}}
</style></head><body><div id="p"><img src="file://{thumb}"><div>
<div class="tag">விளம்பரம்</div>
<div class="t1">JCOM வணிகக் கூட்டம்</div>
<div class="t2">நவ. 18 • மாலை 6 • மகாலட்சுமி ஹால்</div>
<div class="t3">₹299 • 94491 17729</div></div></div></body></html>"""
(C / "promo.html").write_text(html)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1040, "height": 320})
    pg.goto(f"file://{(C / 'promo.html').resolve()}"); pg.wait_for_timeout(600)
    pg.locator("#p").screenshot(path=str(C / "promo.png"), omit_background=True); b.close()

# strip over the reel: x 20, y 1584 (1040 x 320) - over the small footer logo, below the subtitles (below the subtitles, above the logo footer), slides up at 1.2 s, stays to the end
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(base), "-loop", "1", "-i", str(C / "promo.png"),
                "-filter_complex", "[1:v]format=rgba,fade=in:st=1.2:d=0.4:alpha=1[pr];"
                "[0:v][pr]overlay=x=20:y='if(lt(t,1.2),1920,max(1584,1920-(t-1.2)*1800))':shortest=1[v]",
                "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "copy", "-movflags", "+faststart", str(out)], check=True)
print("done", out)
