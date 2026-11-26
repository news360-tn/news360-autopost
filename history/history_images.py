"""owner 26 Nov: the history reel's pictures - the story's OWN scenes drawn by the free image chain (research_free/imagegen.py).
When no model answers (no keys / limits), a plain drawn heritage placeholder is used so a reel is never blocked by pictures alone -
but then the reel is NOT marked as AI-visuals (the caption disclosure follows what was really used).

make_scenes(prompts, outdir, seed) -> (data uris [one per prompt], ai_count)"""
import base64
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_free"))


def placeholder(i, w=900, h=1000):
    """a sepia hills-and-sun scene (PIL), different per scene"""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (232, 205, 150))
    d = ImageDraw.Draw(im)
    for y in range(h):      # sky gradient
        k = y / h
        d.line([(0, y), (w, y)], fill=(int(240 - 40 * k), int(214 - 60 * k), int(160 - 70 * k)))
    sx = int(w * (0.25 + 0.5 * ((i * 37) % 100) / 100))
    d.ellipse([sx - 110, 230 - 110, sx + 110, 230 + 110], fill=(250, 232, 190))
    for layer, (col, base) in enumerate([((150, 105, 60), 560), ((118, 78, 40), 700), ((82, 52, 26), 850)]):
        pts = [(0, h)]
        for x in range(0, w + 60, 60):
            pts.append((x, base - 60 * ((x * (layer + 3) + i * 91) % 7) / 6 - 30 * layer))
        pts.append((w, h))
        d.polygon(pts, fill=col)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def to_uri(data):
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def make_scenes(prompts, outdir, seed=1, generate=None, log=print):
    """-> (uris, ai_count). generate(prompt, seed) -> image bytes (default: the repo's imagegen chain)."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if generate is None:
        try:
            import imagegen
            generate = imagegen.generate
        except Exception as e:
            log("image chain not available:", str(e)[:100])
            generate = None
    uris, ai = [], 0
    for i, pr in enumerate(prompts):
        data = None
        if generate:
            try:
                data = generate(pr, seed + i)
                ai += 1
            except Exception as e:
                log(f"scene {i + 1}: picture model failed ({str(e)[:100]}) - placeholder")
        if not data:
            data = placeholder(i)
        (outdir / f"scene{i + 1}.jpg").write_bytes(data)
        uris.append(to_uri(data))
    return uris, ai
