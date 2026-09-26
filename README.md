# FantasyFootball

Audit nflverse's maintained weekly `stats_player` and `stats_team` releases for
2022–2026 regular seasons from the repository root (Python 3.10+, standard library only):

```powershell
python scripts/audit_nflverse.py --refresh
```

Read [the audit report](reports/nflverse_audit/report.md). Detailed results and
source provenance are saved beside it as `audit.json` and `sources.json`.
The audit covers weeks, position counts, missing identifiers/teams, duplicate
keys, kicking/defensive column coverage, and schedule reconciliation.

Raw CSVs and release metadata are cached in gitignored `data/audit_cache/`.
Omit `--refresh` to replay that snapshot offline with SHA-256 verification.
Preserve this directory to reproduce the same inputs; `--refresh` replaces it.
Use `--cache-dir data/audit_cache/<snapshot-name>` for a separate snapshot,
and `--output-dir <path>` for separate results. Network or schema failures exit
nonzero; absent season assets are explicitly reported instead of counted as zero.
The initial run downloads data if no snapshot exists. Audit findings themselves
are reported without a failing exit status.

Run audit logic checks with `python -m unittest discover -s tests -v`.
