import unittest
from datetime import date, timedelta
from indicators import indicators, ema, rma


class Indicators(unittest.TestCase):
    def data(self, flat=False):
        days = [date(2025, 1, 1) + timedelta(days=n) for n in range(220)]
        rows = [dict(date=str(day), open=100+n, close=100+n,
                     high=101+n, low=99+n, volume=100) for n, day in enumerate(days)]
        if flat:
            for row in rows:
                row.update(open=100, high=100, low=100, close=100)
        else:
            rows[-1]['volume'] = 200
        return days, rows

    def test_darvas_and_pine_bands(self):
        days, rows = self.data()
        result = indicators(rows, days[-1], set(days))
        self.assertTrue(result['darvas_pass'])
        self.assertEqual(result['previous_20_high'], rows[-2]['high'])
        self.assertEqual(result['sma10'], sum(r['close'] for r in rows[-10:])/10)
        self.assertEqual(result['volume_sma20'], 105)
        self.assertAlmostEqual(result['atr14'], 2)
        self.assertAlmostEqual(result['master_upper'] - result['ema20'], .2)
        self.assertAlmostEqual(result['ema20'] - result['master_lower'], .2)
        self.assertEqual(result['master_trend'], 'BULLISH')
        self.assertFalse(indicators(rows, days[-1], set(days), prior_breakout=False)['darvas_pass'])

    def test_equality_and_distance(self):
        days, rows = self.data(flat=True)
        result = indicators(rows, days[-1], set(days))
        self.assertEqual(result['master_trend'], 'BULLISH')
        self.assertFalse(result['darvas_pass'])
        self.assertEqual(result['ema13_abs_distance_pct'], 0)
        self.assertEqual(result['atr14'], 0)

    def test_ema_and_wilder_seed(self):
        self.assertAlmostEqual(ema([100, 107], 13), 101)
        self.assertAlmostEqual(rma([2]*14 + [16], 14), 3)

    def test_future_bar_cannot_change_results(self):
        days, rows = self.data()
        original = indicators(rows, days[-1], set(days))
        future = dict(rows[-1], date=str(days[-1]+timedelta(days=1)), close=10000)
        self.assertEqual(original, indicators(rows+[future], days[-1], set(days)))

    def test_insufficient_duplicate_and_missing(self):
        days, rows = self.data()
        for data in (rows[-49:], rows + [rows[-1]], rows[:-2] + rows[-1:]):
            with self.assertRaises(ValueError):
                indicators(data, days[-1], set(days))

    def test_bearish(self):
        days, rows = self.data()
        rows[-1].update(open=100, high=110, low=90, close=100)
        result = indicators(rows, days[-1], set(days))
        self.assertEqual(result['master_trend'], 'BEARISH')
        self.assertLess(result['ema13_distance_pct'], 0)
        self.assertGreater(result['ema13_abs_distance_pct'], 0)


if __name__ == '__main__':
    unittest.main()
