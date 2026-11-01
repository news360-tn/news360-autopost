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
| 2026-11-01 | `7c9a922` | the fact-check / location hold also applies to owner ready reels (they skipped every news check before); RN-272 repost path |
| 2026-11-01 | `65b0ed4` | writer must name the town or village from the article in location (a district alone is not allowed); a story whose location is only the district is held from posting (RN-272) |
| 2026-11-01 | `5cc8699` | hold a story from posting when its fact-check found any problem or its location is unknown (RN-272); the verification label now shows the real check result instead of a fixed 'not checked by Claude yet' |
| 2026-11-01 | `fe27d35` | Heartbeat |
| 2026-11-01 | `1da681a` | rasipalan: திதி / நட்சத்திரம் / யோகம் as Maalaimalar's daily panchangam (Vakya) prints them; own calculation only when not found |
| 2026-11-01 | `df9539f` | stories shared |
| 2026-11-01 | `155ae71` | Namakkal: never written - another district's story (even on the paper's Namakkal page), a shop offer, a suicide (RN-251, RN-255) |
| 2026-11-01 | `b25f824` | story catch-up: a post shared once is remembered (poster/story_shared.json) - the rasipalan got a 2nd story |
| 2026-11-01 | `d25ab08` | story catch-up: video re-hosted on Cloudinary first (Instagram refused its own CDN link: container ERROR); tries capped per run |
| 2026-11-01 | `cced927` | story catch-up: a post's owner id is the account's app id - every post was taken for the other page's collab |
| 2026-11-01 | `0b4cd01` | story catch-up: log quota / posts / stories seen |
| 2026-11-01 | `93c6f33` | stories: every post (news reel, carousel, rasipalan, any job) also goes to the story - fixed 25-post cut removed, missing stories caught up every run, last 5 of the 50/day kept for news |
| 2026-11-01 | `ed69875` | powercut: log the title of a power cut skipped as another district |
| 2026-11-01 | `889f623` | powercut: Namakkal district power-shutdown notices posted at once - hourly, Dinamani + Dinamalar Namakkal, never twice, never late, fails loudly; the normal collection is untouched |
| 2026-11-01 | `0e7d218` | rasipalan writer: 5 tries, best draft kept, only the lines still wrong are replaced (1 Nov Coimbatore repost failed over 1 line) |
| 2026-11-01 | `5a606f6` | rasipalan posted |
| 2026-11-01 | `09f5a62` | rasipalan: repost input - post today again once the old post is deleted |
| 2026-11-01 | `5770aa7` | rasipalan: நல்ல நேரம், சூலம் (+பரிகாரம்), சுபமுகூர்த்த நாள் on the panchangam slide and caption; ஞாயிற்றுக்கிழமை spelling; overlap check |
| 2026-11-01 | `34e6836` | voice: no dash ever reaches the voice - 'சேலம் - நாமக்கல்' was read as minus (RN-256); routes read முதல் ... வரை |
| 2026-11-01 | `7520454` | rasipalan posted |
| 2026-11-01 | `9f9ff6a` | rasipalan: never miss a day - 1 source enough after 9:30, keep trying until 12:30, backups 9:45 and 11:45 |
| 2026-11-01 | `55d6197` | rasipalan: find today's article when the day is written 01 or the link has no date (1 Nov nothing posted) |
| 2026-10-31 | `2db8072` | rasipalan: proofreader may only fix sandhi/spacing (never a changed letter); TV9 'மேஷ ராசி' headings read |
| 2026-10-31 | `de6fa35` | rasipalan: test runs keep the slides and log on a preview branch |
| 2026-10-31 | `2fa30af` | Daily rasipalan carousel for Rasipuram 360 (7:31 AM, temple design, festival themes, collab Namakkal 360) |
| 2026-10-31 | `99f4f39` | Real photos: one Gemini 'too many requests' (429) stops the photo check for 30 min - the free quota stays for the writer (owner 31 Oct) |
| 2026-10-31 | `53e4015` | Headline-only pages are never written; one prison escape is one event; 'details not yet known' scripts are not news (owner 31 Oct) |
| 2026-10-31 | `e274b44` | Namakkal: repeats within 2 days, fights and collapses are incidents (the Coimbatore fix, owner 31 Oct) |
| 2026-10-31 | `84f0b0b` | Real news photos: only our page's branding - source watermarks / channel logos removed, no source credit (owner 31 Oct) |
| 2026-10-31 | `8f263cd` | Real news photos: the source article's own photo is used when it shows this news, enhanced to a presentable picture; else AI pictures (owner 31 Oct) |
<!-- recent-changes:end -->
