# Roadmap

Captured 2026-07-30. **All five items below shipped the same day** — kept here as a
record of the decisions behind them. Remaining work is listed at the bottom.

**Season context:** Week 1 kicks off **2026-09-09** (~6 weeks out). Items 1 and 2 are
worthless after the season starts without a scramble, so they're the ones with a real
deadline. Everything else can land whenever.

---

## 1. Move game picks to their own tab

Home becomes takes + news only. Matchups move to a dedicated tab.

- **Size:** small
- **Needs:** new route (`/picks` or `/games`), move `MatchupsWidget` off the dashboard,
  add the nav entry
- **Blocks:** item 2 — the pick UI needs somewhere to live
- **Already have:** `/api/schedule/upcoming`, `/api/schedule/week`, the `game` table

## 2. Pick'em — users pick each game, live leaderboard

Users pick winners; records tracked as results come in; standings panel on the side,
styled like the draft board's existing `RankingsPanel`.

- **Size:** medium-large — the biggest item here
- **Needs:**
  - `game_pick` table: `(user_id, game_id, picked_team, created_at)`, unique per user per game
  - `POST /api/picks`, `GET /api/picks/me`, `GET /api/picks/leaderboard`
  - **Pick locking at kickoff** — otherwise picks can be made after results are known.
    `game.kickoff_et` already exists, so the data is there.
  - Result grading: compare `picked_team` to `game.home_score`/`away_score`. Needs the
    schedule re-ingested regularly during the season to pull in scores (cron or manual).
  - Standings aggregation: wins/losses/pct per user, by week and season-to-date
- **Open questions:**
  - Anonymous picks like draft-board voting allows, or signed-in only? (Voting already
    supports an anon `X-Client-Id` path that could be reused.)
  - Straight-up picks, or against the spread? `game.spread_line` is already ingested.
  - Confidence points?
- **Depends on:** item 1

## 3. Power Rankings — rank teams 1–32

Personal 1–32 ranking, possibly with community voting for a consensus.

- **Size:** medium
- **Needs:** ranking table, drag-to-reorder UI, week-over-week movement arrows
- **⚠ Design note — read before building:** make the schema **generic from day one**:
  `subject_type` (`team` | `player`) + `subject_id`, not a `team_id` column. That makes
  item 4 a configuration change instead of a migration + rewrite. This is the single
  highest-leverage decision in this list.
- **Open questions:** is the consensus averaged across users, or is it your ranking with
  community as a separate column? Weekly snapshots so movement can be shown?

## 4. Positional power rankings (QB first)

Same machinery as item 3, pointed at players instead of teams.

- **Size:** small **if item 3 is built generically**, large if not
- **Needs:** `player_dim` already has everyone; mostly a UI/config layer over item 3
- **Depends on:** item 3's schema decision

## 5. Fantasy Draft board — default to 2026

`/fantasy` currently opens on historical production rankings. It should open on a **2026
draft board**, with year-switching falling back to the existing rankings view.

- **Size:** medium (board only) → large (if the simulator comes too)
- **Data is ready:** `C:\Users\trist\OneDrive\Desktop\draft\players.json` — **773 players**
  with `rk`, `tier`, `name`, `team`, `pos`, `posRank`, `bye`, `sos`, `ecrAdp`, `avgDiff`.
  Classic ECR/ADP cheat sheet. Bijan RB1, Gibbs RB2, Chase WR1.
- **Scope decision needed:** that folder also holds a **complete mock draft simulator**
  (`mock_draft_template.html`) — AI opponents with personalities, bulk simulate, saved
  drafts, roster construction, value index, player-fall stats. Porting that is its own
  project, well beyond "show a 2026 board."
  - **Phase A:** ingest `players.json` → tiered draft board at `/fantasy`, year selector
    switches to existing production rankings. Reasonable.
  - **Phase B:** port the mock draft simulator. Big.
- **Needs:** `fantasy_rank` table (season, rank, tier, player, pos, bye, sos, adp), an
  ingest for `players.json`, and a year-switch that swaps between board and rankings
- **Open question:** does the 2026 list need refreshing as ADP moves through August, or
  is it a one-time import?

---

## Built (2026-07-30)

Order was 1 → 5A → 2 → 3 → 4, as planned.

| Item | Shipped as |
|---|---|
| 1 | `/picks` tab; matchups off the dashboard |
| 5A | `fantasy_rank` + `0010`, `scripts/ingest_fantasy_ranks.py`, `/fantasy` opens on the 2026 board |
| 2 | `game_pick` + `0011`, `app/api_picks.py`, kickoff locking, weekly/season standings |
| 3 | `power_ranking`/`power_ranking_entry` + `0012`, `app/api_power.py`, `/power` |
| 4 | Nothing new — the generic schema meant QB rankings were a query-string change |

**Decisions made along the way**, so they don't get re-litigated:
- Picks are **anonymous-allowed** (X-Client-Id, same as draft voting), **straight up**,
  with **both weekly and season** standings.
- Power rankings are **editorial-first**: `is_official` marks the site's list, every
  other ballot is a user's, and the consensus column is the mean of those. This was
  assumed, not confirmed — the alternative is a pure community average.
- The generic `subject_type` + `subject_group` schema paid off exactly as hoped:
  item 4 needed zero new code, and RB/WR/TE rankings are already live for free.

## Still open

- **Phase B of item 5** — porting the mock draft simulator from
  `C:\Users\trist\OneDrive\Desktop\draft\mock_draft_template.html`. Still its own project.
- **In-season score refresh.** Pick'em grading reads `game.home_score`, which only
  updates when `scripts/ingest_schedules.py` re-runs. Needs a weekly cron before Sept 9.
- **Browser verification.** Sortable columns, pick buttons, and ballot drag-and-drop are
  proven at the API layer but were never clicked in a real browser.
- **Fantasy board refresh** — is the 2026 list a one-time import, or does it need
  re-pulling as ADP moves through August?
- **`ecrAdp` refresh + rookie linking.** 105 of 742 board players don't link to
  `player_dim` because they're 2026 rookies who aren't in `players_NFL.csv` yet.
