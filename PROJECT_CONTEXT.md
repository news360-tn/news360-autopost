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
| 2026-11-26 | `bfc5c05` | Backend site: top numbers and district cards follow Today/7/14 days, cards aligned (4+3 on big screens, no overflow), data age shown (amber when late); collector runs hourly |
| 2026-11-26 | `b2e8bfc` | stories shared / Instagram pause |
| 2026-11-26 | `6c8a2e3` | Picture sync: the website keeps its own small copy of each story's pictures (R2 links are deleted after 24 hours) |
| 2026-11-26 | `4178d68` | stories shared / Instagram pause |
| 2026-11-26 | `fd8750c` | facebook RN-852 |
| 2026-11-26 | `8c738ae` | posted RN-852 |
| 2026-11-26 | `8785ff7` | Backend site: posts are stacked cards on phones (all numbers visible, no sideways scroll) |
| 2026-11-26 | `8b1ca77` | stories shared / Instagram pause |
| 2026-11-26 | `923bf47` | stories shared / Instagram pause |
| 2026-11-26 | `c94eba6` | stories shared / Instagram pause |
| 2026-11-26 | `418f72e` | stories shared / Instagram pause |
| 2026-11-26 | `6de04e1` | stories shared / Instagram pause |
| 2026-11-26 | `6966287` | stories shared / Instagram pause |
| 2026-11-26 | `208b499` | stories shared / Instagram pause |
| 2026-11-26 | `23ab24f` | stories shared / Instagram pause |
| 2026-11-26 | `6eed6d4` | stories shared / Instagram pause |
| 2026-11-26 | `7215341` | goldrate posted |
| 2026-11-26 | `1edacdc` | stories shared / Instagram pause |
| 2026-11-26 | `707f3ca` | stories shared / Instagram pause |
| 2026-11-26 | `452a298` | stories shared / Instagram pause |
| 2026-11-26 | `3af7c85` | stories shared / Instagram pause |
| 2026-11-26 | `cfa7ea6` | stories shared / Instagram pause |
| 2026-11-26 | `9451066` | stories shared / Instagram pause |
| 2026-11-26 | `e6ee8f6` | stories shared / Instagram pause |
| 2026-11-26 | `95016e5` | stories shared / Instagram pause |
| 2026-11-26 | `b7ea9c2` | stories shared / Instagram pause |
| 2026-11-26 | `45be6cc` | stories shared / Instagram pause |
| 2026-11-26 | `01a38aa` | Website gets each story's kind of news (safe note like the source comment); link sync puts Facebook and YouTube links on the website |
| 2026-11-26 | `59da77a` | powercut: notices written |
| 2026-11-26 | `c35f34a` | stories shared / Instagram pause |
<!-- recent-changes:end -->
