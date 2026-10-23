"""What Instagram insights taught us (written by poster/insights.py into learned.json). Used ONLY to order candidate stories and to give the
writer style hints. It never relaxes a fact / quality check."""
import json, pathlib

HERE = pathlib.Path(__file__).parent
TOPICS = {
    "weather": ["மழை", "வெயில்", "வானிலை", "எச்சரிக்கை", "புயல்", "வெள்ளம்"],
    "crime": ["கொலை", "கைது", "திருட", "போலீஸ்", "குற்ற", "மோசடி", "தற்கொலை", "கொள்ளை"],
    "accident": ["விபத்து", "பலி", "உயிரிழ", "தீ விபத்து", "மோதி"],
    "temple": ["கோயில்", "கோவில்", "திருவிழா", "தேர்", "சாமி", "பூஜை", "குடமுழுக்கு"],
    "politics": ["முதல்வர்", "அமைச்சர்", "திமுக", "அதிமுக", "எம்எல்ஏ", "எம்.எல்.ஏ", "தேர்தல்", "ஆட்சியர்", "கட்சி"],
    "poultry_agri": ["முட்டை", "கோழி", "விவசாய", "விலை", "கொள்முதல்", "மஞ்சள்", "பண்ணை", "லாரி"],
    "education_jobs": ["மாணவ", "பள்ளி", "கல்லூரி", "தேர்வு", "வேலைவாய்ப்பு", "முகாம்", "வேலை"],
    "civic": ["மின்தடை", "மின் தடை", "குடிநீர்", "சாலை", "பேருந்து", "நகராட்சி", "பஞ்சாயத்து", "குப்பை"],
    "sports_culture": ["போட்டி", "கபடி", "விளையாட்டு", "கலை", "சினிமா", "விருது"],
}


def topic(text):
    t = text or ""
    best, n = "other", 0
    for k, words in TOPICS.items():
        c = sum(1 for w in words if w in t)
        if c > n:
            best, n = k, c
    return best


def load():
    try:
        return json.loads((HERE / "learned.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def boost(text):
    """score adjustment for a candidate headline from its topic's measured performance (weights are already clamped by insights.py)"""
    w = (load().get("topic_weight") or {}).get(topic(text))
    return float(w) if w is not None else 0.0


def hints():
    """short style guidance for the writer prompt; '' until enough posts have been measured"""
    d = load()
    out = []
    if d.get("avg_watch_s"):
        out.append(f"Viewers leave after about {d['avg_watch_s']} seconds on average: the FIRST sentence of reel_script must carry the most surprising fact (a number, place or consequence), never a greeting or background.")
    if d.get("top_openings"):
        out.append("Openings of our best-performing reels (style reference only, never copy facts): " + " | ".join(d["top_openings"][:4]))
    return "\n".join(out)
