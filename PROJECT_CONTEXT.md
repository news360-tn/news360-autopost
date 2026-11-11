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
| 2026-11-11 | `4d4b215` | comment replies: Google Form per batch (works on any device, no account) - news, comment, tick-box replies (one or more), own reply, Reply/Skip/Hide; posted only after the owner submits; 5-minute check (setupCommentPoll_) |
| 2026-11-11 | `addeafe` | facebook RN-500 |
| 2026-11-11 | `0d8afe7` | comment reply form: the e-mailed link and form buttons use the bridge's own public address (getUrl gave an address that opened Google Drive) (owner 11 Nov) |
| 2026-11-11 | `980a496` | powercut: notices written |
| 2026-11-11 | `4a1562c` | comment replies: one reply form per page (works anywhere) - full news, the comment, 5-7 tick-box replies (one or more) or own text, Post reply / Skip / Hide; nothing is posted before the owner presses Post reply; manual test e-mail (owner 11 Nov) |
| 2026-11-11 | `79d242f` | powercut: notices written |
| 2026-11-11 | `83dfb90` | power cuts: a cancellation / postponement / day change is posted (urgent) only when this page posted that cut - never dropped as a duplicate of the original; the power-cut check remembers notices the writer refused (owner 11 Nov) |
| 2026-11-11 | `939a2ae` | facebook RN-502 |
| 2026-11-11 | `2710639` | powercut: notices written |
| 2026-11-11 | `bbd7bca` | comments: old unanswered comments offered too (60 days, 100 posts); comments the page already answered in the app are skipped (owner 11 Nov) |
| 2026-11-11 | `83ae709` | powercut: notices written |
| 2026-11-11 | `72d7f7f` | caption ends with 'Source: <paper> (<date>): <article link>'; no source comment under the post (owner 11 Nov) |
| 2026-11-11 | `f89b928` | facebook RN-503 |
| 2026-11-11 | `bcd92a9` | facebook RN-498 |
| 2026-11-11 | `a6813ea` | facebook RN-507 |
| 2026-11-11 | `a30e1b2` | powercut: notices written |
| 2026-11-11 | `6667341` | powercut: notices written |
| 2026-11-11 | `f4dc59b` | Apps Script: comment replies merged into Code.gs - the owner pastes one file (owner 11 Nov) |
| 2026-11-11 | `0695f4c` | facebook RN-504 |
| 2026-11-11 | `3b4c4d5` | facebook RN-499 |
| 2026-11-11 | `8d946c7` | powercut: notices written |
| 2026-11-11 | `d273c5f` | Facebook: only top news by insights (urgent / best topics), 5 a day 2 h apart, 24 h pause on Facebook's limit (368), no retry; news source (paper + date) on the reel header, end card and captions, article link in the Facebook caption and the page's Instagram comment; comment replies e-mailed with 3 options - posted only after the owner's choice (owner 11 Nov) |
| 2026-11-11 | `07ee52b` | facebook RN-496 |
| 2026-11-11 | `e35567d` | facebook RN-506 |
| 2026-11-11 | `95b91ad` | facebook retry |
| 2026-11-11 | `6be58ee` | powercut: notices written |
| 2026-11-11 | `88b9cdc` | powercut: notices written |
| 2026-11-11 | `19b3133` | facebook retry |
| 2026-11-11 | `901efe9` | facebook RN-493 |
| 2026-11-11 | `c1fcde0` | facebook RN-492 |
<!-- recent-changes:end -->
