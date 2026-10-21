"""Checks on a free-model draft. Returns a list of problems (empty = passes). Used for the retry loop and as the first gate."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "poster"))
OUTLETS = ["தினமலர்", "தினத்தந்தி", "தினமணி", "மாலைமலர்", "தினகரன்", "இந்து தமிழ்", "தி இந்து", "புதிய தலைமுறை", "நியூஸ்18", "நியூஸ் 18",
           "பாலிமர்", "சன் நியூஸ்", "நியூஸ்7", "நியூஸ் 7", "கலைஞர் செய்திகள்", "விகடன்", "ஒன்இந்தியா", "வே2நியூஸ்", "டாப் தமிழ்",
           "தமிழ் மணி", "டைம்ஸ் ஆஃப் இந்தியா", "dinamalar", "dinamani", "dinathanthi", "daily thanthi", "maalaimalar", "dinakaran",
           "the hindu", "hindu tamil", "times of india", "dt next", "indian express", "news18", "polimer", "sun news", "news7", "vikatan",
           "oneindia", "way2news", "puthiya thalaimurai", "kalaignar", "toptamilnews", "ஆதாரம்", "source:", "http", "www."]
LAST = "மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்."
FOLLOW = "உள்ளூர் செய்திகளுக்கு Follow செய்யுங்கள் 🙏"
KEYS = ["tamil_headline", "english_headline", "category", "location", "importance", "post_to", "slides_spec", "reel_script", "caption", "scenes"]


def _tags(t):
    return re.sub(r"<[^>]+>", "", t or "")


def _digits_in(text):
    return set(re.findall(r"\d+", text or ""))


def validate(d, article, today_digits=("2026",)):
    p = []
    if not isinstance(d, dict):
        return ["output is not a JSON object"]
    for k in KEYS:
        if not d.get(k):
            p.append(f"missing key: {k}")
    if p:
        return p
    sp = d["slides_spec"]
    if sp.get("v") != 3:
        p.append("slides_spec.v must be 3")
    sl = sp.get("slides") or []
    if not 3 <= len(sl) <= 4:
        p.append("slides must have 3 or 4 items")
    if len(sp.get("hl1", "")) > 40:
        p.append("hl1 longer than 40 characters")
    if len(sp.get("hl2", "")) > 28:
        p.append("hl2 longer than 28 characters")
    for i, s in enumerate(sl, 1):
        if len(_tags(s.get("title", ""))) > 18:
            p.append(f"slide {i} title longer than 18 characters")
        ln = s.get("lines") or []
        if not 2 <= len(ln) <= 3:
            p.append(f"slide {i} must have 2-3 lines")
        for j, l in enumerate(ln, 1):
            if len(_tags(l)) > 60:
                p.append(f"slide {i} line {j} longer than 60 characters")
    if len(d["scenes"]) != len(sl) + 1:
        p.append(f"scenes must be {len(sl)+1} (slides + 1), got {len(d['scenes'])}")
    rs = d["reel_script"].strip()
    if re.search(r"[0-9A-Za-z]", rs):
        p.append("reel_script must have no digits or English letters (write numbers as Tamil words)")
    if not rs.endswith(LAST):
        p.append("reel_script must end with exactly: " + LAST)
    wc = len(rs.split())
    if not 32 <= wc <= 62:
        p.append(f"reel_script has {wc} words; need 38-55 (short, fast reel)")
    if "வணக்கம்" in rs.split(".")[0]:
        p.append("reel_script must not start with a greeting")
    cap = d["caption"]
    if FOLLOW not in cap:
        p.append("caption must contain the exact follow line")
    tags = re.findall(r"#\S+", cap)
    if not 3 <= len(tags) <= 7:
        p.append(f"caption needs 4-6 hashtags, has {len(tags)}")
    if d.get("importance") not in ("High", "Medium", "Low"):
        p.append("importance must be High, Medium or Low")
    if not (d["post_to"].startswith("Namakkal 360")):
        p.append("post_to must start with 'Namakkal 360'")
    blob = json.dumps(d, ensure_ascii=False).lower()
    hits = [o for o in OUTLETS if o.lower() in blob]
    if hits:
        p.append("source/outlet name or link appears: " + ", ".join(hits[:3]))
    if re.search(r"AI (image|generated)|AI பிரதிநிதித்துவ", blob, re.I):
        p.append("no AI-image notes allowed")
    # every number must come from the article
    src = _digits_in(article) | set(today_digits) | {"1", "2", "3", "4", "5"}
    text = " ".join([d["tamil_headline"], d["english_headline"], _tags(json.dumps(sp, ensure_ascii=False)), cap.split("#")[0]])
    stray = sorted(n for n in _digits_in(text) if n not in src and len(n) > 0 and n not in ("0", "360"))
    if stray:
        p.append("numbers not found in the article: " + ", ".join(stray[:6]))
    try:
        from verify import tamil_sequence_problems
        for t in [d["tamil_headline"], rs, _tags(cap)]:
            p += tamil_sequence_problems(t) or []
    except Exception:
        pass
    return p
