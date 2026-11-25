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
| 2026-11-25 | `b32181c` | stories shared / Instagram pause |
| 2026-11-25 | `3b63157` | After a posting error wait 10 minutes before the next try (Instagram, Facebook, YouTube); YouTube and Facebook 20 a day; rasipalan and gold rate on YouTube too, first, outside the 20 |
| 2026-11-25 | `bac84e2` | stories shared / Instagram pause |
| 2026-11-25 | `e297fa6` | stories shared / Instagram pause |
| 2026-11-25 | `72ab9f6` | Posting order: power cut / shutdown first, then High, then the topic this page's insights rank best, then oldest first |
| 2026-11-25 | `a7854f1` | stories shared / Instagram pause |
| 2026-11-25 | `e48cb9e` | Night stop 00:00-04:00 IST (was 05:00); at most 35 news a day per page on Instagram; YouTube up to 35 a day from 04:00, following Instagram; insights test uses today's date |
| 2026-11-25 | `744e907` | facebook RN-815 |
| 2026-11-25 | `73494d2` | posted RN-815 |
| 2026-11-25 | `b7c2997` | One e-mail per news with its Instagram, Facebook and YouTube links (sent when all three are done or after 45 minutes; max 60 a day for all pages); YouTube follows Instagram: 5-minute gap, 05:00-24:00 IST, up to 30 a day |
| 2026-11-25 | `3863c15` | stories shared / Instagram pause |
| 2026-11-25 | `2521744` | stories shared / Instagram pause |
| 2026-11-25 | `bf1fa5e` | Per-post e-mail for every post, at most 60 a day for all 7 pages together (one Gmail account); later posts are in the daily summary |
| 2026-11-25 | `55241cf` | facebook RN-810 |
| 2026-11-25 | `7adff9f` | posted RN-810 |
| 2026-11-25 | `856545f` | stories shared / Instagram pause |
| 2026-11-25 | `89c6c26` | autofix: corrected held news |
| 2026-11-25 | `eea4446` | stories shared / Instagram pause |
| 2026-11-25 | `295b54a` | stories shared / Instagram pause |
| 2026-11-25 | `bbf1070` | stories shared / Instagram pause |
| 2026-11-25 | `f5d8577` | stories shared / Instagram pause |
| 2026-11-25 | `74a15b6` | stories shared / Instagram pause |
| 2026-11-25 | `845e6c2` | stories shared / Instagram pause |
| 2026-11-25 | `18c1b95` | stories shared / Instagram pause |
| 2026-11-25 | `2941e05` | stories shared / Instagram pause |
| 2026-11-25 | `65da25a` | stories shared / Instagram pause |
| 2026-11-25 | `dd16fdd` | stories shared / Instagram pause |
| 2026-11-25 | `64a6c0c` | stories shared / Instagram pause |
| 2026-11-25 | `4beadf7` | stories shared / Instagram pause |
| 2026-11-25 | `fbe0933` | stories shared / Instagram pause |
<!-- recent-changes:end -->
