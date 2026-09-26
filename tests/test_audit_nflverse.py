import unittest
from scripts.audit_nflverse import audit, duplicates, missing, reconcile

class AuditTests(unittest.TestCase):
    def game(self, week='1', score='20'):
        return dict(season='2026', week=week, game_type='REG', game_id='game-' + week,
                    home_team='LA', away_team='SEA', home_score=score, away_score=score)

    def row(self, **changes):
        row = dict(season='2026', season_type='REG', week='1', team='LAR',
                   player_id='p1', position='K', opponent_team='SEA', game_id='game-1', fg_made='0', def_sacks='')
        row.update(changes)
        return row

    def test_duplicate_player_key_ignores_team(self):
        result = duplicates([self.row(), self.row(team='SEA'), self.row(player_id='p2')], ['player_id', 'season', 'week'])
        self.assertEqual(result['duplicate_groups'], 1)
        self.assertEqual(result['excess_rows'], 1)
        self.assertEqual(result['rows_in_duplicate_groups'], 2)

    def test_schedule_two_sides_future_and_alias(self):
        result = reconcile([self.row()], [self.game(), self.game('2', '')], 2026)
        self.assertEqual(len(result['missing_completed_team_weeks']), 1)
        self.assertEqual(len(result['unobserved_unfinished_team_weeks']), 2)
        self.assertEqual(result['weekly'][0]['observed_games_any_team'], 1)
        self.assertEqual(result['weekly'][0]['observed_games_both_teams'], 0)
        self.assertFalse(result['unexpected_team_weeks'])
        self.assertFalse(result['opponent_or_game_id_mismatches'])

    def test_regular_filter_nulls_and_zero_coverage(self):
        rows = [self.row(player_id='', team='', position=''), self.row(season_type='POST'), self.row(season='2025')]
        result = audit(rows, list(rows[0]), 'stats_player', 2026, [self.game()])
        self.assertEqual(result['regular_rows'], 1)
        self.assertEqual(result['missing_ids_and_teams']['player_id'], 1)
        self.assertEqual(result['rows_by_position'], {'<missing>': 1})
        self.assertEqual(result['relevant_columns']['kicking']['fg_made']['nonzero'], 0)
        self.assertEqual(result['relevant_columns']['defense']['def_sacks']['missing'], 1)
        self.assertTrue(missing(' NA '))

    def test_schedule_mismatch_and_unexpected(self):
        result = reconcile([self.row(opponent_team='KC'), self.row(team='BUF')], [self.game()], 2026)
        self.assertEqual(len(result['unexpected_team_weeks']), 1)
        self.assertEqual(len(result['opponent_or_game_id_mismatches']), 1)

    def test_schema_failure(self):
        with self.assertRaises(ValueError):
            audit([], ['season'], 'stats_player', 2026, [])

if __name__ == '__main__':
    unittest.main()


class SnapshotTests(unittest.TestCase):
    def test_checksum_rejects_modified_snapshot(self):
        import tempfile
        from pathlib import Path
        from scripts.audit_nflverse import read_source, sha
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = b'player_id,team\np1,SEA\n'
            (root / 'sample.csv').write_bytes(data)
            source = dict(name='sample.csv', sha256=sha(data))
            rows, columns = read_source(root, source)
            self.assertEqual(rows, [dict(player_id='p1', team='SEA')])
            (root / 'sample.csv').write_bytes(data + b'p2,LA\n')
            with self.assertRaises(ValueError):
                read_source(root, source)

    def test_team_duplicates_and_missing_schedule(self):
        rows = [dict(team='SEA', season='2026', week='1')] * 2
        result = duplicates(rows, ['team', 'season', 'week'])
        self.assertEqual(result['excess_rows'], 1)
        self.assertFalse(reconcile(rows, [], 2026)['schedule_available'])

