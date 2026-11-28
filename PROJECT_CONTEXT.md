# news360-autopost - project context

Automatic Namakkal-district news for Instagram pages **நாமக்கல் 360** (@namakkal360.official) and **இராசிபுரம் 360** (@rasipuram360.official),
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
| Posting time | owner 27 Nov: 06:00-22:00 IST every reel posts as soon as it is ready; 22:00-06:00 only urgent news. News is collected every 2 hours |
| Errors and blocks | owner 27 Nov: after an error 5 tries 10 minutes apart, then 1 try 1 hour later, then Hold - never retried at once; a temporary block waits the time the platform states, else 2 hours. No manual work for the owner (config.json owner_emails false) |
| Daily cap | owner 27 Nov: 30 news a day per page on Instagram, Facebook and YouTube each (IST day; rasipalan / gold rate extra); after 30 only urgent news |
| Priority | owner 27 Nov: by this page's Instagram views per topic (research_free/learned.json); urgent = an upcoming power cut (first) or a topic whose reels often pass 10,000 views (1 in 5) |
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
| 2026-11-28 | `3b6bf76` | Top 5: headline at most 3 lines (never over the 5-4-3-2-1 row), the row a little lower, 'nettru' for yesterday's news |
| 2026-11-28 | `c903354` | stories shared / Instagram pause |
| 2026-11-28 | `2543db3` | stories shared / Instagram pause |
| 2026-11-28 | `a447642` | stories shared / Instagram pause |
| 2026-11-28 | `5864866` | Rasipalan and top 5: the page's real Instagram username as the fallback (never a made-up Tamil name on the follow card) |
| 2026-11-28 | `88eb470` | stories shared / Instagram pause |
| 2026-11-28 | `07cd523` | stories shared / Instagram pause |
| 2026-11-28 | `9c5fab1` | New reels: parrot rasipalan (kili josiyam) with panchangam, rasi times and first comment; evening top 5 |
| 2026-11-28 | `997ed11` | stories shared / Instagram pause |
| 2026-11-28 | `328a379` | stories shared / Instagram pause |
| 2026-11-28 | `a3e5666` | stories shared / Instagram pause |
| 2026-11-28 | `f4df757` | stories shared / Instagram pause |
| 2026-11-28 | `6389528` | facebook RN-884 |
| 2026-11-28 | `f1c341d` | posted RN-884 |
| 2026-11-28 | `415cd1b` | autofix: corrected held news |
| 2026-11-28 | `9983e52` | stories shared / Instagram pause |
| 2026-11-28 | `6d300f4` | stories shared / Instagram pause |
| 2026-11-28 | `9cb130d` | facebook RN-883 |
| 2026-11-28 | `99996b3` | posted RN-883 |
| 2026-11-28 | `ae5406e` | stories shared / Instagram pause |
| 2026-11-28 | `35d6c9b` | stories shared / Instagram pause |
| 2026-11-28 | `a3dbb54` | facebook RN-881 |
| 2026-11-28 | `eeb8236` | posted RN-881 |
| 2026-11-28 | `e820916` | stories shared / Instagram pause |
| 2026-11-28 | `1a6c7ee` | stories shared / Instagram pause |
| 2026-11-28 | `43efa30` | facebook RN-882 |
| 2026-11-28 | `d493d0c` | posted RN-882 |
| 2026-11-28 | `58476ea` | stories shared / Instagram pause |
| 2026-11-28 | `bb29793` | stories shared / Instagram pause |
| 2026-11-28 | `891be2c` | goldrate posted |
<!-- recent-changes:end -->
