"""Write our own short rasipalan (4 labelled lines per rasi + stars) from today's sources, then check and proofread it.

Never copies: every line is our own short wording of what most sources agree on. The remedy (பரிகாரம்) is a fixed, simple worship
for the rasi's ruling planet - not taken from any outlet. Checks: all 12 rasis, every field present and short, Tamil only, no
4-word run copied from a source, no fear words, stars 1-5 (chandrashtamam rasi at most 2). A failed check is sent back to the
model with the reasons (3 tries); if it still fails, nothing is posted."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research_free"))
import llm      # noqa: E402

RASI = ["மேஷம்", "ரிஷபம்", "மிதுனம்", "கடகம்", "சிம்மம்", "கன்னி", "துலாம்", "விருச்சிகம்", "தனுசு", "மகரம்", "கும்பம்", "மீனம்"]
FIELDS = ["work", "money", "family", "health"]
LABELS = {"work": "தொழில்", "money": "பணம்", "family": "குடும்பம்", "health": "உடல்நலம்", "remedy": "பரிகாரம்"}
# ruling planet worship (traditional, positive, free)
REMEDY = {"மேஷம்": "முருகன் வழிபாடு", "விருச்சிகம்": "முருகன் வழிபாடு", "ரிஷபம்": "மகாலட்சுமி வழிபாடு", "துலாம்": "மகாலட்சுமி வழிபாடு",
          "மிதுனம்": "பெருமாள் வழிபாடு", "கன்னி": "பெருமாள் வழிபாடு", "கடகம்": "அம்மன் வழிபாடு", "சிம்மம்": "சூரிய நமஸ்காரம்",
          "தனுசு": "குரு பகவான் வழிபாடு", "மீனம்": "குரு பகவான் வழிபாடு", "மகரம்": "சனீஸ்வரர் வழிபாடு", "கும்பம்": "ஆஞ்சநேயர் வழிபாடு"}
FEAR = ("கெட்ட", "மரண", "சாவு", "உயிரிழ", "விபத்து நேர", "ஆபத்து", "கண்டம்", "துரதிர்ஷ்ட", "சாபம்", "பில்லி", "சூனிய", "ஆபரேஷன்", "நோய் தீவிர")
MAX_CHARS = 30      # code points; the renderer also shrinks a line that is still too wide

SYSTEM = """You are a senior Tamil astrology editor writing a daily rasipalan for a Tamil Instagram page read by Tamil Nadu families.
You get today's rasipalan for all 12 rasis from 2-4 Tamil outlets. For EACH rasi write OUR OWN short lines:
  work   - தொழில் / வேலை / வியாபாரம்
  money  - பணம் / வருமானம் / செலவு
  family - குடும்பம் / உறவு / நண்பர்கள்
  health - உடல்நலம் / மனநிலை
and a star rating 1-5 for the day (5 = very good).
RULES:
- Use only what the sources say; where they disagree, follow the majority; never invent events. If no source mentions health, write a
  gentle neutral health line (e.g. "உடல்நலம் சீராக இருக்கும்").
- Each line: ONE short, complete, natural Tamil sentence of 3-6 words, at most 28 Tamil characters, ending without a full stop.
- Write in your own words: never copy 4 or more consecutive words from any source.
- Pure Tamil script (no English words), correct spelling and sandhi, formal written Tamil (not spoken forms).
- Positive and caring tone; cautions are gentle ("கவனம் தேவை", "பொறுமை அவசியம்"). Never fear words (death, accident, danger, curse).
- Stars: 5 = clearly very good in most sources, 4 = good, 3 = mixed, 2 = needs care, 1 = difficult. Be honest, not all 4-5.
Return ONLY JSON: {"rasis":[{"rasi":"மேஷம்","stars":4,"work":"...","money":"...","family":"...","health":"..."}, ... all 12 in order]}"""

PROOF = """You are a strict Tamil proofreader. You get short Tamil rasipalan lines as JSON {key: line}.
Fix ONLY real mistakes: spelling, sandhi (புணர்ச்சி, missing க்/ச்/த்/ப் doubling), wrong case ending or verb form, a word that does
not exist, spoken/colloquial forms, English words. Never change the meaning, never add or remove a "not", keep each line short.
Return ONLY JSON: {"fixes": {"key": "corrected full line", ...}} - only keys that need a change; {} when all are correct."""


def ask(system, user, log=print):
    try:
        return llm.ask_json(system, user)
    except Exception as e:
        log("  free models:", str(e)[:150])
        if llm.claude_available():
            return llm.ask_claude(system, user, max_tokens=6000)
        raise


def words(t):
    return re.findall(r"[஀-௿]+", t or "")


def copied(line, sources_text):
    w = words(line)
    for i in range(len(w) - 3):
        if " ".join(w[i:i + 4]) in sources_text:
            return " ".join(w[i:i + 4])
    return ""


def check(data, sources, chandra):
    errs = []
    src = " ".join(" ".join(words(t)) for s in sources for t in s["rasis"].values())
    rs = data.get("rasis") if isinstance(data, dict) else None
    if not isinstance(rs, list) or len(rs) != 12:
        return ["need exactly 12 rasis"]
    for k, (r, item) in enumerate(zip(RASI, rs)):
        if item.get("rasi", "").strip() != r:
            errs.append(f"item {k + 1} must be {r}")
            continue
        try:
            st = int(item.get("stars"))
            if not 1 <= st <= 5:
                raise ValueError
        except Exception:
            errs.append(f"{r}: stars must be 1-5")
        for f in FIELDS:
            t = (item.get(f) or "").strip().rstrip(".")
            item[f] = t
            if not t:
                errs.append(f"{r}.{f}: empty")
                continue
            if re.search(r"[A-Za-z]", t):
                errs.append(f"{r}.{f}: English letters")
            if len(t) > MAX_CHARS + 6:
                errs.append(f"{r}.{f}: too long ({len(t)} chars, max {MAX_CHARS})")
            if any(x in t for x in FEAR):
                errs.append(f"{r}.{f}: fear word")
            c = copied(t, src)
            if c:
                errs.append(f"{r}.{f}: copied from a source ('{c}') - rewrite in your own words")
            if len(words(t)) < 2:
                errs.append(f"{r}.{f}: too short")
    for item in rs:
        if item.get("rasi") == chandra:
            try:
                item["stars"] = min(int(item.get("stars", 2)), 2)
            except Exception:
                item["stars"] = 2
    return errs


def sandhi_key(t):
    return re.sub(r"[கசதப]்|\s", "", t or "")


def proofread(rs, log=print):
    lines = {f"{i}.{f}": item[f] for i, item in enumerate(rs) for f in FIELDS}
    try:
        res, model = ask(PROOF, json.dumps(lines, ensure_ascii=False), log)
    except Exception as e:
        log("  proofread skipped:", str(e)[:120])
        return 0
    fixes = (res or {}).get("fixes", {}) if isinstance(res, dict) else {}
    n = 0
    for key, new in (fixes or {}).items():
        if key not in lines or not isinstance(new, str):
            continue
        new = new.strip().rstrip(".")
        old = lines[key]
        # only sandhi / spacing fixes are applied (a doubled க்/ச்/த்/ப் added or removed, words joined or split): a proofreader once
        # turned "கேட்ட சலுகை" (asked-for concession) into "கெட்ட சலுகை" (bad concession) - a changed letter is never applied blindly
        if new == old or sandhi_key(new) != sandhi_key(old) or any(x in new for x in FEAR):
            if new != old:
                log(f"  proofread suggestion NOT applied ({RASI[int(key.split('.')[0])]}): '{old}' -> '{new}'")
            continue
        i, f = key.split(".")
        rs[int(i)][f] = new
        n += 1
        log(f"  proofread {RASI[int(i)]}.{f}: '{old}' -> '{new}'")
    return n


def write(sources, chandra, log=print):
    """-> list of 12 dicts {rasi, stars, work, money, family, health, remedy}"""
    src = {s["name"]: s["rasis"] for s in sources}
    user = "TODAY'S SOURCES (one block per outlet):\n" + json.dumps(src, ensure_ascii=False)
    note = ""
    for attempt in range(3):
        data, model = ask(SYSTEM, user + note, log)
        errs = check(data, sources, chandra)
        log(f"  draft {attempt + 1} by {model}: {len(errs)} problem(s)")
        if not errs:
            rs = data["rasis"]
            proofread(rs, log)
            if check({"rasis": rs}, sources, chandra):
                log("  a proofread fix broke a check; using the draft as written")
                rs = data["rasis"]
            for item in rs:
                item["remedy"] = REMEDY[item["rasi"]]
                item["stars"] = int(item["stars"])
            return rs
        for e in errs[:15]:
            log("   -", e)
        note = "\n\nYOUR PREVIOUS ANSWER HAD THESE PROBLEMS - fix all of them:\n" + "\n".join(errs[:40]) + \
               "\nPREVIOUS ANSWER:\n" + json.dumps(data, ensure_ascii=False)[:6000]
    raise RuntimeError("the rasipalan could not be written cleanly in 3 tries")
