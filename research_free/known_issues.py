"""Known issues that must NEVER repeat (owner 29 Oct: "once an issue is found, the automatic creating and posting must not repeat it").

Every issue found in a posted reel gets ONE entry here: the pattern that catches it, the story it came from, a real bad example and a good
one. The SAME list is checked
  - when a story is written (research_free/validate.py -> the writer rewrites it), and
  - right before posting (poster/post.py skip_reason -> a story written before the fix is not posted).
tests/test_regressions.py runs every entry against its own examples, so an entry that stops catching its issue fails the tests.
To add an issue: add an entry with its bad and good example; nothing else needs changing."""
import json, re

DANGLING = re.compile(r"(க்|ச்|த்|ப்)$")
FOREIGN = re.compile(r"[ঀ-૿ఀ-෿　-鿿가-힯Ѐ-ӿ؀-ۿ]")
META = ["கட்டுரை", "தகவல் இல்லை", "விவரம் இல்லை", "தெரியவந்ததும் பகிரப்படும்", "தொடர்புடையது அல்ல", "செய்தியில் இல்லை",
        "குறிப்பிடப்படவில்லை", "the article", "this article", "not mentioned in", "no information"]


def texts(story):
    """the words a viewer sees or hears, from a writer draft (tamil_headline, slides_spec dict) or a Sheet row (headline_ta, slides_spec JSON)"""
    sp = story.get("slides_spec") or {}
    if isinstance(sp, str):
        try:
            sp = json.loads(sp)
        except Exception:
            sp = {}
    cards = [re.sub(r"<[^>]+>", "", str(ln)) for sl in (sp.get("slides") or []) for ln in (sl.get("lines") or [])]
    return {"headline": str(story.get("tamil_headline") or story.get("headline_ta") or ""), "script": str(story.get("reel_script") or ""),
            "caption": str(story.get("caption") or ""), "cards": cards}


def _meta(t):
    for k in ("headline", "script", "caption"):
        s = re.sub(r"கட்டுரைப்?\s*போட்டி", " ", t[k])      # an essay competition is real school news
        hit = next((w for w in META if w.lower() in s.lower()), "")
        if hit:
            return f"{k} talks about the article instead of the news ('{hit}')"
    return ""


def _foreign(t):
    for k in ("headline", "script", "caption"):
        bad = FOREIGN.findall(t[k])
        if bad:
            return f"{k} has letters of another script ({''.join(bad[:4])})"
    return next((f"card has letters of another script ({''.join(FOREIGN.findall(c)[:4])})" for c in t["cards"] if FOREIGN.search(c)), "")


def _english(t):
    eng = sorted(set(re.findall(r"[A-Za-z]{2,}", t["script"])))
    return f"voice script has English words the voice skips ({', '.join(eng[:4])})" if eng else ""


def _dangling(t):
    bad = next((c for c in t["cards"] if DANGLING.search(c.strip(" .,;:"))), "")
    return f"card cut off mid-phrase ('{bad[-24:]}')" if bad else ""


# normal Tamil doubling ('விடிய விடிய மழை' = rain all night) is not a mistake
REDUP = {"விடிய", "மெல்ல", "மெதுவாக", "சிறிது", "கொஞ்சம்", "ஓடி", "வேகமாக", "அங்கும்", "இங்கும்", "தனித்தனி", "ஒவ்வொன்றாக", "பல", "சில",
         "நாள்", "வீடு", "ஊர்", "தெரு", "கடகட", "பளபள", "மளமள", "சலசல", "திடீர்", "மீண்டும்", "நன்றாக"}


def _repeat(t):
    w = t["script"].split()
    rep = next((a for a, b in zip(w, w[1:]) if a == b and len(a) > 3 and a not in REDUP), "")      # 'எஸ் எஸ்' (a name) is fine
    if rep:
        return f"word said twice in a row ('{rep}')"
    sents = [s.strip() for s in re.split(r"[.!?]", t["script"]) if len(s.strip()) > 15]
    return "the same sentence is read twice" if len(sents) != len(set(sents)) else ""


# id, first seen, check, a real bad example, a good example
ISSUES = [
    ("meta_article", "Namakkal RN-189 (29 Oct, deleted by the owner)", _meta,
     {"headline_ta": "முட்டை விலை நிலவரம்", "reel_script": "முட்டை விலை விவரம் இந்தக் கட்டுரையில் வெளியிடப்படவில்லை. தெரியவந்ததும் பகிரப்படும்."},
     {"headline_ta": "முட்டை விலை ரூ.5.70", "reel_script": "நாமக்கல் மண்டலத்தில் முட்டை விலை ரூ.5.70 ஆக நீடிக்கிறது."}),
    ("foreign_script", "Coimbatore RN-20 (29 Oct)", _foreign,
     {"headline_ta": "ச監獄탈옥: குறைந்த பணியாளர், பயிற்சি பற்றாக்குறை", "reel_script": "சிறைக் காவலர் பற்றாக்குறை."},
     {"headline_ta": "சிறைக் காவலர் பற்றாக்குறை", "reel_script": "சிறைக் காவலர் பற்றாக்குறை."}),
    ("english_in_voice", "Coimbatore RN-34 (29 Oct)", _english,
     {"reel_script": "ஜெர்மனியில் FBN Global Summit மாநாடு நடந்தது."},
     {"reel_script": "ஜெர்மனியில் எஃப்பிஎன் உலக உச்சி மாநாடு நடந்தது."}),
    ("card_cut_mid_phrase", "Coimbatore RN-34 (29 Oct)", _dangling,
     {"slides_spec": {"slides": [{"lines": ["குடும்பத் தொழில்முனைவு பிரிவில் உலகளவில் சிறந்த 3 இறுதிப்"]}]}},
     {"slides_spec": {"slides": [{"lines": ["உலகளவில் சிறந்த 3 நிறுவனங்களில் ஒன்று"]}]}}),
    ("repeated_words", "Namakkal RN-158 (28 Oct)", _repeat,
     {"reel_script": "பள்ளிக்குச் செல்லாமல் செல்லாமல் பிறந்த நாள் கொண்டாடினர்."},
     {"reel_script": "பள்ளிக்குச் செல்லாமல் பிறந்த நாள் கொண்டாடினர். விடிய விடிய மழை பெய்தது. எஸ் எஸ் கன்ஸ்ட்ரக்சன் மூலம் பணி."}),
]


def problems(story):
    """[(issue id, what is wrong)] for every known issue found in this draft or Sheet row"""
    t = texts(story)
    out = []
    for iid, _, check, _, _ in ISSUES:
        why = check(t)
        if why:
            out.append((iid, why))
    return out
