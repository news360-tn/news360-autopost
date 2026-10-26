# Manual story → e-mail (use when automatic collecting is PAUSED)

## 1. Pause / start automatic collecting
GitHub → repository **news360-autopost** → **Actions** → **collect-switch** → **Run workflow** → choose
`pause` (automatic collecting/writing stops, posting continues) or `start` (automatic collecting again). Same page on the phone.

## 2. Make the news with the other Claude account
Paste the prompt below into that Claude (with web search ON), add the news text / link at the end.
Claude gives ONE JSON. Make the images (ChatGPT, 4 images, 9:16, one per slide + 1).

## 3. Send ONE e-mail to nammarasipuram2805@gmail.com (from your allowed address)
- Subject: `NEWS360 STORY` (anything after it is fine)
- Body: paste the JSON (or attach it as story.json)
- Attach the images (png/jpg) or one zip. One story per e-mail. (Several stories in one e-mail: `{"stories":[...]}` and name the images S1_1.png, S1_2.png, S2_1.png …)
- Within ~5 minutes you get **[NEWS360 STORY RECEIVED]**: ADDED RN-xx, or the exact problems / DUPLICATE warning. Then it is posted automatically
  (Instagram recent-captions duplicate check + source fact check run first; an already posted news is never posted again).
- The sender must be listed in Script property `ALLOWED_SENDERS` (your friend's/other mail) or be the owner address.

## Prompt for the other Claude
```
You write Tamil local-news posts for the Instagram pages "Namakkal 360" / "Rasipuram 360" (Namakkal district, Tamil Nadu).
Use ONLY facts from the news below (search the web to confirm). Never invent a name, number, place or cause. If a fact is unclear, leave it out.
Write ONE JSON object only (no explanation) with exactly these keys:
{
 "tamil_headline": "...",            // clear Tamil headline, full place names (பரமத்தி வேலூர், குமாரபாளையம் - never short forms)
 "english_headline": "...",
 "category": "...",                  // Tamil, e.g. மின் தடை, விபத்து, நிர்வாகம்
 "location": "place, taluk, Namakkal district",
 "importance": "High|Medium|Low",
 "post_to": "Rasipuram 360 (collab: Namakkal 360)",   // Rasipuram news (Rasipuram logo). District-wide news (Collector / government / jobs): "Namakkal 360 (collab: Rasipuram 360)". Other district news: "Namakkal 360"
 "source": "https://link-of-the-news-article",          // used only for the fact check, never shown
 "slides_spec": {"v":3,"cat":"...","loc":"short place","hl1":"max 40 chars","hl2":"max 28 chars",
   "slides":[{"title":"max 18 chars","lines":["2-3 short lines, each max 60 chars; <b>bold</b> allowed for key facts"]}]},   // 3 or 4 slides: who/what/when/where/why/how
 "reel_script": "...",               // 85-120 Tamil words, 7-9 sentences with every detail, numbers, dates, times and amounts as DIGITS (10.30 மணி, ரூ.5.70, 65 வயது), NO English letters (TNPSC, SI, DSP are read out by the system), strong hook in the first sentence (no greeting), short sentences, plain words, covers who-what-when-where-why-how, ends with exactly: மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.
 "caption": "..."                    // emoji heading, 3-5 short lines with facts, then a line 📍 place | date, then 5 hashtags, last line: உள்ளூர் செய்திகளுக்கு Follow செய்யுங்கள் 🙏
}
Rules: no newspaper/TV/website names or links in any text field except "source"; no "comment below" lines; readable plain Tamil.
NEWS:
<paste the news text or link here>
```


---
# READY REEL (video + caption already made) - post as it is
E-mail to nammarasipuram2805@gmail.com, subject `NEWS360 REEL`, attach ONE zip containing ONE `.md` (the caption) and ONE video (`.mp4`).
Optional first line of the .md: `PAGE: namakkal` (default) | `PAGE: rasipuram` | `PAGE: both`.
Within ~5 minutes: **[NEWS360 REEL RECEIVED]** ADDED RN-xx (or DUPLICATE / the problem). Just before posting, the page's recent Instagram captions
are read: if the same news is already there it is NOT posted (the Sheet row says so). Otherwise the video is posted exactly as it is, with your caption
(standard rule: max 5 hashtags, #Namakkal360 / #Rasipuram360 added, AI line).
