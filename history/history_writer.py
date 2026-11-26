"""owner 26 Nov: the daily district HISTORY / TEMPLE STORY - topic bank, script and the fact gate. No network except the writer model.

  eligible(topic)                 verified + at least one source url + at least 3 facts (a topic without them is NEVER posted)
  pick_topic(page, ...)           the next eligible topic of the page's bank that has not been told yet (a finished bank starts again)
  plain_script(topic)             the narration made straight from the facts (always passes the gate)
  write(topic, ask=None)          the writer model's script, kept only if it passes the gate; otherwise plain_script
  scene_prompts(topic, n)         6-8 picture prompts, never naming a real person
The writer may use ONLY the topic's facts; every number is checked (lanes/factgate.py); legends must be worded as tradition."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lanes"))
import lane_factgate as factgate  # noqa: E402

MIN_FACTS = 3
MAX_LINES = 8
SYSTEM = """நீங்கள் தமிழ்நாட்டு உள்ளூர் வரலாற்றை 35-50 வினாடி வீடியோவுக்காக எழுதும் எழுத்தாளர்.
கண்டிப்பான விதிகள்:
- கொடுக்கப்பட்ட "facts" பட்டியலில் உள்ள தகவல்களை மட்டுமே பயன்படுத்துங்கள். புதிய ஆண்டு, எண், பெயர், உரிமைகோரல் எதுவும் சேர்க்கக்கூடாது.
- ஒவ்வொரு வரியும் எந்த fact id-ஐ அடிப்படையாகக் கொண்டது என்று "facts" பட்டியலில் தரவும் (முதல், கடைசி வரிகள் மட்டும் "frame": true எனக் குறிக்கலாம், facts இல்லாமல்).
- kind = "tradition" என்ற facts-ஐ உண்மையாகச் சொல்லாமல் "நம்பிக்கை", "கதை", "சொல்லப்படுகிறது" போன்ற சொற்களுடன் சொல்லவும்.
- 5 முதல் 7 வரிகள்; ஒவ்வொன்றும் 110 எழுத்துகளுக்குள், எளிய பேச்சுத் தமிழில்; முதல் வரி ஒரு கவர்ச்சியான கேள்வி அல்லது தொடக்கம்; கடைசி வரி "நம்ம ஊர் வரலாறு" தொடரைப் பின்தொடரச் சொல்லும் அழைப்பு (எண்கள் இல்லாமல்).
- கவிதை / பாடல் வரிகளை நகலெடுக்காதீர்கள். எந்த மூலத்தின் வாக்கியத்தையும் அப்படியே எடுக்காதீர்கள்.
JSON மட்டும்: {"lines": [{"text": "...", "facts": ["f1"], "frame": false}]}"""


def load_bank(page, root=ROOT):
    p = Path(root) / "history" / "topics" / f"{page}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("topics", [])
    except Exception:
        return []


def eligible(topic, allow_unverified=False):
    """why a topic cannot be posted yet ('' = it can)"""
    if len(topic.get("facts", [])) < MIN_FACTS:
        return f"needs at least {MIN_FACTS} sourced facts"
    if allow_unverified:      # dry runs / previews only
        return ""
    if not topic.get("verified"):
        return "not verified"
    if not any(str(s.get("url", "")).startswith("https://") for s in topic.get("sources", [])):
        return "no source url"
    return ""


def pick_topic(page, used, bank=None, allow_unverified=False):
    """the next eligible topic (by "order") not yet in `used`; when every eligible topic was told, the cycle starts again"""
    bank = bank if bank is not None else load_bank(page)
    ok = sorted((t for t in bank if not eligible(t, allow_unverified)), key=lambda t: t.get("order", 999))
    if not ok:
        return None
    fresh = [t for t in ok if t["id"] not in used]
    return (fresh or ok)[0] if fresh else ok[0]


def plain_script(topic):
    """narration straight from the facts: opening + each fact + the follow line. Always passes the gate (no new words)."""
    title = topic["title_ta"]
    lines = [{"text": f"{title}. இதன் வரலாறு தெரியுமா?", "facts": [], "frame": True}]
    for f in topic["facts"][:MAX_LINES - 2]:
        lines.append({"text": f["ta"], "facts": [f["id"]]})
    lines.append({"text": "இன்னும் நம்ம ஊர் வரலாறு கதைகளுக்கு எங்களைப் பின்தொடருங்கள்.", "facts": [], "frame": True})
    return lines


def gate(lines, topic):
    """problems with a script (empty list = fine). The opening/closing lines are checked like the others."""
    sheet = dict(topic)
    problems = factgate.check_history_lines(lines, sheet)
    if len(lines) > MAX_LINES:
        problems.append(f"{len(lines)} lines (max {MAX_LINES})")
    return problems


def write(topic, ask=None, log=print):
    """-> (lines, how). ask(system, user) -> parsed JSON; None = no model (plain script). A model script that fails the gate is dropped."""
    if ask:
        try:
            user = json.dumps({"title": topic["title_ta"], "town": topic["town_ta"],
                               "facts": [{"id": f["id"], "kind": f.get("kind", "fact"), "text": f["ta"]} for f in topic["facts"]]}, ensure_ascii=False)
            data = ask(SYSTEM, user)
            lines = [{"text": str(x.get("text", "")).strip(), "facts": list(x.get("facts", [])), "frame": bool(x.get("frame"))} for x in (data or {}).get("lines", [])]
            problems = gate(lines, topic)
            if not problems:
                return lines, "model"
            log("model script rejected by the fact gate:", "; ".join(problems)[:300])
        except Exception as e:
            log("writer model not used:", str(e)[:150])
    lines = plain_script(topic)
    problems = gate(lines, topic)
    if problems:      # a topic whose own facts fail the gate is not postable
        raise ValueError("fact sheet fails the gate: " + "; ".join(problems)[:300])
    return lines, "plain"


def scene_prompts(topic, n=6):
    """6-8 picture prompts for the story's own scenes (history-telling visuals); the topic's scene_hints first. No real people."""
    hints = [h for h in topic.get("scene_hints", []) if h][:8]
    base = f"{topic.get('town_ta', '')} {topic.get('title_ta', '')}"
    style = ", warm sepia heritage illustration, soft painterly light, vertical composition, no text, no real people"
    out = [h + style for h in hints]
    while len(out) < max(6, min(n, 8)):
        out.append(f"Tamil Nadu temple town heritage scene, {len(out) + 1}" + style)
    bad = factgate.check_scene_prompts(out, topic)
    if bad:
        raise ValueError("; ".join(bad))
    return out[:max(6, min(len(out), 8))]


def hashtag(s):
    return re.sub(r"\s+", "", s)
