"""Free AI image generation through the NVIDIA NIM API (build.nvidia.com) - realistic 9:16 news photos.
generate(prompt, seed) -> PNG/JPEG bytes, or raises. Tries the models in order (best first); a model that answers 401/403/404
(not in the free plan) is skipped for the rest of the run, 402/429 (credits / rate limit) switches to the next model."""
import base64, os, sys, time, requests

GEN = "https://ai.api.nvidia.com/v1/genai/"
# (model path, request body builder). FLUX only accepts sizes that are multiples of 64 inside 768..1344 -> 768x1344 is 9:16.
MODELS = [
    ("black-forest-labs/flux.1-dev", lambda p, s: {"prompt": p, "mode": "base", "cfg_scale": 3.5, "width": 768, "height": 1344, "seed": s, "steps": 40}),
    ("black-forest-labs/flux.1-schnell", lambda p, s: {"prompt": p, "width": 768, "height": 1344, "seed": s, "steps": 4}),
    ("bytedance/stable-diffusion-xl-lightning", lambda p, s: {"prompt": p, "width": 768, "height": 1344, "seed": s, "steps": 4}),
    ("stabilityai/stable-diffusion-3-medium", lambda p, s: {"prompt": p, "aspect_ratio": "9:16", "seed": s, "steps": 40, "cfg_scale": 5, "negative_prompt": "text, letters, watermark, logo, collage, blurry"}),
]
DEAD = set()
USED = {}


def _one(model, body, key):
    r = requests.post(GEN + model, json=body, timeout=100,
                      headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"{model} {r.status_code}: {r.text[:300]}")
    j = r.json()
    art = (j.get("artifacts") or [{}])[0]
    b64 = art.get("base64") or j.get("image")
    if not b64 or art.get("finishReason") not in (None, "SUCCESS"):
        raise RuntimeError(f"{model} no image ({art.get('finishReason')}): {str(j)[:200]}")
    return base64.b64decode(b64)


CF = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/@cf/"
CF_MODELS = [
    ("black-forest-labs/flux-1-schnell", lambda p, s: {"prompt": p, "steps": 8}),
]


def _cf(model, body, token, acct):
    r = requests.post(CF.format(acct) + model, json=body, timeout=100, headers={"Authorization": "Bearer " + token})
    if r.status_code != 200:
        raise RuntimeError(f"cloudflare {model} {r.status_code}: {r.text[:300]}")
    if r.headers.get("content-type", "").startswith("image/"):
        return r.content
    j = r.json()
    b64 = (j.get("result") or {}).get("image")
    if not b64:
        raise RuntimeError(f"cloudflare {model} no image: {str(j)[:200]}")
    return base64.b64decode(b64)


def to_story_size(data):
    """FLUX answers a 1024x1024 square: cut the centre 9:16 column and enlarge it to 1152x2048 (the poster crops/enhances again later)"""
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(data)).convert("RGB")
    w, h = im.size
    if w / h > 0.5625:
        nw = round(h * 9 / 16)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    im = im.resize((1152, 2048), Image.LANCZOS)
    out = BytesIO()
    im.save(out, "JPEG", quality=95, subsampling=0)
    return out.getvalue()


def generate(prompt, seed=0, key=None):
    return to_story_size(_generate(prompt, seed, key))


def _generate(prompt, seed=0, key=None):
    """Cloudflare Workers AI first (free daily allowance), NVIDIA second."""
    tok, acct = os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    last = None
    if tok and acct:
        for model, build in CF_MODELS:
            if model in DEAD:
                continue
            try:
                img = _cf(model, build(prompt, seed), tok, acct)
                USED[model] = USED.get(model, 0) + 1
                return img
            except Exception as e:
                last = e
                m = str(e)
                print("imagegen:", m[:220], file=sys.stderr)
                if any(c in m for c in (" 401", " 403", " 404", " 400", " 422", "no image")) or "Timeout" in type(e).__name__:
                    DEAD.add(model)
    try:
        return generate_nvidia(prompt, seed, key)
    except Exception as e:
        raise RuntimeError(f"all image models failed: {last or ''} | {e}")


def generate_nvidia(prompt, seed=0, key=None):
    key = key or os.environ.get("NVIDIA_API_KEY")
    if not key:
        raise RuntimeError("NVIDIA_API_KEY missing")
    last = None
    for model, build in MODELS:
        if model in DEAD:
            continue
        for k in range(2):
            try:
                img = _one(model, build(prompt, seed + k), key)
                USED[model] = USED.get(model, 0) + 1
                return img
            except Exception as e:
                last = e
                m = str(e)
                if "Timeout" in type(e).__name__ or "timed out" in m:
                    m += " 504 timeout"
                print("imagegen:", m[:220], file=sys.stderr)
                if any(c in m for c in (" 401", " 403", " 404", " 422", " 504")):
                    DEAD.add(model)
                    break
                if any(c in m for c in (" 402", " 429")):
                    time.sleep(8) if " 429" in m and k == 0 else None
                    if k == 1 or " 402" in m:
                        break
                time.sleep(3)
    raise RuntimeError(f"all image models failed: {last}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "test.jpg"
    data = generate(sys.argv[2] if len(sys.argv) > 2 else "Photorealistic news photo, tall vertical, a rural road in Namakkal, Tamil Nadu at dawn, police jeep parked, mist, sharp detail")
    open(out, "wb").write(data)
    print("saved", out, len(data), "bytes", USED)
