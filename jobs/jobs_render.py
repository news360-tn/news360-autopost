"""owner 26 Nov: the JOBS reel design - an animated JOB BOARD: dark teal board with a faint grid, a "வேலைவாய்ப்பு அறிவிப்பு" header, and cards that
slide in one after another (post name, vacancies, qualification, last date with the days left, where to apply), then an official-link card.
Clearly different from the news design and from the heritage history design. Page logo small, top-right. About 18-22 s, music only.

reel_page(p, job, days_left, day) -> HTML whose every frame is set by window.seek(t) (window.DUR seconds)."""
import html as _html
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lanes"))
import lane_common as common  # noqa: E402
import lane_factgate as factgate  # noqa: E402

INTRO_S = 2.4
STEP_S = 2.6
COVER_MS = 5200      # Instagram cover: the board with the post and its first cards built

ICONS = {
    "post": '<path d="M3 8h18v11H3zM8 8V5h8v3M3 13h18"/>',
    "vac": '<path d="M17 20v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M10 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM21 20v-2a4 4 0 0 0-3-3.9M16 2.1a4 4 0 0 1 0 7.8"/>',
    "edu": '<path d="m2 9 10-5 10 5-10 5zM6 11v5c3 2 9 2 12 0v-5"/>',
    "cal": '<path d="M3 5h18v16H3zM3 10h18M8 3v4M16 3v4"/>',
    "pin": '<path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12zM12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z"/>',
}


def esc(s):
    return _html.escape(str(s or ""))


def date_ta(d):
    return f"{d.day} {factgate.MONTHS_TA[d.month - 1]} {d.year}"


def cards(job, left, day):
    """[(kind, label, value, accent)] in the order they slide in"""
    last = date.fromisoformat(job["last_date"]) if job.get("last_date") else None
    event = date.fromisoformat(job["event_date"]) if job.get("event_date") else None
    out = [("post", "பணி", job["post"], "#22d3ee")]
    if str(job.get("vacancies", "")).strip():
        out.append(("vac", "காலிப்பணியிடங்கள்", job["vacancies"], "#a3e635"))
    out.append(("edu", "கல்வித் தகுதி", job["qualification"], "#fbbf24"))
    if last:
        tail = "" if left is None else (" · இன்று கடைசி நாள்" if left == 0 else f" · இன்னும் {left} நாட்கள்")
        out.append(("cal", "கடைசி தேதி", date_ta(last) + tail, "#fb7185"))
    elif event:
        out.append(("cal", "நிகழ்ச்சி தேதி", date_ta(event) + ("" if left is None else f" · இன்னும் {left} நாட்கள்"), "#fb7185"))
    out.append(("pin", "எங்கே விண்ணப்பிக்க", job["apply_where"], "#c084fc"))
    return out


def reel_page(p, job, left, day, tag="புதிய அறிவிப்பு"):
    cs = cards(job, left, day)
    n = len(cs)
    dur = INTRO_S + STEP_S * n + 2.2 + 2.6      # intro + cards + official-link card + follow card
    host = (urlparse(job.get("link", "")).hostname or "").replace("www.", "")
    data = {"dur": dur, "intro": INTRO_S, "step": STEP_S, "n": n, "cards": [{"k": k, "label": lb, "v": v, "c": c} for k, lb, v, c in cs],
            "host": host, "district": p["district_ta"], "town": p["town"], "tag": tag}
    px = int(p.get("brand_px", 54)) * 2.4
    icons = json.dumps(ICONS)
    return f"""<!doctype html><html lang="ta"><head><meta charset="utf-8"><style>
{common.font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:#07151f}}
body{{font-family:'NST','Noto Sans Tamil',sans-serif;color:#e8f6fb;position:relative}}
#bg{{position:absolute;inset:0;background:radial-gradient(ellipse at 20% 0%,#0f4254 0%,#0a2433 45%,#06121b 100%)}}
#grid{{position:absolute;inset:0;opacity:.35;background-image:linear-gradient(rgba(120,220,240,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(120,220,240,.10) 1px,transparent 1px);background-size:60px 60px}}
#logo{{position:absolute;top:62px;right:62px;width:{px:.0f}px;height:{px:.0f}px;border-radius:50%;background:#fff url({p['logo']}) center/cover;box-shadow:0 0 0 5px #0a2433,0 0 0 8px #22d3ee;z-index:20}}
#head{{position:absolute;left:70px;top:70px;right:250px;z-index:10}}
#head .chip{{display:inline-block;background:#22d3ee;color:#04202b;font-weight:900;font-size:40px;padding:8px 30px;border-radius:50px}}
#head .dist{{margin-top:20px;font-size:56px;font-weight:900;line-height:1.15;white-space:nowrap}}
#head .sub{{margin-top:4px;font-size:34px;font-weight:700;color:#8fd3e6}}
#new{{position:absolute;left:70px;top:312px;font-size:34px;font-weight:900;color:#06121b;background:#fbbf24;padding:6px 26px;border-radius:50px;z-index:10}}
#intro{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;z-index:18;background:radial-gradient(ellipse at 50% 40%,#0f4254,#06121b);padding:0 100px}}
#intro .big{{font-size:104px;font-weight:900;line-height:1.2;color:#fff}}
#intro .big b{{color:#22d3ee}}
#intro .d{{margin-top:40px;font-size:64px;font-weight:800;color:#fbbf24}}
#list{{position:absolute;left:60px;right:60px;top:392px;z-index:6}}
.card{{display:flex;gap:26px;align-items:flex-start;margin-bottom:18px;padding:22px 30px;border-radius:30px;background:rgba(12,52,68,.82);border:2px solid rgba(120,220,240,.25);box-shadow:0 18px 40px rgba(0,0,0,.4);opacity:0;position:relative;overflow:hidden}}
.card:before{{content:"";position:absolute;left:0;top:0;bottom:0;width:12px;background:var(--c)}}
.card .ic{{flex:none;width:92px;height:92px;border-radius:24px;background:rgba(255,255,255,.08);display:grid;place-items:center;color:var(--c)}}
.card .ic svg{{width:54px;height:54px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}}
.card .l{{font-size:32px;font-weight:700;color:#8fd3e6;letter-spacing:.3px}}
.card .v{{margin-top:4px;font-size:46px;font-weight:800;line-height:1.26;color:#fff;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.card.big .v{{font-size:60px;line-height:1.2;-webkit-line-clamp:2}}
#official{{position:absolute;left:60px;right:60px;bottom:150px;padding:30px 36px;border-radius:30px;background:#22d3ee;color:#04202b;opacity:0;z-index:8;text-align:center}}
#official .a{{font-size:38px;font-weight:800}}
#official .b{{margin-top:6px;font-size:52px;font-weight:900;word-break:break-all}}
#end{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;opacity:0;z-index:19;background:radial-gradient(ellipse at 50% 40%,#0f4254,#06121b);padding:0 110px}}
#end .big{{font-size:78px;font-weight:900;line-height:1.3}}
#end .at{{margin-top:34px;font-size:56px;font-weight:800;color:#04202b;background:#22d3ee;padding:12px 44px;border-radius:60px}}
#end .w{{margin-top:56px;font-size:34px;font-weight:600;color:#8fd3e6;line-height:1.5}}
#prog{{position:absolute;left:60px;right:60px;bottom:96px;height:8px;border-radius:6px;background:rgba(255,255,255,.12);z-index:12}}
#prog i{{display:block;height:100%;width:0;border-radius:6px;background:#22d3ee}}
</style></head><body>
<div id="bg"></div><div id="grid"></div><div id="logo"></div>
<div id="head"><span class="chip">வேலைவாய்ப்பு அறிவிப்பு</span><div class="dist">{esc(p['district_ta'])} மாவட்டம்</div><div class="sub">{esc(p['town'])} 360</div></div>
<div id="new">{esc(tag)}</div>
<div id="list"></div>
<div id="official"><div class="a">அதிகாரப்பூர்வ அறிவிப்பு</div><div class="b" id="host"></div></div>
<div id="prog"><i></i></div>
<div id="intro"><div class="big"><b>வேலை</b> தேடுகிறீர்களா?</div><div class="d">{esc(p['district_ta'])} மாவட்டத்தில் புதிய அறிவிப்பு</div></div>
<div id="end"><div class="big">மேலும் வேலைவாய்ப்பு<br>அறிவிப்புகளுக்கு</div><div class="at">{esc(p.get('handle', ''))}</div>
<div class="w">விண்ணப்பிக்கும் முன் அதிகாரப்பூர்வ அறிவிப்பில் தகுதி, கடைசி தேதியை சரிபாருங்கள்.<br>வேலை தருவதாகச் சொல்லிப் பணம் கேட்பவர்களிடம் எச்சரிக்கை.</div></div>
<script>
const D = {json.dumps(data, ensure_ascii=False)}, IC = {icons};
window.DUR = D.dur;
const $ = (s) => document.querySelector(s);
const list = $('#list');
D.cards.forEach((c, i) => {{
  const e = document.createElement('div'); e.className = 'card' + (i === 0 ? ' big' : ''); e.id = 'c' + i; e.style.setProperty('--c', c.c);
  e.innerHTML = '<div class="ic"><svg viewBox="0 0 24 24">' + IC[c.k] + '</svg></div><div><div class="l"></div><div class="v"></div></div>';
  e.querySelector('.l').textContent = c.label; e.querySelector('.v').textContent = c.v; list.appendChild(e);
}});
$('#host').textContent = D.host;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const ease = (x) => 1 - Math.pow(1 - x, 3);
window.seek = function (t) {{
  $('#intro').style.opacity = 1 - clamp((t - (D.intro - 0.5)) / 0.5, 0, 1);
  $('#intro .big').style.transform = 'scale(' + (0.92 + 0.08 * ease(clamp(t / 0.8, 0, 1))) + ')';
  D.cards.forEach((c, i) => {{
    const a = D.intro + i * D.step, p = ease(clamp((t - a) / 0.55, 0, 1));
    const e = $('#c' + i); e.style.opacity = p; e.style.transform = 'translateX(' + ((1 - p) * 420) + 'px)';
  }});
  const oa = D.intro + D.n * D.step; $('#official').style.opacity = ease(clamp((t - oa) / 0.6, 0, 1));
  $('#official').style.transform = 'translateY(' + ((1 - ease(clamp((t - oa) / 0.6, 0, 1))) * 60) + 'px)';
  $('#end').style.opacity = ease(clamp((t - (D.dur - 2.6)) / 0.6, 0, 1));
  $('#prog i').style.width = (clamp(t / D.dur, 0, 1) * 100) + '%';
}};
window.seek(0);
</script></body></html>"""
