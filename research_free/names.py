"""Full place names and spoken forms. News sites shorten names (ப.வேலூர், கு.பாளையம்) and use abbreviations (ஆர்.டி.ஓ.): a voice engine reads
those badly and many viewers do not recognise them. Everything we publish uses the full name; the reel voice also gets spoken role words."""
import re

# (pattern, full name). The ending (-ில், -இல், -க்கு ...) after the matched name is kept.
PLACES = [
    (r"ப\s?\.\s?வேல(?:ூ|ுா)ர", "பரமத்தி வேலூர"),
    (r"பரமத்தி\s?வேலுார", "பரமத்தி வேலூர"),
    (r"கு\s?\.\s?பாளைய", "குமாரபாளைய"),
    (r"பள்ளி\s?\.\s?பாளைய", "பள்ளிப்பாளைய"),
    (r"திருச்செங்\s?\.", "திருச்செங்கோடு"),
    (r"நாமக்\s?\.", "நாமக்கல்"),
    (r"ராசி\s?\.", "ராசிபுரம்"),
    (r"சேந்\s?\.", "சேந்தமங்கலம்"),
]
# only for the spoken reel script (the screen text may keep the short, well-known forms)
ROLES = [
    (r"ஆர்\s?\.\s?டி\s?\.\s?ஓ\s?\.?,?", "வருவாய் கோட்டாட்சியர்"),
    (r"டி\s?\.\s?ஆர்\s?\.\s?ஓ\s?\.?,?", "மாவட்ட வருவாய் அலுவலர்"),
    (r"பி\s?\.\s?டி\s?\.\s?ஓ\s?\.?,?", "வட்டார வளர்ச்சி அலுவலர்"),
    (r"டி\s?\.\s?எஸ்\s?\.\s?பி\s?\.?,?", "காவல் துணை கண்காணிப்பாளர்"),
    (r"எஸ்\s?\.\s?பி\s?\.?,?", "காவல் கண்காணிப்பாளர்"),
    (r"ஜி\s?\.\s?ஹெச்\s?\.?,?|ஜி\s?\.\s?எச்\s?\.?,?", "அரசு மருத்துவமனை"),
    (r"கி\s?\.\s?மீ\s?\.?,?", "கிலோமீட்டர்"),
    (r"அக்\s?\.", "அக்டோபர்"),
]


def full_places(text):
    for pat, full in PLACES:
        text = re.sub(pat, full, text or "")
    return text


def spoken(text):
    text = full_places(text)
    for pat, full in ROLES:
        text = re.sub(pat, full, text)
    for a, b in (("ர்வும்", "ரும்"), ("ர்வின்", "ரின்"), ("ர்வுக்கு", "ருக்கு")):      # the ending that followed the abbreviation (ஆர்.டி.ஓ.,வும்)
        text = text.replace(a, b)
    return text
