# News360 Backend - setup (owner, once)

Website: **https://news360-backend.pages.dev** (Cloudflare Pages). Home: / - each district has its own link: /namakkal /coimbatore /erode /karur /salem /tirupur /trichy - plus /overview /instagram /facebook /youtube /posts. Nothing here changes the posting workflows; the site only READS.

How it fits: website (Cloudflare Pages, `pages/_worker.js`) -> private store + login (Google Apps Script, `Code.gs`) <- collector
(GitHub Actions `dashboard.yml`, every 3 hours, read-only). The Apps Script link is never shown on the website.

## 1. Store + login (Google Apps Script) - already created
1. script.google.com -> News360 Dashboard -> `Code.gs`: replace all with `dashboard/Code.gs` from GitHub -> Save.
   (Optional: also replace `Index.html` with `dashboard/Index.html`.)
2. Deploy -> Manage deployments -> pencil -> Version: **New version** -> Deploy. The Web app link stays the same.
3. Script properties (already set): `DASH_USER` + `DASH_PASS` or `DASH_USERS`, and `DASH_WRITE_KEY`.

## 2. Website (Cloudflare Pages)
1. dash.cloudflare.com -> Workers & Pages -> Create -> Pages -> **Upload assets** (Direct Upload).
2. Project name: **news360-backend** -> Create project.
3. Upload `dashboard/pages/news360-backend.zip` (download: https://github.com/news360-tn/news360-autopost/raw/main/dashboard/pages/news360-backend.zip) -> Deploy site.
4. Project -> Settings -> Variables and secrets -> Add -> Type **Secret**, name `DASH_URL`, value = the Apps Script Web app link
   (`https://script.google.com/macros/s/.../exec`, no `/u/1/`) -> Save.
5. Deployments -> Create deployment -> upload the same zip again (a secret applies from the next deployment).
6. Open https://news360-backend.pages.dev and sign in.

## 3. GitHub secrets (repository `news360-autopost`) - already added
`DASH_URL`, `DASH_WRITE_KEY`, `YT_API_KEY`. Actions -> dashboard -> Run workflow sends the first numbers.

## Updating the website later
After a change to `dashboard/Index.html`: `python dashboard/build_worker.py`, commit, then in Cloudflare upload the new zip
(Deployments -> Create deployment).

Username / password: only in the Apps Script properties and your own note - never in chat, a page or a repository.
