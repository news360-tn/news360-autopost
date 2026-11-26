"""owner 26 Nov: the HISTORY reel design - NOT the news template. Warm parchment / heritage look: a title card "நம்ம ஊர் வரலாறு",
then 6-8 scenes (the story's own AI pictures, slow zoom) with the narration as subtitles on a paper panel, then a follow card.
No news bar, no ticker, no headline strip. The page logo is small, top-right (never bottom-right).

reel_page(p, topic, lines, scene_uris, line_times, ai=True) -> HTML whose every frame is set by window.seek(t) (window.DUR seconds).
  p           the page (lanes/pages.page(key)) + p["logo"] (data uri)
  scene_uris  one picture per scene (data: / file: address)
  line_times  [(start, end)] seconds of each narration line (from the voice clip lengths, or an estimate)"""
import html as _html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lanes"))
import lane_common as common  # noqa: E402

TITLE_S = 3.0
END_S = 3.0
XFADE = 0.7
COVER_MS = 2600      # Instagram cover: the title card fully built


def esc(s):
    return _html.escape(str(s or ""))


def fit_size(text):
    """subtitle font size (px) so the line fits the paper panel: long lines get smaller type"""
    n = len(text)
    return 58 if n <= 52 else 52 if n <= 78 else 46 if n <= 100 else 42 if n <= 125 else 38


def timeline(line_times):
    """-> (scenes [(start, end)], total duration). Scene i shows narration line i (the last scenes share the last lines)."""
    t0 = TITLE_S
    scenes = []
    for a, b in line_times:
        scenes.append((t0 + a, t0 + b))
    dur = (scenes[-1][1] if scenes else TITLE_S) + END_S
    return scenes, dur


def estimate_times(lines, per_char=0.085, min_s=3.4, gap=0.35):
    """narration length without a voice (subtitles only): reading speed per character"""
    out, t = [], 0.0
    for ln in lines:
        d = max(min_s, len(ln["text"]) * per_char)
        out.append((t, t + d))
        t += d + gap
    return out


def reel_page(p, topic, lines, scene_uris, line_times, ai=True):
    scenes, dur = timeline(line_times)
    n = len(lines)
    pics = [scene_uris[i % len(scene_uris)] for i in range(n)]      # fewer pictures than lines: they repeat in order
    data = {"dur": dur, "title": TITLE_S, "end": END_S, "xf": XFADE,
            "scenes": [{"a": a, "b": b, "text": lines[i]["text"], "img": pics[i], "k": i, "fs": fit_size(lines[i]["text"])} for i, (a, b) in enumerate(scenes)]}
    handle = esc(p.get("handle", ""))
    px = int(p.get("brand_px", 54)) * 2.4
    note = "படங்கள் AI மூலம் உருவாக்கப்பட்டவை - உண்மையான இடத்தின் புகைப்படங்கள் அல்ல" if ai else ""
    return f"""<!doctype html><html lang="ta"><head><meta charset="utf-8"><style>
{common.font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:#2a1a0c}}
body{{font-family:'NST','Noto Sans Tamil',sans-serif;color:#3a2210;position:relative}}
#paper{{position:absolute;inset:0;background:
  radial-gradient(ellipse at 50% 38%,#f6e8c8 0%,#eed9a8 52%,#d9bd84 100%);}}
#grain{{position:absolute;inset:0;opacity:.22;mix-blend-mode:multiply}}
#vig{{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,transparent 55%,rgba(60,30,8,.55) 100%)}}
#frame{{position:absolute;inset:34px;border:5px double #7a4b1e;border-radius:26px;pointer-events:none}}
#frame:after{{content:"";position:absolute;inset:12px;border:2px solid rgba(122,75,30,.55);border-radius:18px}}
#logo{{position:absolute;top:62px;right:62px;width:{px:.0f}px;height:{px:.0f}px;border-radius:50%;background:#fff url({p['logo']}) center/cover;
  box-shadow:0 0 0 5px #f6e8c8,0 0 0 8px #7a4b1e,0 10px 26px rgba(60,30,8,.4);z-index:20}}
#brand{{position:absolute;top:84px;left:70px;font-weight:800;font-size:40px;letter-spacing:.5px;color:#7a4b1e;z-index:20}}
#brand small{{display:block;font-size:28px;font-weight:700;color:#9a6a35}}
#title{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 110px;z-index:10}}
#title .series{{font-size:60px;font-weight:800;color:#8a4d12;letter-spacing:1px}}
#title .orn{{width:520px;height:26px;margin:26px 0 40px;background:
  linear-gradient(90deg,transparent,#8a4d12 30%,#8a4d12 70%,transparent) center/100% 3px no-repeat;position:relative}}
#title .orn:after{{content:"❖";position:absolute;left:50%;top:50%;transform:translate(-50%,-52%);background:#efdcae;padding:0 18px;color:#8a4d12;font-size:34px}}
#title h1{{font-size:96px;line-height:1.22;font-weight:900;color:#3a2210;text-wrap:balance}}
#title .town{{margin-top:46px;font-size:46px;font-weight:700;color:#fff;background:#8a4d12;padding:10px 40px;border-radius:60px}}
.sc{{position:absolute;left:90px;right:90px;top:250px;height:1010px;border-radius:360px 360px 34px 34px;overflow:hidden;opacity:0;
  box-shadow:0 0 0 8px #f6e8c8,0 0 0 12px #7a4b1e,0 30px 60px rgba(60,30,8,.45);background:#c9a86a}}
.sc img{{position:absolute;inset:-6%;width:112%;height:112%;object-fit:cover;filter:sepia(.35) saturate(1.1) contrast(1.02)}}
.sc:after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,226,160,.14),rgba(80,40,10,.22))}}
.cap{{position:absolute;left:90px;right:90px;top:1320px;height:430px;opacity:0;display:flex;align-items:center;justify-content:center;text-align:center;
  background:linear-gradient(180deg,#f9edcf,#ecd7a2);border:4px solid #7a4b1e;border-radius:30px;padding:30px 44px;
  box-shadow:0 18px 40px rgba(60,30,8,.4);font-size:58px;line-height:1.38;font-weight:800;color:#3a2210;text-wrap:balance}}
#prog{{position:absolute;left:90px;right:90px;bottom:118px;height:8px;border-radius:6px;background:rgba(122,75,30,.25);z-index:12}}
#prog i{{display:block;height:100%;width:0;border-radius:6px;background:#8a4d12}}
#end{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;opacity:0;padding:0 120px;
  background:radial-gradient(ellipse at 50% 40%,rgba(246,232,200,.96),rgba(217,189,132,.98));z-index:15}}
#end .big{{font-size:78px;font-weight:900;color:#3a2210;line-height:1.25}}
#end .at{{margin-top:34px;font-size:56px;font-weight:800;color:#fff;background:#8a4d12;padding:12px 44px;border-radius:60px}}
#end .ai{{margin-top:70px;font-size:34px;font-weight:600;color:#6b4423;line-height:1.5}}
</style></head><body>
<div id="paper"></div>
<svg id="grain" width="1080" height="1920"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 .45  0 0 0 0 .3  0 0 0 0 .12  0 0 0 .55 0"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>
<div id="vig"></div><div id="frame"></div>
<div id="logo"></div>
<div id="brand">நம்ம ஊர் வரலாறு<small>{handle}</small></div>
<div id="title"><div class="series">நம்ம ஊர் வரலாறு</div><div class="orn"></div><h1>{esc(topic['title_ta'])}</h1><div class="town">{esc(topic['town_ta'])}</div></div>
<div id="scenes"></div>
<div id="prog"><i></i></div>
<div id="end"><div class="big">மேலும் நம்ம ஊர் வரலாறு<br>தினமும் இங்கே</div><div class="at">{handle}</div><div class="ai">{esc(note)}</div></div>
<script>
const D = {json.dumps(data, ensure_ascii=False)};
window.DUR = D.dur;
const $ = (s) => document.querySelector(s);
const host = $('#scenes');
D.scenes.forEach((s, i) => {{
  const sc = document.createElement('div'); sc.className = 'sc'; sc.id = 'sc' + i; const im = document.createElement('img'); im.src = s.img; sc.appendChild(im); host.appendChild(sc);
  const cp = document.createElement('div'); cp.className = 'cap'; cp.id = 'cp' + i; cp.textContent = s.text; cp.style.fontSize = s.fs + 'px'; host.appendChild(cp);
}});
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const ease = (x) => x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
window.seek = function (t) {{
  // title card: builds in, then fades as the first scene arrives
  const tt = $('#title'); const tin = ease(clamp(t / 0.9, 0, 1)); const tout = 1 - clamp((t - (D.title - 0.5)) / 0.5, 0, 1);
  tt.style.opacity = tin * tout; tt.style.transform = 'scale(' + (0.94 + 0.06 * tin + 0.02 * clamp(t / D.title, 0, 1)) + ')';
  D.scenes.forEach((s, i) => {{
    const sc = $('#sc' + i), cp = $('#cp' + i), im = sc.firstChild;
    const a = s.a - D.xf * 0.5, b = s.b + D.xf * 0.5;
    const op = t < a || t > b ? 0 : Math.min(clamp((t - a) / D.xf, 0, 1), clamp((b - t) / D.xf, 0, 1));
    sc.style.opacity = ease(op); cp.style.opacity = ease(op);
    const p = clamp((t - a) / (b - a), 0, 1);
    const dir = i % 2 ? -1 : 1;      // slow zoom + a small drift, alternating direction
    im.style.transform = 'translate(' + (dir * (p - 0.5) * 36) + 'px,' + (-(p - 0.5) * 24) + 'px) scale(' + (1 + 0.09 * p) + ')';
    sc.style.transform = 'translateY(' + ((1 - ease(op)) * 26) + 'px)'; cp.style.transform = 'translateY(' + ((1 - ease(op)) * 20) + 'px)';
  }});
  const e = $('#end'); e.style.opacity = ease(clamp((t - (D.dur - D.end)) / 0.7, 0, 1));
  $('#prog i').style.width = (clamp(t / D.dur, 0, 1) * 100) + '%';
}};
window.seek(0);
</script></body></html>"""
