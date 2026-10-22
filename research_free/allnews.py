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
OUTLET_WORDS = ["தினமலர்", "தினத்தந்தி", "தினமணி", "மாலைமலர்", "தினகரன்", "இந்து தமிழ்", "தி இந்து", "புதிய தலைமுறை", "நியூஸ்18", "நியூஸ் 18",
                "விகடன்", "ஏபிபி", "சமயம்", "polimer", "பாலிமர்", "தந்தி டிவி", "ஜீ தமிழ்", "நக்கீரன்", "டைம்ஸ்"]


def _get(url, timeout=40, headers=None):
    r = requests.get(url, headers=headers or UA, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r


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
    try:
        from googlenewsdecoder import gnewsdecoder
        r = gnewsdecoder(url, interval=1)
        if r.get("status") and r.get("decoded_url"):
            return r["decoded_url"]
    except Exception:
        pass
    try:
        return _get(url, timeout=30).url
    except Exception:
        return url


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
