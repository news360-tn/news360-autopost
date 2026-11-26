# Team dashboard - setup (owner, once)

Nothing here changes the posting workflows. The dashboard only READS.

## 1. The store + login (Google Apps Script, your Google account)
1. script.google.com -> **New project** (name: News360 Dashboard).
2. Replace the code in `Code.gs` with `dashboard/Code.gs`. Add a file: **+ -> HTML**, name it exactly `Index`, paste `dashboard/Index.html`.
3. **Project Settings (gear) -> Script properties -> Add**:
   - `DASH_USER` and `DASH_PASS` (one shared login) **or** `DASH_USERS` = `siva:password1,team1:password2` (a login per person)
   - `DASH_WRITE_KEY` = about 40 random characters (the collector uses it)
4. **Deploy -> New deployment -> Web app**: Execute as **Me**, Who has access **Anyone**. Authorize when asked. Copy the web-app link.

## 2. GitHub secrets (repository `news360-autopost` only): Settings -> Secrets and variables -> Actions
- `DASH_URL` = the web-app link
- `DASH_WRITE_KEY` = the same value as in step 1
- `YT_API_KEY` = a YouTube Data API key (console.cloud.google.com -> any project -> APIs & Services -> Library -> YouTube Data API v3 -> Enable
  -> Credentials -> Create credentials -> API key -> restrict it to "YouTube Data API v3"). Without it the YouTube numbers stay empty.

## 3. First data
Actions tab -> **dashboard** -> Run workflow. Open the web-app link, sign in, press Refresh. After that it updates every 3 hours.

Username / password: only in the Script properties and your own private note - never in chat, a page or a repository.
Change a password: edit the property. Lock: 5 wrong tries lock that username for 15 minutes.
