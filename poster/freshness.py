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


# ---- repeating topics (daily egg price, gold rate, fuel price ...): the same headline every day is NEW news each day
RECUR = re.compile(r"முட்டை\s*(விலை|கொள்முதல்)|egg\s*(price|rate)|தங்கம்\s*விலை|gold\s*(rate|price)|பெட்ரோல்\s*விலை|டீசல்\s*விலை|petrol|diesel", re.I)


def recurring(text):
    return bool(RECUR.search(text or ""))


def different_numbers(a, b):
    """both headlines give numbers and none of them match: a different event (8 arrested / Rs 1,47,000 is not 6 people / Rs 11,600)"""
    na = set(re.findall(r"\d+", (a or "").replace(",", "")))
    nb = set(re.findall(r"\d+", (b or "").replace(",", "")))
    return bool(na) and bool(nb) and not (na & nb)


def similar(a, b, thr, other_filed=None, today=None):
    """True when headline a and b are the same news. A repeating-price topic (e.g. today's egg price) counts as the same
    only when the other story was filed the same day - tomorrow's price is a new post."""
    import difflib
    if not a or not b or difflib.SequenceMatcher(None, a, b).ratio() <= thr or different_numbers(a, b):
        return False
    if recurring(a) or recurring(b):
        today = today or datetime.datetime.now(IST).date()
        return pub_date(other_filed) == today
    return True
