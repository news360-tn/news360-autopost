# News360 – Complete Guide (Namakkal 360 & Rasipuram 360)

Owner: Sivaraj. Bridge Gmail (receives your e-mails and sends replies): **nammarasipuram2805@gmail.com**
Sheet (all stories and status): https://docs.google.com/spreadsheets/d/10lKyQo4rPkSyGP6kj3zvVBpm17r5fXzTa6vwdnu3y00/edit

---

## 0. Two ways to get a story onto Instagram

| Way | Who makes it | What you send by e-mail | Speed |
|---|---|---|---|
| **A. Automatic collecting** (runs every 4 hours) | The system: free AI models first, Claude only when free models fail | Nothing. You get one e-mail `[NEWS360 IMAGES NEEDED]` when there is news; you make the images and reply | Images needed from you |
| **B. Your own story** (you or a friend, when you want) | Claude (web search) → you make images in ChatGPT → you e-mail | E-mail `NEWS360 STORY`: JSON + images | Posted within ~30 min of your e-mail |
| **C. Ready reel** (you already made the video and caption) | You | E-mail `NEWS360 REEL`: zip with one `.md` (caption) + one video `.mp4` | Posted as it is, within ~30 min |

Posting itself is always automatic (every 5 minutes it looks for ready stories). Every post passes the Instagram duplicate check first.

---

## 1. Pause and start the automatic collecting

Pausing only stops the automatic collecting and writing (way A). Posting of stories you send (B and C) and of already queued stories continues.

1. Open the repository on GitHub: **the news360-autopost repository** → tab **Actions**.
2. Left side: **collect-switch**.
3. Button **Run workflow** → choose:
   - `pause` → automatic collecting stops (no new e-mail `IMAGES NEEDED` until you start again).
   - `start` → automatic collecting starts again (every 4 hours).
4. The summary of the run says: "Automatic collecting: ON" or "PAUSED".
5. Phone: same page in the GitHub app or mobile browser.

Full stop (posting too): repository **Settings → Secrets and variables → Actions → Variables** → set `PAUSED` = `true`. Remove it or set `false` to resume posting.

---

## 2. Way A – automatic collecting (when ON)

- Every 4 hours the collector reads all Namakkal-district news (Rasipuram first). It keeps only news that names a place in the district and is today's/recent.
- Free AI models write the story. A model that is **slow (over 90 s)**, gives **unreadable answers**, or is **not allowed/over quota** is skipped automatically for 30 minutes to 6 hours, then checked again. Claude (paid key) is used only when no free model can produce a good result.
- A story is never posted if: its date has passed (power cut of yesterday, job fair over), the same news is already posted, or the source check fails.
- One e-mail `[NEWS360 IMAGES NEEDED] <batch>` lists the new stories with ChatGPT prompts (Prompt 2 below).
- Reply to that e-mail with the images (zip or attachments). Name the files `RN-xx_1.png` … (the e-mail tells you the names). `SKIP RN-xx` in the reply skips a story.
- If stories are still waiting for images from an earlier round, they are listed again in the same e-mail.

Daily cap: about 40 posts per page per 24 hours (Instagram's limit is 50). The last 10 slots are kept for High-importance news. A story waiting for the cap is posted later, not lost.

---

## 3. PROMPT 1 – collect today's news (give to Claude with web search ON)

Use this when you collect news yourself (way B). Run it once or twice a day.

```
You write Tamil local-news posts for the Instagram pages "Namakkal 360" and "Rasipuram 360" (Namakkal district, Tamil Nadu).

TASK
1. Search the web for TODAY'S and the last 24 hours' news of ALL Namakkal district places: Namakkal town, Rasipuram, Tiruchengode, Paramathi Velur, Kumarapalayam, Mohanur, Namagiripettai, Velur, Sendamangalam, Kolli Hills, Pallipalayam, and every village/taluk of the district. Check at least 10 Tamil news sites and the district news pages.
2. Do NOT miss anything important: accidents, power cuts, government orders, police, health, school/college, weather damage, prices, job fairs, deaths of notable people, festivals, road closures. Rasipuram news first, then the rest of the district.
3. Skip: news outside the district, old news (before the last 24 hours), national/world news, pure opinion, advertisements.
4. Use ONLY facts stated in the articles you read. Never invent a name, number, place, date, cause or quote. If a fact is unclear, leave it out.
5. Give every story a real article link.

WRITE
- Full place names always: பரமத்தி வேலூர் (not ப.வேலூர்), குமாரபாளையம் (not கு.பாளையம்), ராசிபுரம், திருச்செங்கோடு.
- Role names in full when spoken: ஆர்.டி.ஓ. → வருவாய் கோட்டாட்சியர், எஸ்.பி. → காவல் கண்காணிப்பாளர்.
- Plain, readable Tamil. Short sentences. No English words in the reel script.

OUTPUT: ONE JSON object only (no explanation):
{
 "stories": [
  {
   "tamil_headline": "clear Tamil headline, full place names",
   "english_headline": "short English headline",
   "category": "Tamil category, e.g. மின் தடை / விபத்து / நிர்வாகம் / மருத்துவம்",
   "location": "place, taluk, Namakkal district",
   "importance": "High | Medium | Low",
   "post_to": "Namakkal 360 + Rasipuram 360  (or only Namakkal 360 when not about Rasipuram)",
   "source": "https://the-article-link",
   "published": "date of the news, e.g. 24 Oct 2026",
   "slides_spec": {
     "v": 3, "cat": "same as category", "loc": "short place name",
     "hl1": "headline line 1, max 40 characters",
     "hl2": "headline line 2, max 28 characters",
     "slides": [ {"title": "max 18 characters", "lines": ["2 or 3 short lines, each max 60 characters"]} ]
   },
   "reel_script": "38-55 Tamil words. NO digits and NO English letters (write numbers in Tamil words). Strong hook in the first sentence, no greeting. Short sentences. Cover who, what, when, where, why, how. Must end with exactly: மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.",
   "caption": "emoji heading line, then 3-5 short fact lines, then a line: 📍 place | date, then exactly 5 hashtags on one line, last line: உள்ளூர் செய்திகளுக்கு Follow செய்யுங்கள் 🙏",
   "prompts": ["image prompt for slide 1 (see Prompt 2 rules)", "...one per slide plus one extra for the opening scene"]
  }
 ]
}

RULES
- slides: 3 or 4. prompts: (number of slides + 1) items.
- No newspaper, TV or website names and no links in any field except "source".
- No "comment below" / "கமெண்டில்" lines.
- If there is no new important news in the district, return: {"stories": []}
```

## 4. PROMPT 2 – make the images (ChatGPT, one prompt at a time)

Take the `prompts` list from the JSON of Prompt 1. Paste the rules below first, then each prompt.

```
READ THIS FIRST - STRICT RULES (follow every one):
1. Make EACH image as its OWN separate single image: one prompt = one image = one file. Never combine prompts.
2. NEVER make a collage, grid, storyboard, multi-panel, split-screen or several scenes in one picture. Every image shows exactly ONE scene filling the whole frame.
3. Every image is ONE continuous photograph from ONE camera angle: no panels, no strips, no borders, no inset pictures.
4. Format: full-frame tall vertical 9:16 portrait, 1080x1920 or larger, maximum clarity, tack-sharp, photorealistic, no blur, no painterly or over-smooth AI look.
5. NO text, letters, numbers, logos, watermarks, news channel names or captions on the image.
6. Do NOT crop, resize, compress or edit the images afterwards. Use the original files.
7. Name each file exactly as given (for example S1_1.png, S1_2.png, S1_3.png, S1_4.png).
8. Do not skip any image and do not change the prompts.
9. At the end put ALL images of the story in ONE zip (stored as they are, no re-compression, no folders). The zip must be smaller than 24 MB.

Prompts:
<paste the prompts here, one after another, separated by ---->
```

Images per story: 4 for a 3-slide story (3 slides + 1 opening scene), 5 for a 4-slide story. Fewer than 3 images is refused.

---

## 5. Way B – send your own story (e-mail with the images)

1. Get the JSON (Prompt 1) and make the images (Prompt 2).
2. Send **one e-mail** to `nammarasipuram2805@gmail.com`
   - **Subject:** `NEWS360 STORY` (any words after it are fine)
   - **Body:** the JSON (paste it as text). For several stories use `{"stories":[ ... ]}`.
   - **Attachments:** the images (png/jpg) or one zip. Several stories in one e-mail: name the images `S1_1.png`, `S1_2.png`, `S2_1.png` … (S1 = first story in the JSON).
   - **One story per e-mail** is the safest.
3. Within about 5 minutes you get `[NEWS360 STORY RECEIVED]`:
   - `ADDED RN-xx` → it will be built and posted automatically (reel and voice are made by the system).
   - `NOT ADDED` → the exact problem is written (too long headline, digits in reel script, duplicate of RN-xx, too few images). Fix and send again.
4. Post checks before publishing: Instagram duplicate check (same news already on the page? → not posted), source fact check (if `source` has a link), Tamil text check, reel check (1080x1920, 10-45 s, voice present).

Sender permission: your own address is always allowed. Another person's address must be in the Apps Script property `ALLOWED_SENDERS` (comma-separated).

---

## 6. Way C – ready reel (video + caption made by you)

Use this when you already have the reel video and the caption. Nothing is rebuilt; the video is posted exactly as it is.

1. Make a folder with exactly these two files:
   - `caption.md` – the caption text. First line may be a setting:
     ```
     PAGE: namakkal
     ```
     (`PAGE: namakkal` = default, `PAGE: rasipuram`, or `PAGE: both`.)
     Then the caption. Use max 5 hashtags. (`#Namakkal360` / `#Rasipuram360` and the AI line are added automatically.)
   - `reel.mp4` – the video: **1080 x 1920 (9:16), 10 to 45 seconds, with voice**, not silent, not clipped (too loud).
2. Put both files in ONE zip, e.g. `RN_reel_2026-10-24.zip`. Only one `.md` and one video inside.
3. Check the video yourself before sending (voice clear, Tamil words correct, the place and time are right, the end line is there).
4. Send **one e-mail** to `nammarasipuram2805@gmail.com`
   - **Subject:** `NEWS360 REEL`
   - **Attachment:** the zip (or the two files)
   - Body: nothing needed.
5. Within about 5 minutes you get `[NEWS360 REEL RECEIVED]`:
   - `ADDED RN-xx` → the reel is queued and posted automatically.
   - `DUPLICATE of RN-xx` → the same news is already in the Sheet; not posted.
   - Other messages → the exact problem (for example the zip has two videos).
6. Just before posting, the system reads the page's recent Instagram captions. If the same news is already on the page, it is **not posted** (the Sheet row shows it).

Large video (over 25 MB): put the zip in Google Drive, share it, and paste the link in the e-mail body. The system reads Drive links.

---

## 7. Reel template and voice (how the reel is made in way A/B)

- Size 1080 x 1920, 9:16. Each image slides with a slow camera move, the headline and key facts appear as Tamil text on the picture, the logo and "AI" tag at the corner.
- Voice: the existing Tamil voice model (Indic-TTS). The voice is not changed. The reel script is read exactly; numbers are spoken in Tamil words.
- Length 20 to 45 seconds, ending with the fixed follow line.
- The system checks every built reel: size, duration, voice present, not silent, not clipped, and that the voice can pronounce every written word.
- Ready reels (way C) get the technical checks (size, duration, voice present, not silent/clipped). The words are checked by you when you watch the video before sending.

---

## 8. Caption format (all ways)

```
⚡ Emoji heading line

Fact line 1.
Fact line 2.
📍 Place | date
#Namakkal360 #tag2 #tag3 #tag4
```
Max 5 hashtags. No "comment below" lines. The system adds the AI line and the page hashtag.

---

## 9. Daily routine (what you do)

1. Morning or afternoon: collect the news (Prompt 1) – or wait for way A's e-mail.
2. For each story: make the images (Prompt 2) → e-mail `NEWS360 STORY`, or make the reel yourself and e-mail `NEWS360 REEL` (way C).
3. Check the `[RECEIVED]` replies for `NOT ADDED` / `DUPLICATE`.
4. Nothing else: posting runs every 5 minutes.
5. Check the Sheet column `post_status` once a day: `Posted`, `Queued`, `Awaiting images`, `Skipped`.

---

## 10. Quick troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| No reply e-mail after 15 min | Apps Script is not checking | Owner: check Apps Script triggers (`processReplies` every 5 min) |
| `NOT ADDED … images` | too few images | send all images again in one e-mail |
| `DUPLICATE of RN-xx` | same news already in the Sheet | nothing; it will not be posted twice |
| `Checks failed` in Sheet notes | a text or fact check failed | the story is not posted; fix or drop it |
| `LIMIT` in the log | Instagram 24-hour post limit reached | story waits; posted automatically later |
| Collector sends no e-mail for a long time | no new news, or automatic collecting is PAUSED | see section 1 |

---

## 11. Model and cost rules (automatic collecting)

- Free models first, in order of how well they answer. A slow or poor model is skipped for a while and checked again.
- Claude (paid key) is used only when no free model can produce a good result, with a per-run limit.
- No model switch is needed by you; you will see `fail`, `slow` or `poor answer` lines in the collector log only if you open it.
