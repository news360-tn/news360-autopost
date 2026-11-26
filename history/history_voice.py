"""owner 26 Nov: the history lane's OWN voice (not the news Chirp-3 Charon allowance, which stays for news).
Providers (history/config.json "voice"):  none (music + subtitles) | sarvam | edge | google
  synth(lines, provider, work)   -> [wav path per line]   (22.05 kHz mono)
  line_times(durations)          -> [(start, end)] for the reel
  python history/history_voice.py samples     the SAME Tamil narration in several voices -> samples/history_voices/ for the owner to listen to
Claude cannot hear audio, so the owner picks after listening. Keys come from the environment (SARVAM_API_KEY, GOOGLE_TTS_API_KEY);
a provider without its key is skipped. Never prints a key."""
import base64
import os
import subprocess
import sys
import wave
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lanes"))
import lane_common as common  # noqa: E402

SARVAM_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_SPEAKERS = ("anushka", "abhilash")       # candidates for the samples; the owner picks one
EDGE_VOICES = ("ta-IN-PallaviNeural", "ta-IN-ValluvarNeural")
GOOGLE_VOICES = ("ta-IN-Chirp3-HD-Aoede", "ta-IN-Chirp3-HD-Puck")      # NOT Charon (news); they still count on Google's free allowance


def to_wav(src, dst):
    subprocess.run([common.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm=I=-16:TP=-1.5",
                    "-ar", "22050", "-ac", "1", str(dst)], check=True)
    return dst


def wav_seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / float(w.getframerate())


def sarvam_say(text, speaker="anushka", key=None, post=requests.post):
    key = key or os.environ.get("SARVAM_API_KEY", "")
    if not key:
        raise RuntimeError("SARVAM_API_KEY not set")
    last = None
    for body in ({"text": text, "target_language_code": "ta-IN", "speaker": speaker, "model": "bulbul:v2", "speech_sample_rate": 22050},
                 {"inputs": [text], "target_language_code": "ta-IN", "speaker": speaker, "model": "bulbul:v2", "speech_sample_rate": 22050}):
        r = post(SARVAM_URL, json=body, headers={"api-subscription-key": key, "Content-Type": "application/json"}, timeout=90)
        if r.status_code == 200:
            audios = r.json().get("audios") or []
            if audios:
                return base64.b64decode(audios[0])
        last = f"sarvam {r.status_code}: {r.text[:160]}"
        if r.status_code in (401, 403):
            break
    raise RuntimeError(last)


def edge_say(text, voice, out_mp3):
    import asyncio
    import edge_tts

    async def go():
        await edge_tts.Communicate(text, voice, rate="-4%").save(str(out_mp3))
    asyncio.run(go())
    return out_mp3


def synth(lines, provider, work, voice=None, log=common.log):
    """-> [wav path per line]; [] for provider none. A failing provider raises (the caller falls back to subtitles-only music)."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    if provider in (None, "", "none"):
        return []
    wavs = []
    for i, ln in enumerate(lines):
        raw, wav = work / f"v{i}.bin", work / f"line{i}.wav"
        text = ln["text"]
        if provider == "sarvam":
            raw.write_bytes(sarvam_say(text, voice or SARVAM_SPEAKERS[0]))
        elif provider == "edge":
            edge_say(text, voice or EDGE_VOICES[0], raw)
        elif provider == "google":
            import reel4
            raw.write_bytes(reel4.google_say(text, voice or GOOGLE_VOICES[0], "ta-IN"))
        else:
            raise ValueError(f"unknown voice provider {provider}")
        wavs.append(to_wav(raw, wav))
    log(f"voice {provider}: {len(wavs)} lines")
    return wavs


def line_times(durations, lead=0.3, gap=0.55, min_s=3.0):
    """each line shows for its clip length (+ a small lead and gap, at least min_s); returns [(start, end)] and the clip start offsets"""
    out, t = [], 0.0
    for d in durations:
        end = t + max(min_s, d + lead + gap)
        out.append((t, end))
        t = end
    return out


def samples(text_lines, outdir, log=common.log):
    """the same narration in every voice we can reach -> mp3 files + a README for the owner"""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tried = []
    plan = [("sarvam", s) for s in SARVAM_SPEAKERS] + [("edge", v) for v in EDGE_VOICES] + [("google", v) for v in GOOGLE_VOICES]
    for prov, voice in plan:
        name = f"{prov}-{voice}"
        try:
            wavs = synth([{"text": t} for t in text_lines], prov, outdir / f"_{name}", voice=voice, log=log)
            lst = outdir / f"_{name}.txt"
            lst.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs), encoding="utf-8")
            subprocess.run([common.ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "libmp3lame", "-q:a", "3",
                            str(outdir / f"{name}.mp3")], check=True)
            tried.append((name, "ok"))
        except Exception as e:
            tried.append((name, "skipped: " + str(e)[:90]))
            log(f"{name}: skipped - {str(e)[:120]}")
    (outdir / "README.txt").write_text(
        "History voice samples: the same narration in each voice. Listen, then tell Claude which voice to lock for the lane.\n\n"
        + "\n".join(f"{n}: {s}" for n, s in tried) + "\n", encoding="utf-8")
    return tried


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "samples":
        sys.path.insert(0, str(HERE))
        import history_writer as hw
        topic = hw.pick_topic("namakkal", [], allow_unverified=True)
        lines, _ = hw.write(topic)
        for t, s in samples([l["text"] for l in lines], ROOT / "samples" / "history_voices"):
            print(t, s)
    else:
        print(__doc__)
