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
| 2026-10-29 | `92f5cc4` | Font check optional: the writer and test runner have no fontTools, so letter repair still runs and tests pass on GitHub (Python 3.11) |
| 2026-10-29 | `4d3e179` | Newest Haiku (claude-haiku-5-5) for Claude calls, older Haiku only if the name is ever refused; news only from Tamil-language articles |
| 2026-10-29 | `17a77ac` | Letters of another script inside Tamil words are repaired (voice and cards), flagged for rewrite, and cleaned in captions (Coimbatore RN-5, 7, 20, 22) |
| 2026-10-29 | `b4f47be` | No made-up stories: skip a page that is only a headline, and never file a draft mostly not grounded in its Tamil article (RN-12 Coimbatore, K.N. Nehru raid) |
| 2026-10-29 | `835cfb9` | News pictures (owner): the scene of THIS news first in every prompt; cover = the main event, each scene 100-150 words with 3+ article facts; seized-goods and civic-problem guides; a generic or short cover plan is sent back once |
| 2026-10-29 | `8c1ced1` | Pictures free first (owner): Cloudflare FLUX schnell, then NVIDIA FLUX (schnell first); FAL only when both fail (cover dev, scenes schnell); Cloudflare daily limit not retried per picture; NVIDIA models answering 404 removed |
| 2026-10-29 | `f4eb7be` | Proofread: a fix must keep the word's grammatical ending - a verb is never turned into a noun (Coimbatore RN-1 நிர்வாகிக்க -> நிர்வாகம்) |
| 2026-10-29 | `9ecb5d5` | Owner fixes 29 Oct: a script that talks about the article instead of the news is refused (RN-189, deleted); one egg/gold/fuel price post a day (RN-188 + RN-189); Claude backup model id claude-haiku-4-5 (claude-haiku-5-5 does not exist) |
| 2026-10-29 | `d24107f` | Not news is never filed or posted: a story that only says the article has no details is rejected at writing and at posting; a real story loses only such a sentence (RN-189 egg price, RN-112) |
| 2026-10-28 | `3a47d79` | Reel longer than 90 s: shorten the script automatically and render again instead of holding the story (RN-153) |
| 2026-10-28 | `0cc5340` | Priority: power cuts and jobs are their own topics with a plus weight (they were -0.5 as civic / education_jobs although our most watched news: 17,328 and 17,209 views, page median 374); exam/election no longer counted as temple; insights relabels older posts |
| 2026-10-28 | `e034b52` | No missed news: writer duplicate check needs 3 shared words and only compares with stories of the last 3 days (28 Oct: rain 140 mm, service-road garbage, farmers' meeting were wrongly skipped); picture check works again (gemini-2.5-flash retired: uses the live model list, next model on timeout/busy) |
| 2026-10-28 | `916a2f8` | README: current automatic flow (collect, write, post, insights), switches, secrets; LIVE file stops posting |
| 2026-10-28 | `bc8f0cf` | Ages read clearly: newspaper shorthand 'செல்வம், 47,' / 'செல்வம் (47)' becomes 'செல்வம் (47 வயது)' in voice, subtitles, cards and caption, also for stories written earlier (RN-156) |
| 2026-10-28 | `c2f3cbf` | No missed news: an arrest/verdict/rescue reported days after the event is new news, not a duplicate (RN-159); the paper's Namakkal page counts as Namakkal news at posting too (RN-161); All News sheet no longer fails on a link listed twice |
| 2026-10-28 | `e30419b` | Clear news reading: the reel opens with the one-line story (6-9 words, first 2-3 s) then the explanation; every number said with its meaning (age, count, date with month) - bare numbers like 'ராஜா, 12,' are rewritten |
| 2026-10-28 | `5025c7a` | Proofread no longer damages reels: only whole-word small spelling fixes, never names/page/follow line/article words/meaning (RN-158 doubled words, RN-155 நம்மக்கல்); ages said as a news reader; repost workflow for a removed reel |
<!-- recent-changes:end -->
