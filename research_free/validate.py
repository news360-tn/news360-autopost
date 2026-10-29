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
    t = text or ""
    # "2,600" counts as 2600 as well
    return set(re.findall(r"\d+", t)) | set(re.findall(r"\d+", re.sub(r"(?<=\d),(?=\d{2,3}\b)", "", t)))


def _calendar_digits():
    """today's / yesterday's / tomorrow's day, the month number and the year (IST): a story written today may name them"""
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=5, minutes=30)))
    out = {str(now.year), str(now.month)}
    for k in (-2, -1, 0, 1, 2):
        out.add(str((now + _dt.timedelta(days=k)).day))
    return out


def _tamil_words(t):
    return [w for w in re.findall(r"[\u0B80-\u0BFF]+", t or "") if len(w) >= 4]


def _stem(w):
    return w[:4]


def grounding_problems(d, article):
    """a draft built from the article re-uses the article's words. Invented places/garbled words do not appear in it."""
    art_words = _tamil_words(article)
    stems = {_stem(w) for w in art_words}
    out = []
    # 1) the place named in the headline / location must be in the article
    for fld in ("tamil_headline",):
        for w in _tamil_words(d.get(fld, ""))[:3]:
            if re.search(r"(ூர்|புரம்|பாளையம்|பட்டி|பேட்டை|கோடு|மலை|நகர்|பாளை|ம்பட்டி)", w) and _stem(w) not in stems:
                out.append(f"not grounded: place word '{w}' is not in the article")
    loc = (d.get("slides_spec") or {}).get("loc", "")
    for w in _tamil_words(loc):
        if _stem(w) not in stems and w not in ("மாவட்டம்", "நாமக்கல்"):
            out.append(f"not grounded: location '{w}' is not in the article")
    # 2) most words of the reel script and slides must come from the article
    body = LAST
    rs = (d.get("reel_script") or "").replace(body, "")
    sl = " ".join(l for s_ in (d.get("slides_spec") or {}).get("slides", []) for l in s_.get("lines", []))
    words = _tamil_words(rs + " " + _tags(sl))
    if words:
        miss = [w for w in words if _stem(w) not in stems]
        ratio = 1 - len(miss) / len(words)
        if ratio < 0.5:
            out.append(f"not grounded: only {int(ratio*100)}% of the words come from the article (e.g. {', '.join(miss[:5])}); use the article's own words and facts")
    return out


def _cut(text, n):
    """shorten to at most n characters at a word boundary (keeps the words that fit; the facts stay whole)"""
    t = (text or "").strip()
    if len(t) <= n:
        return t
    c = t[:n]
    return (c[:c.rfind(" ")] if " " in c else c).rstrip(" ,;:-")


def autofix(d):
    """Small mechanical repairs of a draft, done BEFORE the checks, so a fine story is not thrown away for a length or a label.
    It never adds or changes a fact: it only shortens lines at a word boundary, fixes the version number and the page label."""
    if not isinstance(d, dict):
        return d
    sp = d.get("slides_spec")
    if isinstance(sp, dict):
        sp["v"] = 3
        sp["hl1"] = _cut(sp.get("hl1", ""), 40)
        sp["hl2"] = _cut(sp.get("hl2", ""), 28)
        sl = sp.get("slides") or []
        sl = sl[:4]
        for x in sl:
            tt = x.get("title", "")
            if len(_tags(tt)) > 18:
                x["title"] = _cut(tt, 18)
            ln = x.get("lines") or []
            x["lines"] = [_cut(l, 60) if len(_tags(l)) > 60 else l for l in ln[:3]]
        sp["slides"] = sl
    pt = str(d.get("post_to") or "")
    if not pt.startswith("Namakkal 360"):
        d["post_to"] = "Namakkal 360"
    return d


META = ["கட்டுரை", "தகவல் இல்லை", "விவரம் இல்லை", "தெரியவந்ததும் பகிரப்படும்", "தொடர்புடையது அல்ல", "செய்தியில் இல்லை",
        "குறிப்பிடப்படவில்லை", "the article", "this article", "not mentioned in", "no information"]


def _reach():
    """owner 29 Oct views plan: poster/config.json "reach" switches ({} = the old behaviour)"""
    try:
        from pathlib import Path
        return json.loads((Path(__file__).resolve().parent.parent / "poster" / "config.json").read_text(encoding="utf-8")).get("reach") or {}
    except Exception:
        return {}


def caption_problems(cap, reach=None):
    """the caption carries the FULL story (viewers ask for 'full details') and one English search line"""
    reach = _reach() if reach is None else reach
    p = []
    lines = [l.strip() for l in str(cap or "").split("\n")]
    if reach.get("caption_full_details"):
        if not any("முழு விவரம்" in l for l in lines):
            p.append('caption has no "📰 முழு விவரம்:" block - put the whole story (every fact) in the caption')
        else:
            i = next(k for k, l in enumerate(lines) if "முழு விவரம்" in l)
            body = [l for l in lines[i + 1:] if len(l.split()) >= 4 and not l.startswith("#")]
            if len(body) < 3:
                p.append("caption full details are too short - at least 3-4 sentences with every fact of the article")
    return p      # the English search line is ADDED at posting when missing (poster/post.py final_caption) - no rewrite needed


def validate(d, article, today_digits=("2026",)):
    p = []
    if not isinstance(d, dict):
        return ["output is not a JSON object"]
    for k in KEYS:
        if not d.get(k):
            p.append(f"missing key: {k}")
    if p:
        return p
    # 29 Oct (RN-189, deleted by the owner): the paper's page had no news, and the model wrote ABOUT the article ("the price is not given
    # in this article ... will be shared when known") and mixed in another story. A news reel never talks about "the article".
    for k in ("reel_script", "caption", "tamil_headline"):
        t = re.sub(r"கட்டுரைப்?\s*போட்டி", " ", str(d.get(k) or ""))      # an essay competition is real school news
        hit = [w for w in META if w.lower() in t.lower()]
        if hit:
            p.append(f"{k} talks about the article instead of the news ({hit[0]}) - if the article has no real news, return an empty reel_script")
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
    # scenes: the reel is built from reel_script, so the count of scenes does not block a story
    rs = d["reel_script"].strip()
    if re.search(r"[A-Za-z]", rs):
        p.append("reel_script must have no English letters (write English words and abbreviations in Tamil script)")
    if not rs.endswith(LAST):
        p.append("reel_script must end with exactly: " + LAST)
    wc = len(rs.split())
    maxw = int(_reach().get("script_max_words") or 170)      # owner 29 Oct: reels at most 60 s (105 words); the caption keeps every detail
    need = min(130, int(len(_tamil_words(article)) * 0.55)) if article else 60      # owner 28 Oct: full detail - a longer article needs a longer reel
    need = min(need, maxw - 20)
    if not max(60, need) <= wc <= maxw + 5:
        p.append(f"reel_script has {wc} words; need {max(60, need)}-{maxw} (the key facts once each, in at most {60 if maxw <= 110 else 90} seconds; "
                 "every other detail goes in the caption's 📰 முழு விவரம் block)")
    ages = re.findall(r"[\u0B80-\u0BFF]+,\s?\d{1,2},", rs)
    if ages:      # owner 28 Oct (RN-158): "ராஜா, 12," is newspaper shorthand; read aloud it is confusing
        p.append(f"reel_script writes ages as newspaper shorthand ({', '.join(ages[:3])}); say it as a news reader: '12 வயது மகன் ராஜா', 'கவுசிக் (14 வயது)' -> '14 வயதான கவுசிக்'")
    first = rs.split(".")[0].split()
    if len(first) > 11:      # owner 28 Oct: the one-line story is heard in the first 2-3 seconds, then the explanation
        p.append(f"sentence 1 (one-line story) has {len(first)} words; make it 6-9 words (about 2-3 seconds), the details follow in the next sentences")
    MONTHS = "ஜனவரி|பிப்ரவரி|மார்ச்|ஏப்ரல்|மே|ஜூன்|ஜூலை|ஆகஸ்ட்|செப்டம்பர்|அக்டோபர்|நவம்பர்|டிசம்பர்"
    bare = [m.group(0).strip() for m in re.finditer(r"(?:^|[\s,(])(\d{1,3}(?:,\d{3})*)(?=\s*[,.)](?:\s|$))", rs)
            if not re.search(rf"({MONTHS}|வயது)[\s\d,]*$", rs[max(0, m.start(1) - 30):m.start(1)])]      # "அக்டோபர் 13, 14, 15", "வயது 40" are clear
    if bare:      # owner 28 Oct: "ஸ்ரீதர், 15," - a number with no word is not understood when it is heard
        p.append(f"reel_script has numbers without their meaning ({', '.join(bare[:4])}); write what each number is: '15 வயது', '30 பாட்டில்கள்', 'அக்டோபர் 26ஆம் தேதி'")
    if "வணக்கம்" in rs.split(".")[0]:
        p.append("reel_script must not start with a greeting")
    cap = d["caption"]
    if FOLLOW not in cap:
        p.append("caption must contain the exact follow line")
    tags = re.findall(r"#\S+", cap)
    if not 3 <= len(tags) <= 5:
        p.append(f"caption needs 5 hashtags (Instagram max), has {len(tags)}")
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
    src = _digits_in(article) | set(today_digits) | _calendar_digits() | {"1", "2", "3", "4", "5"}
    text = " ".join([d["tamil_headline"], d["english_headline"], _tags(json.dumps(sp, ensure_ascii=False)), cap.split("#")[0], rs])      # the spoken script too
    stray = sorted(n for n in _digits_in(text) if n not in src and len(n) > 0 and n not in ("0", "360"))
    if stray:
        p.append("numbers not found in the article: " + ", ".join(stray[:6]))
    p += grounding_problems(d, article)
    blob_all = " ".join([d.get("tamil_headline", ""), rs, cap, json.dumps(sp, ensure_ascii=False)])
    foreign = sorted(set(re.findall(r"[\u0900-\u0B7F\u0C00-\u0D7F\u3040-\u30FF\u3400-\u9FFF\uAC00-\uD7AF]", blob_all)))
    if foreign:      # owner 29 Oct: letters of another script inside Tamil words (Coimbatore RN-5, RN-20 ...)
        p.append("letters of another script inside Tamil words: " + " ".join(foreign[:8]) + " - write every word only in Tamil letters")
    try:
        from verify import tamil_sequence_problems
        for t in [d["tamil_headline"], rs, _tags(cap)]:
            p += tamil_sequence_problems(t) or []
    except Exception:
        pass
    p += caption_problems(d.get("caption"))
    try:      # owner 29 Oct: every known issue is checked here AND right before posting (research_free/known_issues.py)
        import known_issues
        seen = " ".join(p)
        for iid, why in known_issues.problems(d):
            if why not in seen:
                p.append(f"known issue {iid}: {why} - rewrite so it does not happen again")
    except ImportError:
        pass
    return p
