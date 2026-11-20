# Promo Hub setup: promotion ads + YouTube details e-mail (owner, 20 Nov)

One Apps Script handles both features for all 8 pages. Until steps 1 to 5 are done, nothing changes on any page: no ad, and the
POSTED e-mails keep coming as they do today.

Done on 20 Nov with clasp: the "360 Promo Hub" project was created and deployed, setup ran through its one-time
`<Web app URL>?setup=1` page, and the 7 bridges were redeployed with the new Code.gs. The steps below are for setting it up again.

## 1. Create the hub (about 5 minutes)
1. Open script.google.com, then **New project**. Name it `360 Promo Hub`.
2. Delete the sample code and paste all of `apps_script_hub/PromoHub.gs`. Click **Save**.
3. Pick `setup` in the function box and click **Run**. Allow the permissions (Advanced, then "Go to 360 Promo Hub").
4. Open **Execution log**. Copy the 4 lines: FORM LINK, EDIT FORM, SHEET and KEY.

## 2. Deploy it as a web app
**Deploy**, then **New deployment**, then the gear icon, then **Web app**:
- Execute as: **Me**
- Who has access: **Anyone**

Click **Deploy** and copy the **Web app URL**.

## 3. GitHub secret (all 7 repos)
Each repo: **Settings**, then **Secrets and variables**, then **Actions**, then **New repository secret**:
- `PROMO_KEY` = the KEY (Apps Script project, Project Settings, Script properties)

The hub's web address is already in the workflows. A `PROMO_URL` secret is needed only if the hub moves to a new address.

Repos: news360-autopost, coimbatore360, salem360, erode360, karur360, tirupur360, trichy360.

## 4. Add the logo / picture question to the form
Google does not let a script add this question, so add it by hand:
1. Open the EDIT FORM link.
2. Click **+**, then **File upload**. Title: `Logo / picture`.
3. Allow only **Image**, 1 file, 10 MB.

People who upload a file must be signed in to Google.

## 5. Stop the per-reel POSTED e-mails
Do this for each page's own bridge Apps Script (the one that already runs the Sheet):
1. Paste the new `apps_script/Code.gs` from that repo.
2. **Deploy**, then **Manage deployments**, then the pencil icon. Version: **New version**. Click **Deploy**.

The URL stays the same. After this, the twice-a-day YouTube e-mail lists the posted reels. Problem e-mails (NOT POSTED etc.)
still come instantly.

---

## How promotions work
1. Fill in the FORM LINK: pages, brand, title (max 40 letters), message (max 80), start and end date, reels a day, picture.
2. Within about 30 minutes you get **[360 PROMO SAMPLE] PR-n**. It is the page's latest real news reel with the ad on it.
3. Reply with one of these:
   - `APPROVED`: the ad starts on the start date.
   - `REJECTED` and your changes (for example: `REJECTED change the title to Deepavali Mega Sale`): a new sample follows.
   - `STOP`: the request is cancelled.
4. The ad appears only:
   - on the chosen pages, between the start and end date
   - on at most N news reels a day per page
   - at the bottom of the reel, during the news

   The footer logo is hidden while the ad shows. The FOLLOW end card never changes. The caption gets "🤝 Sponsored: brand".
5. To stop an ad early, open the SHEET and set its Status to `stopped`.

## YouTube details e-mail
- One e-mail per page, at 12:05 and 21:05, with up to 10 news reels a day per page (gold rate and rasipalan are left out).
- Most useful first: power cuts, then alerts, then camps and jobs, then the newest.
- Each reel has a **Download video** button (Cloudinary), plus a title, description (📰 Source, 📅 date), tags and a suggested
  upload time.
- Download within 1 day. The video is kept 2 days.
