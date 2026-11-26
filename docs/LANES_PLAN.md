# Daily lanes: District History / Temple Story + District Jobs

Decision record 26 Nov 2026 (owner: Sivaraj / news360-tn). Status: **built, dry-run only, nothing enabled, nothing scheduled.**

## What exists now
| Part | Where | State |
|---|---|---|
| Shared safety + plumbing | `lanes/lane_common.py`, `lane_factgate.py`, `lane_pages.py` | done, tested |
| History lane | `history/` (`history_daily.py`, `_writer`, `_render`, `_images`, `_voice`, `topics/<page>.json`, `config.json`) | done; topic banks NOT verified |
| Jobs lane | `jobs/` (`jobs_daily.py`, `_engine`, `_render`, `sources/<page>.json`, `config.json`) | done; sources NOT confirmed |
| Workflows | `history.yml`, `jobs.yml`, `history_voice_samples.yml` | manual only, dry run by default, no schedule |
| Tests | `tests/test_lanes_26nov.py` (29) | whole suite: 669 passed |

Both lanes output a **REEL** (1080x1920) per page per day, separate from `post.yml`, `rasipalan.yml`, `goldrate.yml`.
A page is configuration: `lanes/lane_pages.py` (names, handle, tag, district words) + `history/topics/<page>.json` +
`jobs/sources/<page>.json`. Adding a page is data, not code.

## Safety switches (nothing can post by accident)
A real post needs ALL of: workflow input `dry=0` **and** `LANE_POST=1` **and** the page in `enabled_pages` of the lane's
`config.json` **and** (history, first 14 days) the owner's approval **and** once a day per page. `enabled_pages` is `[]` today.
A lane failure is only logged (the run never turns red) and never touches news, rasipalan or gold.

## History lane rules (as decided)
- Topic bank first. A topic is postable only if `verified:true` AND >= 1 `https://` source URL AND >= 3 facts. **No bank topic is verified yet.**
- The writer may use only the topic's facts; every number/year/number-word is checked against the sheet; legends need words like
  "நம்பிக்கை"/"கதை"; sources that disagree are listed in `avoid_regex` (ages/heights) and blocked. A model script that fails the gate is
  dropped for a plain script made straight from the facts.
- Own design (parchment, "நம்ம ஊர் வரலாறு" title card, arched picture, subtitle panel, logo small top-right, no news bar). 6-8 AI scenes with
  slow zoom (free image chain `research_free/imagegen.py`; a drawn placeholder if no model answers, and then no AI disclosure is added).
  Caption: AI-visuals line + source site names. Scene prompts never name a real person.
- Voice: own voice, NOT the news Chirp-3 Charon allowance. `history/config.json "voice"`: none | sarvam | edge | google. **Chosen by the owner after
  listening to `history_voice_samples.yml` output.** Until then: subtitles + music.
- First 14 days: each story is **held** (`history/state/pending_<page>.json`) until approved: run the `history` workflow with input
  `approve = namakkal:<topic id>` (writes `history/state/approvals.json`). (A dashboard tick is a later step.)

## Jobs lane rules (as decided)
Posts only when ALL hold: official source the owner confirmed (`confirmed:true`, official host) - for THIS district - every field (post,
qualification, where to apply, official link, last/event date) present and every date/number found in the fetched official text -
still open - NEW (published / first seen <= 2 days) or UPCOMING (event <= 14 days) - not posted before. No match -> no post.
First run of a page is a baseline (existing notices never count as new). Never old jobs, never other districts, never filler.
Look: animated job board (cards slide in), ~20 s, music only, logo top-right. Caption: facts + official link + fraud warning.
`jobs/state/` keeps `seen_<page>.json`, `keys_<page>.json`, `posted_<page>.json`.

## Owner steps (in order)
1. Review the dry-run reels: run `history` (dry=1) and `jobs` (dry=1) from the Actions tab; download the `*-preview` artifact.
2. Run `history-voice-samples`; listen to `samples/history_voices/*.mp3`; tell Claude the voice to lock.
3. Confirm which official job sources each district may use (`jobs/sources/<page>.json`, set `confirmed:true`).
4. Verify topics: Claude researches each topic's sources; the owner/Claude set `verified:true` only with real source URLs.
5. Confirm slots (suggested history ~13:00 IST, jobs ~09:00 IST) -> add a schedule to the workflows.
6. Add any new secrets himself. Then enable a page: add it to `enabled_pages` and set `LANE_POST=1`.

## Roll-out to the other repos
All seven `*-autopost` repos have the same layout (`goldrate/`, `rasipalan/`, `reel/`, `poster/`, `kit/`), so the lanes are copied unchanged
and each repo runs its own page(s) (`news360`: namakkal + rasipuram; the others one page). Checked 26 Nov: layouts match.
Per district still to do: topic bank (verified) + confirmed job sources. Pages stay disabled until then.
