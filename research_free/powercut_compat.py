"""Namakkal power-cut lane (research_free/powercut.py): the power-cut helpers of the Coimbatore copy of poster/freshness.py, kept
here so the Namakkal poster's own freshness.py - and with it every other story - stays exactly as it was. Only powercut.py uses this."""
import datetime, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "poster"))
from freshness import IST, TOMORROW, dates_in, power_cut_over, pub_date      # noqa: E402,F401


POWER = re.compile(r"மின்\s*தடை|மின்\s*நிறுத்த|power\s*(cut|shut)", re.I)


POWER_ANY = re.compile(r"(?:" + POWER.pattern + r"|மின்\s*வெட்டு|மின்\s*விநியோகம்\s*(?:நிறுத்த|தடை))(?!க்கும்|யால்)", re.I)      # not a bare 'shutdown' (TASMAC / shop shutdown); 31 Oct: not 'மின் தடைக்கும்' (a remark) / 'மின் தடையால்' (a complaint)


def is_power_cut(*texts):
    """owner 30 Oct (Coimbatore): the ONE test for 'this is a power-cut notice' - such a reel may run to 90 s, is judged by the day of
    the cut (power_cut_ahead) and is never held back by a daily cap"""
    return bool(POWER_ANY.search(" ".join(str(t or "") for t in texts)))


NUM_DATE = re.compile(r"(?<![\d.])(\d{1,2})[./-](\d{1,2})[./-](20\d\d|\d\d)(?![\d.])")


def _num_dates(text):
    """day-first number dates of power-cut notices: 'நாளை 29.10.26', '(29.10.2026)', '30-10-2026' (30 Oct archive titles)"""
    out = []
    for m in NUM_DATE.finditer(text or ""):
        y = int(m.group(3))
        try:
            out.append(datetime.date(y + 2000 if y < 100 else y, int(m.group(2)), int(m.group(1))))
        except ValueError:
            pass
    return out


_POWER_COMMON = ("மின்", "தடை", "நாளை", "இன்று", "இன்றை", "காலை", "மதியம", "மாலை", "வரை", "முதல்", "பகுதி", "துணை", "நிலைய",
                 "பராமர", "பணி", "காரண", "அறிவி", "மணி", "கோவை", "கோயம்", "மாவட", "எந்தெ", "power", "cut", "shut", "tomorr", "today",
                 "areas", "mainte", "substa", "kovai", "coimb", "நாமக்", "namak", "from", "till", "will", "the")


_PLACE_COMMON = _POWER_COMMON + ("நகர்", "நகரில்", "காலனி", "சாலை", "ரோடு", "வீதி", "தெரு", "கிராம", "ஊராட்", "பஞ்சா", "மற்றும்", "உள்ளிட்",
                                 "இடங்க", "இடங்கள", "விநியோ", "நிறுத்", "பகுதிக", "தமிழ்", "முக்கி", "அறிவிப்")


def cut_day(headline, published):
    """the day of the cut a power-cut headline announces: its own date ('29.10.26', '30 அக்டோபர்'), else the day after publishing
    for 'நாளை', else the day it was published"""
    pub = pub_date(published)
    ref = pub or datetime.datetime.now(IST).date()
    ds = [d for d in dates_in(headline or "", ref.year) + _num_dates(headline) if abs((d - ref).days) < 300]
    if ds:
        return max(ds), True
    if pub and TOMORROW.search(headline or ""):
        return pub + datetime.timedelta(days=1), False
    return pub, False


def same_power_cut(a, a_published, b, b_published):
    """owner 30 Oct (Coimbatore): two power-cut notices are the SAME news when they announce the same cut day and name the same place
    ('நாளை காளப்பட்டியில் மின் தடை' posted last night = 'காளப்பட்டி பகுதியில் இன்று மின் தடை' this morning). The headline check alone
    misses these (different words). Without a shared place nothing is blocked: a power cut is never lost as a false duplicate.
    A day from 'நாளை' may be one day off (posted after midnight, Instagram time), so it may differ by 1; two printed dates must match."""
    if not (is_power_cut(a) and is_power_cut(b)):
        return False
    (da, fa), (db, fb) = cut_day(a, a_published), cut_day(b, b_published)
    if not da or not db or abs((da - db).days) > (0 if fa and fb else 1):
        return False
    def places(t):
        return {w[:6] for w in re.findall(r"[\u0B80-\u0BFFa-zA-Z]{4,}", (t or "").lower()) if not w.startswith(_PLACE_COMMON)}
    return bool(places(a) & places(b))


# owner 11 Nov: a power cut and its cancellation / change are never the same notice (freshness.cancel_differs)
_same_power_cut = same_power_cut


def same_power_cut(a, a_published, b, b_published):
    from freshness import cancel_differs
    return False if cancel_differs(a, b) else _same_power_cut(a, a_published, b, b_published)
