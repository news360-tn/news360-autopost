"""நாமக்கல் 360 / இராசிபுரம் 360 — news reel v4 (DESIGN PREVIEW, not used by the posting job yet).
Usage: python3 reel4.py spec.json out.mp4 [page]      (same spec as reel3.py)

What changed from v3 (why):
- Everything that matters sits inside Instagram's safe zone (y 150-1600, x 48-950): v3 put its logo strip at the very bottom and the caption box
  under the like/share buttons, where Instagram's own caption and buttons cover them.
- No scrolling ticker and no bottom logo bar: they repeated the headline and competed with the captions.
- A short headline stays on screen after the hook, so a viewer who joins late still knows what the story is (watch time is the first ranking signal).
- 5W fact cards (where / when / who / how many / action) with an icon, instead of one yellow sticker: the details people ask for in comments.
- Captions are whole short phrases (never a sentence cut in the middle), large, outlined, the spoken word highlighted, 2 lines max.
- Location pin from frame 1: local news is watched because it is about the viewer's own town.
- End card asks for a SEND ("தேவைப்படுவோருக்கு அனுப்புங்கள்") - DM sends are the strongest signal for reaching new people - then Follow.
Env PREVIEW_TTS=edge: preview voice from edge-tts (no local Tamil voice model needed); the posting job keeps tts.py.
"""
import json, sys, os, re, subprocess, html, math
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reel as R
import reel3 as V3
from digits import to_digits

E = html.escape
W, H, FPS = 1080, 1920, 30

CSS = R.ff("CT", "catamaran", [700, 800, 900]) + R.ff("NST", "noto-sans-tamil", [600, 700, 800]) + R.ff("BT", "baloo-thambi-2", [800]) + """
:root{--acc:#E3151B;--navy:#071433;--yellow:#FFD233}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
body{font-family:'NST','CT',sans-serif;color:#fff;position:relative}
.ic{width:1em;height:1em;display:block}
#stage{position:absolute;inset:0;overflow:hidden}
.pic{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover;opacity:0;will-change:transform,filter}
#shade{position:absolute;inset:0;z-index:5;background:linear-gradient(180deg,rgba(3,8,22,.80) 0%,rgba(3,8,22,.35) 18%,rgba(3,8,22,0) 34%,rgba(3,8,22,0) 50%,rgba(3,8,22,.30) 62%,rgba(3,8,22,.66) 78%,rgba(3,8,22,.88) 100%)}
#flash{position:absolute;inset:0;z-index:7;background:#fff;opacity:0}
/* top: story-style progress segments (one per sentence) */
#segs{position:absolute;left:48px;right:48px;top:30px;height:8px;z-index:30;display:flex;gap:8px}
#segs i{flex:1;background:rgba(255,255,255,.28);border-radius:4px;overflow:hidden;position:relative}
#segs i b{position:absolute;left:0;top:0;bottom:0;width:0;background:#fff;border-radius:4px}
/* header */
#hdr{position:absolute;left:48px;top:150px;z-index:30;display:flex;align-items:center;gap:22px}
#hdr img{width:108px;height:108px;border-radius:50%;border:4px solid #fff;box-shadow:0 8px 24px rgba(0,0,0,.5)}
#hdr .nm{font:800 50px/1.05 'BT','NST';text-shadow:0 3px 12px rgba(0,0,0,.7)}
#hdr .sub{display:flex;align-items:center;gap:12px;margin-top:6px;font:700 30px 'NST','CT';color:#E8ECF5;text-shadow:0 2px 8px rgba(0,0,0,.8)}
#hdr .tag{background:var(--acc);color:#fff;padding:4px 16px 0;border-radius:8px;font:800 28px 'NST','CT'}
/* location pin (frame 1) */
#pin{position:absolute;left:48px;top:300px;z-index:30;display:flex;align-items:center;gap:14px;max-width:880px;background:rgba(255,255,255,.96);color:var(--navy);
  padding:12px 28px 8px 18px;border-radius:999px;font:800 40px/1.2 'NST','CT';box-shadow:0 10px 30px rgba(0,0,0,.45)}
#pin .ic{font-size:40px;color:var(--acc);flex:none;margin-top:-4px}
#pin span{display:block;white-space:nowrap;overflow:hidden;max-width:800px}
/* hook (first seconds) */
#hook{position:absolute;left:48px;right:48px;top:560px;z-index:22;text-align:left;opacity:0}
#hook .h1{font:900 104px/1.1 'CT','NST';color:#fff;-webkit-text-stroke:14px #000;paint-order:stroke fill;text-shadow:0 10px 30px rgba(0,0,0,.5)}
#hook .h2{display:inline-block;margin-top:22px;font:900 84px/1.15 'CT','NST';color:var(--navy);background:var(--yellow);padding:10px 26px 0;border-radius:14px;box-shadow:0 12px 34px rgba(0,0,0,.45)}
/* persistent mini headline after the hook */
#mini{position:absolute;left:48px;right:130px;top:410px;z-index:22;opacity:0;font:800 46px/1.28 'NST','CT';color:#fff;
  border-left:10px solid var(--yellow);padding:4px 0 0 22px;text-shadow:0 3px 14px rgba(0,0,0,.85)}
/* 5W fact cards */
.card{position:absolute;left:48px;top:640px;width:820px;z-index:23;opacity:0;display:flex;align-items:stretch;background:#fff;border-radius:26px;
  box-shadow:0 18px 50px rgba(0,0,0,.5);overflow:hidden}
.card .ico{flex:none;width:150px;display:flex;align-items:center;justify-content:center;background:var(--acc);color:#fff;font-size:72px}
.card .tx{padding:22px 30px 16px;display:flex;flex-direction:column;justify-content:center;gap:4px}
.card .lb{font:800 30px 'NST','CT';color:var(--acc);letter-spacing:.5px}
.card .vl{font:800 52px/1.25 'NST','CT';color:var(--navy)}
/* captions: whole phrases, outlined, in the safe zone above Instagram's caption */
#cap{position:absolute;left:56px;right:140px;top:1190px;height:330px;z-index:25}
.ph{position:absolute;left:0;right:0;bottom:0;text-align:left;font:800 70px/1.3 'CT','NST';color:#fff;opacity:0;-webkit-text-stroke:12px #000;paint-order:stroke fill;text-shadow:0 6px 18px rgba(0,0,0,.6)}
.ph span{display:inline-block;transform-origin:50% 70%;margin-right:.22em}
.ph span.on{color:var(--yellow)}
/* full-details summary (last news sentence): every key fact in one place - people pause on it or screenshot it */
#sum{position:absolute;left:48px;right:48px;top:540px;z-index:24;opacity:0;background:rgba(255,255,255,.97);border-radius:30px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.55)}
#sum .st{background:var(--acc);color:#fff;font:900 46px 'CT','NST';padding:18px 34px 10px;display:flex;align-items:center;gap:16px}
#sum .st .ic{font-size:42px;margin-top:-6px}
#sum .row{display:flex;align-items:center;gap:22px;padding:14px 30px 8px;border-top:2px solid #E6E9F0;opacity:0}
#sum .row .ic{flex:none;font-size:42px;color:var(--acc);margin-top:-6px}
#sum .row .l{flex:none;width:200px;font:800 30px/1.2 'NST','CT';color:#6B7280;overflow:hidden}
#sum .row .v{font:800 38px/1.3 'NST','CT';color:var(--navy)}
/* end card */
#end{position:absolute;inset:0;z-index:40;opacity:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:34px;text-align:center;
  padding:0 70px 260px;background:rgba(3,8,22,.62)}
#end img{width:250px;height:250px;border-radius:50%;border:6px solid #fff;box-shadow:0 14px 50px rgba(0,0,0,.6)}
#end .send{display:flex;align-items:center;gap:24px;background:#fff;color:var(--navy);padding:22px 40px 16px;border-radius:28px;font:900 58px/1.2 'CT','NST';box-shadow:0 14px 40px rgba(0,0,0,.5)}
#end .send .ic{font-size:64px;color:var(--acc);flex:none;margin-top:-6px}
#end .fol{display:flex;align-items:center;gap:18px;background:var(--acc);font:900 52px 'CT','NST';padding:16px 44px 10px;border-radius:999px}
#end .fol .ic{font-size:46px;margin-top:-6px}
#end .pl{font:800 44px 'NST','CT';color:var(--yellow)}
"""

# three looks for the same layout and timing (REEL_STYLE=A|B|C, or config "reel_style"); A = the original v4 look
STYLES = {
    "A": "",
    # B - TV broadcast: red headline band, yellow tags, dark cards, captions on a black bar
    "B": """
#hdr{background:rgba(7,20,51,.88);padding:12px 26px 12px 12px;border-radius:999px 24px 24px 999px}
#hdr img{width:92px;height:92px}
#pin{background:var(--yellow);color:var(--navy)}
#pin .ic{color:var(--navy)}
#hook{text-align:center}
#hook .h1{display:inline-block;background:var(--acc);color:#fff;-webkit-text-stroke:0;padding:18px 34px 6px;border-radius:12px;font-size:92px;text-shadow:none;box-shadow:0 14px 40px rgba(0,0,0,.5)}
#hook .h2{background:#fff;color:var(--navy)}
#mini{left:0;right:0;top:405px;background:var(--acc);border-left:0;padding:14px 48px 6px;font-size:42px;text-shadow:none;box-shadow:0 10px 30px rgba(0,0,0,.4)}
.card{background:rgba(7,20,51,.94);border:3px solid var(--yellow)}
.card .ico{background:var(--yellow);color:var(--navy)}
.card .lb{color:var(--yellow)}
.card .vl{color:#fff}
#cap{left:48px;right:48px}
.ph{text-align:center;-webkit-text-stroke:0;background:rgba(0,0,0,.78);padding:16px 30px 6px;border-radius:16px;font-size:62px;text-shadow:none;border-bottom:8px solid var(--acc)}
#sum{background:rgba(7,20,51,.96);border:3px solid var(--yellow)}
#sum .st{background:var(--yellow);color:var(--navy)}
#sum .row{border-top:2px solid rgba(255,255,255,.12)}
#sum .row .ic{color:var(--yellow)}
#sum .row .l{color:#AAB4C8}
#sum .row .v{color:#fff}
#end .send{background:var(--yellow)}
""",
    # C - minimal glass: centred text, frosted cards, more of the photo visible
    "C": """
#shade{background:linear-gradient(180deg,rgba(0,0,0,.65) 0%,rgba(0,0,0,0) 26%,rgba(0,0,0,0) 55%,rgba(0,0,0,.55) 75%,rgba(0,0,0,.85) 100%)}
#hdr{left:0;right:0;justify-content:center}
#hdr img{width:84px;height:84px;border-width:3px}
#hdr .nm{font-size:44px}
#hdr .tag{background:transparent;border:2px solid #fff;padding:2px 14px 0}
#pin{left:0;right:0;margin:0 auto;width:fit-content;transform-origin:50% 50%;background:rgba(255,255,255,.16);color:#fff;border:2px solid rgba(255,255,255,.45);backdrop-filter:blur(16px);box-shadow:none}
#pin .ic{color:var(--yellow)}
#hook{text-align:center;top:640px}
#hook .h1{-webkit-text-stroke:0;font-size:100px;text-shadow:0 6px 40px rgba(0,0,0,.85)}
#hook .h2{background:transparent;color:var(--yellow);box-shadow:none;padding:0;border-bottom:8px solid var(--yellow);border-radius:0;font-size:80px}
#mini{left:90px;right:90px;text-align:center;border-left:0;padding:0;font-size:40px;top:420px;color:#F1F3F8}
.card{left:90px;width:900px;background:rgba(255,255,255,.14);backdrop-filter:blur(22px);border:2px solid rgba(255,255,255,.4);box-shadow:0 20px 60px rgba(0,0,0,.35)}
.card .ico{width:130px;background:transparent;color:var(--yellow);font-size:66px}
.card .lb{color:var(--yellow)}
.card .vl{color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.4)}
#cap{left:60px;right:60px}
.ph{text-align:center;-webkit-text-stroke:0;font-size:68px;text-shadow:0 4px 24px rgba(0,0,0,.95),0 2px 4px rgba(0,0,0,.9)}
.ph span.on{color:#fff;text-decoration:underline;text-decoration-color:var(--yellow);text-decoration-thickness:8px;text-underline-offset:12px}
#sum{background:rgba(20,24,36,.55);backdrop-filter:blur(26px);border:2px solid rgba(255,255,255,.35)}
#sum .st{background:transparent;border-bottom:2px solid rgba(255,255,255,.3)}
#sum .row{border-top:1px solid rgba(255,255,255,.15)}
#sum .row .ic{color:var(--yellow)}
#sum .row .l{color:#C9D0DE}
#sum .row .v{color:#fff}
#end .send{background:rgba(255,255,255,.95)}
""",
}

ACCENT = {"மின் தடை": "#F59E0B", "மழை": "#1E88E5", "வானிலை": "#1E88E5", "வெள்ள": "#1E88E5", "விபத்து": "#E3151B", "குற்ற": "#B91C1C",
          "கோவில்": "#C2410C", "திருவிழா": "#C2410C", "வேலை": "#059669", "கல்வி": "#2563EB", "தாக்குதல்": "#DC2626"}

# what a fact is about -> icon + label (the label tells the viewer which of the 5W the card answers)
KINDS = [
    (r"ரூ\.?|₹|லட்சம்|கோடி|ரூபாய்", "indian-rupee-sign", "தொகை"),
    (r"மணி|நேரம்", "clock", "நேரம்"),
    (r"தேதி|ஜனவரி|பிப்ரவரி|மார்ச்|ஏப்ரல்|ஜூன்|ஜூலை|ஆகஸ்ட்|செப்டம்பர்|அக்டோபர்|நவம்பர்|டிசம்பர்|இன்று|நாளை", "calendar-days", "நாள்"),
    (r"மருத்துவமனை|சிகிச்சை", "hospital", "சிகிச்சை"),
    (r"கைது|போலீஸ்|போலீசார்|காவல்", "handcuffs", "நடவடிக்கை"),
    (r"வயது|குழந்தை|சிறுமி|சிறுவன்|மாணவ", "child", "யார்"),
    (r"\d+\s*பேர்|பலர்|மக்கள்", "users", "எத்தனை பேர்"),
    (r"நடவடிக்கை|கோரிக்கை|உத்தரவு|அறிவிப்பு", "bullhorn", "நடவடிக்கை"),
    (r"நகர்|சாலை|கிராம|ஊராட்சி|பகுதி", "location-dot", "இடம்"),
]


def accent_for(cat):
    for k, v in ACCENT.items():
        if k in (cat or ""):
            return v
    return "#E3151B"


def card_for(fact):
    """{"icon","label","text"} or a plain fact string -> card"""
    if isinstance(fact, dict):
        return fact if fact.get("text") else None
    t = re.sub(r"<[^>]+>", "", str(fact or "")).strip()
    if not t:
        return None
    for pat, ic, lb in KINDS:
        if re.search(pat, t):
            return {"icon": ic, "label": lb, "text": t}
    return {"icon": "circle-info", "label": "முக்கிய தகவல்", "text": t}


def phrases(words, maxw=4):
    """whole short phrases: break after punctuation, otherwise every ~maxw words; never leave one word alone"""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[,.!?।:]$", w[0]) or len(cur) >= maxw:
            out.append(cur); cur = []
    if cur:
        if out and len(cur) <= 2 and len(out[-1]) + len(cur) <= maxw + 2:
            out[-1] += cur
        else:
            out.append(cur)
    return out


def edge_lines(work, texts, voice="ta-IN-ValluvarNeural"):
    """preview voice: edge-tts per line (numbers and abbreviations prepared exactly like the real voice)"""
    import tts
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research_free"))
    import names
    for i, t in enumerate(texts):
        mp3, wav = work / f"line{i}.mp3", work / f"line{i}.wav"
        say = tts.clean(names.spoken(t))
        for k in range(4):      # the free voice service fails now and then: try again
            r = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", voice, "--rate=+8%", "--text", say, "--write-media", str(mp3)], timeout=90)
            if r.returncode == 0 and mp3.exists() and mp3.stat().st_size > 1000:
                break
            import time; time.sleep(5 * (k + 1))
        else:
            raise RuntimeError(f"preview voice failed for line {i}")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm=I=-16:TP=-1.5",
                        "-ar", "22050", "-ac", "1", str(wav)], check=True)


def build_html(spec, shots, sents, caps, hook_end, end_t, total, page):
    logo = f"file://{R.KIT.resolve() / page['logo']}"
    acc = accent_for(spec.get("cat", ""))
    imgs = "".join(f'<img class="pic" id="p{i}" src="file://{Path(p).resolve()}">' for i, p in enumerate(spec["images"]))
    cards = ""
    for i, s in enumerate(sents):
        c = card_for(s.get("card") or s.get("fact"))
        s["has_card"] = bool(c)
        if c:
            cards += (f'<div class="card" id="c{i}"><div class="ico">{R.icon(c["icon"])}</div>'
                      f'<div class="tx"><div class="lb">{E(c["label"])}</div><div class="vl">{E(to_digits(c["text"]))}</div></div></div>')
    # one row per kind of fact (the longest text wins), the most useful kinds first
    best = {}
    for c in [{"icon": "location-dot", "label": "இடம்", "text": spec.get("location", "")}] + [card_for(s.get("card") or s.get("fact")) for s in sents] + list(spec.get("summary") or []):
        if c and c.get("text"):
            k = c["label"]
            if k not in best or len(c["text"]) > len(best[k]["text"]):
                best[k] = c
    ORDER = ["இடம்", "நாள்", "நேரம்", "என்ன நடந்தது", "யார்", "பலத்த காயம்", "எத்தனை பேர்", "காயமடைந்தோர்", "தொகை", "சிகிச்சை",
             "நடவடிக்கை", "கோரிக்கை", "மக்கள் புகார்", "மக்கள் கவனத்திற்கு", "முக்கிய தகவல்"]
    must = ["இடம்", "சிகிச்சை", "நடவடிக்கை", "மக்கள் கவனத்திற்கு", "தொகை", "நேரம்", "நாள்"]      # never dropped for space
    keys = sorted(best, key=lambda k: (k not in must, ORDER.index(k) if k in ORDER else 99))[:6]
    rows = [best[k] for k in sorted(keys, key=lambda k: ORDER.index(k) if k in ORDER else 99)]
    summary = "" if len(rows) < 3 else ('<div id="sum"><div class="st">' + R.icon('circle-info') + '<span>முழு விவரம்</span></div>' + "".join(
        f'<div class="row" id="r{i}">{R.icon(c["icon"])}<div class="l">{E(c["label"])}</div><div class="v">{E(to_digits(c["text"]))}</div></div>' for i, c in enumerate(rows)) + '</div>')
    cap_html = ""
    for gi, g in enumerate(caps):
        spans = "".join(f'<span id="w{gi}_{k}">{E(w[0])}</span>' for k, w in enumerate(g["words"]))
        cap_html += f'<div class="ph" id="g{gi}">{spans}</div>'
    hook = spec.get("hook") or ["", ""]
    mini = spec.get("mini") or " ".join(x for x in hook if x)
    segs = "".join("<i><b></b></i>" for _ in sents)
    data = json.dumps({"shots": shots, "sents": [{"a": s["a"], "b": s["b"], "card": s["has_card"]} for s in sents],
                       "caps": [{"a": g["a"], "b": g["b"], "w": [[x[1], x[2]] for x in g["words"]]} for g in caps],
                       "hook_end": hook_end, "end_t": end_t, "total": total, "n": len(spec["images"]),
                       "sum_a": (sents[-2]["a"] if len(sents) > 5 else sents[-1]["a"]) if len(sents) > 3 else end_t, "rows": len(rows) if summary else 0})
    style = (os.environ.get("REEL_STYLE") or spec.get("style") or "A").upper()
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}{STYLES.get(style, "")}</style></head><body style="--acc:{acc}">
<div id="stage">{imgs}</div><div id="shade"></div><div id="flash"></div>
<div id="segs">{segs}</div>
<div id="hdr"><img src="{logo}"><div><div class="nm">{page['name']}</div>
<div class="sub"><span class="tag">{E(spec.get('cat', ''))}</span><span>{E(spec['date'])}</span></div></div></div>
<div id="pin">{R.icon('location-dot')}<span>{E(spec.get('location', ''))}</span></div>
<div id="hook"><div class="h1">{E(hook[0])}</div><div class="h2">{E(hook[1])}</div></div>
<div id="mini">{E(mini)}</div>
{cards}
{summary}
<div id="cap">{cap_html}</div>
<div id="end"><img src="{logo}">
<div class="send">{R.icon('paper-plane')}<span>தேவைப்படுவோருக்கு அனுப்புங்கள்</span></div>
<div class="fol">{R.icon('user-plus')}<span>FOLLOW @{page['handle']}</span></div>
<div class="pl">{E(page['tagline'])}</div></div>
<script>
const D={data};
const cl=x=>Math.max(0,Math.min(1,x)), ease=x=>1-Math.pow(1-x,3), back=x=>{{const c=1.70158,c3=c+1;return 1+c3*Math.pow(x-1,3)+c*Math.pow(x-1,2)}};
function place(sh_,t,el,extra){{
  const dur=Math.max(0.5,sh_.b-sh_.a), tt=Math.min(t,sh_.b), pr=cl((tt-sh_.a)/Math.min(dur,2.4));
  const pe=pr<0.5?2*pr*pr:1-Math.pow(-2*pr+2,2)/2, z=sh_.z0+(sh_.z1-sh_.z0)*pe;
  el.style.transformOrigin=(sh_.fx*100)+'% '+(sh_.fy*100)+'%';
  el.style.transform='translate('+(sh_.px*(pe-0.5)+(extra||0))+'px,'+(sh_.py*(pe-0.5))+'px) scale('+(z*1.02)+')';
}}
window.renderAt=function(t){{
  let ai=D.shots.length-1; D.shots.forEach((s,i)=>{{if(t>=s.a&&t<s.b)ai=i}});
  const active=D.shots[ai], k=t-active.a, prev=ai>0?D.shots[ai-1]:null;
  const TR=0.3, trans=(prev&&prev.img!==active.img&&k<TR)?cl(k/TR):1;
  for(let i=0;i<D.n;i++){{const e=document.getElementById('p'+i);e.style.opacity=0;e.style.zIndex=0;e.style.filter='none';}}
  const el=document.getElementById('p'+active.img); el.style.opacity=ease(trans); el.style.zIndex=2; place(active,t,el,(1-ease(trans))*90);
  if(trans<1){{const pe_=document.getElementById('p'+prev.img);pe_.style.opacity=1;pe_.style.zIndex=1;place(prev,t,pe_,-ease(trans)*120);}}
  if(t>=D.end_t)el.style.filter='blur('+(18*Math.min(1,(t-D.end_t)/0.3))+'px)';
  document.getElementById('flash').style.opacity=(active.a>0&&k<0.1&&prev&&prev.img!==active.img)?0.12*(1-k/0.1):0;
  // progress segments: one per sentence
  document.querySelectorAll('#segs b').forEach((b,i)=>{{const s=D.sents[i];b.style.width=(100*cl((t-s.a)/Math.max(0.3,s.b-s.a)))+'%';}});
  // hook: frame 1 -> hook_end, then the mini headline stays
  const h=document.getElementById('hook'), hin=back(cl(t/0.3)), hout=cl((t-(D.hook_end-0.25))/0.25);
  h.style.opacity=(t<D.hook_end)?cl(t/0.12)*(1-hout):0; h.style.transform='translateY('+(30*(1-Math.min(1,hin)))+'px)';
  const m=document.getElementById('mini'), min_=ease(cl((t-D.hook_end)/0.35));
  m.style.opacity=(t>=D.hook_end&&t<D.end_t)?min_:0; m.style.transform='translateX('+(-(1-min_)*60)+'px)';
  // pin + header always (until the end card)
  const live=t<D.end_t?1:0;
  ['pin','hdr','segs'].forEach(id=>document.getElementById(id).style.opacity=live);
  document.getElementById('pin').style.transform='scale('+(0.9+0.1*back(cl(t/0.35)))+')';
  // 5W cards: with the sentence they belong to (not during the hook)
  D.sents.forEach((s,i)=>{{
    if(!s.card)return; const c=document.getElementById('c'+i);
    const a=Math.max(s.a+0.15,D.hook_end+0.1), b=s.b+0.25;
    const p=back(cl((t-a)/0.4)), out=cl((t-(b-0.2))/0.2);
    c.style.opacity=(t>=a&&t<b&&t<D.end_t)?cl(p*1.5)*(1-out):0;
    c.style.transform='translateX('+((1-Math.min(1,p))*-260)+'px)';
  }});
  // full-details summary: during the last news sentence, rows appear one by one
  const sm=document.getElementById('sum');
  if(sm){{const u=ease(cl((t-D.sum_a)/0.4)); sm.style.opacity=(t>=D.sum_a&&t<D.end_t)?u:0; sm.style.transform='translateY('+(40*(1-u))+'px)';
    for(let i=0;i<D.rows;i++){{const r=document.getElementById('r'+i), a=D.sum_a+0.25+i*0.28; r.style.opacity=cl((t-a)/0.25); r.style.transform='translateX('+(-40*(1-ease(cl((t-a)/0.3))))+'px)';}}
    if(t>=D.sum_a)document.querySelectorAll('.card').forEach(c=>c.style.opacity=0);}}
  // captions
  D.caps.forEach((g,gi)=>{{
    const ge=document.getElementById('g'+gi), on=(t>=g.a&&t<g.b)&&t<D.end_t;
    ge.style.opacity=on?cl((t-g.a)/0.08):0;
    if(on){{const u=ease(cl((t-g.a)/0.2)); ge.style.transform='translateY('+(22*(1-u))+'px)';
      g.w.forEach((w,k)=>{{const sp=document.getElementById('w'+gi+'_'+k),act=(t>=w[0]&&t<w[1]);sp.className=act?'on':'';
        sp.style.transform=act?'scale(1.04)':'none';}});}}
  }});
  const e=document.getElementById('end'); e.style.opacity=ease(cl((t-D.end_t)/0.3));
  e.style.transform='scale('+(0.94+0.06*ease(cl((t-D.end_t)/0.4)))+')';
}};
function fitEl(el,maxH,min){{let fs=parseFloat(getComputedStyle(el).fontSize),n=0;while((el.scrollWidth>el.clientWidth+1||el.offsetHeight>maxH)&&fs>min&&n++<60){{fs-=2;el.style.fontSize=fs+'px';}}}}
window.fitAll=function(){{
  document.querySelectorAll('.ph').forEach(e=>fitEl(e,200,58));
  document.querySelectorAll('.card .vl').forEach(e=>fitEl(e,200,34));
  fitEl(document.querySelector('#hook .h1'),360,56); fitEl(document.querySelector('#hook .h2'),210,48);
  fitEl(document.getElementById('mini'),124,30); document.querySelectorAll('#sum .v').forEach(e=>fitEl(e,104,26)); document.querySelectorAll('#sum .l').forEach(e=>fitEl(e,76,20)); fitEl(document.querySelector('#pin span'),70,28);
}};
</script></body></html>"""


def main(spec_path, out_mp4, page_key="namakkal"):
    R.PAGE = R.PAGES[page_key]; R.LOGO = R.KIT / R.PAGE["logo"]
    if page_key == "rasipuram":
        V3.OUTRO_EN = "Follow Rasipuram Three Sixty for more local news."
    spec = json.loads(Path(spec_path).read_text())
    work = Path(out_mp4).with_suffix("")
    work = work.parent / (work.name + "_work"); work.mkdir(parents=True, exist_ok=True)
    sents, outro = spec["sentences"], spec["outro"]
    texts = [s["say"] for s in sents] + [outro["say"]]
    gap, lead = 0.16, 0.08
    if os.environ.get("REUSE_VOICE") == "1" and all((work / f"line{i}.wav").exists() for i in range(len(texts))):
        print("voice of an earlier render reused (design comparison: same story, same voice)")
    else:
        if os.environ.get("PREVIEW_TTS") == "edge":
            edge_lines(work, texts)
        else:
            (work / "lines.json").write_text(json.dumps(texts, ensure_ascii=False))
            subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "tts.py"), str(work / "lines.json"), str(work), spec.get("voice", "female")], check=True)
        V3.english_outro(work, len(texts) - 1)
    starts, ends, t = [], [], lead
    for i in range(len(texts)):
        d = V3.wav_dur(work / f"line{i}.wav")
        starts.append(round(t, 3)); ends.append(round(t + d, 3)); t += d + (V3.PAUSE if i == len(texts) - 2 else gap)
    V3.CHIME_T = round(ends[-2] + 0.12, 3)
    end_t = V3.CHIME_T
    total = round(max(ends[-1] + 0.6, end_t + 1.8), 3)
    R.make_voice_track(work, texts, starts, total)
    for i, s in enumerate(sents):
        s["a"], s["b"] = starts[i], ends[i]
    caps = []
    for i, s in enumerate(sents):
        wt = V3.word_times(to_digits(s["say"]), starts[i], ends[i])
        for g in phrases(wt):
            caps.append({"a": g[0][1], "b": g[-1][2], "words": g})
    snaps = [w[1] for g in caps for w in g["words"]]
    shots = V3.plan_shots(len(spec["images"]), end_t, snaps)
    hook_end = min(2.6, ends[0])
    V3.build_audio(work, starts, shots, [dict(s, fact="") for s in sents], total)
    page = work / "reel4.html"
    page.write_text(build_html(spec, shots, sents, caps, hook_end, end_t, total, R.PAGE))
    nframes = int(math.ceil(total * FPS))
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                            "-i", str(work / "mix.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out_mp4)], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto(page.resolve().as_uri())
        pg.wait_for_function("document.fonts.status==='loaded'")
        pg.evaluate("document.fonts.ready")
        pg.evaluate("fitAll()")
        for f in range(nframes):
            pg.evaluate(f"renderAt({f / FPS})")
            enc.stdin.write(pg.screenshot(type="jpeg", quality=95))
            if f % 150 == 0:
                print(f"frame {f}/{nframes}", flush=True)
        pg.evaluate("renderAt(0.9)")
        pg.evaluate("document.getElementById('cap').style.display='none';document.getElementById('segs').style.display='none';document.getElementById('hook').style.opacity=1;")
        pg.screenshot(path=str(Path(out_mp4).with_name(Path(out_mp4).stem + "_cover.jpg")), type="jpeg", quality=95)
        b.close()
    enc.stdin.close(); enc.wait()
    print(f"done {out_mp4} {total:.1f}s")


if __name__ == "__main__":
    main(*sys.argv[1:])
