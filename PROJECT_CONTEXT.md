# news360-autopost - project context

Automatic Namakkal-district news for Instagram pages **நாமக்கல் 360** (@namakkal.360) and **இராசிபுரம் 360** (@rasipuram.360),
and for the website **www.namakkal360.workers.dev** (repo: news360-tn/namakkal360-web).
Everything runs on GitHub Actions; the Google Sheet (through the Apps Script bridge) is the working store.

## How it works (end to end)

```
every 4 h   research_free.yml   collect news (newspaper sites, Google/Bing News, 42 searches) -> open + check each article
                                 -> only Namakkal-district news of today/yesterday -> queue (research_free/archive/queue.json)
every 20 min write_stories.yml  write each queued news by priority (LLM chain) -> 3 AI images (cover FLUX dev, scenes FLUX schnell)
                                 -> story saved in the Sheet -> starts posting at once
every 5 min  post.yml           checks (Namakkal only, not stale, no duplicate, prime time) -> reel (reel/reel4.py) -> Instagram
                                 -> the posted story is sent to the website (poster/website.py)
daily        insights.yml       Instagram insights -> learned topic weights (writer priority)
```

## Rules the owner decided (keep them)

| Area | Rule |
|---|---|
| News scope | Only Namakkal-district news, published today or yesterday. Rasipuram-area news -> Rasipuram 360 (Namakkal 360 invited as collab); district-wide news -> Namakkal 360 (Rasipuram 360 collab) |
| Never miss news | Everything eligible is queued and written; duplicates and other-district news are skipped; nothing eligible is dropped |
| Posting time | Urgent news (power cut, accident, rain warning, Collector/Govt notice, jobs, exams, today/tomorrow) posts at once. Other reels are made ahead and posted 09:00-12:00 / 18:00-21:30 IST; no reel waits more than 12 h (`poster/config.json` `prime_time`) |
| Instagram limit | 50 posts per page per 24 h; no internal cap below that |
| Voice | Google Chirp 3 HD **Charon** for every reel, ONLY inside Google's free allowance (code stops at 700,000 characters/month), then Valluvar (edge-tts). Never paid |
| Reel opening | Striking fact spoken first with the big headline; no double reading when the one-line story already says it; then one-line story, then full news |
| Reel language | Formal news Tamil, no slang; everyday Tamil Nadu words in voice, subtitles and cards (பஸ், டூவீலர், போலீசார், கலெக்டர் ...); dates always with the month |
| Images | New AI images for every story, made from the story's own scenes; older pictures are never reused |
| Text | No `<b>` marks on screen; website never shows long dashes |
| Proofread | The last Tamil proofread only fixes small spelling/sandhi mistakes of whole words; never page/place names, the follow line, English lines, words the article itself uses, or anything that changes meaning |
| Costs | Free tiers first (Gemini/Groq/NVIDIA/Cloudflare/Mistral...); Claude Haiku only as backup; FAL images ~₹2.7 per reel |
| Privacy | Personal project: commits only as **news360-tn**; no office account, office email or Claude lines in commits; files only in the owner's personal folder |

## Main files

| Path | What |
|---|---|
| `research_free/collect.py`, `allnews.py`, `sources.py` | collection, district checks, queue, writer, images |
| `research_free/rules.md`, `examples.json`, `names.py` | writing rules and spoken-word fixes |
| `poster/post.py` | posting checks, prime time, Instagram publishing |
| `poster/freshness.py` | stale / duplicate / power-cut timing rules |
| `poster/website.py` | sends posted stories to the website (+ English version); `backfill` for old stories |
| `poster/config.json` | voice, prime time, punch line, design switches |
| `reel/reel4.py` | reel renderer (design A, voice, opening, dates, everyday words) |
| `apps_script/Code.gs` | Google Sheet bridge (redeploy in Apps Script after changes) |
| `tests/test_regressions.py` | regression tests from real cases (run before every push) |

## Secrets (GitHub -> Settings -> Secrets -> Actions; values never in the repo)

BRIDGE_URL, BRIDGE_KEY, GEMINI_API_KEY, GROQ_API_KEY, NVIDIA_API_KEY, MISTRAL_API_KEY, GH_MODELS_TOKEN, CLOUDFLARE_API_TOKEN,
CLOUDFLARE_ACCOUNT_ID, OPENROUTER_API_KEY, ANTHROPIC_API_KEY, FAL_KEY, CLOUDINARY_CLOUD, CLOUDINARY_PRESET, GOOGLE_TTS_API_KEY,
WEBSITE_INGEST_KEY. Local copies live only in `.env` (git-ignored).

## Run and check

```
python3 -m unittest discover -s tests        # regression tests (also run by tests.yml on every code push)
python3 poster/website.py backfill --from RN-1   # (Actions: website-backfill) resend posted stories to the website
python3 tools/repost.py RN-158                   # (Actions: repost) post a reel again after it was removed from Instagram
```

## Recent changes
<!-- recent-changes:start (updated automatically by .github/workflows/context.yml - do not edit by hand) -->
| Date | Commit | Change |
|---|---|---|
| 2026-11-17 | `adf89b9` | pictures: NVIDIA FLUX no longer accepts 'seed' (422) - dropped so the free NVIDIA pictures work again |
| 2026-11-17 | `3f45cec` | goldrate posted |
| 2026-11-17 | `d705ed2` | facebook RN-648 |
| 2026-11-17 | `566bc2b` | facebook RN-636 |
| 2026-11-17 | `9db8bcd` | stories shared |
| 2026-11-17 | `e7281a9` | stories shared |
| 2026-11-17 | `daf319a` | stories shared |
| 2026-11-17 | `0d1f61c` | rasipalan posted |
| 2026-11-17 | `156d6e0` | powercut: notices written |
| 2026-11-17 | `7dc0084` | comments: normal comments recorded (not e-mailed) |
| 2026-11-17 | `9ee496c` | powercut: notices written |
| 2026-11-17 | `0113fab` | stories shared |
| 2026-11-17 | `ca6b80f` | facebook RN-647 |
| 2026-11-17 | `0034219` | facebook RN-646 |
| 2026-11-17 | `4fb6325` | stories shared |
| 2026-11-17 | `9fe833b` | facebook RN-637 |
| 2026-11-17 | `2b5aa3f` | facebook RN-639 |
| 2026-11-17 | `3b49ae9` | facebook RN-638 |
| 2026-11-17 | `cbc4b97` | facebook RN-631 |
| 2026-11-17 | `d500205` | facebook RN-632 |
| 2026-11-17 | `c36d0f2` | facebook RN-627 |
| 2026-11-17 | `7910fa4` | facebook RN-628 |
| 2026-11-17 | `9a72bea` | facebook RN-635 |
| 2026-11-17 | `64699c6` | facebook RN-634 |
| 2026-11-17 | `e13849a` | facebook RN-630 |
| 2026-11-16 | `12c4886` | facebook RN-616 |
| 2026-11-16 | `6c7480f` | facebook RN-619 |
| 2026-11-16 | `eea7757` | facebook RN-620 |
| 2026-11-16 | `71aff19` | facebook RN-622 |
| 2026-11-16 | `664f9e6` | facebook RN-617 |
<!-- recent-changes:end -->
