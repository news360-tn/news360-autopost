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
| 2026-11-28 | `eaca15f` | Writer hook (first 3 s): place first + strong event word + one hard detail; நாளை/இன்று first; schemes open with the amount / last date; caption first line 7-12 words (data: 2,686 reels) |
| 2026-11-28 | `7a57071` | stories shared / Instagram pause |
| 2026-11-28 | `482b7c5` | stories shared / Instagram pause |
| 2026-11-28 | `0f58948` | facebook RN-879 |
| 2026-11-28 | `2eab562` | posted RN-879 |
| 2026-11-28 | `a54c14e` | facebook RN-886 |
| 2026-11-28 | `29193c3` | posted RN-886 |
| 2026-11-28 | `e2ddc7d` | stories shared / Instagram pause |
| 2026-11-28 | `6f059f5` | facebook RN-877 |
| 2026-11-28 | `c203903` | posted RN-877 |
| 2026-11-28 | `66c5f24` | stories shared / Instagram pause |
| 2026-11-28 | `3e13ff1` | stories shared / Instagram pause |
| 2026-11-28 | `b7a71d8` | stories shared / Instagram pause |
| 2026-11-28 | `5827860` | stories shared / Instagram pause |
| 2026-11-28 | `f28770a` | stories shared / Instagram pause |
| 2026-11-28 | `2b5dcc9` | stories shared / Instagram pause |
| 2026-11-28 | `e3f589e` | stories shared / Instagram pause |
| 2026-11-28 | `8d00866` | stories shared / Instagram pause |
| 2026-11-28 | `ff54fa3` | stories shared / Instagram pause |
| 2026-11-28 | `1338b7a` | stories shared / Instagram pause |
| 2026-11-28 | `f23fd61` | stories shared / Instagram pause |
| 2026-11-28 | `18b28c7` | stories shared / Instagram pause |
| 2026-11-28 | `35de6fa` | facebook RN-874 |
| 2026-11-28 | `4747c40` | posted RN-874 |
| 2026-11-28 | `e31b3c4` | stories shared / Instagram pause |
| 2026-11-28 | `e1c31ad` | stories shared / Instagram pause |
| 2026-11-28 | `a83b239` | facebook RN-875 |
| 2026-11-28 | `e5e6584` | posted RN-875 |
| 2026-11-28 | `bde6555` | rasipalan posted |
| 2026-11-28 | `e49f953` | stories shared / Instagram pause |
<!-- recent-changes:end -->
