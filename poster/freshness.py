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
    try:      # owner 29 Oct: an ISO time with a zone ('...T22:17:23Z' = 03:47 next morning in IST) is read in IST, not by its UTC date
        t = datetime.datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        if t.tzinfo is not None:
            return t.astimezone(IST).date()
    except ValueError:
        pass
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


RECUR_TOPICS = {"egg": re.compile(r"முட்டை\s*(விலை|கொள்முதல்)|egg\s*(price|rate)", re.I),
                "gold": re.compile(r"தங்கம்\s*விலை|gold\s*(rate|price)", re.I),
                "fuel": re.compile(r"பெட்ரோல்\s*விலை|டீசல்\s*விலை|petrol|diesel", re.I)}


def recur_topic(*texts):
    t = " ".join(x or "" for x in texts)
    return next((k for k, rx in RECUR_TOPICS.items() if rx.search(t)), "")


def same_day_recurring(old, new, today=None):
    """29 Oct (RN-188 + RN-189 both egg price): a daily price topic is posted ONCE a day, whatever the headline words"""
    k = recur_topic(old.get("headline_ta"), old.get("headline_en"))
    if not k or k != recur_topic(new.get("headline_ta"), new.get("headline_en")):
        return ""
    d_old = pub_date(old.get("researched"))
    d_new = pub_date(new.get("researched")) or today or datetime.datetime.now(IST).date()
    return k if d_old and d_old == d_new else ""


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


FOLLOW = re.compile(r"கைது|சிறை|தீர்ப்பு|மீட்பு|மீட்கப்|பறிமுதல்|இழப்பீடு|குற்றப்பத்திரிகை|ஜாமீன்|சரண்|உயிரிழப்பு|பலி|"
                    r"arrest|held|nabbed|sentenc|verdict|convict|rescued|recovered|seized|compensation|bail|surrender|died|dead", re.I)


def follow_up(old, new, days=2):
    """28 Oct (RN-159 '3 arrested for stealing laptops' was blocked as a duplicate of RN-42 'laptops stolen', 6 days earlier):
    a later report that brings a new development (arrest, verdict, rescue, seizure ...) about a story filed more than `days`
    days before is new news, not a duplicate"""
    o, n = pub_date(old.get("researched")), pub_date(new.get("researched"))
    if not o or not n or (n - o).days <= days:
        return False
    text = lambda r: (r.get("headline_ta") or "") + " " + (r.get("headline_en") or "")
    return bool(FOLLOW.search(text(new))) and not FOLLOW.search(text(old))


# owner 29 Oct (RN-189 egg price): a story that only says the article has no facts is NOT news and is never filed or posted.
# The writer sometimes "explains" a page it could not read (price in an image, wrong text scraped) instead of reporting news.
NO_NEWS_TA = ("கட்டுரையில் இல்லை", "கட்டுரையில் குறிப்பிடப்படவில்லை", "கட்டுரையில் வெளியிடப்படவில்லை", "இந்தக் கட்டுரையில்",
              "விவரம் இன்னும் தெரியவரவில்லை", "விவரம் தெரியவரவில்லை", "விவரம் இன்னும் தெரியவில்லை", "தகவல் இல்லை",
              "எண்ணோ தகவலோ இல்லை", "விவரம் கிடைத்ததும் பகிரப்படும்", "தெரியவந்ததும் பகிரப்படும்", "தொடர்புடையது அல்ல", "தொடர்பில்லை")
NO_NEWS_EN = ("not in the article", "not mentioned in the article", "article does not", "article doesn't", "no details available",
              "details not available", "details are not available", "will be shared when", "not related to")


def _meta(sentence):
    low = sentence.lower()
    return [x for x in NO_NEWS_TA if x in sentence] + [x for x in NO_NEWS_EN if x in low]


def _sentences(text):
    import re as _re
    return [x.strip() for x in _re.split(r"(?<=[.!?\u0964])\s+|\n+", str(text or "")) if x.strip()]


def no_news(headline, reel_script="", caption=""):
    """'' = real news. Otherwise why the story is only about missing facts: the headline/hook says so, or at least
    40% of the reel script's news sentences (the follow line not counted) talk about details that are missing."""
    found = _meta(str(headline or ""))
    if found:
        return f"not news: the headline says the details are missing ({found[0]})"
    sents = [x for x in _sentences(reel_script) if "பின்தொடரு" not in x and "follow" not in x.lower()]
    bad = [x for x in sents if _meta(x)]
    if sents and len(bad) / len(sents) >= 0.4:
        return f"not news: {len(bad)} of {len(sents)} sentences only say the article has no details"
    return ""


def strip_no_news(text):
    """remove the sentences/lines that only say a detail is missing from the article (the rest of a real story stays)"""
    import re as _re
    out = []
    for line in str(text or "").split("\n"):
        keep = [x for x in _re.split(r"(?<=[.!?\u0964])\s+", line) if not _meta(x)]
        if line.strip() and not "".join(keep).strip():
            continue
        out.append(" ".join(keep))
    return "\n".join(out)


# owner 29 Oct (Coimbatore RN-29, a 2025 wedding re-told in a new article): a story whose every dated fact is months old and that
# has no sign of anything happening now (today / yesterday / a weekday / "so far" / an arrest or verdict) is an old event.
RECENT_WORDS = ("இன்று", "நேற்று", "நேற்றிரவு", "முன்தினம்", "இன்றிரவு", "இந்த வாரம்", "நாளை", "இதுவரை", "தற்போது", "இன்னும்",
                "சமீபத்தில்", "திங்கள்", "செவ்வாய்", "புதன்", "வியாழ", "வெள்ளிக்கிழமை", "சனிக்கிழமை", "ஞாயிற்று")


def old_event(text, today=None):
    t = text or ""
    today = today or datetime.datetime.now(IST).date()
    if any(w in t for w in RECENT_WORDS) or FOLLOW.search(t):
        return ""
    if any(abs((d - today).days) <= 7 for d in dates_in(t, today.year)):
        return ""
    tam = {**TA_ABB, **TA_FULL}
    mon = "|".join(sorted(tam, key=len, reverse=True))
    olds = []
    for m in re.finditer(r"(\d{1,2})?\s*(%s)\.?\s*,?\s*(20\d\d)" % mon, t):
        try:
            olds.append(datetime.date(int(m.group(3)), tam[m.group(2)], int(m.group(1) or 1)))
        except (ValueError, KeyError):
            pass
    if olds and all((today - d).days >= 60 for d in olds):
        return f"old event: the story is about {max(olds):%d %b %Y}, nothing in it happened in the last days"
    return ""


# owner 29 Oct (Coimbatore RN-13 / RN-24 bus fight, Namakkal RN-86 / RN-115 Collector wall): the same event reported by two outlets
# in different words. Compared on the DISTINCTIVE words of the two reel scripts (words that appear in few other stories: names,
# places, numbers), not on the headline wording.
def _event_stems(t):
    t = re.sub(r"மேலும் செய்திகளுக்கு.*$", "", t or "")
    return {w[:5] for w in re.findall(r"[஀-௿]{5,}", t)} | set(re.findall(r"\d{2,}", t))


def event_df(scripts):
    import collections
    df = collections.Counter()
    for s in scripts:
        df.update(_event_stems(s))
    return df, max(1, len(scripts))


def same_event(a, b, df_n):
    df, n = df_n
    rare = lambda t: {s for s in _event_stems(t) if df[s] <= max(2, n * 0.05)}
    x, y = rare(a), rare(b)
    if len(x) < 4 or len(y) < 4:
        return False
    shared = len(x & y)
    r = shared / min(len(x), len(y))
    # 30 Oct RN-214 = RN-209 (short scripts, 8 shared rare stems, 0.62): short reports of one event share fewer words.
    # In 80 filed Namakkal stories no two different events shared more than 5 rare stems.
    return (shared >= 9 and r >= 0.45) or (shared >= 6 and r >= 0.55) or same_incident(a, b, df_n, shared, r)


# 31 Oct (Coimbatore RN-96 = RN-95, one prisoner's escape told by two outlets; earlier RN-39 = RN-76, RN-17 = RN-54 posted twice):
# word overlap cannot tell "the same event" from "the same kind of story" (two temple poojas share as many rare words as two reports of one
# escape). An INCIDENT is the same event when both reports name the same person or the same distinctive number - or share many rare words.
INCIDENT = {"escape": r"தப்பி", "arrest": r"கைது", "verdict": r"தண்டனை", "accident": r"விபத்து|மோதி", "death": r"உயிரிழ|பலி|சடலம",
            "fire": r"தீப்பிடி|தீப்பற்|தீ விபத்து", "transfer": r"இடமாற்ற", "seizure": r"பறிமுதல்", "fraud": r"மோசடி", "theft": r"திருட|கொள்ளை",
            "murder": r"கொலை"}
_NAME = (re.compile(r"([஀-௿]{3,})\s*\(\d{1,3}\)"), re.compile(r"([஀-௿]{3,})\s+(?:என்பவ|என்ற\s)"),
         re.compile(r"\d{1,3}\s*வயது(?:டைய|ான|ுடைய)?\s+([஀-௿]{3,})"))


def _incidents(t):
    return {k for k, p in INCIDENT.items() if re.search(p, t or "")}


# role words written like a name before an age ('இளைஞர் (25)', 'பெண் (40)') - not a person's name
_ROLES = ("இளைஞ", "வாலிப", "பெண்", "முதிய", "மூதாட", "தொழில", "விவசா", "மாணவ", "சிறுவ", "சிறுமி", "கணவர", "மனைவ", "டிரைவ", "ஓட்டுந",
          "கூலித", "ஒருவர", "நபர்", "தந்தை", "தாய்", "மகன்", "மகள்", "குழந்", "நண்பர", "உறவின", "ஊழியர", "காவலர", "போலீஸ", "அதிகா")


def _names(t):
    return {m.group(1)[:5] for p in _NAME for m in p.finditer(t or "") if not m.group(1).startswith(_ROLES)}


def _numbers(t):
    """distinctive numbers: 3+ digits or with a decimal point (2015, 2.25, 11.15) - not this year or last year, not round amounts"""
    y = datetime.datetime.now(IST).year
    t = re.sub(r"(?<=\d),(?=\d)", "", t or "")
    return {n for n in re.findall(r"\d+(?:\.\d+)?", t)
            if (len(n) >= 3 or "." in n) and n not in (str(y), str(y - 1)) and not ("." not in n and int(n) % 100 == 0)}      # 1,000 police / Rs 500 are not distinctive


def same_incident(a, b, df_n, shared=None, r=None):
    """two reports of one incident: a common incident type AND (the same rarely seen person's name, the same rarely seen distinctive number,
    or 8+ shared rare words). Two different poojas / health tips / recipes are no incident, so they are never matched here."""
    if not (_incidents(a) & _incidents(b)):
        return False
    df, n = df_n
    if any(df[x] <= 3 for x in _names(a) & _names(b)):
        return True
    if any("." in x or df[x] <= 3 for x in _numbers(a) & _numbers(b)):
        return True
    return shared is not None and shared >= 9 and r >= 0.3
