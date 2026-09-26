# nflverse weekly data audit

Snapshot captured at **2026-09-26T22:26:05.040369+00:00**. Seasons 2022–2026; regular season only.


## Findings

- 75 regular-season player rows have missing player IDs. They remain in all row counts; inspect their nonempty fields in `missing_identity_rows` in `audit.json` before joining to player data.
- Other missing ID/team fields: 0; duplicate key groups: 0. Keys are player-season-week or team-season-week; null key fields are counted separately.
- 2026 coverage: week 1: 16/16 scheduled games; week 2: 16/16 scheduled games; week 3: 1/16 scheduled games. An available week is not necessarily a complete week.

Missing-ID rows can contain nonzero statistics and are not safe to silently discard or assign to a player. The saved snapshot provides the evidence; the audit does not infer their upstream cause.

Rerun from the repository root (Python 3.10+, standard library only):

```powershell
python scripts/audit_nflverse.py --refresh
```

Omit `--refresh` to replay the checksum-verified cached inputs offline. Refresh replaces the snapshot; use `--cache-dir data/audit_cache/<snapshot-name>` to preserve separate captures. `audit.json` provides all counts and discrepancy keys; `sources.json` records source provenance.

| Dataset | Season | REG weeks | Rows | Missing player IDs | Missing teams | Duplicate groups / excess rows |
|---|---:|---|---:|---:|---:|---:|
| stats_player | 2022 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 17981 | 18 | 0 | 0 / 0 |
| stats_player | 2023 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 17806 | 18 | 0 | 0 / 0 |
| stats_player | 2024 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 18130 | 18 | 0 | 0 / 0 |
| stats_player | 2025 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 18540 | 18 | 0 | 0 / 0 |
| stats_player | 2026 | 1, 2, 3 | 2294 | 3 | 0 | 0 / 0 |
| stats_team | 2022 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 542 | N/A | 0 | 0 / 0 |
| stats_team | 2023 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 544 | N/A | 0 | 0 / 0 |
| stats_team | 2024 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 544 | N/A | 0 | 0 / 0 |
| stats_team | 2025 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 544 | N/A | 0 | 0 / 0 |
| stats_team | 2026 | 1, 2, 3 | 66 | N/A | 0 | 0 / 0 |

## Player rows by position

| Position | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|
| (missing) | 18 | 18 | 18 | 18 | 3 |
| C | 144 | 145 | 156 | 123 | 24 |
| CB | 1844 | 1862 | 2009 | 1987 | 242 |
| DB | 628 | 521 | 387 | 409 | 36 |
| DE | 1541 | 1545 | 1492 | 1408 | 169 |
| DL | 28 | 16 | 28 | 52 | 6 |
| DT | 1425 | 1469 | 1551 | 1526 | 208 |
| FB | 110 | 96 | 71 | 71 | 8 |
| FS | 331 | 270 | 256 | 141 | 13 |
| G | 278 | 320 | 295 | 255 | 32 |
| ILB | 206 | 131 | 89 | 53 | 6 |
| K | 545 | 543 | 543 | 543 | 66 |
| LB | 2145 | 2272 | 2478 | 2939 | 367 |
| LS | 87 | 77 | 64 | 69 | 11 |
| MLB | 207 | 153 | 149 | 77 | 8 |
| NT | 123 | 111 | 63 | 79 | 6 |
| OL | 0 | 4 | 10 | 15 | 1 |
| OLB | 407 | 278 | 239 | 212 | 16 |
| OT | 438 | 406 | 515 | 474 | 71 |
| P | 537 | 539 | 534 | 531 | 65 |
| QB | 633 | 663 | 664 | 664 | 78 |
| RB | 1581 | 1474 | 1536 | 1575 | 189 |
| S | 255 | 169 | 103 | 66 | 8 |
| SAF | 876 | 1060 | 1216 | 1455 | 190 |
| TE | 1207 | 1188 | 1223 | 1287 | 158 |
| WR | 2387 | 2476 | 2441 | 2511 | 313 |

Team rows have no position dimension. Counts represent stat rows, not rosters or participation.

## Schedule reconciliation

Completed means both schedule scores are populated. Team-season-week keys use the alias map in `audit.json`. A game is fully observed only when both teams occur; player rows establish team coverage, not roster completeness. Unplayed/cancelled games with missing scores are not missing completed games. Sources are fetched sequentially, so brief update lag is possible.

| Dataset | Season | Completed games | Observed, both teams | Missing completed team-weeks | Unexpected team-weeks | Opponent/game-ID mismatches | Unobserved unfinished team-weeks |
|---|---:|---:|---:|---:|---:|---:|---:|
| stats_player | 2022 | 271 | 271 | 0 | 0 | 0 | 0 |
| stats_player | 2023 | 272 | 272 | 0 | 0 | 0 | 0 |
| stats_player | 2024 | 272 | 272 | 0 | 0 | 0 | 0 |
| stats_player | 2025 | 272 | 272 | 0 | 0 | 0 | 0 |
| stats_player | 2026 | 33 | 33 | 0 | 0 | 0 | 478 |
| stats_team | 2022 | 271 | 271 | 0 | 0 | 0 | 0 |
| stats_team | 2023 | 272 | 272 | 0 | 0 | 0 | 0 |
| stats_team | 2024 | 272 | 272 | 0 | 0 | 0 | 0 |
| stats_team | 2025 | 272 | 272 | 0 | 0 | 0 | 0 |
| stats_team | 2026 | 33 | 33 | 0 | 0 | 0 | 478 |

Weekly scheduled/completed/observed game counts, observed unfinished team-weeks, and discrepancy keys are in `audit.json`.

## Kicking and defense

- Kicking columns (union across player/team seasons): `fg_att`, `fg_blocked`, `fg_blocked_distance`, `fg_blocked_list`, `fg_long`, `fg_made`, `fg_made_0_19`, `fg_made_20_29`, `fg_made_30_39`, `fg_made_40_49`, `fg_made_50_59`, `fg_made_60_`, `fg_made_distance`, `fg_made_list`, `fg_missed`, `fg_missed_0_19`, `fg_missed_20_29`, `fg_missed_30_39`, `fg_missed_40_49`, `fg_missed_50_59`, `fg_missed_60_`, `fg_missed_distance`, `fg_missed_list`, `fg_pct`, `gwfg_att`, `gwfg_blocked`, `gwfg_distance`, `gwfg_made`, `gwfg_missed`, `pat_att`, `pat_blocked`, `pat_made`, `pat_missed`, `pat_pct`, `pt_att`, `pt_blocked`, `pt_downed`, `pt_fair_caught`, `pt_inside_20`, `pt_long`, `pt_net_yards`, `pt_out_of_bounds`, `pt_return_tds`, `pt_return_yards`, `pt_returned`, `pt_touchback`, `pt_yards`.
- Defense columns (union across player/team seasons): `def_2pt_atts`, `def_2pt_made`, `def_fg_blocks`, `def_fumbles`, `def_fumbles_forced`, `def_interception_yards`, `def_interceptions`, `def_pass_defended`, `def_pat_blocks`, `def_punt_blocks`, `def_qb_hits`, `def_sack_yards`, `def_sacks`, `def_safeties`, `def_tackle_assists`, `def_tackles_for_loss`, `def_tackles_for_loss_yards`, `def_tackles_solo`, `def_tackles_with_assist`, `def_tds`, `fumble_recovery_opp`, `fumble_recovery_tds`, `fumble_recovery_yards_opp`.
- Returns columns (union across player/team seasons): `kickoff_return_yards`, `kickoff_returns`, `pt_return_tds`, `pt_return_yards`, `pt_returned`, `punt_return_yards`, `punt_returns`, `special_teams_tds`.

Inventories select columns by name, not fantasy scoring rules. Per-season non-null and nonzero counts in `audit.json` distinguish column presence from populated data. Missing columns are not treated as zero. Defensive and return totals require explicit scoring rules before calculating fantasy D/ST scores.

## Source update times

| Asset | Status | Asset updated (UTC) | Retrieved (UTC) |
|---|---|---|---|
| [stats_player_week_2022.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2022.csv) | available | 2026-08-13T16:48:13Z | 2026-09-26T22:26:07.206830+00:00 |
| [stats_player_week_2023.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2023.csv) | available | 2026-08-13T16:48:37Z | 2026-09-26T22:26:08.089413+00:00 |
| [stats_player_week_2024.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2024.csv) | available | 2026-08-13T16:49:11Z | 2026-09-26T22:26:09.229250+00:00 |
| [stats_player_week_2025.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2025.csv) | available | 2026-08-13T16:51:22Z | 2026-09-26T22:26:10.023012+00:00 |
| [stats_player_week_2026.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv) | available | 2026-09-26T13:47:00Z | 2026-09-26T22:26:10.569203+00:00 |
| [stats_team_week_2022.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2022.csv) | available | 2026-08-13T16:48:16Z | 2026-09-26T22:26:11.766472+00:00 |
| [stats_team_week_2023.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2023.csv) | available | 2026-08-13T16:48:38Z | 2026-09-26T22:26:12.264734+00:00 |
| [stats_team_week_2024.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2024.csv) | available | 2026-08-13T16:49:13Z | 2026-09-26T22:26:12.760736+00:00 |
| [stats_team_week_2025.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2025.csv) | available | 2026-08-13T16:51:24Z | 2026-09-26T22:26:13.254145+00:00 |
| [stats_team_week_2026.csv](https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2026.csv) | available | 2026-09-26T13:47:02Z | 2026-09-26T22:26:13.716241+00:00 |
| [games.csv](https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv) | available | 2026-09-26T22:16:19Z | 2026-09-26T22:26:14.803846+00:00 |

Asset timestamps describe publication, not the latest game or finality of statistics. Release creation times and HTTP Last-Modified values (when supplied) are retained separately in `sources.json`.

References: [player releases](https://github.com/nflverse/nflverse-data/releases/tag/stats_player), [team releases](https://github.com/nflverse/nflverse-data/releases/tag/stats_team), [schedule release](https://github.com/nflverse/nflverse-data/releases/tag/schedules), [player dictionary](https://nflreadr.nflverse.com/articles/dictionary_player_stats.html), [team dictionary](https://nflreadr.nflverse.com/articles/dictionary_team_stats.html).
