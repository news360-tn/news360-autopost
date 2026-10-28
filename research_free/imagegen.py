"""Free AI image generation through the NVIDIA NIM API (build.nvidia.com) - realistic 9:16 news photos.
generate(prompt, seed) -> PNG/JPEG bytes, or raises. Tries the models in order (best first); a model that answers 401/403/404
(not in the free plan) is skipped for the rest of the run, 402/429 (credits / rate limit) switches to the next model."""
import base64, json, os, sys, time, requests

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


FAL_URL = "https://fal.run/"
# fal.ai (paid, cheap). FAL_MODEL can be switched without code changes, e.g. fal-ai/bytedance/seedream/v4/text-to-image
FAL_MODEL = os.environ.get("FAL_MODEL") or "fal-ai/flux/dev"   # owner 25 Oct: stronger model follows the news details better (Schnell is the cheap fallback)
# fal bills per megapixel rounded UP: 720x1280 = 0.92 MP -> billed as 1 MP (768x1344 = 1.03 MP would be billed as 2 MP)
FAL_W, FAL_H = 720, 1280
# owner 27 Oct (cost): the cover (scene 1, the picture people see first) stays FLUX dev ($0.025); scenes 2-3 of the same news use
# FLUX schnell ($0.003) - still drawn from the story's own scenes and checked against the headline. Dev is the backup if schnell fails.
FAL_SCENE_MODEL = os.environ.get("FAL_SCENE_MODEL") or "fal-ai/flux/schnell"


def _fal(prompt, seed, key, model=None):
    model = model or FAL_MODEL
    body = {"prompt": prompt, "image_size": {"width": FAL_W, "height": FAL_H}, "num_images": 1, "seed": seed,
            "enable_safety_checker": True}
    if "schnell" in model:
        body["num_inference_steps"] = 4
    r = requests.post(FAL_URL + model, json=body, timeout=120,
                      headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"fal {model} {r.status_code}: {r.text[:300]}")
    imgs = r.json().get("images") or []
    if not imgs or not imgs[0].get("url"):
        raise RuntimeError(f"fal {model} no image: {r.text[:200]}")
    d = requests.get(imgs[0]["url"], timeout=120)
    d.raise_for_status()
    return d.content


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


_VISION = []


def _vision_models(key):
    """flash models that exist for this key right now (same list as the writer), asked once per run"""
    if not _VISION:
        env = os.environ.get("GEMINI_VISION_MODEL")
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import llm
            found = llm.gemini_models(key)
        except Exception:
            found = []
        stable = [m for m in found if "preview" not in m]      # a stable, answering model first (3.6 / 3.5 answered on 28 Oct; 3.8 / 3.7 timed out)
        _VISION.extend(dict.fromkeys(([env] if env else []) + stable[2:] + stable[:2] + llm.GEMINI_MODELS))
    return list(_VISION)


def matches(data, headline):
    """a vision model checks that the picture shows the news headline. True when it matches or the check is not available."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not headline:
        return True
    try:
        body = {"contents": [{"parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(data).decode()}},
                    {"text": f'Does this photo show the news story: "{headline}"? Check the place type, the event, and the people. '
                             'Answer only JSON: {"match": true or false, "why": "short reason"}'}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
        j, last = None, None
        for model in _vision_models(key):      # 28 Oct: gemini-2.5-flash was retired (404) and every picture went out unchecked
            try:      # the newest models often time out or are busy (503): the next one answers
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                  headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body, timeout=30)
                if r.status_code == 404:
                    _VISION.remove(model)
                r.raise_for_status()
                j = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
                break
            except Exception as e:
                last = f"{model}: {e}"
        if j is None:
            raise RuntimeError(last or "no vision model")
        print("image match:", j.get("match"), str(j.get("why", ""))[:120], flush=True)
        return bool(j.get("match"))
    except Exception as e:
        print("image match check unavailable:", str(e)[:120], flush=True)
        return True


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


def generate(prompt, seed=0, key=None, cheap=False):
    """cheap=True: a scene after the cover - FLUX schnell first, FLUX dev only when schnell fails"""
    return to_story_size(_generate(prompt, seed, key, cheap))


def _generate(prompt, seed=0, key=None, cheap=False):
    """fal.ai first (paid, cheap), then Cloudflare Workers AI (free daily allowance), then NVIDIA."""
    tok, acct = os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    last = None
    fkey = os.environ.get("FAL_KEY")
    for fm in ([FAL_SCENE_MODEL, FAL_MODEL] if cheap and FAL_SCENE_MODEL != FAL_MODEL else [FAL_MODEL]):
        if not fkey or fm in DEAD:
            continue
        for k in range(2):
            try:
                img = _fal(prompt, seed + k, fkey, fm)
                USED[fm] = USED.get(fm, 0) + 1
                return img
            except Exception as e:
                last = e
                m = str(e)
                print("imagegen:", m[:220], file=sys.stderr)
                if any(c in m for c in (" 401", " 403", " 404", " 422")):
                    DEAD.add(fm)     # bad key / no balance / wrong model id: use the backups for the rest of this run
                    break
                time.sleep(3)
    if os.environ.get("NVIDIA_API_KEY"):      # owner 25 Oct: NVIDIA (free credits) before Cloudflare, whose daily allowance runs out early
        try:
            return generate_nvidia(prompt, seed, os.environ.get("NVIDIA_API_KEY"))
        except Exception as e:
            last = e
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
