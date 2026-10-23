# News360 – நாமக்கல் 360 auto-posting (photo flow)

How a story gets from news to Instagram:

1. **Research (Claude scheduled task, every 3 hours, 06:17-21:17 IST).** Finds and verifies Namakkal-district news, writes the
   Tamil poster text, caption and reel script, files each story in Notion, a Google Doc and the Google Sheet
   (`Post status = Awaiting images`) and sends ONE email `[NEWS360 IMAGES NEEDED] <batch>` with ChatGPT image prompts.
   The task's instructions are kept in `docs/research_task_prompt.md`.
2. **You reply to that email** with the ChatGPT images (a zip, or the images attached). `SKIP RN-26` in the reply skips a story.
3. **Apps Script bridge** (`apps_script/Code.gs`, runs in nammarasipuram2805@gmail.com) reads the reply every 5 minutes,
   uploads the images to Cloudinary, saves the links in the Sheet and sets the story to `Queued`.
   Stories without images after 12 hours expire.
4. **GitHub Actions** (`.github/workflows/post.yml`, every 20 minutes) picks the top ready story, builds the carousel
   (`kit/render_photo.py`) and the reel (`reel/reel.py`, your images with camera motion + Tamil voice), runs the checks
   (`poster/verify.py`: Tamil text and fonts, no clipped text, reel length/voice, news verified, no source names),
   and only then posts to **நாமக்கல் 360**. Rasipuram stories also invite **இராசிபுரம் 360** as a collaborator
   (accept the invite once in that app). Each posted story is recorded in the Sheet and Doc and emailed to you.

Switches: scheduled posting only happens when a file named `LIVE` exists in the repository root. Manual runs
(Actions -> Post stories -> Run workflow) are test-only by default. Set the repository variable `PAUSED=true` to stop everything.
`poster/config.json`: `ai_label` (small "AI" tag on images + caption line), `collab_username`.

## Secrets (GitHub -> Settings -> Secrets and variables -> Actions)
`BRIDGE_URL`, `BRIDGE_KEY`, `CLOUDINARY_CLOUD`, `CLOUDINARY_PRESET`. Instagram tokens live only in Apps Script
(Project settings -> Script properties: `BRIDGE_KEY`, `IG_TOKEN_NAMAKKAL`, `IG_TOKEN_RASIPURAM`, optional `ALLOWED_SENDERS`).

## Updating the Apps Script (after every change to `Code.gs`)
1. Open the Apps Script project, replace the code with `apps_script/Code.gs`, save.
2. Run the function `setup` once (asks for Gmail permission; creates the 5-minute reply trigger and the weekly token refresh).
3. Deploy -> Manage deployments -> pencil -> Version: New version -> Deploy (the web app URL stays the same).


## Pause automatic collecting / send your own stories
Actions -> **collect-switch** -> Run workflow -> `pause` or `start` (only the automatic collecting/writing; posting continues).
While paused, e-mail a story (subject `NEWS360 STORY`, JSON in the body, images attached) - see `docs/manual_story_prompt.md`.
Posting always runs the Instagram recent-captions duplicate check and the source fact gate first.
