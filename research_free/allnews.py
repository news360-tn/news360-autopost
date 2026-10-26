"""Collect EVERY Namakkal-district news item from many outlets (Dinamalar list + Google News + Bing News RSS, any extra
listing pages in sources.json), tag each one Rasipuram ('R') or rest-of-district ('N'), merge duplicates reported by several
outlets, and give the owner a full list to analyse. Nothing here writes posts; collect.py ranks and writes the best ones.
Every request is wrapped so one broken outlet never stops the others."""
import datetime, difflib, email.utils, html, json, re, time, urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
import sources as dinamalar

HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "ta-IN,ta;q=0.9,en;q=0.5"}
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# Rasipuram town + its taluk villages (same list as rules.md) -> posted on Namakkal 360 + Rasipuram 360 (collab)
RASIPURAM = ["ராசிபுரம்", "நாமகிரிப்பேட்டை", "வெண்ணந்தூர்", "புதுச்சத்திரம்", "மெட்டாலா", "ஆயில்பட்டி", "சீராப்பள்ளி",
             "சிங்களாந்தபுரம்", "ஆண்டகளூர்", "அத்தனூர்", "மல்லசமுத்திரம்", "குருக்கபுரம்", "அணைப்பாளையம்", "முத்துக்காளிப்பட்டி",
             "காக்காவேரி", "வடுகம்", "ராசிபுரத்தில்", "ராசிபுரம்"]
# searches that cover the whole district (every taluk and big town)
QUERIES = ["நாமக்கல்", "ராசிபுரம்", "திருச்செங்கோடு", "பரமத்தி வேலூர்", "குமாரபாளையம்", "பள்ளிபாளையம்", "சேந்தமங்கலம்", "கொல்லிமலை",
           "மோகனூர்", "நாமகிரிப்பேட்டை", "வெண்ணந்தூர்", "எருமப்பட்டி", "நாமக்கல் மாவட்டம்", "நாமக்கல் முட்டை விலை"]
# every outlet is also searched on its own (so a channel like News7 Tamil or NDTV Tamil is never missed)
SITES = {"நியூஸ்7 தமிழ்": "news7tamil.live", "என்டிடிவி தமிழ்": "ndtv.com/tamil", "மாலைமலர்": "maalaimalar.com", "தினத்தந்தி": "dailythanthi.com",
         "தினமணி": "dinamani.com", "இந்து தமிழ்": "hindutamil.in", "தினகரன்": "dinakaran.com", "புதிய தலைமுறை": "puthiyathalaimurai.com",
         "நியூஸ்18 தமிழ்": "news18.com", "விகடன்": "vikatan.com", "பாலிமர்": "polimernews.com", "சமயம் தமிழ்": "tamil.samayam.com",
         "தினமலர்": "dinamalar.com", "DT Next": "dtnext.in", "ஜீ தமிழ்": "zeenews.india.com", "ABP நாடு": "tamil.abplive.com",
         "Oneindia தமிழ்": "tamil.oneindia.com", "நக்கீரன்": "nakkheeran.in", "தினபூமி": "dinaboomi.com", "தமிழ் முரசு": "tamilmurasu.com.sg"}
SITE_QUERIES = ["நாமக்கல்", "ராசிபுரம்", "திருச்செங்கோடு"]
OUTLET_WORDS = ["தினமலர்", "தினத்தந்தி", "தினமணி", "மாலைமலர்", "தினகரன்", "இந்து தமிழ்", "தி இந்து", "புதிய தலைமுறை", "நியூஸ்18", "நியூஸ் 18",
                "விகடன்", "ஏபிபி", "சமயம்", "polimer", "பாலிமர்", "தந்தி டிவி", "ஜீ தமிழ்", "நக்கீரன்", "டைம்ஸ்"]


def _get(url, timeout=40, headers=None):
    r = requests.get(url, headers=headers or UA, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r


# Namakkal district places (town / taluk / union / well-known villages). A story that names none of them AND names a state-wide or
# another district's place is not Namakkal district news (e.g. "17 districts rain alert", "Chennai yellow alert").
NAMAKKAL_WORDS = ["நாமக்கல்", "ராசிபுரம்", "திருச்செங்கோடு", "பரமத்தி", "குமாரபாளையம்", "பள்ளிபாளையம்", "சேந்தமங்கலம்", "கொல்லிமலை", "மோகனூர்",
                  "நாமகிரிப்பேட்டை", "வெண்ணந்தூர்", "எருமப்பட்டி", "புதுச்சத்திரம்", "கபிலர்மலை", "பாண்டமங்கலம்", "ஜேடர்பாளையம்", "மல்லசமுத்திரம்",
                  "எலச்சிபாளையம்", "வேலகவுண்டம்பட்டி", "நல்லிபாளையம்", "பிள்ளாநல்லூர்", "மெட்டாலா", "ஆயில்பட்டி", "சீராப்பள்ளி", "Namakkal", "Rasipuram",
                  "Tiruchengode", "Kumarapalayam", "Paramathi", "Pallipalayam", "Mohanur", "Sendamangalam", "Kolli"]
OUTSIDE_WORDS = ["தமிழகத்தில்", "தமிழ்நாட்டில்", "மாவட்டங்களில்", "மாவட்டங்களுக்கு", "மாவட்டங்கள்", "தென் மாவட்ட", "டெல்டா", "சென்னை", "மதுரை", "கோவை",
                 "கோயம்புத்தூர்", "திருச்சி", "சேலம்", "ஈரோடு", "திருப்பூர்", "நெல்லை", "தூத்துக்குடி", "வேலூர்", "தஞ்சை", "கடலூர்", "காஞ்சிபுரம்", "புதுச்சேரி",
                 "தமிழக", "இந்தியா", "பிரதமர்", "முதல்வர் ஸ்டாலின்", "விஜய்", "டெல்லி", "கேரளா", "கர்நாடக", "Chennai", "Tamil Nadu"]


# these headlines are never Namakkal-district news, even when Namakkal is one name in a long list
ALWAYS_OUTSIDE = ["மாவட்டங்களில்", "மாவட்டங்களுக்கு", "மாவட்டங்கள்", "தமிழகத்தில்", "தமிழ்நாட்டில்", "தமிழகம் முழுவதும்", "மாநிலம் முழுவதும்",
                  "மத்தியப் பிரதேச", "மத்திய பிரதேச", "ராஜ்யசபா", "மாநிலங்களவை", "பிரதமர்", "இடைத்தேர்தல்", "தேர்தல் ஆணையம்", "உச்ச நீதிமன்றம்"]
# weather forecasts / alerts are not local reporting
WEATHER_FORECAST = ["மழை எச்சரிக்கை", "மஞ்சள் எச்சரிக்கை", "ஆரஞ்சு எச்சரிக்கை", "சிவப்பு எச்சரிக்கை", "வானிலை", "ரெட் அலர்ட்", "ஆரஞ்சு அலர்ட்", "மஞ்சள் அலர்ட்", "மழைக்கு வாய்ப்பு", "மழை பெய்ய வாய்ப்பு",
                    "கனமழை பெய்யும்", "கனமழைக்கு வாய்ப்பு", "காற்றழுத்த", "புயல் உருவாக", "வளிமண்டல", "பள்ளிகளுக்கு விடுமுறை"]


# places next to Rasipuram: used for the Rasipuram page only when Rasipuram town itself has less than a round's worth of news
RASI_NEAR = ["சேந்தமங்கலம்", "எருமப்பட்டி", "புதுச்சத்திரம்", "பட்டணம்", "ஆர்.புதுப்பட்டி", "முள்ளுக்குறிச்சி", "மோகனூர்", "ஆத்தூர்", "கொல்லிமலை"]


# Tamil joins a place name to its ending (சேந்தமங்கலம் -> சேந்தமங்கலத்தில், திருச்செங்கோடு -> திருச்செங்கோட்டில்), so match the stems too
PLACE_STEMS = [w[:-1] if w.endswith("ம்") else w for w in NAMAKKAL_WORDS if not w.isascii()] + [
    "திருச்செங்கோட்", "ராசிபுரத்", "குமாரபாளையத்", "பள்ளிபாளையத்", "ப.வேலூ", "ப.வேலு", "பொத்தனூ", "பொத்தனு", "தும்மங்குறிச்சி", "பேளுக்குறிச்சி",
    "தலைமலை", "கபிலக்குறிச்சி", "அணியாபுரம்", "ஆண்டகளூர்", "பிள்ளாநல்லுார்", "பரமத்தி", "சீராப்பள்ளி", "மல்லசமுத்திர", "நாமகிரிப்பேட்", "வெண்ணந்துார்"]


def has_place(text):
    return any(w in (text or "") for w in PLACE_STEMS) or any(w in (text or "") for w in NAMAKKAL_WORDS if w.isascii())


def outside_district(text, via=""):
    """True when the headline is clearly NOT Namakkal-district news: state-wide / multi-district / national news, weather forecasts, or a headline
    that names another place and none of ours. A headline that names no place at all is KEPT (many local reports omit it) - the article itself
    is checked for a Namakkal place before anything is written (collect.py)."""
    text = text or ""
    if any(w in text for w in ALWAYS_OUTSIDE) or any(w in text for w in WEATHER_FORECAST):
        return True
    if has_place(text):
        return False
    if via == "dinamalar-list":
        return False
    if "முட்டை" in text and any(w in text for w in ("விலை", "கொள்முதல்")):
        return False          # Namakkal is the egg-price centre; the daily rate is local news
    return any(w in text for w in OUTSIDE_WORDS)


def area_of(text, default="N"):
    return "R" if any(k in text for k in RASIPURAM) else default


def _clean_title(t):
    t = html.unescape(t or "").strip()
    return re.sub(r"\s+[-|–]\s+[^-|–]{2,40}$", "", t).strip()      # drop the " - outlet" suffix of RSS titles


def _outlet(t, fallback=""):
    m = re.search(r"\s[-|–]\s+([^-|–]{2,40})$", html.unescape(t or ""))
    return (m.group(1).strip() if m else fallback) or fallback


def _parse_pub(s):
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(IST).isoformat()
    except Exception:
        return ""


def from_google(q):
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:2d") + "&hl=ta&gl=IN&ceid=IN:ta"
    root = ET.fromstring(_get(url).content)
    out = []
    for it in root.iter("item"):
        title = it.findtext("title") or ""
        src = it.find("source")
        out.append({"key": it.findtext("guid") or it.findtext("link"), "url": it.findtext("link"), "title": _clean_title(title),
                    "source": (src.text if src is not None and src.text else _outlet(title, "Google News")), "published": _parse_pub(it.findtext("pubDate") or ""),
                    "via": "google", "query": q, "snippet": re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))[:300]})
    return out


def from_bing(q):
    url = "https://www.bing.com/news/search?q=" + urllib.parse.quote(q) + "&format=rss&setmkt=ta-IN&qft=sortbydate%3d%221%22"
    root = ET.fromstring(_get(url).content)
    out = []
    for it in root.iter("item"):
        link = it.findtext("link") or ""
        real = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("url", [link])[0]
        title = it.findtext("title") or ""
        src = [e.text for e in it if e.tag.lower().endswith("source")]
        out.append({"key": real, "url": real, "title": _clean_title(title), "source": (src[0] if src else _outlet(title, "Bing News")),
                    "published": _parse_pub(it.findtext("pubDate") or ""), "via": "bing", "query": q,
                    "snippet": re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))[:300]})
    return out


def from_dinamalar_list():
    out = []
    for u in dinamalar.candidate_links(60):
        out.append({"key": u, "url": u, "title": "", "source": "தினமலர்", "published": "", "via": "dinamalar-list", "query": "district list", "snippet": ""})
    return out


def from_listing(cfg):
    """extra outlet pages from sources.json: {"name","url","link_regex"} -> article links (the article page gives title/date/text)"""
    h = _get(cfg["url"]).text
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(cfg["url"]))
    seen, out = set(), []
    for m in re.finditer(cfg.get("link_regex", r'href="([^"#?]+/\d{5,}[^"]*)"'), h):
        u = urllib.parse.urljoin(base, m.group(1))
        if u not in seen:
            seen.add(u)
            out.append({"key": u, "url": u, "title": "", "source": cfg["name"], "published": "", "via": "listing", "query": cfg["url"], "snippet": ""})
    return out[: cfg.get("limit", 30)]


def collect(log):
    """every item from every source, merged. Returns a list of dicts (see keys above + area, mentions, outlets)."""
    items = []

    def add(fn, *a, label=""):
        try:
            got = fn(*a)
            log.append(f"source {label or fn.__name__}: {len(got)} items")
            items.extend(got)
        except Exception as e:
            log.append(f"source {label or fn.__name__} FAILED: {str(e)[:120]}")
    add(from_dinamalar_list, label="dinamalar list")
    for q in QUERIES:
        add(from_google, q, label=f"google '{q}'")
        add(from_bing, q, label=f"bing '{q}'")
    for name, dom in SITES.items():
        for q in SITE_QUERIES:
            add(from_google, f"{q} site:{dom}", label=f"google {name} '{q}'")
            add(from_bing, f"{q} site:{dom}", label=f"bing {name} '{q}'")
    try:
        for cfg in json.loads((HERE / "sources.json").read_text(encoding="utf-8")):
            add(from_listing, cfg, label=cfg["name"])
    except FileNotFoundError:
        pass
    # merge: same URL or very similar headline = one story reported by several outlets
    merged = []
    for it in items:
        if not it.get("key"):
            continue
        hit = None
        for m in merged:
            if m["key"] == it["key"] or m["url"] == it["url"]:
                hit = m
                break
            if it["title"] and m["title"] and difflib.SequenceMatcher(None, it["title"], m["title"]).ratio() > 0.62:
                hit = m
                break
        if hit:
            hit["outlets"].add(it["source"])
            hit["alts"].append(it["url"])
            if not hit["title"] and it["title"]:
                hit["title"] = it["title"]
            if not hit["published"] and it["published"]:
                hit["published"] = it["published"]
            if len(it.get("snippet", "")) > len(hit.get("snippet", "")):
                hit["snippet"] = it["snippet"]
            if it["via"] == "dinamalar-list" or (it["via"] == "bing" and hit["via"] == "google"):
                hit["url"] = it["url"]          # prefer a direct publisher link
                hit["via"] = it["via"]
        else:
            it = dict(it)
            it["outlets"] = {it["source"]}
            it["alts"] = [it["url"]]
            merged.append(it)
    for m in merged:
        m["mentions"] = len(m["outlets"])
        m["area"] = area_of(m["title"] + " " + m.get("snippet", ""))
        m["outlets"] = sorted(m["outlets"])
    log.append(f"all sources: {len(items)} items -> {len(merged)} different news ({sum(1 for m in merged if m['area'] == 'R')} Rasipuram)")
    return merged


# ---------------------------------------------------------------- article text
def resolve(url):
    """Google News links are redirects; turn one into the publisher's page (needs the googlenewsdecoder package)."""
    if "news.google.com" not in url:
        return url
    err = ""
    for attempt in range(3):      # the decoder is rate-limited when many links come at once: pause and try again
        try:
            from googlenewsdecoder import gnewsdecoder
            r = gnewsdecoder(url, interval=2)
            if (r.get("success") or r.get("status")) and r.get("decoded_url"):      # 0.2.x answers "success", older versions "status"
                return r["decoded_url"]
            err = str(r.get("message") or "no decoded url")[:80]
        except Exception as e:
            err = f"decoder: {str(e)[:70]}"
        time.sleep(6 * (attempt + 1))
    try:
        final = _get(url, timeout=30).url
        if "news.google.com" not in final:
            return final
        raise RuntimeError("google page, not the article")
    except Exception as e:
        raise RuntimeError(f"google news link not decoded ({err}; {str(e)[:60]})")


def article_any(url):
    """title / published / text from any outlet's article page (JSON-LD first, then page paragraphs)."""
    if "dinamalar.com" in url:
        return dinamalar.article(url)
    h = _get(url, timeout=40).text
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
                    body = body or e.get("articleBody", "")
    if not title:
        m = re.search(r'property="og:title"\s+content="([^"]+)"', h) or re.search(r"<title>([^<]+)</title>", h)
        title = html.unescape(m.group(1)).strip() if m else ""
    if not pub:
        m = re.search(r'property="article:published_time"\s+content="([^"]+)"', h)
        pub = m.group(1) if m else ""
    if len(body) < 200:
        h2 = re.sub(r"<(style|script|noscript|svg)[^>]*>.*?</\1>", " ", h, flags=re.S)
        paras = [re.sub(r"\s+", " ", html.unescape(x)).strip() for x in re.sub(r"<[^>]+>", "\n", h2).split("\n")]
        paras = [x for x in paras if len(x) > 60 and re.search(r"[஀-௿]", x) and "{" not in x and "css-" not in x]
        seen, out = set(), []
        for x in paras:
            if x not in seen:
                seen.add(x)
                out.append(x)
        body = "\n".join(out)
    return {"url": url, "title": html.unescape(title).strip(), "published": pub, "text": html.unescape(body).strip()}
