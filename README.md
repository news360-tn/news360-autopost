# News360 auto-posting – இராசிபுரம் 360 & நாமக்கல் 360

Posts verified Namakkal district news to two Instagram pages, 24/7, with no PC.

## How it works

| Step | Who | When |
|---|---|---|
| Find news, verify, write Tamil, proofread, design slides, write reel script, save to Sheet + Doc + email | Claude scheduled task | every hour (:15 IST) |
| **Workflow 1 – Carousel**: post the top queued story to each page (max 1 post per page per hour) | GitHub Actions `carousel.yml` | every hour (:10 IST) |
| **Workflow 2 – Reel**: make a 10–30 s reel of the top reel-worthy story and post it | GitHub Actions `reel.yml` | every 2 hours |
| After each post: update Sheet + Doc, email the posted details | Apps Script bridge | right after posting |

Page routing: Rasipuram town and nearby areas → **both pages**; rest of Namakkal district → **நாமக்கல் 360 only**.

Safety: a story is only posted if its **Post status** is `Queued`. Set **Review status** to `Hold` in the Sheet to stop any story.
Stories older than 36 hours (power shutdowns 72 hours) are not posted late. After 3 failed tries a story is put on Hold and you get an email.
To pause everything: repository **Settings → Secrets and variables → Actions → Variables → New variable** `PAUSED` = `true`.

Voice for reels: the free Tamil female voice model (AI4Bharat Indic-TTS). If a real recording named after the story ID
(for example `RN-7.m4a`) is in the Drive folder **Voice**, that recording is used instead.

## One-time setup

### 1. Apps Script (Google account nammarasipuram2805@gmail.com)
1. Open https://script.google.com → **New project** → name it `News360 bridge`.
2. Delete the sample code, paste all of `apps_script/Code.gs`, click **Save**.
3. Choose the function **setup** in the toolbar → **Run** → allow the permissions.
   Open **Execution log** and copy the `BRIDGE_KEY` value.
4. **Project Settings (gear) → Script properties → Add**:
   - `IG_TOKEN_RASIPURAM` = Instagram token of இராசிபுரம் 360
   - `IG_TOKEN_NAMAKKAL` = Instagram token of நாமக்கல் 360
5. **Deploy → New deployment → type: Web app** → Execute as **Me**, Who has access **Anyone** → **Deploy** → copy the **Web app URL**.

### 2. Cloudinary (free image/video hosting)
Sign up at cloudinary.com → copy the **Cloud name** → **Settings → Upload → Add upload preset** →
Signing mode **Unsigned** → Save → copy the preset name.

### 3. GitHub secrets
Repository **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `BRIDGE_URL` | Apps Script Web app URL |
| `BRIDGE_KEY` | BRIDGE_KEY from the Apps Script log |
| `CLOUDINARY_CLOUD` | Cloudinary cloud name |
| `CLOUDINARY_PRESET` | Cloudinary unsigned upload preset |

### 4. Test, then go live
**Actions → Carousel posts → Run workflow** (leave *Test only* ticked). You get a `[NEWS360 TEST – NOT POSTED]` email
with the rendered images. Do the same for **Reel**. When both look right, the schedules post automatically.

## Files
- `kit/` – slide renderer, page logos, follow slides (approved bold style)
- `reel/` – cinematic reel builder + Tamil voice
- `poster/post.py` – picks stories, renders, uploads, posts to Instagram, reports back
- `apps_script/Code.gs` – Sheet/Doc/Gmail/Drive bridge and Instagram token refresh
