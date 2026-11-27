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
| 2026-11-27 | `5e318f7` | Rasipalan theme: Coimbatore page named in full (கோயம்புத்தூர்) gets its colour too |
| 2026-11-27 | `0d4f168` | stories shared / Instagram pause |
| 2026-11-27 | `4e84e9e` | Gold rate and rasipalan reels: each page its own colour theme |
| 2026-11-27 | `5f71603` | stories shared / Instagram pause |
| 2026-11-27 | `378f4be` | Power cuts are never missed: held notices are rewritten at once |
| 2026-11-27 | `aaa1949` | facebook RN-869 |
| 2026-11-27 | `de5538f` | posted RN-869 |
| 2026-11-27 | `d88ec88` | stories shared / Instagram pause |
| 2026-11-27 | `61e860d` | facebook RN-868 |
| 2026-11-27 | `f04e520` | posted RN-868 |
| 2026-11-27 | `1a7bf17` | stories shared / Instagram pause |
| 2026-11-27 | `81eebdc` | Blocked Google News links: also look for the same headline at another trusted outlet |
| 2026-11-27 | `587c040` | stories shared / Instagram pause |
| 2026-11-27 | `575dbb0` | stories shared / Instagram pause |
| 2026-11-27 | `305f817` | stories shared / Instagram pause |
| 2026-11-27 | `0470d67` | Sources: Dailythanthi and Maalaimalar Tamil Nadu / district lists (this district's links only) |
| 2026-11-27 | `5c0611d` | stories shared / Instagram pause |
| 2026-11-27 | `dd0bfcf` | stories shared / Instagram pause |
| 2026-11-27 | `7d26ebf` | goldrate posted |
| 2026-11-27 | `8ae0795` | stories shared / Instagram pause |
| 2026-11-27 | `ec4948d` | stories shared / Instagram pause |
| 2026-11-27 | `54bf355` | stories shared / Instagram pause |
| 2026-11-27 | `aa392b3` | stories shared / Instagram pause |
| 2026-11-27 | `04d879b` | stories shared / Instagram pause |
| 2026-11-27 | `0f91b4d` | stories shared / Instagram pause |
| 2026-11-27 | `f032d5a` | stories shared / Instagram pause |
| 2026-11-27 | `4d61a48` | stories shared / Instagram pause |
| 2026-11-27 | `d96a35e` | stories shared / Instagram pause |
| 2026-11-27 | `ac7adc3` | stories shared / Instagram pause |
| 2026-11-27 | `27e76a7` | powercut: notices written |
<!-- recent-changes:end -->
