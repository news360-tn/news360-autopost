"""Makes one sample file per available Tamil voice, same news text, so people can compare. Output: samples/voices/*.mp3"""
import asyncio, json, os, subprocess, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples" / "voices"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "reel"))

TEXT = ("ராசிபுரம் அருகே கார் மோதியதில், மொபட்டில் சென்ற விவசாயி கோவிந்தராஜன் உயிரிழந்தார். "
        "சாய்பவன் ஓட்டல் அருகில் நடந்த இந்த விபத்தில், சபரிமலை சென்று திரும்பிய ஆறு பேர் காரில் இருந்தனர். "
        "மற்றொரு விபத்தில், அடையாளம் தெரியாத கார் மோதியதில் மூதாட்டி ஒருவர் படுகாயம் அடைந்தார். "
        "நிற்காமல் சென்ற காரை, பேளுக்குறிச்சி போலீசார் தேடி வருகின்றனர். "
        "மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.")
report = []


def mp3(src, name):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "24000", "-b:a", "64k", str(OUT / name)], check=True)


def guard(label, fn):
    try:
        fn(); report.append(f"ok   {label}")
    except Exception as e:
        report.append(f"FAIL {label}: {str(e)[:150]}"); traceback.print_exc()


EDGE = [("ta-IN-PallaviNeural", "பெண் (இந்தியா)"), ("ta-IN-ValluvarNeural", "ஆண் (இந்தியா)"), ("ta-LK-SaranyaNeural", "பெண் (இலங்கை)"),
        ("ta-LK-KumarNeural", "ஆண் (இலங்கை)"), ("ta-MY-KaniNeural", "பெண் (மலேசியா)"), ("ta-MY-SuryaNeural", "ஆண் (மலேசியா)"),
        ("ta-SG-VenbaNeural", "பெண் (சிங்கப்பூர்)"), ("ta-SG-AnbuNeural", "ஆண் (சிங்கப்பூர்)")]


def edge(v):
    import edge_tts
    async def go():
        await edge_tts.Communicate(TEXT, v, rate="+5%").save(str(OUT / f"edge_{v}.mp3"))
    asyncio.run(go())


for v, _ in EDGE:
    guard("edge-tts " + v, lambda v=v: edge(v))


def gtts():
    from gtts import gTTS
    gTTS(TEXT, lang="ta").save(str(OUT / "google_gtts.mp3"))
guard("Google gTTS", gtts)


def mms():
    import torch, scipy.io.wavfile as w
    from transformers import VitsModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained("facebook/mms-tts-tam"); m = VitsModel.from_pretrained("facebook/mms-tts-tam")
    with torch.no_grad():
        y = m(**tok(TEXT, return_tensors="pt")).waveform[0].numpy()
    w.write("/tmp/mms.wav", m.config.sampling_rate, y); mp3("/tmp/mms.wav", "meta_mms.mp3")
guard("Meta MMS", mms)


def indic(g):
    import tts
    Path("/tmp/l.json").write_text(json.dumps([TEXT], ensure_ascii=False))
    tts.main("/tmp/l.json", f"/tmp/ind_{g}", g)
    mp3(f"/tmp/ind_{g}/line0.wav", f"indic_tts_{g}_CURRENT.mp3")
for g in ("female", "male"):
    guard("AI4Bharat Indic-TTS " + g, lambda g=g: indic(g))

(OUT / "report.txt").write_text("\n".join(report), encoding="utf-8")
print("\n".join(report))
