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
D = r"\s?\.\s?"      # the dot between the letters of a Tamil abbreviation (எஸ்.ஐ. / எஸ் . ஐ)
ROLES = [
    # longest first: ஏ.டி.எஸ்.பி. must not become ஏ.+டி.எஸ்.பி.
    (r"ஏ" + D + r"டி" + D + r"எஸ்" + D + r"பி\s?\.?,?|(?<![A-Za-z])ADSP(?![A-Za-z])", "கூடுதல் காவல் கண்காணிப்பாளர்"),
    (r"எஸ்" + D + r"எஸ்" + D + r"ஐ\s?\.?,?|(?<![A-Za-z])SSI(?![A-Za-z])", "சிறப்பு உதவி ஆய்வாளர்"),
    (r"(?<![அ-ஹ.])எஸ்" + D + r"ஐ\s?\.?,?|(?<![A-Za-z])SI(?![A-Za-z])", "காவல் உதவி ஆய்வாளர்"),
    (r"(?<![A-Za-z])DSP(?![A-Za-z])", "காவல் துணை கண்காணிப்பாளர்"),
    (r"(?<![A-Za-z])SP(?![A-Za-z])", "காவல் கண்காணிப்பாளர்"),
    (r"எம்" + D + r"எல்" + D + r"ஏ\s?\.?,?|(?<![A-Za-z])MLA(?![A-Za-z])", "சட்டமன்ற உறுப்பினர்"),
    (r"(?<![அ-ஹ.])எம்" + D + r"பி\s?\.?,?(?!\s?[அ-ஹ]\s?\.)|(?<![A-Za-z])MP(?![A-Za-z])", "நாடாளுமன்ற உறுப்பினர்"),
    (r"வி" + D + r"ஏ" + D + r"ஓ\s?\.?,?|(?<![A-Za-z])VAO(?![A-Za-z])", "கிராம நிர்வாக அலுவலர்"),
    (r"(?<![அ-ஹ.])ஆர்" + D + r"ஐ\s?\.?,?(?!\s?[அ-ஹ]\s?\.)", "வருவாய் ஆய்வாளர்"),
    (r"(?<![A-Za-z])RDO(?![A-Za-z])", "வருவாய் கோட்டாட்சியர்"),
    (r"(?<![A-Za-z])BDO(?![A-Za-z])", "வட்டார வளர்ச்சி அலுவலர்"),
    (r"(?<![A-Za-z])DRO(?![A-Za-z])", "மாவட்ட வருவாய் அலுவலர்"),
    (r"டி" + D + r"என்" + D + r"இ" + D + r"பி\s?\.?,?|(?<![A-Za-z])TNEB(?![A-Za-z])", "மின்சார வாரியம்"),
    (r"(?<![A-Za-z])TNSTC(?![A-Za-z])", "அரசுப் போக்குவரத்துக் கழகம்"),
    (r"மி" + D + r"மீ\s?\.?,?", "மில்லிமீட்டர்"),
    (r"செ" + D + r"மீ\s?\.?,?", "சென்டிமீட்டர்"),
    (r"கி" + D + r"கி\s?\.?,?", "கிலோகிராம்"),
    (r"ச" + D + r"அடி", "சதுர அடி"),
    (r"(?<![A-Za-z])No\.\s?", "எண் "),
    (r"(?<![A-Za-z])NEET(?![A-Za-z])", "நீட்"),
    (r"(?<![A-Za-z])TASMAC(?![A-Za-z])", "டாஸ்மாக்"),
    (r"(?<![A-Za-z])COVID(?![A-Za-z])", "கோவிட்"),
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


# English letters as a Tamil news reader says them (the voice model drops Latin letters completely: "TNPSC" was silent)
LATIN = {"A": "ஏ", "B": "பி", "C": "சி", "D": "டி", "E": "இ", "F": "எஃப்", "G": "ஜி", "H": "ஹெச்", "I": "ஐ", "J": "ஜே", "K": "கே", "L": "எல்", "M": "எம்",
         "N": "என்", "O": "ஓ", "P": "பி", "Q": "க்யூ", "R": "ஆர்", "S": "எஸ்", "T": "டி", "U": "யு", "V": "வி", "W": "டபிள்யூ", "X": "எக்ஸ்", "Y": "ஒய்", "Z": "இசட்"}


def spoken(text):
    text = full_places(text)
    for pat, full in ROLES:
        text = re.sub(pat, full, text)
    # any other abbreviation is read letter by letter: TNPSC -> டி என் பி எஸ் சி, ஐ.பி.எஸ். -> ஐ பி எஸ், தி.மு.க. -> தி மு க
    text = re.sub(r"(?<![A-Za-z])[A-Z]{2,7}(?![A-Za-z])", lambda m: " ".join(LATIN[c] for c in m.group()), text)
    L = r"[அ-ஹ](?:[\u0bbe-\u0bcc]|[அ-ஹ]\u0bcd|\u0bcd)?"      # one spoken letter: ஐ, பி, எஸ், எம், தி, க
    text = re.sub(r"(?<![அ-ஹ\u0bbe-\u0bcd])((?:" + L + r"\s?\.\s?){2,}" + L + r")\.?",
                  lambda m: " ".join(x.strip() for x in m.group(1).split(".") if x.strip()), text)
    for a, b in (("ர்வும்", "ரும்"), ("ர்வின்", "ரின்"), ("ர்வுக்கு", "ருக்கு")):      # the ending that followed the abbreviation (ஆர்.டி.ஓ.,வும்)
        text = text.replace(a, b)
    return text
