"""Checks that must pass BEFORE anything is posted: Tamil text, fonts, voice/reel audio, and news verification."""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "kit" / "node_modules" / "@fontsource"

# fonts the poster and reel really use (Tamil + Latin subsets)
FONT_FILES = [("noto-sans-tamil", "tamil", (600, 700, 800)), ("noto-sans-tamil", "latin", (600, 700, 800)),
              ("baloo-thambi-2", "tamil", (700, 800)), ("baloo-thambi-2", "latin", (700, 800)),
              ("catamaran", "latin", (700, 800, 900))]
_cov = None


def font_coverage():
    global _cov
    if _cov is None:
        from fontTools.ttLib import TTFont
        per = {}
        for pkg, sub, weights in FONT_FILES:
            for w in weights:
                f = FONTS / pkg / "files" / f"{pkg}-{sub}-{w}-normal.woff2"
                if f.exists():
                    per[(pkg, sub, w)] = set(TTFont(str(f)).getBestCmap().keys())
        _cov = per
    return _cov


def strip_tags(t):
    return re.sub(r"<[^>]+>", "", t or "")


def spec_texts(spec):
    out = [spec.get("hl1", ""), spec.get("hl2", ""), spec.get("cat", ""), spec.get("loc", ""), spec.get("date", "")]
    for s in spec.get("slides", []):
        out.append(s.get("title", ""))
        out += s.get("lines", [])
    return [strip_tags(x) for x in out if x]


TAMIL_CONS = range(0x0B95, 0x0BBA)
SIGNS = set(range(0x0BBE, 0x0BCE)) | {0x0BD7}


def tamil_sequence_problems(text):
    """Broken Tamil: a vowel sign or pulli with no consonant before it, doubled signs, replacement characters."""
    probs = []
    if "�" in text:
        probs.append("replacement character (broken text)")
    prev = None
    for i, ch in enumerate(text):
        c = ord(ch)
        if c in SIGNS:
            ok = prev is not None and (ord(prev) in TAMIL_CONS or (ord(prev) in (0x0BC6, 0x0BC7) and c in (0x0BBE, 0x0BD7)))
            if not ok:
                probs.append(f"stray Tamil sign '{ch}' after '{prev or ''}' in «{text[max(0, i - 6):i + 4]}»")
        prev = ch
    return probs


def check_fonts(texts):
    """Every character shown on a slide or in a reel caption must exist in the fonts (otherwise it prints as a box)."""
    cov = font_coverage()
    if not cov:
        return ["font files not found - cannot check Tamil rendering"]
    probs = []
    for key_pkg in ("noto-sans-tamil", "baloo-thambi-2"):
        cps = set()
        for (pkg, sub, w), s in cov.items():
            if pkg == key_pkg:
                cps |= s
        cat = set()
        for (pkg, sub, w), s in cov.items():
            if pkg == "catamaran":
                cat |= s
        missing = set()
        for t in texts:
            for ch in t:
                if ch.isspace() or ord(ch) in (0x200C, 0x200D):
                    continue
                if ord(ch) not in cps and ord(ch) not in cat:
                    missing.add(ch)
        if missing:
            probs.append(f"characters missing in font {key_pkg}: {' '.join(sorted(missing))}")
    return probs


def check_texts(spec, reel_captions):
    texts = spec_texts(spec) + list(reel_captions)
    probs = []
    for t in texts:
        probs += tamil_sequence_problems(t)
    probs += check_fonts(texts)
    return probs


def check_news(row):
    v = (row.get("verification") or "").strip().lower()
    if not v:
        return ["news not marked as verified"]
    if re.search(r"unconfirmed|not verified|not confirmed|rumou?r|unverified|single source - unclear", v):
        return [f"news verification is weak: '{row.get('verification')}'"]
    return []


def ff_json(args):
    return json.loads(subprocess.run(args, capture_output=True, text=True, check=True).stdout)


def check_reel(mp4, spoken_lines):
    probs = []
    info = ff_json(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(mp4)])
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = float(info["format"].get("duration", 0))
    if not v or (v.get("width"), v.get("height")) != (1080, 1920):
        probs.append("reel is not 1080x1920")
    if not a:
        probs.append("reel has no audio (voice missing)")
    if not 10 <= dur <= 90:
        probs.append(f"reel length {dur:.1f}s is outside 10-90 seconds")
    if a:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                           capture_output=True, text=True)
        m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", r.stderr)
        mx = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr)
        if not m or float(m.group(1)) < -40:
            probs.append("reel audio is silent or far too quiet")
        if mx and float(mx.group(1)) > -0.1:
            probs.append("reel audio is clipping (too loud)")
    # does the voice say everything that is written? (the voice model drops letters it cannot pronounce)
    sys.path.insert(0, str(ROOT / "reel"))
    try:
        import tts
        for line in spoken_lines:
            letters = [c for c in line if 0x0B80 <= ord(c) <= 0x0BFF]
            kept = [c for c in tts.clean(line) if 0x0B80 <= ord(c) <= 0x0BFF]
            if letters and (len(letters) - len(kept)) / len(letters) > 0.03:
                probs.append(f"the voice cannot pronounce part of: «{line[:40]}»")
    except Exception as e:
        probs.append(f"voice check could not run: {e}")
    return probs


def clean_text(t):
    """owner 25 Oct: Tamil text problems are FIXED, never a reason to skip a story. Removes broken characters, stray Tamil
    vowel signs/pulli (no consonant before them) and characters the fonts cannot draw."""
    if not isinstance(t, str) or not t:
        return t
    t = t.replace("\ufffd", "")
    out, prev = [], None
    for ch in t:
        c = ord(ch)
        if c in SIGNS:
            if not (prev is not None and (ord(prev) in TAMIL_CONS or (ord(prev) in (0x0BC6, 0x0BC7) and c in (0x0BBE, 0x0BD7)))):
                continue      # stray sign: dropped
        out.append(ch)
        prev = ch
    t = "".join(out)
    cov = font_coverage() or {}
    cps = set()
    for (pkg, sub, w), s in cov.items():
        if pkg in ("noto-sans-tamil", "baloo-thambi-2", "catamaran"):
            cps |= s
    if cps:
        t = "".join(ch for ch in t if not (0x0B80 <= ord(ch) <= 0x0BFF and ord(ch) not in cps and not ch.isspace()))
    return t


def clean_obj(o):
    """clean_text on every string inside a dict/list (used on the spec and the reel scenes before rendering)"""
    if isinstance(o, str):
        return clean_text(o)
    if isinstance(o, list):
        return [clean_obj(x) for x in o]
    if isinstance(o, dict):
        return {k: clean_obj(v) for k, v in o.items()}
    return o
