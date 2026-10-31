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
| 2026-10-31 | `9391e60` | Writing order from our own Instagram insights (owner 31 Oct) |
| 2026-10-31 | `0f65b11` | Prime time off: a reel posts as soon as it is written (owner 31 Oct) |
| 2026-10-30 | `383d9b4` | Heartbeat |
| 2026-10-30 | `499e23a` | Refused stories are not written again and again (owner 30 Oct) |
| 2026-10-30 | `cec615a` | Same event from two outlets in one writer round is caught (stories filed this round join the check), and short reports of one event count as the same (RN-214 = RN-209) |
| 2026-10-30 | `84e663c` | Writer/collector: the Sheet bridge is tried 3 times when Apps Script does not answer (writer crashed once at 09:00 UTC 30 Oct on a 120 s timeout) |
| 2026-10-30 | `ba06b8e` | Sarvam out of the live writer order until writer-compare proves it |
| 2026-10-30 | `e033529` | writer compare output |
| 2026-10-30 | `401f8a5` | Sarvam: reasoning low (API accepts low/medium/high only) |
| 2026-10-30 | `f495008` | writer compare output |
| 2026-10-30 | `761c232` | Sarvam: thinking off, bigger answer budget; empty answers logged with the reason |
| 2026-10-30 | `2c68b07` | writer compare output |
| 2026-10-30 | `cdbdc9a` | Remove Cerebras writer: it now needs a card (paid after $5 trial) |
| 2026-10-30 | `b12e4a4` | Free writers: Gemini 3.6/3.5 first, Sarvam + Cerebras (skipped until keys), Gemma ready (off), Groq short retry on 413; remove GitHub Models, Mistral, OpenRouter, NVIDIA text; writer-compare test workflow |
| 2026-10-30 | `5caf346` | SiliconFlow removed (owner): not free for this account ('balance insufficient'); picture order Cloudflare -> Pollinations -> NVIDIA -> FAL |
| 2026-10-30 | `af5c2ae` | image test output |
| 2026-10-30 | `db908ee` | imagegen-test: each free picture service tested on its own (Cloudflare, SiliconFlow, Pollinations, NVIDIA) - nothing posted |
| 2026-10-30 | `73a8041` | Free pictures first (owner 30 Oct): Cloudflare kept for pictures (not writing, 4 steps = ~230 free pictures/day) -> SiliconFlow free FLUX -> Together free FLUX -> Pollinations -> NVIDIA -> FAL only when all fail (each new service skipped until its key is set); 2 news-specific pictures per reel on every page (cover = main event, 2nd = detail); the cover is kept if the 2nd picture fails; switches in config.json free_images |
| 2026-10-30 | `a07407b` | Code bugs never repeat (owner): tests fail on any undefined name in poster/research_free/reel (pyflakes on GitHub - would have stopped the 29 Oct 'verify' posting crash) and run the caption + posting-check steps end to end on a sample story |
| 2026-10-30 | `8c8ebec` | Known issues are repaired, not lost (owner): a card cut mid-phrase, a sentence or word said twice, a sentence about 'the article' are fixed before posting; only what cannot be fixed is held (RN-199, RN-203 held for a cut card); repeated-sentence check no longer splits at 'ரூ.2.50' / 'ஹெச்.பி.' (RN-200 false alarm) |
| 2026-10-29 | `3614b3b` | Caption holds ALL the news (owner): every number, date, age, amount and place in the article sentences about this story must be in the caption, else the writer adds it (RN-175, 178, 181, 185, 186 missed one); other headlines on the page and datelines ignored; never drops a story; switch reach.caption_all_facts |
| 2026-10-29 | `dff5d94` | Reach plan for Namakkal + Rasipuram (owner): reels at most 60 s (70-105 words; every detail stays in the caption's full-details block, checked at writing), English search line added at posting (whole words), 5 focused hashtags (page + #Namakkal + town + topic + broad), location tags on (24 known places), no brand names/logos in pictures; all behind poster/config.json reach switches |
| 2026-10-29 | `6b5a4e6` | Known issues never repeat (owner): one list (research_free/known_issues.py) checked when a story is written AND right before posting - script about the article, letters of another script (repaired first), English words the voice skips, card cut mid-phrase, words said twice; every entry has a real bad and good example run by the tests |
| 2026-10-29 | `a29cddd` | Fix: every post job crashed with NameError (verify not imported in clean_caption) since 13:00 UTC 29 Oct |
| 2026-10-29 | `d04afbd` | A story whose first lines name another district (and no Namakkal place in the headline) is not filed or posted (RN-195 Erode onion prices); Pallipalayam/Kokkarayanpettai spellings with ப் count as Namakkal places |
| 2026-10-29 | `85d02eb` | Topic / tag / author / page-N listing pages are never written or posted as a news story (RN-194: abplive topic page gave a Cuddalore story) |
| 2026-10-29 | `5ff36f3` | Writer started by the collector waits for the queue instead of skipping; same event from another outlet is not written again (RN-193 = RN-168) |
| 2026-10-29 | `d60d546` | Publish times with a time zone are read in IST (a 22:17 UTC story is the next day in IST, not the day before) |
| 2026-10-29 | `c2df785` | Collection is never cancelled by the story writer: each has its own queue; the collector waits while a writer runs, the writer skips its round while a collection runs (Coimbatore lost 2 collections on 29 Oct) |
| 2026-10-29 | `0b28615` | No old events and no same-event repeats: an old event re-told in a new article is not filed or posted (Coimbatore RN-29); the same event from another outlet in other words is not posted twice (RN-13/24, RN-86/115) |
<!-- recent-changes:end -->
