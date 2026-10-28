"""Free-model chain. HARD RULE: only free models are ever called.
 - Google Gemini (AI Studio key, free tier)         GEMINI_API_KEY
 - Groq (free tier)                                  GROQ_API_KEY      (optional)
 - OpenRouter, ONLY models whose id ends in ':free' and whose listed price is 0     OPENROUTER_API_KEY
Every call goes through ask_json(); a model is tried in order, the next one is used when a limit/error is hit.
"""
import json, os, re, time
import requests

GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash"]      # only used when the model list cannot be read (2.5 retired 28 Oct)
GROQ_MODELS = ["llama-3.3-70b-versatile"]
OR_PREFER = ["gemma", "llama-3.3", "qwen", "deepseek", "mistral", "gpt-oss"]
OR_BLOCK = ["flint", "recursive", "lite", "tiny", "mini", "1b", "3b", "7b", "8b"]   # weak models write broken Tamil
LOG = []


def _log(msg):
    LOG.append(msg)
    print(msg, flush=True)


def _json_from(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text, strict=False)
    except Exception:
        i = text.find("{")
        if i >= 0:
            try:
                return json.JSONDecoder(strict=False).raw_decode(text[i:])[0]
            except Exception:
                m = re.search(r"\{.*\}", text, flags=re.S)
                if m:
                    return json.loads(m.group(0), strict=False)
        raise


def _gemini(model, system, user, key):
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"role": "user", "parts": [{"text": user}]}],
              "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"gemini {model} {r.status_code}: {r.text[:700]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq(model, system, user, key):
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.3, "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"groq {model} {r.status_code}: {r.text[:700]}")
    return r.json()["choices"][0]["message"]["content"]


NVIDIA_MODELS = []     # every NIM model we tried now answers 404/410 (gone / not on this plan): skipped so rounds do not lose minutes on them


def _nvidia(model, system, user, key):
    """NVIDIA NIM hosted API (build.nvidia.com): free developer credits/rate-limited tier, no card."""
    r = requests.post("https://integrate.api.nvidia.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.3, "max_tokens": 4096,
                            "messages": [{"role": "system", "content": system + "\nReturn ONLY the JSON object."},
                                         {"role": "user", "content": user}]}, timeout=70)
    if r.status_code != 200:
        raise RuntimeError(f"nvidia {model} {r.status_code}: {r.text[:700]}")
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
        out = [i for i in out if any(p in i for p in OR_PREFER) and not any(b in i for b in OR_BLOCK)]   # only known-good families
        out.sort(key=lambda i: min([k for k, p in enumerate(OR_PREFER) if p in i] or [99]))
        _or_free = out
    return _or_free


def _openrouter(model, system, user, key):
    assert model.endswith(":free"), "refusing to call a non-free OpenRouter model"
    r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.3, "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=70)
    if r.status_code != 200:
        raise RuntimeError(f"openrouter {model} {r.status_code}: {r.text[:700]}")
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


def groq_models(key):
    try:
        r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=40)
        r.raise_for_status()
        ids = [m["id"] for m in r.json().get("data", []) if not any(x in m["id"] for x in ("whisper", "guard", "tts", "orpheus", "playai", "embed", "distil"))]
        ids.sort(key=lambda i: min([k for k, p in enumerate(("llama-3.3", "llama-4", "gpt-oss-120b", "qwen", "kimi", "llama")) if p in i] or [99]))
        _log("groq models: " + ", ".join(ids[:5]))
        return ids[:2] or GROQ_MODELS
    except Exception as e:
        _log(f"groq model list failed: {e}")
        return GROQ_MODELS


PREFERRED = [None]
SLOW_SECS = int(os.environ.get('LLM_SLOW_SECS', '90'))   # a free model slower than this is skipped for 30 min
DEAD = {}   # (provider, model) -> time until which it is skipped
DEADLINE = [None]   # unix time after which no more model calls are made


MISTRAL_MODELS = ["mistral-small-latest"]   # open-mistral-nemo removed: 9 of 9 stories it wrote on 23 Oct had 1-7 format/number errors


_LAST_MISTRAL = [0.0]


def _mistral(model, system, user, key):
    time.sleep(max(0.0, 1.6 - (time.time() - _LAST_MISTRAL[0])))     # the free tier allows about one request per second
    _LAST_MISTRAL[0] = time.time()
    r = requests.post("https://api.mistral.ai/v1/chat/completions", headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.3, "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"mistral {model} {r.status_code}: {r.text[:700]}")
    return r.json()["choices"][0]["message"]["content"]


GHM_MODELS = []   # removed: every model returned a non-JSON reply on every run (owner request 24 Oct)


def _ghmodels(model, system, user, key):
    r = requests.post("https://models.github.ai/inference/chat/completions",
                      headers={"Authorization": f"Bearer {key}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
                      json={"model": model, "temperature": 0.3, "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"ghmodels {model} {r.status_code}: {r.text[:700]}")
    return r.json()["choices"][0]["message"]["content"]


CF_MODELS = ["@cf/meta/llama-3.3-70b-instruct-fp8-fast", "@cf/mistralai/mistral-small-3.1-24b-instruct"]


def _cloudflare(model, system, user, key):
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0.3, "response_format": {"type": "json_object"}, "max_tokens": 4096,
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"cloudflare {model} {r.status_code}: {r.text[:700]}")
    return r.json()["choices"][0]["message"]["content"]


def chain():
    out = []
    g, q, o = os.environ.get("GEMINI_API_KEY"), os.environ.get("GROQ_API_KEY"), os.environ.get("OPENROUTER_API_KEY")
    if g:
        out += [("gemini", m, _gemini, g) for m in gemini_models(g)]
    n = os.environ.get("NVIDIA_API_KEY")
    if n:
        out += [("nvidia", m, _nvidia, n) for m in NVIDIA_MODELS]
    gk = os.environ.get("GH_MODELS_TOKEN")
    if gk:
        out += [("ghmodels", m, _ghmodels, gk) for m in GHM_MODELS]
    if q:
        out += [("groq", m, _groq, q) for m in groq_models(q)]
    ck = os.environ.get("CLOUDFLARE_API_TOKEN")
    if ck and os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        out += [("cloudflare", m, _cloudflare, ck) for m in CF_MODELS]
    mk = os.environ.get("MISTRAL_API_KEY")
    if mk:  # small Mistral models are the weakest (break the format rules) -> tried last
        out += [("mistral", m, _mistral, mk) for m in MISTRAL_MODELS]
    if o and os.environ.get("OPENROUTER_ENABLE") == "1":   # removed from the chain (quota 429 on every run, owner request 24 Oct); set OPENROUTER_ENABLE=1 to use again
        try:
            out += [("openrouter", m, _openrouter, o) for m in openrouter_free_models(o)[:8]]
        except Exception as e:
            _log(f"openrouter model list failed: {e}")
    return out


CLAUDE_FIRST = os.environ.get("CLAUDE_FIRST", "0") == "1"      # 0 (default) = free models first; Claude only when free models fail, are slow, or hit the limit. 1 = Claude for everything
FREE_FAILS = [0]                                              # failures of free models in a row (slow, poor or refused answers)
FREE_FAIL_LIMIT = int(os.environ.get("LLM_FREE_FAIL_LIMIT", "3"))


def ask_json(system, user, tries_per_model=1):
    """returns (data, model_name). Starts with the model that worked last time; retries a busy (503/429) model once after a pause.
    Owner rule: when the free models have failed FREE_FAIL_LIMIT times in a row, this raises at once, so the caller uses Claude (paid) straight away."""
    if CLAUDE_FIRST and claude_available():      # owner decision 24 Oct: Claude (paid) for every writing/check call for one month, free models not used
        raise RuntimeError("Claude first (owner setting): using Claude")
    if FREE_FAILS[0] >= FREE_FAIL_LIMIT and claude_available():
        raise RuntimeError(f"free models not efficient ({FREE_FAILS[0]} failures in a row): using Claude")
    last = None
    ch = chain()
    if PREFERRED[0]:
        ch.sort(key=lambda c: 0 if (c[0], c[1]) == PREFERRED[0] else 1)
    for provider, model, fn, key in ch:
        if DEAD.get((provider, model), 0) > time.time():
            continue
        for k in range(3):
            if DEADLINE[0] and time.time() > DEADLINE[0]:
                raise RuntimeError(f"time budget used up; last error: {last}")
            t0 = time.time()
            try:
                text = fn(model, system, user, key)
                took = time.time() - t0
                data = _json_from(text)
                FREE_FAILS[0] = 0
                if took > SLOW_SECS:      # answered, but far too slow: use another model for a while (checked again later)
                    DEAD[(provider, model)] = time.time() + 1800
                    _log(f"slow ({int(took)}s) - skipped for 30 min: {provider}/{model}")
                _log(f"ok {provider}/{model} ({int(took)}s)")
                PREFERRED[0] = (provider, model)
                return data, f"{provider}/{model}"
            except Exception as e:
                last = e
                msg = str(e)
                FREE_FAILS[0] += 1
                _log(f"fail {provider}/{model}: {msg[:120]}")
                low = msg.lower()
                if any(c in msg for c in (" 401", " 403", " 404")):
                    DEAD[(provider, model)] = time.time() + 6 * 3600     # not allowed on this key/plan: never try it again this round
                    _log(f"not available on this plan: {provider}/{model}")
                    break
                if " 429" in msg and ("perday" in low or "per day" in low or "daily" in low or "limit: 0" in low or "tokens per day" in low):
                    DEAD[(provider, model)] = time.time() + 6 * 3600      # daily quota is gone: skip it for the rest of the round
                    _log(f"dead for this round: {provider}/{model}")
                    break
                if " 413" in msg or "request too large" in low:
                    break
                if not any(c in msg for c in (" 400", " 401", " 403", " 404", " 408", " 413", " 429", " 500", " 502", " 503", " 504")) and "time budget" not in low:
                    # a poor / unreadable answer (not valid JSON, or an empty reply): this model is skipped for 30 min, the next one is tried
                    DEAD[(provider, model)] = time.time() + 1800
                    _log(f"poor answer - skipped for 30 min: {provider}/{model}")
                    break
                if k >= 1 and (" 429" in msg or " 503" in msg):
                    DEAD[(provider, model)] = time.time() + 600     # still limited after a retry: switch to the next model for 10 min
                    _log(f"switching away from {provider}/{model} for 10 min")
                    break
                if k < 2 and (" 503" in msg or " 429" in msg) and provider != "openrouter":
                    time.sleep(15 + 15 * k)      # per-minute free limits reset quickly; wait instead of falling to a weaker model
                    continue
                break
    raise RuntimeError(f"no free model answered: {last}")


# ---- Claude (paid, optional): used only to FACT-CHECK drafts and, if the free models cannot produce a clean draft, to rewrite it. Needs ANTHROPIC_API_KEY.
CLAUDE_CALLS = [0]
CLAUDE_MAX = int(os.environ.get("CLAUDE_MAX_CALLS", "100000"))   # owner decision 24 Oct: no per-run limit; cost checked after one month       # cost guard per run


def claude_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and CLAUDE_CALLS[0] < CLAUDE_MAX


def ask_claude(system, user, max_tokens=4000):
    """returns (data, model_name); raises when the key is missing, the budget guard is hit or the API fails (the caller then falls back to the free chain)"""
    if not claude_available():
        raise RuntimeError("claude not available")
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")
    CLAUDE_CALLS[0] += 1
    sysb, usr = system, user
    cut = user.find("\n\nTODAY (IST):")
    if cut > 500:      # the rules + the few-shot examples are identical for every story: send them as a cached block (cache reads cost ~10%)
        sysb = [{"type": "text", "text": system}, {"type": "text", "text": user[:cut], "cache_control": {"type": "ephemeral"}}]
        usr = user[cut:].lstrip()
    body = {"model": model, "max_tokens": max_tokens, "system": sysb, "messages": [{"role": "user", "content": usr}],
            "thinking": {"type": "disabled"}}      # thinking tokens ate the whole answer budget (stop_reason=max_tokens, empty JSON) and cost money
    hdr = {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"}
    r = requests.post("https://api.anthropic.com/v1/messages", headers=hdr, json=body, timeout=120)
    if r.status_code == 400 and "thinking" in r.text.lower():
        body.pop("thinking"); body["max_tokens"] = max(max_tokens, 12000)
        r = requests.post("https://api.anthropic.com/v1/messages", headers=hdr, json=body, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"anthropic {r.status_code} {r.text[:200]}")
    j = r.json()
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type", "text") == "text")
    _log(f"ok anthropic/{model}")
    try:
        return _json_from(text), f"anthropic/{model}"
    except Exception as e:
        print(f"claude answer not JSON ({e}); stop_reason={j.get('stop_reason')} blocks={[b.get('type') for b in j.get('content', [])]} usage={j.get('usage')} head={text[:200]!r}")
        raise
