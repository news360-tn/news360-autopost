"""Date checks for announcement-type news (power cuts, job fairs / interviews, camps, 'today' / 'tomorrow' items):
such a story is only worth posting while the date it announces has not passed. Pure functions, used by the poster and by the collector."""
import datetime, re

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
EN_M = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
TA_FULL = {"ஜனவரி": 1, "பிப்ரவரி": 2, "மார்ச்": 3, "ஏப்ரல்": 4, "மே": 5, "ஜூன்": 6, "ஜூலை": 7, "ஆகஸ்ட்": 8, "செப்டம்பர்": 9, "அக்டோபர்": 10, "நவம்பர்": 11, "டிசம்பர்": 12}
TA_ABB = {"ஜன": 1, "பிப்": 2, "மார்": 3, "ஏப்": 4, "ஆக": 8, "செப்": 9, "அக்": 10, "நவ": 11, "டிச": 12}
TRIGGER = re.compile(r"மின்\s?தடை|power\s?cut|shutdown|வேலைவாய்ப்பு|job\s?fair|interview|recruitment|camp\b|முகாம்|நேர்முகத்|walk-?in|இன்று|நாளை|tonight|\btoday\b|\btomorrow\b", re.I)
SHUT = re.compile(r"மின்\s?தடை|power\s?cut|shutdown", re.I)
TODAY = re.compile(r"இன்று|\btoday\b|tonight", re.I)
TOMORROW = re.compile(r"நாளை|\btomorrow\b", re.I)


def _mon_en(t):
    return EN_M.get(t[:3].lower())


def dates_in(text, year):
    """explicit dates ('23 Oct', 'Oct 23', '23 அக்டோபர்', 'அக். 23') found in the text -> list of date objects"""
    out = []
    pats_en = [(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", 1, 2),
               (r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})\b", 2, 1)]
    for p, di, mi in pats_en:
        for m in re.finditer(p, text, re.I):
            out.append((int(m.group(di)), _mon_en(m.group(mi))))
    tamil_mon = "|".join(sorted(list(TA_FULL) + list(TA_ABB), key=len, reverse=True))
    tam = {**TA_ABB, **TA_FULL}
    for m in re.finditer(r"(\d{1,2})\s*-?\s*(%s)\.?(?![஀-௿])" % tamil_mon, text):
        out.append((int(m.group(1)), tam[m.group(2)]))
    for m in re.finditer(r"(%s)\.?\s*-?\s*(\d{1,2})(?!\d)" % tamil_mon, text):
        out.append((int(m.group(2)), tam[m.group(1)]))
    res = []
    for d, mo in out:
        try:
            res.append(datetime.date(year, mo, d))
        except (ValueError, TypeError):
            pass
    return res


def pub_date(s):
    """date of the 'published' cell: ISO or '21 Oct 2026, 05:24 IST'"""
    s = str(s or "")
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})", s)
    if m and _mon_en(m.group(2)):
        return datetime.date(int(m.group(3)), _mon_en(m.group(2)), int(m.group(1)))
    return None


def stale_reason(headline_ta, headline_en, category, published, today=None):
    """'' when the story is still current, else why it must not be posted"""
    today = today or datetime.datetime.now(IST).date()
    text = f"{headline_ta} {headline_en} {category}"
    price = bool(RECUR.search(text))
    if not TRIGGER.search(text) and not price:
        return ""
    pub = pub_date(published)
    ds = dates_in(f"{headline_ta} {headline_en}", today.year)
    ds = [d for d in ds if (d - today).days < 300]
    if ds:
        if max(ds) < today:
            return f"announced date {max(ds):%d %b} has passed"
        return ""
    if pub:
        if price and pub < today:           # a daily price is only news on the day it applies to
            return f"price news from {pub:%d %b}, not today"
        if TODAY.search(text) and pub < today:
            return f"says 'today' but was published {pub:%d %b}"
        if TOMORROW.search(text) and pub + datetime.timedelta(days=1) < today:
            return f"says 'tomorrow' but was published {pub:%d %b}"
        if SHUT.search(text) and pub < today and not TOMORROW.search(text):
            return f"power-cut notice from {pub:%d %b} with no date"
    return ""


def news_date(published, source_url="", filed=None):
    """the day the news was published: the 'published' cell, else the date in the newspaper's link (/2026/Oct/26/, 2026-10-26,
    dinakaran namakkal-261026-3), else the day it was filed (never earlier than the real day, so it can only be lenient)"""
    d = pub_date(published)
    if d:
        return d
    u = str(source_url or "")
    m = re.search(r"/(20\d\d)/([A-Za-z]{3})[a-z]*/(\d{1,2})/", u)
    if m and _mon_en(m.group(2)):
        return datetime.date(int(m.group(1)), _mon_en(m.group(2)), int(m.group(3)))
    m = re.search(r"/(20\d\d)[/-](\d{2})[/-](\d{2})(?:/|\b)", u)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.search(r"dinakaran\.com/district/[a-z]+-(\d{2})(\d{2})(\d{2})", u)
    if m:
        try:
            return datetime.date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return filed.date() if filed else None


def power_cut_over(headline_ta, headline_en, published, now=None):
    """'' or why a power-cut notice is too late to post: the cut is today and its end time ('மதியம் 2 வரை', 'till 5 pm') is less
    than 1 hour away or past. Checked even for stories filed today (27 Oct: a 9-2 cut was about to go out at 1:40 pm as 'tomorrow')."""
    text = f"{headline_ta} {headline_en}"
    if not SHUT.search(text):
        return ""
    now = now or datetime.datetime.now(IST)
    today, pub = now.date(), pub_date(published)
    ds = [d for d in dates_in(text, today.year) if abs((d - today).days) < 300]
    day = max(ds) if ds else (pub + datetime.timedelta(days=1) if pub and TOMORROW.search(text) else pub)
    if day != today:
        return ""
    m = (re.search(r"(மதியம்|மாலை|இரவு|பிற்பகல்)?\s*(\d{1,2})(?:[.:](\d{2}))?\s*(?:மணி\s*)?வரை", headline_ta or "")
         or re.search(r"(?:till|to|until)\s*(\d{1,2})(?:[.:](\d{2}))?\s*(pm|am)?", headline_en or "", re.I))
    if not m:
        return ""
    if m.re.pattern.startswith("(மதியம்"):
        pm, h, mi = bool(m.group(1)) or int(m.group(2)) <= 7, int(m.group(2)), int(m.group(3) or 0)
    else:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        pm = (m.group(3) or "").lower() == "pm" or (not m.group(3) and h <= 7)
    if pm and h < 12:
        h += 12
    end = now.replace(hour=min(h, 23), minute=mi, second=0, microsecond=0)
    if now >= end - datetime.timedelta(minutes=60):
        return f"power cut ends today at {end:%H:%M} - too late to post"
    return ""


# ---- repeating topics (daily egg price, gold rate, fuel price ...): the same headline every day is NEW news each day
RECUR = re.compile(r"முட்டை\s*(விலை|கொள்முதல்)|egg\s*(price|rate)|தங்கம்\s*விலை|gold\s*(rate|price)|பெட்ரோல்\s*விலை|டீசல்\s*விலை|petrol|diesel", re.I)


def recurring(text):
    return bool(RECUR.search(text or ""))


def different_numbers(a, b):
    """both headlines give numbers and none of them match: a different event (8 arrested / Rs 1,47,000 is not 6 people / Rs 11,600)"""
    na = set(re.findall(r"\d+", (a or "").replace(",", "")))
    nb = set(re.findall(r"\d+", (b or "").replace(",", "")))
    return bool(na) and bool(nb) and not (na & nb)


POWER = re.compile(r"மின்\s*தடை|மின்\s*நிறுத்த|power\s*(cut|shut)", re.I)
_POWER_COMMON = ("மின்", "தடை", "நாளை", "இன்று", "இன்றை", "காலை", "மதியம", "மாலை", "வரை", "முதல்", "பகுதி", "துணை", "நிலைய",
                 "பராமர", "பணி", "காரண", "அறிவி", "மணி", "நாமக்", "மாவட", "எந்தெ", "power", "cut", "shut", "tomorr", "today",
                 "areas", "mainte", "substa", "namakk", "from", "till", "will", "the")


def different_power_cut(a, b, other_filed=None, today=None):
    """two power-cut notices look alike ('நாளை மின்தடை ... 9 முதல் 2 வரை'); they are the same news only when they name the same
    place and were filed within 3 days (27 Oct: Kalappanaickenpatti's cut was skipped as a 'duplicate' of an older notice)"""
    if not (POWER.search(a or "") and POWER.search(b or "")):
        return False
    def places(t):
        return {w[:6] for w in re.findall(r"[\u0B80-\u0BFFa-zA-Z]{4,}", t.lower()) if not w.startswith(_POWER_COMMON)}
    pa, pb = places(a), places(b)
    if pa and pb and not (pa & pb):
        return True
    d = pub_date(other_filed)
    today = today or datetime.datetime.now(IST).date()
    return bool(d and (today - d).days >= 3)


_GENERIC = ("நாமக்", "ராசிப", "இராசி", "மாவட்", "namak", "rasip", "அருகே", "அருகில்", "இன்று", "நாளை", "நேற்று", "உயிரிழ",
            "தொழிலா", "கைது", "பகுதி", "நடந்த", "வழங்க")


def shares_words(a, b):
    """Tamil headlines share many letters, so a letter match alone is weak (27 Oct: 'நாமக்கல் நீதிமன்றத்திலிருந்து தப்பியோடிய
    கைதி பிடிப்பு' was taken for 'நாமக்கல்லில் நீதிமன்ற உத்தரவுப்படி ஆர்எஸ்எஸ் ஊர்வலம்'). The same news also shares a third of
    its own words (place names and common words left out), or is almost letter-for-letter the same."""
    import difflib
    n = lambda t: (t or "").replace("ா்", "ர்").lower()
    w = lambda t: {x[:4] for x in re.findall(r"[\u0B80-\u0BFFa-z0-9]{3,}", n(t)) if not x.startswith(_GENERIC)}
    x, y = w(a), w(b)
    if x and y and len(x & y) / min(len(x), len(y)) >= 0.34:
        return True
    return difflib.SequenceMatcher(None, n(a), n(b)).ratio() >= 0.75


def similar(a, b, thr, other_filed=None, today=None):
    """True when headline a and b are the same news. A repeating-price topic (e.g. today's egg price) counts as the same
    only when the other story was filed the same day - tomorrow's price is a new post."""
    import difflib
    if (not a or not b or difflib.SequenceMatcher(None, a, b).ratio() <= thr or different_numbers(a, b)
            or different_power_cut(a, b, other_filed, today) or not shares_words(a, b)):
        return False
    if recurring(a) or recurring(b):
        today = today or datetime.datetime.now(IST).date()
        return pub_date(other_filed) == today
    return True
