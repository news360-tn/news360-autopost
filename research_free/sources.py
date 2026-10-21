"""Fetch Namakkal district news candidates. Free sources only; polite 1.5 s gaps. Used inside GitHub Actions."""
import re, time, html
import requests
UA = {"User-Agent": "Mozilla/5.0 (compatible; Namakkal360-research/1.0)"}
LIST_URL = "https://www.dinamalar.com/news/tamil-nadu-district-news-namakkal"


def _get(u):
    time.sleep(1.5)
    r = requests.get(u, headers=UA, timeout=40)
    r.raise_for_status()
    return r.text


def candidate_links(limit=15):
    h = _get(LIST_URL)
    links = []
    for m in re.finditer(r'href="(/news/[^"#?]+?/\d{6,})"', h):
        u = "https://www.dinamalar.com" + m.group(1)
        if u not in links:
            links.append(u)
    return links[:limit]


def article(url):
    """returns dict(title, published, text) parsed from the page"""
    h = _get(url)
    def g(pat):
        m = re.search(pat, h)
        return html.unescape(m.group(1)).strip() if m else ""
    title = g(r'"newstitle"\s*:\s*"([^"]+)"') or g(r"<title>([^<]+)</title>")
    pub = g(r'"publisheddate"\s*:\s*"([^"]+)"')
    paras = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<p[^>]*>(.*?)</p>", h, re.S)]
    text = "\n".join(x for x in paras if len(x) > 40)
    return {"url": url, "title": title, "published": pub, "text": text}
