"""Today's rasipalan from the Tamil outlets that publish it every morning, split into the 12 rasis.

Each source: a listing page where today's article link appears (matched by today's date in the URL), the article text
(JSON-LD articleBody first, then the page paragraphs), and a check that it really is TODAY's palan for all 12 rasis.
Also fetches the day's Maalaimalar panchangam / important-events article, used only to confirm festivals (festivals.py)."""
import html, json, re
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "ta-IN,ta;q=0.9,en;q=0.5"}
RASI = ["மேஷம்", "ரிஷபம்", "மிதுனம்", "கடகம்", "சிம்மம்", "கன்னி", "துலாம்", "விருச்சிகம்", "தனுசு", "மகரம்", "கும்பம்", "மீனம்"]
# other spellings used by the outlets
STEM = {"மேஷம்": "மேஷ", "ரிஷபம்": "ரிஷப", "மிதுனம்": "மிதுன", "கடகம்": "கடக", "சிம்மம்": "சிம்ம", "கன்னி": "கன்னி", "துலாம்": "துலா",
        "விருச்சிகம்": "விருச்சிக", "தனுசு": "தனுசு", "மகரம்": "மகர", "கும்பம்": "கும்ப", "மீனம்": "மீன"}
ALT = {r: [r, STEM[r] + " ராசி", STEM[r] + "ம் ராசி", STEM[r] + "ராசி"] for r in STEM}      # TV9 writes "மேஷ ராசி..."
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def get(url, timeout=30):
    r = requests.get(url, headers=UA, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r.text


def links(page_html, base):
    out = []
    for h in re.findall(r'href="([^"#]+)"', page_html):
        h = html.unescape(h)
        if h.startswith("/"):
            h = base + h
        if h.startswith("http") and h not in out:
            out.append(h)
    return out


def date_tokens(day):
    m = MONTHS[day.month - 1]
    d, y = day.day, day.year
    return [f"{m}-{d}-{y}", f"{d}-{m}-{y}", f"{d:02d}-{m}-{y}", f"{d}{m}{y}", f"{d:02d}{day.month:02d}{y}", f"{d}-{day.month}-{y}",
            f"{y}-{day.month:02d}-{d:02d}", f"{d}st-{m}-{y}", f"{d}nd-{m}-{y}", f"{d}rd-{m}-{y}", f"{d}th-{m}-{y}",
            f"tns{y % 100:02d}{day.month:02d}{d:02d}"]


SOURCES = [
    # name, listing pages, url must contain one of these words, base
    ("TV9 Tamil", ["https://www.tv9tamilnews.com/religion"], ("rasi-palan", "rasipalan", "horoscope"), "https://www.tv9tamilnews.com"),
    ("Maalaimalar", ["https://www.maalaimalar.com/spirituality", "https://www.maalaimalar.com/astrology"], ("rasi-palan", "rasipalan"),
     "https://www.maalaimalar.com"),
    ("ETV Bharat", ["https://www.etvbharat.com/ta/!spiritual", "https://www.etvbharat.com/ta/spiritual"], ("rasipalan", "rasi-palan", "horoscope"),
     "https://www.etvbharat.com"),
    ("Boldsky Tamil", ["https://tamil.boldsky.com/astrology/"], ("horoscope", "rasi-palan", "rasipalan"), "https://tamil.boldsky.com"),
]


def find_url(src, day, log=print):
    name, pages, words, base = src
    toks = date_tokens(day)
    for pg in pages:
        try:
            for u in links(get(pg), base):
                low = u.lower()
                if any(w in low for w in words) and any(t in low for t in toks) and "weekly" not in low and "monthly" not in low \
                        and "week" not in low.split("/")[-1][:12] and "tomorrow" not in low:
                    return u
        except Exception as e:
            log(f"  {name}: listing {pg} failed: {str(e)[:120]}")
    if name == "Maalaimalar":      # the usual address, tried directly
        return f"https://www.maalaimalar.com/spirituality/today-rasi-palan-in-tamil-{day.day}-{MONTHS[day.month - 1]}-{day.year}"
    return ""


def article(url):
    h = get(url)
    title = pub = body = ""
    for blk in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, flags=re.S):
        try:
            data = json.loads(blk)
        except Exception:
            continue
        for d in (data if isinstance(data, list) else [data]):
            for e in (d.get("@graph", [d]) if isinstance(d, dict) else []):
                if isinstance(e, dict) and "Article" in str(e.get("@type", "")):
                    title = title or e.get("headline", "")
                    pub = pub or e.get("datePublished", "")
                    if len(e.get("articleBody", "") or "") > len(body):
                        body = e.get("articleBody", "")
    if not pub:
        m = re.search(r'(?:property|name)="article:published_time"\s+content="([^"]+)"', h)
        pub = m.group(1) if m else ""
    if len(body) < 600:
        h2 = re.sub(r"<(style|script|noscript|svg)[^>]*>.*?</\1>", " ", h, flags=re.S)
        h2 = re.split(r">\s*(?:Also Read|Related (?:News|Stories|Articles)|Read More|இதையும் படிக்க|இதையும் படியுங்கள்|தொடர்புடைய செய்திகள்|மேலும் படிக்க)\s*<",
                      h2, maxsplit=1)[0]
        h2 = re.sub(r"<(a|figcaption|time|button|nav|header|footer)\b[^>]*>.*?</\1>", " ", h2, flags=re.S | re.I)
        parts = [re.sub(r"\s+", " ", html.unescape(x)).strip() for x in re.sub(r"<[^>]+>", "\n", h2).split("\n")]
        parts = [x for x in parts if re.search(r"[஀-௿]", x) and "{" not in x and len(x) >= 4]
        seen, out = set(), []
        for x in parts:
            if x not in seen:
                seen.add(x)
                out.append(x)
        body = "\n".join(out)
    return {"url": url, "title": html.unescape(title).strip(), "published": pub, "text": html.unescape(re.sub(r"<[^>]+>", " ", body)).strip()}


def split_rasis(text):
    """{rasi: its palan text} - the 12 rasi names must appear in order (each as a heading / line start)"""
    pos, at = [], 0
    for r in RASI:
        best = None
        for v in ALT[r]:
            for m in re.finditer(re.escape(v), text[at:]):
                i = at + m.start()
                before = text[max(0, i - 3):i]
                if i == 0 or re.search(r"[\s\n:.|\-–*#>(\"'0-9]$", before) or before.endswith("\n"):
                    best = i if best is None else min(best, i)
                    break
        if best is None:
            return {}
        pos.append(best)
        at = best + 2
    out = {}
    for k, r in enumerate(RASI):
        seg = text[pos[k]:pos[k + 1] if k < 11 else len(text)]
        seg = re.sub(r"^\S+\s*(?:ராசி(?:க்காரர்கள்|யினர்)?|ராசி அன்பர்களே)?\s*[:\-–]?\s*", "", seg).strip()
        out[r] = seg[:1500]
    return out


def is_today(art, day):
    pub = art.get("published", "")
    if pub[:10] == day.isoformat():
        return True
    u = art["url"].lower()
    return any(t in u for t in date_tokens(day))


def collect(day, log=print):
    """-> list of {name, url, rasis{12}}; only sources whose article is today's and has all 12 rasis with real text"""
    got = []
    for src in SOURCES:
        name = src[0]
        try:
            url = find_url(src, day, log)
            if not url:
                log(f"  {name}: today's article not found")
                continue
            art = article(url)
            if not is_today(art, day):
                log(f"  {name}: {url} is not today's ({art.get('published')})")
                continue
            rs = split_rasis(art["text"])
            short = [r for r in RASI if len(rs.get(r, "")) < 25]
            if not rs or short:
                log(f"  {name}: could not read all 12 rasis ({', '.join(short) or 'none found'})")
                continue
            got.append({"name": name, "url": url, "rasis": rs})
            log(f"  {name}: ok {url}")
        except Exception as e:
            log(f"  {name}: failed {str(e)[:150]}")
    return got


def panchang_article(day, log=print):
    """the day's Maalaimalar panchangam + important-events article text ('' when not found) - for festival confirmation only"""
    toks = [f"important-events-{day.day}-{MONTHS[day.month - 1]}", f"important-events-{day.day:02d}-{MONTHS[day.month - 1]}"]
    for pg in ("https://www.maalaimalar.com/spirituality", "https://www.maalaimalar.com/astrology"):
        try:
            for u in links(get(pg), "https://www.maalaimalar.com"):
                if any(t in u.lower() for t in toks):
                    a = article(u)
                    log(f"  panchangam article: {u}")
                    return a["title"] + "\n" + a["text"] + "\n" + u
        except Exception as e:
            log(f"  panchangam listing failed: {str(e)[:120]}")
    return ""
