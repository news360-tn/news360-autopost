"""owner 26 Nov: the FACT GATE of the daily lanes (history/, jobs/). Nothing is posted unless every number, year and date in the post
can be found in the sourced material (the topic's fact sheet / the fetched official notice). Pure functions - no network, no keys.

  unsupported_numbers(text, allowed_text)   numbers / number words in the post that the source does not contain
  value_in_text(value, text)                a value written the way the source writes it (spacing / case / commas ignored)
  date_in_text(day, text)                   a date in any of the usual ways an official notice writes it
  check_history_lines(lines, sheet)         -> [problems] for the history narration (empty list = fine)"""
import re
from datetime import date

TA_DIGITS = str.maketrans("௦௧௨௩௪௫௬௭௮௯", "0123456789")
# number WORDS (a narration may write "ஆயிரம்" instead of 1,000): if the post uses one, the sheet must contain it too
NUMBER_WORDS = ("ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து", "ஆறு", "ஏழு", "எட்டு", "ஒன்பது", "பத்து", "இருபது", "முப்பது", "நாற்பது",
                "ஐம்பது", "அறுபது", "எழுபது", "எண்பது", "தொண்ணூறு", "நூறு", "நூற்று", "ஆயிரம்", "லட்சம்", "கோடி")
HEDGES = ("நம்பிக்கை", "கதை", "புராணம்", "மரபு", "சொல்லப்படுகிறது", "சொல்வர்", "கூறப்படுகிறது", "நம்புகின்றனர்", "வழக்கு")
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MONTHS_TA = ["ஜனவரி", "பிப்ரவரி", "மார்ச்", "ஏப்ரல்", "மே", "ஜூன்", "ஜூலை", "ஆகஸ்ட்", "செப்டம்பர்", "அக்டோபர்", "நவம்பர்", "டிசம்பர்"]


def norm(s):
    """lower case, Tamil digits -> 0-9, commas inside numbers removed, spaces collapsed"""
    s = str(s or "").translate(TA_DIGITS).lower()
    s = re.sub(r"(?<=\d),(?=\d)", "", s)
    return re.sub(r"\s+", " ", s).strip()


def numbers_in(text):
    return set(re.findall(r"\d+(?:\.\d+)?", norm(text)))


def number_words_in(text):
    t = str(text or "")
    return {w for w in NUMBER_WORDS if w in t}


def unsupported_numbers(text, allowed_text):
    """digits and number words used in `text` that `allowed_text` does not contain (sorted list)"""
    bad = sorted(numbers_in(text) - numbers_in(allowed_text))
    bad += sorted(number_words_in(text) - number_words_in(allowed_text))
    return bad


def _squash(s):
    return re.sub(r"[\s\-–—.,:;()\[\]/\\]+", "", norm(s))


def value_in_text(value, text):
    """True when `value` appears in `text` the way the source writes it (case, spaces, commas and light punctuation ignored)"""
    v = _squash(value)
    return bool(v) and v in _squash(text)


def date_forms(d):
    """the ways an official notice writes a date"""
    dd, mm, yy = d.day, d.month, d.year
    en, ta = MONTHS_EN[mm - 1], MONTHS_TA[mm - 1]
    forms = set()
    for day in (str(dd), f"{dd:02d}"):
        for mon in (str(mm), f"{mm:02d}"):
            for sep in ("/", ".", "-"):
                forms.add(f"{day}{sep}{mon}{sep}{yy}")
                forms.add(f"{day}{sep}{mon}{sep}{str(yy)[2:]}")
        for name in (en, en[:3], ta):
            forms.update({f"{day} {name} {yy}", f"{day}-{name}-{yy}", f"{day} {name}, {yy}", f"{name} {day}, {yy}", f"{name} {day} {yy}",
                          f"{day}th {name} {yy}", f"{day}st {name} {yy}", f"{day}nd {name} {yy}", f"{day}rd {name} {yy}"})
    forms.add(f"{yy}-{mm:02d}-{dd:02d}")
    return {_squash(f) for f in forms}


def date_in_text(d, text):
    t = _squash(text)
    return any(f in t for f in date_forms(d))


def check_history_lines(lines, sheet):
    """lines: [{"text": ..., "facts": [fact ids]}]; sheet: the topic dict (facts, avoid_regex, people). -> [problem strings]"""
    problems = []
    facts = {f["id"]: f for f in sheet.get("facts", [])}
    allowed = " ".join(f.get("ta", "") for f in facts.values()) + " " + str(sheet.get("title_ta", "")) + " " + str(sheet.get("town_ta", ""))
    avoid = [re.compile(p) for p in sheet.get("avoid_regex", [])]
    if not lines:
        return ["no narration lines"]
    for i, ln in enumerate(lines, 1):
        text = str(ln.get("text", "")).strip()
        if not text:
            problems.append(f"line {i}: empty")
            continue
        bad = unsupported_numbers(text, allowed)
        if bad:
            problems.append(f"line {i}: number(s) not in the fact sheet: {', '.join(bad)}")
        for rx in avoid:
            if rx.search(text):
                problems.append(f"line {i}: says something the sources disagree on ({rx.pattern})")
        used = [facts[x] for x in ln.get("facts", []) if x in facts]
        unknown = [x for x in ln.get("facts", []) if x not in facts]
        if unknown:
            problems.append(f"line {i}: uses fact id(s) that are not on the sheet: {', '.join(map(str, unknown))}")
        if any(f.get("kind") == "tradition" for f in used) and not any(h in text for h in HEDGES):
            problems.append(f"line {i}: a legend is told as a fact (needs words like நம்பிக்கை / கதை)")
        if not used and not ln.get("frame"):      # an opening / closing line may be a "frame" line (no facts, but its numbers are still checked)
            problems.append(f"line {i}: not based on any fact of the sheet")
    return problems


def check_scene_prompts(prompts, sheet):
    """no real person's name in a picture prompt (no real-person likenesses)"""
    problems = []
    names = [n for n in sheet.get("people", []) if n]
    for i, p in enumerate(prompts, 1):
        low = str(p).lower()
        for n in names:
            if n.lower() in low:
                problems.append(f"scene {i}: names a real person ({n}) - pictures must not show real people")
    return problems
