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
| 2026-11-23 | `e9d3417` | Reels only: no Instagram or Facebook stories; wait 5 minutes after an error |
| 2026-11-23 | `76587e9` | stories shared / Instagram pause |
| 2026-11-23 | `227efe9` | stories shared / Instagram pause |
| 2026-11-23 | `d393492` | stories shared / Instagram pause |
| 2026-11-23 | `0f4be26` | stories shared / Instagram pause |
| 2026-11-23 | `2e25bad` | Posting: next reel about 5 minutes after the last (5-minute gap kept); a temporary Instagram error waits 10 minutes, then posts (no manual e-mail for it) |
| 2026-11-23 | `fa83a21` | stories shared / Instagram pause |
| 2026-11-23 | `de0aa7f` | stories shared / Instagram pause |
| 2026-11-23 | `5638816` | District filter: Tindivanam, Gingee, Chidambaram, Neyveli and nearby towns are other-district news |
| 2026-11-23 | `4c9af6f` | stories shared / Instagram pause |
| 2026-11-23 | `0cf6fff` | stories shared / Instagram pause |
| 2026-11-23 | `d5f38f2` | facebook RN-794 |
| 2026-11-23 | `c11f8f1` | posted RN-794 |
| 2026-11-23 | `2991ed1` | stories shared / Instagram pause |
| 2026-11-23 | `be7ebf6` | YouTube Namakkal: public, 20 a day, 40 min apart, 7-22 IST; daily cap 30 |
| 2026-11-23 | `34c8f78` | goldrate posted |
| 2026-11-23 | `8165228` | stories shared / Instagram pause |
| 2026-11-23 | `286486f` | stories shared / Instagram pause |
| 2026-11-23 | `895765d` | stories shared / Instagram pause |
| 2026-11-23 | `3e2c405` | stories shared / Instagram pause |
| 2026-11-23 | `96bbe72` | stories shared / Instagram pause |
| 2026-11-23 | `aa7e272` | facebook RN-784 |
| 2026-11-23 | `48abfe1` | posted RN-784 |
| 2026-11-23 | `502d368` | stories shared / Instagram pause |
| 2026-11-23 | `f50bc57` | Yesterday's pending news (held only by the daily maximum) is offered again; common place words (நகரம், ரோடு, நிலையம் ...) no longer hold a news; Indian number grouping (29,86,950) is understood |
| 2026-11-23 | `52006ac` | stories shared / Instagram pause |
| 2026-11-23 | `a770a3c` | stories shared / Instagram pause |
| 2026-11-23 | `559d297` | stories shared / Instagram pause |
| 2026-11-23 | `93b5ffd` | stories shared / Instagram pause |
| 2026-11-23 | `be6af0b` | stories shared / Instagram pause |
<!-- recent-changes:end -->
