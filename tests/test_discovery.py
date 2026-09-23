import unittest
from datetime import date
from discovery import calculate, rank, universe, ROOT


class Calculations(unittest.TestCase):
    def setUp(self):
        self.days = [date(2026, 8, d) for d in (27,28,31)] + [date(2026,9,d) for d in (1,2)]
        self.rows = [dict(date=str(d), open=10, high=12, low=8, close=10, volume=100) for d in self.days]
        self.rows[-1].update(open=20, high=24, low=16, close=20, volume=300)

    def test_previous_excludes_today_and_weighted_month(self):
        row = calculate('X', self.rows, self.days[-1], set(self.days))
        self.assertEqual(row['previous_3_high'], 12)
        self.assertEqual(row['previous_3_low'], 8)
        self.assertAlmostEqual(row['vah'], 11.4)
        self.assertAlmostEqual(row['val'], 8.6)
        self.assertEqual(row['monthly_avwap'], 17.5)
        self.assertEqual(row['monthly_sessions'], 2)

    def test_first_of_month_resets_anchor(self):
        row = calculate('X', self.rows, self.days[-2], set(self.days))
        self.assertEqual(row['monthly_avwap'], 10)
        self.assertEqual(row['monthly_sessions'], 1)

    def test_missing_month_session(self):
        with self.assertRaisesRegex(ValueError, 'Missing required'):
            calculate('X', self.rows[:3]+self.rows[4:], self.days[-1], set(self.days))

    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            calculate('X', self.rows+[self.rows[-1]], self.days[-1], set(self.days))

    def test_bad_volume_and_nan(self):
        for value in (0, -1, float('nan')):
            self.rows[-1]['volume'] = value
            with self.assertRaises(ValueError):
                calculate('X', self.rows, self.days[-1], set(self.days))

    def test_stale_stock(self):
        with self.assertRaisesRegex(ValueError, 'Missing required'):
            calculate('X', self.rows[:-1], self.days[-1], set(self.days))

    def test_ranking_and_boundaries(self):
        rows = [dict(symbol='B', close=12, vah=10, val=8, monthly_avwap=9),
                dict(symbol='A', close=12, vah=10, val=8, monthly_avwap=9),
                dict(symbol='C', close=6, vah=10, val=8, monthly_avwap=9),
                dict(symbol='D', close=10, vah=10, val=8, monthly_avwap=9)]
        bulls, bears = rank(rows, 'proposed')
        self.assertEqual([r['symbol'] for r in bulls], ['A','B'])
        self.assertAlmostEqual(bulls[0]['score_pct'], 20)
        self.assertEqual(bears[0]['score_pct'], 25)
        self.assertEqual(rows[-1]['classification'], 'NEUTRAL')

    def test_universe(self):
        self.assertEqual(len(universe(ROOT/'data/universe.csv')), 207)


if __name__ == '__main__':
    unittest.main()
