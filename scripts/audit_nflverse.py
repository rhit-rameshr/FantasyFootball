"""Reproducible audit of maintained nflverse weekly releases; Python 3.10+."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SEASONS = range(2022, 2027)
API = 'https://api.github.com/repos/nflverse/nflverse-data/releases/tags/'
ALIASES = {'LA': 'LAR', 'JAC': 'JAX', 'WSH': 'WAS', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}

def now():
    return datetime.now(timezone.utc).isoformat()

def missing(v):
    return v is None or str(v).strip().lower() in ('', 'na', 'nan', 'null', 'none')

def team(v):
    v = (v or '').strip()
    return ALIASES.get(v, v)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def download(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'FantasyFootball-data-audit'})
            with urllib.request.urlopen(req, timeout=90) as response:
                return response.read(), dict(response.headers)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def capture(cache):
    cache.mkdir(parents=True, exist_ok=True)
    manifest = {'captured_at_utc': now(), 'python': platform.python_version(), 'sources': []}
    for tag in ('stats_player', 'stats_team', 'schedules'):
        raw, _ = download(API + tag)
        release = json.loads(raw)
        metadata_file = tag + '_release.json'
        (cache / metadata_file).write_bytes(raw)
        assets = {a['name']: a for a in release['assets']}
        names = ['games.csv'] if tag == 'schedules' else [f'{tag}_week_{y}.csv' for y in SEASONS]
        for name in names:
            source = dict(release=tag, name=name, release_metadata_url=API + tag,
                          release_metadata_file=metadata_file, release_metadata_sha256=sha(raw),
                          release_published_at=release['published_at'])
            manifest['sources'].append(source)
            if name not in assets:
                source['status'] = 'asset_absent'
                continue
            asset = assets[name]
            payload, headers = download(asset['browser_download_url'])
            digest = asset.get('digest') or ''
            if digest.startswith('sha256:') and digest != 'sha256:' + sha(payload):
                raise ValueError(f'Upstream changed during capture: {name}; retry --refresh')
            (cache / name).write_bytes(payload)
            source.update(status='available', url=asset['browser_download_url'], asset_id=asset['id'],
                          asset_updated_at=asset['updated_at'], asset_created_at=asset['created_at'],
                          retrieved_at_utc=now(), sha256=sha(payload), bytes=len(payload),
                          http_last_modified=headers.get('Last-Modified'), upstream_digest=digest)
            print(f'Downloaded {name}', flush=True)
    # Never publish a complete manifest if a download failed.
    save(cache / 'sources.json', manifest)
    return manifest

def read_source(cache, source):
    payload = (cache / source['name']).read_bytes()
    if sha(payload) != source['sha256']:
        raise ValueError(f"Snapshot checksum mismatch: {source['name']}")
    reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
    rows = list(reader)
    return rows, reader.fieldnames or []

def duplicates(rows, keys):
    counts = Counter(tuple(r.get(k, '') for k in keys) for r in rows)
    repeated = [(key, n) for key, n in sorted(counts.items()) if n > 1]
    return dict(keys=keys, duplicate_groups=len(repeated),
                rows_in_duplicate_groups=sum(n for _, n in repeated),
                excess_rows=sum(n - 1 for _, n in repeated),
                groups=[dict(zip(keys, key), count=n) for key, n in repeated])

def reconcile(rows, games, year):
    games = [g for g in games if g['season'] == str(year) and g['game_type'] == 'REG']
    expected, completed = {}, set()
    for g in games:
        for side, other in (('home_team', 'away_team'), ('away_team', 'home_team')):
            key = (g['season'], g['week'], team(g[side]))
            if key in expected:
                raise ValueError(f'Duplicate schedule team-week: {key}')
            expected[key] = (g['game_id'], team(g[other]))
            if not missing(g['home_score']) and not missing(g['away_score']):
                completed.add(key)
    observed = {(r['season'], r['week'], team(r['team'])) for r in rows if not missing(r['team'])}
    mismatches = set()
    for r in rows:
        key = (r['season'], r['week'], team(r['team']))
        if key not in expected:
            continue
        gid, opponent = expected[key]
        if ((not missing(r.get('opponent_team')) and team(r['opponent_team']) != opponent)
                or (not missing(r.get('game_id')) and r['game_id'] != gid)):
            mismatches.add(key + (r.get('game_id', ''), r.get('opponent_team', '')))
    def records(keys):
        return [dict(zip(('season', 'week', 'team'), k)) for k in sorted(keys)]
    weekly = []
    for week in sorted({g['week'] for g in games} | {r['week'] for r in rows}, key=int):
        scheduled = [g for g in games if g['week'] == week]
        def sides(g):
            return {(str(year), week, team(g['home_team'])), (str(year), week, team(g['away_team']))}
        weekly.append(dict(week=int(week), scheduled_games=len(scheduled),
                           completed_games=sum(sides(g) <= completed for g in scheduled),
                           observed_games_any_team=sum(bool(sides(g) & observed) for g in scheduled),
                           observed_games_both_teams=sum(sides(g) <= observed for g in scheduled),
                           observed_team_weeks=sum(k[1] == week for k in observed)))
    return dict(schedule_available=bool(games), weekly=weekly,
                missing_completed_team_weeks=records(completed - observed),
                unobserved_unfinished_team_weeks=records(expected.keys() - completed - observed),
                unexpected_team_weeks=records(observed - expected.keys()),
                observed_unfinished_team_weeks=records(observed & (expected.keys() - completed)),
                opponent_or_game_id_mismatches=[list(k) for k in sorted(mismatches)])

def audit(rows, columns, dataset, year, games):
    required = {'season', 'season_type', 'week', 'team'}
    if dataset == 'stats_player':
        required |= {'player_id', 'position'}
    if not required <= set(columns):
        raise ValueError(f'{dataset} {year}: missing columns {sorted(required - set(columns))}')
    regular = [r for r in rows if r['season'] == str(year) and r['season_type'] == 'REG']
    keys = ['player_id', 'season', 'week'] if dataset == 'stats_player' else ['team', 'season', 'week']
    groups = dict(
        kicking=[c for c in columns if c.startswith(('fg_', 'pat_', 'gwfg_', 'pt_'))],
        defense=[c for c in columns if c.startswith('def_') or c in
                 ('sacks', 'sack_yards', 'interceptions', 'fumble_recovery_opp', 'fumble_recovery_opp_tds', 'safeties', 'blocked_kicks', 'fumble_recovery_yards_opp', 'fumble_recovery_tds')],
        returns=[c for c in columns if 'return' in c or c == 'special_teams_tds'])
    def counts(c):
        values = [r[c] for r in regular if not missing(r[c])]
        def nonzero(v):
            try:
                return float(v) != 0
            except ValueError:
                return True
        return dict(non_null=len(values), missing=len(regular) - len(values), nonzero=sum(nonzero(v) for v in values))
    def positions(rr):
        return dict(sorted(Counter('<missing>' if missing(r.get('position')) else r['position'] for r in rr).items()))
    id_team = [c for c in columns if c.endswith('_id') or c == 'team' or c.endswith('_team')]
    weeks = sorted({r['week'] for r in regular}, key=int)
    return dict(dataset=dataset, season=year, status='available', source_rows=len(rows),
                regular_rows=len(regular), excluded_rows=len(rows) - len(regular),
                source_season_types=dict(Counter(r['season_type'] for r in rows)),
                unexpected_source_seasons=sorted({r['season'] for r in rows} - {str(year)}),
                weeks=list(map(int, weeks)), rows_by_week=dict(Counter(r['week'] for r in regular)),
                rows_by_position=positions(regular) if dataset == 'stats_player' else None,
                rows_by_week_position={w: positions([r for r in regular if r['week'] == w]) for w in weeks} if dataset == 'stats_player' else None,
                missing_ids_and_teams={c: sum(missing(r[c]) for r in regular) for c in id_team},
                missing_key_fields={c: sum(missing(r[c]) for r in regular) for c in keys},
                missing_identity_rows=[{c: r[c] for c in columns if not missing(r[c]) and r[c] not in ('0', '0.0')} for r in regular if any(missing(r[c]) for c in id_team)],
                duplicates=duplicates(regular, keys), columns=columns,
                relevant_columns={g: {c: counts(c) for c in names} for g, names in groups.items()},
                schedule=reconcile(regular, games, year))

def report(results, manifest):
    lines = ['# nflverse weekly data audit', '',
             f"Snapshot captured at **{manifest['captured_at_utc']}**. Seasons 2022–2026; regular season only.", '',
             'Rerun from the repository root (Python 3.10+, standard library only):', '',
             '```powershell', 'python scripts/audit_nflverse.py --refresh', '```', '',
             'Omit `--refresh` to replay the checksum-verified cached inputs offline. Refresh replaces the snapshot; '
             'use `--cache-dir data/audit_cache/<snapshot-name>` to preserve separate captures. '
             '`audit.json` provides all counts and discrepancy keys; `sources.json` records source provenance.', '',
             '| Dataset | Season | REG weeks | Rows | Missing player IDs | Missing teams | Duplicate groups / excess rows |',
             '|---|---:|---|---:|---:|---:|---:|']
    valid = [r for r in results if r['status'] == 'available']
    for r in results:
        if r['status'] != 'available':
            lines.append(f"| {r['dataset']} | {r['season']} | asset absent | — | — | — | — |")
            continue
        d = r['duplicates']
        lines.append(f"| {r['dataset']} | {r['season']} | {', '.join(map(str, r['weeks'])) or 'none'} | {r['regular_rows']} | {r['missing_ids_and_teams'].get('player_id', 'N/A')} | {r['missing_ids_and_teams']['team']} | {d['duplicate_groups']} / {d['excess_rows']} |")
    players = [r for r in valid if r['dataset'] == 'stats_player']
    positions = sorted({p for r in players for p in r['rows_by_position']})
    lines += ['', '## Player rows by position', '', '| Position | ' + ' | '.join(str(r['season']) for r in players) + ' |',
              '|---|' + '---:|' * len(players)]
    for pos in positions:
        lines.append('| ' + ('(missing)' if pos == '<missing>' else pos) + ' | ' + ' | '.join(str(r['rows_by_position'].get(pos, 0)) for r in players) + ' |')
    lines += ['', 'Team rows have no position dimension. Counts represent stat rows, not rosters or participation.',
              '', '## Schedule reconciliation', '',
              'Completed means both schedule scores are populated. Team-season-week keys use the alias map in `audit.json`. '
              'A game is fully observed only when both teams occur; player rows establish team coverage, not roster completeness. '
              'Unplayed/cancelled games with missing scores are not missing completed games. '
              'Sources are fetched sequentially, so brief update lag is possible.', '',
              '| Dataset | Season | Completed games | Observed, both teams | Missing completed team-weeks | Unexpected team-weeks | Opponent/game-ID mismatches | Unobserved unfinished team-weeks |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in valid:
        s = r['schedule']
        if not s['schedule_available']:
            lines.append(f"| {r['dataset']} | {r['season']} | N/A: no schedule | — | — | — | — | — |")
            continue
        lines.append(f"| {r['dataset']} | {r['season']} | {sum(w['completed_games'] for w in s['weekly'])} | {sum(w['observed_games_both_teams'] for w in s['weekly'])} | {len(s['missing_completed_team_weeks'])} | {len(s['unexpected_team_weeks'])} | {len(s['opponent_or_game_id_mismatches'])} | {len(s['unobserved_unfinished_team_weeks'])} |")
    lines += ['', 'Weekly scheduled/completed/observed game counts, observed unfinished team-weeks, and discrepancy keys are in `audit.json`.',
              '', '## Kicking and defense', '']
    for group in ('kicking', 'defense', 'returns'):
        cols = sorted({c for r in valid for c in r['relevant_columns'][group]})
        lines.append(f"- {group.capitalize()} columns (union across player/team seasons): " + (', '.join(f'`{c}`' for c in cols) or 'none found') + '.')
    lines += ['', 'Inventories select columns by name, not fantasy scoring rules. Per-season non-null and nonzero counts '
              'in `audit.json` distinguish column presence from populated data. Missing columns are not treated as zero. '
              'Defensive and return totals require explicit scoring rules before calculating fantasy D/ST scores.',
              '', '## Source update times', '',
              '| Asset | Status | Asset updated (UTC) | Retrieved (UTC) |', '|---|---|---|---|']
    for s in manifest['sources']:
        label = f"[{s['name']}]({s['url']})" if s.get('url') else s['name']
        lines.append(f"| {label} | {s['status']} | {s.get('asset_updated_at', 'N/A')} | {s.get('retrieved_at_utc', 'N/A')} |")
    lines += ['', 'Asset timestamps describe publication, not the latest game or finality of statistics. Release creation times '
              'and HTTP Last-Modified values (when supplied) are retained separately in `sources.json`.', '',
              'References: [player releases](https://github.com/nflverse/nflverse-data/releases/tag/stats_player), '
              '[team releases](https://github.com/nflverse/nflverse-data/releases/tag/stats_team), '
              '[schedule release](https://github.com/nflverse/nflverse-data/releases/tag/schedules), '
              '[player dictionary](https://nflreadr.nflverse.com/articles/dictionary_player_stats.html), '
              '[team dictionary](https://nflreadr.nflverse.com/articles/dictionary_team_stats.html).', '']
    summary = ['', '## Findings', '']
    missing_total = sum(r['missing_ids_and_teams'].get('player_id', 0) for r in valid)
    summary.append(f"- {missing_total} regular-season player rows have missing player IDs. They remain in all row counts; inspect their nonempty fields in `missing_identity_rows` in `audit.json` before joining to player data.")
    missing_other = sum(n for r in valid for c, n in r['missing_ids_and_teams'].items() if c != 'player_id')
    duplicate_total = sum(r['duplicates']['duplicate_groups'] for r in valid)
    summary.append(f"- Other missing ID/team fields: {missing_other}; duplicate key groups: {duplicate_total}. Keys are player-season-week or team-season-week; null key fields are counted separately.")
    for r in valid:
        if r['dataset'] == 'stats_team' and r['season'] == 2026:
            observed = [w for w in r['schedule']['weekly'] if w['observed_games_both_teams']]
            detail = '; '.join(f"week {w['week']}: {w['observed_games_both_teams']}/{w['scheduled_games']} scheduled games" for w in observed)
            summary.append(f"- 2026 coverage: {detail}. An available week is not necessarily a complete week.")
    summary += ['', 'Missing-ID rows can contain nonzero statistics and are not safe to silently discard or assign to a player. '
                'The saved snapshot provides the evidence; the audit does not infer their upstream cause.', '']
    lines[4:4] = summary
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Replace selected snapshot with current releases')
    parser.add_argument('--cache-dir', type=Path, default=ROOT / 'data/audit_cache')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/nflverse_audit')
    args = parser.parse_args()
    path = args.cache_dir / 'sources.json'
    manifest = capture(args.cache_dir) if args.refresh or not path.exists() else json.loads(path.read_text(encoding='utf-8'))
    for s in manifest['sources']:
        if sha((args.cache_dir / s['release_metadata_file']).read_bytes()) != s['release_metadata_sha256']:
            raise ValueError('Release metadata checksum mismatch')
    schedule = next(s for s in manifest['sources'] if s['name'] == 'games.csv')
    if schedule['status'] != 'available':
        raise ValueError('Schedule absent; cannot complete reconciliation')
    games, columns = read_source(args.cache_dir, schedule)
    if not {'season', 'week', 'game_type', 'game_id', 'home_team', 'away_team', 'home_score', 'away_score'} <= set(columns):
        raise ValueError('Schedule schema missing required columns')
    results = []
    for s in manifest['sources']:
        if s['release'] == 'schedules':
            continue
        year = int(s['name'].removesuffix('.csv').split('_')[-1])
        if s['status'] != 'available':
            results.append(dict(dataset=s['release'], season=year, status=s['status']))
            continue
        rows, columns = read_source(args.cache_dir, s)
        results.append(audit(rows, columns, s['release'], year, games))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save(args.output_dir / 'audit.json', dict(snapshot_captured_at_utc=manifest['captured_at_utc'],
         seasons=list(SEASONS), season_type='REG', team_aliases=ALIASES, results=results))
    save(args.output_dir / 'sources.json', manifest)
    (args.output_dir / 'report.md').write_text(report(results, manifest), encoding='utf-8')
    print(f"Report: {args.output_dir / 'report.md'}")

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print(f'Audit failed: {exc}', file=sys.stderr)
        sys.exit(1)

