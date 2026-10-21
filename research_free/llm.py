"""Free-model chain. HARD RULE: only free models are ever called.
 - Google Gemini (AI Studio key, free tier)         GEMINI_API_KEY
 - Groq (free tier)                                  GROQ_API_KEY      (optional)
 - OpenRouter, ONLY models whose id ends in ':free' and whose listed price is 0     OPENROUTER_API_KEY
Every call goes through ask_json(); a model is tried in order, the next one is used when a limit/error is hit.
"""
import json, os, re, time
import requests

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]
GROQ_MODELS = ["llama-3.3-70b-versatile"]
OR_PREFER = ["gemma", "llama-3.3", "qwen", "deepseek", "mistral", "gpt-oss"]
LOG = []


def _log(msg):
    LOG.append(msg)
    print(msg, flush=True)


def _json_from(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            return json.loads(m.group(0))
        raise


def _gemini(model, system, user, key):
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"role": "user", "parts": [{"text": user}]}],
              "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}}, timeout=100)
    if r.status_code != 200:
        raise RuntimeError(f"gemini {model} {r.status_code}: {r.text[:200]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq(model, system, user, key):
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.3, "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=100)
    if r.status_code != 200:
        raise RuntimeError(f"groq {model} {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]


NVIDIA_MODELS = ["meta/llama-3.3-70b-instruct", "qwen/qwen2.5-72b-instruct", "meta/llama-3.1-70b-instruct"]


def _nvidia(model, system, user, key):
    """NVIDIA NIM hosted API (build.nvidia.com): free developer credits/rate-limited tier, no card."""
    r = requests.post("https://integrate.api.nvidia.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.3, "max_tokens": 4096,
                            "messages": [{"role": "system", "content": system + "\nReturn ONLY the JSON object."},
                                         {"role": "user", "content": user}]}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"nvidia {model} {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]


_or_free = None


def openrouter_free_models(key):
    """free models only: id ends in ':free' AND prompt/completion price is 0"""
    global _or_free
    if _or_free is None:
        r = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=60)
        r.raise_for_status()
        out = []
        for m in r.json().get("data", []):
            pr = m.get("pricing", {})
            if m["id"].endswith(":free") and float(pr.get("prompt", 1)) == 0 and float(pr.get("completion", 1)) == 0:
                out.append(m["id"])
        out.sort(key=lambda i: min([k for k, p in enumerate(OR_PREFER) if p in i] or [99]))
        _or_free = out
    return _or_free


def _openrouter(model, system, user, key):
    assert model.endswith(":free"), "refusing to call a non-free OpenRouter model"
    r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.3, "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"openrouter {model} {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]


def gemini_models(key):
    """ask the API which flash models exist for this key (names change often); newest first, lite last"""
    try:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers={"x-goog-api-key": key}, timeout=60)
        r.raise_for_status()
        names = [m["name"].split("/")[-1] for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        fl = [n for n in names if "flash" in n and not any(x in n for x in ("image", "tts", "live", "audio", "preview-", "exp", "thinking", "embedding", "robotics", "computer"))]
        def ver(n):
            m = re.search(r"(\d+(?:\.\d+)?)", n)
            return float(m.group(1)) if m else 0
        fl.sort(key=lambda n: ("lite" in n, -ver(n)))
        _log("gemini models: " + ", ".join(fl[:6]))
        return fl[:3] or GEMINI_MODELS
    except Exception as e:
        _log(f"gemini model list failed: {e}")
        return GEMINI_MODELS


def chain():
    out = []
    g, q, o = os.environ.get("GEMINI_API_KEY"), os.environ.get("GROQ_API_KEY"), os.environ.get("OPENROUTER_API_KEY")
    if g:
        out += [("gemini", m, _gemini, g) for m in gemini_models(g)]
    if q:
        out += [("groq", m, _groq, q) for m in GROQ_MODELS]
    n = os.environ.get("NVIDIA_API_KEY")
    if n:
        out += [("nvidia", m, _nvidia, n) for m in NVIDIA_MODELS]
    if o:
        try:
            out += [("openrouter", m, _openrouter, o) for m in openrouter_free_models(o)[:4]]
        except Exception as e:
            _log(f"openrouter model list failed: {e}")
    return out


def ask_json(system, user, tries_per_model=1):
    """returns (data, model_name). Falls through the free models until one returns valid JSON."""
    last = None
    for provider, model, fn, key in chain():
        for _ in range(tries_per_model):
            try:
                text = fn(model, system, user, key)
                data = _json_from(text)
                _log(f"ok {provider}/{model}")
                return data, f"{provider}/{model}"
            except Exception as e:
                last = e
                _log(f"fail {provider}/{model}: {str(e)[:160]}")
                time.sleep(2)
    raise RuntimeError(f"no free model answered: {last}")
