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
| 2026-10-28 | `c2f3cbf` | No missed news: an arrest/verdict/rescue reported days after the event is new news, not a duplicate (RN-159); the paper's Namakkal page counts as Namakkal news at posting too (RN-161); All News sheet no longer fails on a link listed twice |
| 2026-10-28 | `e30419b` | Clear news reading: the reel opens with the one-line story (6-9 words, first 2-3 s) then the explanation; every number said with its meaning (age, count, date with month) - bare numbers like 'ராஜா, 12,' are rewritten |
| 2026-10-28 | `5025c7a` | Proofread no longer damages reels: only whole-word small spelling fixes, never names/page/follow line/article words/meaning (RN-158 doubled words, RN-155 நம்மக்கல்); ages said as a news reader; repost workflow for a removed reel |
| 2026-10-28 | `98bdd3f` | Reels: full news detail from the source (every fact, 130-170 words; examples and rules no longer push short scripts), at most 90 seconds (voice read up to 1.2x faster instead of cutting facts) |
| 2026-10-27 | `1fd4cb5` | PROJECT_CONTEXT.md: how the pipeline works, owner rules, files, secrets; recent changes updated automatically after every code commit |
| 2026-10-27 | `e9deebe` | Reels: no double reading of the opening, full dates (month added), short pauses in long lists, everyday Tamil Nadu words (பஸ், டூவீலர், போலீசார், கலெக்டர்) in voice, subtitles and cards |
| 2026-10-27 | `2bfa658` | Reel opening: the most striking fact is spoken first (~2-4 s) while the big headline and number are on screen |
| 2026-10-27 | `316bfed` | Prime-time posting: urgent news at once, other reels made ahead and posted in 9-12 / 18-21:30 IST; nothing dropped (max 12 h wait) |
| 2026-10-27 | `48dc44f` | Google Charon voice for every reel while free (stops at 700,000 characters a month, then Valluvar); Valluvar whenever Google fails |
| 2026-10-27 | `029fe0e` | Website: each posted story goes to www.namakkal360.workers.dev with English version and all details; Sheet 'posted_rows' view + one-time backfill workflow |
| 2026-10-27 | `9c96409` | Regression test pack from real cases (23 tests) + GitHub check on every code change |
| 2026-10-27 | `5093f5a` | Posting gate: only today's or yesterday's news is posted; publish date also read from the news link (late power-cut notice and a 2-day-old story went out) |
| 2026-10-27 | `714694e` | Second check really happens: the old 'rejected' mark is removed so the writer does not skip the item |
| 2026-10-27 | `5acd002` | Two news voices: Google Chirp 3 HD Charon for even stories only while it is free (stops at 800,000 characters a month), otherwise Valluvar |
| 2026-10-27 | `a04e2ce` | Back to one news voice: Valluvar for every reel (Google voice removed) |
| 2026-10-27 | `f46f9b9` | Two news voices take turns: odd stories Valluvar, even stories Google Chirp 3 HD (falls back to Valluvar if not set up) |
| 2026-10-27 | `72f3093` | Images: cover stays FLUX dev, scenes 2-3 of the same news use FLUX schnell (dev as backup); every picture still checked against the headline |
| 2026-10-27 | `0dc701a` | Search more: other Rasipuram spelling, smaller towns, English reports and English papers |
| 2026-10-27 | `6781c29` | No missed news: full Dinamalar Namakkal list, paper's Namakkal page counts as district news, word-based duplicate check; recheck wrongly skipped items once |
| 2026-10-27 | `3a3cf23` | Power cuts: different place or older notice is not a duplicate; never post a cut that ends within the hour |
| 2026-10-27 | `e6b2973` | Reel: never show <b> tags on screen; rebuild ready reels made before this fix |
| 2026-10-26 | `7d65259` | Heartbeat |
| 2026-10-26 | `d63fc7b` | Posting install: ffmpeg from GitHub (checksum checked), Ubuntu only as backup; cached browser |
| 2026-10-26 | `ed03ef0` | Reel: viewer feedback - logo top-right, footer, one-line story opening, news voice |
| 2026-10-26 | `d17fa3c` | Posting gate: a headline that names another district is never posted |
| 2026-10-26 | `17d5db0` | Posting job: apt gives up on a silent mirror after 20 s and retries |
| 2026-10-26 | `0ac8155` | Writer restarts itself only after progress (no restart loop) |
| 2026-10-26 | `17ba72c` | Posting job: never post a story that is not Namakkal-district news |
| 2026-10-26 | `16bc946` | Queue only news that was opened and checked |
| 2026-10-26 | `b852ced` | Only Namakkal-district news: nearby areas removed, link district checked |
<!-- recent-changes:end -->
