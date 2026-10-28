# News360 – நாமக்கல் 360 auto-posting

Automatic Namakkal-district news reels for **நாமக்கல் 360** (@namakkal.360) and **இராசிபுரம் 360** (@rasipuram.360),
also sent to the website www.namakkal360.workers.dev. Everything runs on GitHub Actions; the Google Sheet (through the
Apps Script bridge) is the working store. Owner rules, main files and recent changes: see `PROJECT_CONTEXT.md`.

## How a story gets from news to Instagram

```
research_free.yml (every 4 h) -> queue.json -> write_stories.yml (every 20 min) -> Google Sheet -> post.yml (every 5 min) -> Instagram + website
                                                                                                        ^
                                                                    insights.yml (daily) -> topic weights for the writer
```

1. **Collect** (`.github/workflows/research_free.yml`, every 4 hours at :07, `research_free/collect.py`).
   Searches newspaper sites and Google/Bing News, opens and checks each article, keeps only Namakkal-district news of
   today or yesterday, removes duplicates and queues the rest by priority in `research_free/archive/queue.json`.
   Manual run with `manual_url` = one article link written and posted at once.
2. **Write** (`.github/workflows/write_stories.yml`, every 20 minutes, same `collect.py` in write mode).
   Takes the queue by priority (3 at a time), writes the Tamil headline, caption and reel script (free LLM chain,
   Claude Haiku only as backup), makes 3 new AI images (cover FLUX dev, scenes FLUX schnell, uploaded to Cloudinary),
   saves the story in the Sheet and starts the posting job at once. An empty queue ends the run in seconds.
3. **Post** (`.github/workflows/post.yml`, every 5 minutes, `poster/post.py`).
   - `check`: reads the Sheet queue and skips stories that are on hold, stale (older than yesterday, finished power cut,
     passed date - `poster/freshness.py`), not Namakkal-district news, or a duplicate of an already posted story.
     Urgent news goes out at once; other reels are made ahead and posted in prime time (`poster/config.json` `prime_time`,
     never more than 12 h wait). Up to 50 posts per page per 24 h, up to 12 stories per run.
     A watchdog restarts the collector or writer if GitHub skipped their schedule.
   - `run`: builds the carousel (`kit/`) and the reel (`reel/reel4.py`, Google Chirp 3 HD Charon voice within the free
     allowance, then Valluvar), runs the checks (`poster/verify.py`), publishes through the bridge and sends the story to
     the website (`poster/website.py`). Rasipuram-area news posts on இராசிபுரம் 360 with நாமக்கல் 360 as collaborator;
     district-wide news the other way round. Finished media is kept in `poster/prebuilt/` so a retry does not rebuild.
4. **Insights** (`.github/workflows/insights.yml`, daily 02:10 IST, `poster/insights.py`): Instagram insights become
   learned topic weights used for the writer's priority.

## Switches

| Switch | Effect |
|---|---|
| `research_free/ENABLED` (Actions -> **collect-switch** -> `pause` / `start`) | Automatic collecting and writing on/off. Posting continues |
| `LIVE` file in the repository root | Scheduled posting to Instagram only happens while it exists. Remove it to stop posting |
| Manual run of **Post stories** | Test only by default (`dry_run`); `prebuild` makes every waiting reel now without posting |

While collecting is paused you can e-mail a story yourself (subject `NEWS360 STORY`, JSON in the body, images attached) -
see `docs/manual_story_prompt.md`. Posting always runs the duplicate check and the source fact gate first.

Repair tools (Actions, run by hand): **repost** (post a removed reel again), **website-backfill** (resend posted stories to
the website), **reoffer-stories**, **rewrite**, **audit**.

## Secrets (GitHub -> Settings -> Secrets and variables -> Actions)

`BRIDGE_URL`, `BRIDGE_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`, `MISTRAL_API_KEY`, `GH_MODELS_TOKEN`,
`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `FAL_KEY`, `CLOUDINARY_CLOUD`,
`CLOUDINARY_PRESET`, `GOOGLE_TTS_API_KEY`, `WEBSITE_INGEST_KEY`. Local copies live only in `.env` (git-ignored).

Instagram tokens live only in Apps Script (Project settings -> Script properties: `BRIDGE_KEY`, `IG_TOKEN_NAMAKKAL`,
`IG_TOKEN_RASIPURAM`, optional `ALLOWED_SENDERS`).

## Updating the Apps Script (after every change to `apps_script/Code.gs`)
1. Open the Apps Script project, replace the code with `apps_script/Code.gs`, save.
2. Run the function `setup` once (asks for Gmail permission; creates the 5-minute mail trigger and the weekly token refresh).
3. Deploy -> Manage deployments -> pencil -> Version: New version -> Deploy (the web app URL stays the same).

## Tests

```
python3 -m unittest discover -s tests        # regression tests (also run by tests.yml on every code push)
```
