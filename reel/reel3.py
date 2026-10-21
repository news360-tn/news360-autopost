"""நாமக்கல் 360 — MODERN reel v3 (hook in frame 1, multi-angle cuts across the story's photos, word-by-word captions).
Usage: python3 reel3.py spec.json out.mp4 [page]
spec: {"date","cat","location","hook":[line1,line2],"images":[paths],"voice":"female",
       "sentences":[{"say":"...","fact":"short on-screen fact or ''"}], "outro":{"say":"..."}}
No intro, no ticker, no AI label. One story per reel. The photos are never stretched: zoom is capped at 1.45.
"""
import json, sys, os, re, subprocess, html, wave, math
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reel as R  # fonts, icons, page branding, voice helpers

E = html.escape
W, H, FPS = 1080, 1920, 30
CUT = 1.9           # seconds per camera angle
MAX_ZOOM = 1.45

CSS = R.ff("CT", "catamaran", [700, 800, 900]) + R.ff("NST", "noto-sans-tamil", [600, 700, 800]) + R.ff("BT", "baloo-thambi-2", [800]) + """
:root{--red:#E3151B;--navy:#06132F;--yellow:#FFCC1F}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
body{font-family:'NST','CT',sans-serif;color:#fff;position:relative}
.ic{width:1em;height:1em;display:block}
#stage{position:absolute;inset:0;overflow:hidden}
.pic{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover;opacity:0;will-change:transform,filter}
#shade{position:absolute;inset:0;z-index:5;background:linear-gradient(180deg,rgba(4,10,28,.78) 0%,rgba(4,10,28,.05) 22%,rgba(4,10,28,0) 52%,rgba(4,10,28,.55) 74%,rgba(4,10,28,.9) 100%)}
#vig{position:absolute;inset:0;z-index:6;background:radial-gradient(ellipse at 50% 45%,transparent 55%,rgba(0,0,0,.45) 100%)}
#flash{position:absolute;inset:0;z-index:7;background:#fff;opacity:0}
#prog{position:absolute;left:0;top:0;height:9px;width:0;z-index:30}
#brand{position:absolute;left:44px;top:56px;z-index:30;display:flex;flex-direction:column;gap:10px}
#brand .row1{display:flex;align-items:stretch;gap:14px}
#brand .bar{width:9px;border-radius:5px}
#brand .nm{font:800 46px/1.1 'BT','NST';text-shadow:0 3px 0 rgba(0,0,0,.6),0 6px 18px rgba(0,0,0,.5)}
#brand .pill{align-self:flex-start;font:800 30px 'NST','CT';padding:6px 20px 0;border-radius:10px;color:#fff;box-shadow:0 6px 18px rgba(0,0,0,.4)}
#brand .dt{display:flex;align-items:center;gap:10px;font:700 30px 'NST','CT';text-shadow:0 2px 8px rgba(0,0,0,.8)}
#brand .dt .ic{font-size:26px;color:var(--yellow)}
#logo{position:absolute;right:44px;top:50px;width:124px;height:124px;border-radius:50%;z-index:30;box-shadow:0 6px 22px rgba(0,0,0,.5)}
#hook{position:absolute;left:50px;right:50px;top:380px;z-index:20;text-align:center;opacity:0}
#hook .h1{font:900 96px/1.12 'CT','NST';color:#fff}
#hook .h2{font:900 108px/1.12 'CT','NST';color:var(--yellow);margin-top:6px}
#hook div{-webkit-text-stroke:14px #000;paint-order:stroke fill;text-shadow:0 10px 30px rgba(0,0,0,.5)}
.sticker{position:absolute;left:0;top:360px;max-width:940px;z-index:22;background:var(--yellow);color:var(--navy);font:800 46px/1.3 'NST','CT';padding:16px 34px 10px 30px;border-radius:0 24px 24px 0;box-shadow:0 10px 30px rgba(0,0,0,.45);opacity:0}
.sticker b{color:#C4100F}
#cap{position:absolute;left:40px;right:40px;top:1150px;height:190px;z-index:25;display:flex;align-items:center;justify-content:center;text-align:center}
.ph{position:absolute;left:0;right:0;font:800 78px/1.25 'CT','NST';color:#fff;opacity:0;-webkit-text-stroke:12px #000;paint-order:stroke fill;text-shadow:0 8px 24px rgba(0,0,0,.6)}
.ph span.on{color:var(--yellow)}
#end{position:absolute;inset:0;z-index:40;opacity:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:30px;text-align:center;background:rgba(4,10,28,.55)}
#end img{width:330px;height:330px;border-radius:50%;box-shadow:0 14px 50px rgba(0,0,0,.6)}
#end .e1{font:900 76px/1.25 'CT','NST'}
#end .e2{background:var(--red);font:900 56px 'CT','NST';padding:16px 46px 8px;border-radius:999px}
#end .e3{font:800 50px 'CT','NST';color:var(--yellow)}
"""

ACCENT = {"மின் தடை": "#F5A100", "மழை": "#1E88E5", "வானிலை": "#1E88E5"}

def accent_for(cat):
    for k, v in ACCENT.items():
        if k in cat:
            return v
    return "#E3151B"


def wav_dur(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def word_times(text, s, e):
    """spread a sentence's duration over its words by letter count (no word clock from the voice model)."""
    words = text.split()
    wts = [max(2, len(w)) for w in words]
    tot = sum(wts)
    out, t = [], s
    for w, k in zip(words, wts):
        d = (e - s) * k / tot
        out.append((w, round(t, 3), round(t + d, 3)))
        t += d
    return out


def phrases(words, n=3):
    """groups of up to 3 words, breaking after a comma/full stop"""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= n or re.search(r"[,.!?।]$", w[0]):
            out.append(cur); cur = []
    if cur:
        if out and len(cur) == 1:
            out[-1] += cur
        else:
            out.append(cur)
    return out


def plan_shots(n_img, content_end, snaps):
    """camera angles: a cut about every CUT s, snapped to a word start; images spread evenly over the story."""
    n = max(2, int(round(content_end / CUT)))
    cuts = [0.0]
    for i in range(1, n):
        t = content_end * i / n
        near = min(snaps, key=lambda x: abs(x - t)) if snaps else t
        cuts.append(near if abs(near - t) < 0.55 and near > cuts[-1] + 0.9 else t)
    cuts.append(content_end + 5)
    # angle presets: (zoom start, zoom end, focus x, focus y, pan px x, pan px y)
    angles = [(1.30, 1.40, .50, .36, 0, -20),   # tight on the subject (upper centre)
              (1.12, 1.22, .50, .50, 0, 0),     # medium
              (1.04, 1.12, .50, .55, 0, 0),     # wide push-in
              (1.22, 1.32, .30, .45, 30, 0),    # left pan
              (1.22, 1.32, .70, .45, -30, 0)]   # right pan
    shots = []
    for i in range(len(cuts) - 1):
        img = min(n_img - 1, int(i * n_img / (len(cuts) - 1)))
        z0, z1, fx, fy, px, py = angles[(i + (0 if i == 0 else 1)) % len(angles)] if i else angles[0]
        shots.append({"a": round(cuts[i], 3), "b": round(cuts[i + 1], 3), "img": img,
                      "z0": min(z0, MAX_ZOOM), "z1": min(z1, MAX_ZOOM), "fx": fx, "fy": fy, "px": px, "py": py})
    return shots


def build_html(spec, shots, sents, caps, hook_end, end_t, total, page):
    logo = f"file://{R.KIT.resolve() / page['logo']}"
    imgs = "".join(f'<img class="pic" id="p{i}" src="file://{Path(p).resolve()}">' for i, p in enumerate(spec["images"]))
    acc = accent_for(spec.get("cat", ""))
    stick = "".join(f'<div class="sticker" id="k{i}">{s["fact"]}</div>' for i, s in enumerate(sents) if s.get("fact"))
    cap_html = ""
    for gi, g in enumerate(caps):
        spans = "".join(f'<span id="w{gi}_{k}">{E(w[0])}</span> ' for k, w in enumerate(g["words"]))
        cap_html += f'<div class="ph" id="g{gi}">{spans}</div>'
    hook = spec.get("hook") or ["", ""]
    data = json.dumps({"shots": shots, "sents": [{"a": s["a"], "b": s["b"], "fact": bool(s.get("fact"))} for s in sents],
                       "caps": [{"a": g["a"], "b": g["b"], "w": [[x[1], x[2]] for x in g["words"]]} for g in caps],
                       "hook_end": hook_end, "end_t": end_t, "total": total, "n": len(spec["images"])})
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div id="stage">{imgs}</div><div id="shade"></div><div id="vig"></div><div id="flash"></div>
<div id="prog" style="background:{acc}"></div>
<div id="brand"><div class="row1"><div class="bar" style="background:{acc}"></div><div class="nm">{page['name']}</div></div>
<div class="pill" style="background:{acc}">{E(spec.get('cat',''))}</div>
<div class="dt">{R.icon('calendar-days')}{E(spec['date'])}</div></div>
<img id="logo" src="{logo}">
<div id="hook"><div class="h1">{E(hook[0])}</div><div class="h2">{E(hook[1])}</div></div>
{stick}
<div id="cap">{cap_html}</div>
<div id="end"><img src="{logo}"><div class="e1">நம்ம நாமக்கல் செய்திகள்</div><div class="e2">FOLLOW @namakkal.360</div><div class="e3">{E(spec.get('location',''))}</div></div>
<script>
const D={data};
const cl=x=>Math.max(0,Math.min(1,x)), ease=x=>1-Math.pow(1-x,3), back=x=>{{const c=1.70158,c3=c+1;return 1+c3*Math.pow(x-1,3)+c*Math.pow(x-1,2)}};
window.renderAt=function(t){{
  let active=null;
  D.shots.forEach(s=>{{if(t>=s.a&&t<s.b)active=s}});
  if(!active)active=D.shots[D.shots.length-1];
  const blurEnd=t>=D.end_t?Math.min(1,(t-D.end_t)/0.3):0;
  for(let i=0;i<D.n;i++){{const el=document.getElementById('p'+i); el.style.opacity=(i===active.img)?1:0;}}
  const el=document.getElementById('p'+active.img);
  const dur=Math.max(0.5,active.b-active.a), pr=cl((t-active.a)/Math.min(dur,CUTMAX)), k=t-active.a;
  const z=active.z0+(active.z1-active.z0)*pr;
  const punch=1+0.05*Math.max(0,1-k/0.18);
  el.style.transformOrigin=(active.fx*100)+'% '+(active.fy*100)+'%';
  el.style.transform='translate('+(active.px*(pr-0.5))+'px,'+(active.py*(pr-0.5))+'px) scale('+(z*punch)+')';
  const wb=(k<0.14&&active.a>0)?(6*(1-k/0.14)):0;
  el.style.filter='blur('+(wb+blurEnd*22)+'px)';
  document.getElementById('flash').style.opacity=(active.a>0&&k<0.12)?0.16*(1-k/0.12):0;
  document.getElementById('prog').style.width=(100*cl(t/D.end_t))+'%';
  // hook: visible from frame 1
  const h=document.getElementById('hook');
  const hin=ease(cl(t/0.18)), hout=cl((t-(D.hook_end-0.3))/0.3);
  h.style.opacity=(t<D.hook_end)?hin*(1-hout):0;
  h.style.transform='scale('+(0.92+0.08*back(cl(t/0.35)))+')';
  // fact stickers
  let ki=0;
  D.sents.forEach((s,i)=>{{
    if(!s.fact)return;
    const st=document.getElementById('k'+i); if(!st)return;
    const a=s.a+0.1,b=s.b+0.15;
    const p=back(cl((t-a)/0.35)), out=cl((t-(b-0.2))/0.2);
    st.style.opacity=(t>=a&&t<b)?cl(p*2)*(1-out):0;
    st.style.transform='translateX('+((1-Math.min(1,p))*-900)+'px)';
  }});
  // captions
  D.caps.forEach((g,gi)=>{{
    const ge=document.getElementById('g'+gi);
    const on=(t>=g.a&&t<g.b)&&t<D.end_t;
    ge.style.opacity=on?1:0;
    if(on){{g.w.forEach((w,k)=>{{document.getElementById('w'+gi+'_'+k).className=(t>=w[0]&&t<w[1])?'on':''}});}}
  }});
  const e=document.getElementById('end');
  e.style.opacity=ease(cl((t-D.end_t)/0.3));
}};
const CUTMAX=2.4;
</script></body></html>"""


def main(spec_path, out_mp4, page_key="namakkal"):
    R.PAGE = R.PAGES[page_key]; R.LOGO = R.KIT / R.PAGE["logo"]
    spec = json.loads(Path(spec_path).read_text())
    work = Path(out_mp4).with_suffix("")
    work = work.parent / (work.name + "_work"); work.mkdir(parents=True, exist_ok=True)
    sents = spec["sentences"]
    outro = spec["outro"]
    texts = [s["say"] for s in sents] + [outro["say"]]
    gap, lead = 0.18, 0.08
    (work / "lines.json").write_text(json.dumps(texts, ensure_ascii=False))
    voice_file = os.environ.get("VOICE_FILE")
    if voice_file:
        raise SystemExit("VOICE_FILE not supported in reel3 yet")
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "tts.py"), str(work / "lines.json"), str(work), spec.get("voice", "female")], check=True)
    speech = sum(wav_dur(work / f"line{i}.wav") for i in range(len(texts)))
    room = 29.0 - lead - 0.5 - gap * (len(texts) - 1)
    if room > 0 and speech > room:
        factor = min(1.25, speech / room)
        for i in range(len(texts)):
            src, tmp = work / f"line{i}.wav", work / f"line{i}_fast.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", f"atempo={factor:.3f}", str(tmp)], check=True)
            tmp.replace(src)
        print(f"voice sped up x{factor:.2f} to fit 30 s")
    starts, ends, t = [], [], lead
    for i in range(len(texts)):
        d = wav_dur(work / f"line{i}.wav")
        starts.append(round(t, 3)); ends.append(round(t + d, 3)); t += d + gap
    end_t = starts[-1] - 0.05            # follow-us line is spoken over the ending card
    total = round(max(ends[-1] + 0.6, end_t + 1.6), 3)
    if total > 30.5:
        print(f"WARNING: reel is {total:.1f}s (>30s)")
    R.make_voice_track(work, texts, starts, total)
    for i, s in enumerate(sents):
        s["a"], s["b"] = starts[i], ends[i]
    # captions: words timed inside each sentence, phrases of up to 3 words
    caps = []
    for i, s in enumerate(sents):
        wt = word_times(s["say"], starts[i], ends[i])
        for g in phrases(wt):
            caps.append({"a": g[0][1], "b": g[-1][2] + 0.05, "words": g})
    snaps = [w[1] for g in caps for w in g["words"]]
    shots = plan_shots(len(spec["images"]), end_t, snaps)
    hook_end = min(2.7, ends[0])
    build_audio(work, starts, shots, sents, total)
    page = work / "reel3.html"
    page.write_text(build_html(spec, shots, sents, caps, hook_end, end_t, total, R.PAGE))
    nframes = int(math.ceil(total * FPS))
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                            "-i", str(work / "mix.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-profile:v", "high",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out_mp4)], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto(page.resolve().as_uri())
        pg.wait_for_function("document.fonts.status==='loaded'")
        pg.evaluate("document.fonts.ready")
        for f in range(nframes):
            pg.evaluate(f"renderAt({f / FPS})")
            enc.stdin.write(pg.screenshot(type="jpeg", quality=96))
            if f % 150 == 0:
                print(f"frame {f}/{nframes}", flush=True)
        b.close()
    enc.stdin.close(); enc.wait()
    print(f"done {out_mp4} {total:.1f}s")


def build_audio(work, starts, shots, sents, total):
    """voice + a soft whoosh on each camera cut + a pop on each fact sticker (no music; add Tamil music in the Instagram app)."""
    parts, labels = [], []
    k = 0
    for s in shots[1:]:
        if s["a"] < total - 1:
            parts.append(f"anoisesrc=d=0.4:c=pink:a=0.5,bandpass=f=1800:w=1500,afade=t=in:d=0.2,afade=t=out:st=0.2:d=0.2,adelay={int(max(0,s['a']-0.2)*1000)}|{int(max(0,s['a']-0.2)*1000)}[w{k}]")
            labels.append(f"[w{k}]"); k += 1
    n_cut = k
    for i, s in enumerate(sents):
        if s.get("fact"):
            d = int((s["a"] + 0.1) * 1000)
            parts.append(f"sine=f=880:d=0.12,afade=t=out:st=0.04:d=0.08,volume=0.5,adelay={d}|{d}[w{k}]")
            labels.append(f"[w{k}]"); k += 1
    if not labels:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / "voice.wav"), "-af", "volume=1.9,alimiter=limit=0.8:level=0",
                        "-ar", "44100", str(work / "mix.wav")], check=True)
        return
    fx = ";".join(parts) + ";" + "".join(labels) + f"amix=inputs={len(labels)}:normalize=0,volume=0.22,apad,atrim=0:{total}[o]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_complex", fx, "-map", "[o]", "-ar", "44100", str(work / "sfx.wav")], check=True)
    mixf = "[0:a]volume=1.9,acompressor=threshold=0.2:ratio=3[vo];[1:a]volume=1[sf];[vo][sf]amix=inputs=2:normalize=0,alimiter=limit=0.8:level=0[m]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / "voice.wav"), "-i", str(work / "sfx.wav"),
                    "-filter_complex", mixf, "-map", "[m]", "-ar", "44100", str(work / "mix.wav")], check=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
