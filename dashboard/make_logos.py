"""owner 26 Nov: puts the common 360 logo and each page's own logo into dashboard/Index.html as small round images (data URIs),
so the website needs no extra files. Sources: dashboard/img/logo_360.webp and dashboard/img/logo_<page>.webp (256px copies of each repo kit/logo_<page>.png)
Run: python dashboard/make_logos.py  (then python dashboard/build_worker.py)"""
import base64
import io
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
PAGES = ["namakkal", "coimbatore", "erode", "karur", "salem", "tirupur", "trichy"]


def round_icon(path, size):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    im.putalpha(mask.resize((size, size), Image.LANCZOS))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=82, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def build():
    logos = {"main": round_icon(HERE / "img" / "logo_360.webp", 160)}
    for pg in PAGES:
        logos[pg] = round_icon(HERE / "img" / f"logo_{pg}.webp", 96)
    p = HERE / "Index.html"
    s = p.read_text(encoding="utf-8")
    block = "/*LOGOS*/var LOGOS = " + json.dumps(logos) + ";/*END LOGOS*/"
    s2, n = re.subn(r"/\*LOGOS\*/.*?/\*END LOGOS\*/", lambda m: block, s, flags=re.S)
    assert n == 1, "Index.html needs the /*LOGOS*/ ... /*END LOGOS*/ marker"
    s2 = re.sub(r'<link rel="icon"[^>]*>', '<link rel="icon" href="' + logos["main"] + '">', s2, count=1)
    p.write_text(s2, encoding="utf-8")
    return {k: len(v) for k, v in logos.items()}


if __name__ == "__main__":
    print(build())
