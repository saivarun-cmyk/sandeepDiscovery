import unittest
from datetime import datetime, date, timezone
from discovery import universe, ROOT, rank
from markets import latest_date


class Markets(unittest.TestCase):
    def test_universe_and_mapping(self):
        items = universe(ROOT/'data/us_universe.csv')
        self.assertEqual(len(items), 47)
        mapping = {r['symbol']: r['yahoo_symbol'] for r in items}
        self.assertEqual(mapping['BRK.A'], 'BRK-A')
        self.assertEqual(mapping['BRK.B'], 'BRK-B')
        self.assertEqual(mapping['GC1!'], 'GC=F')
        self.assertEqual(mapping['SI1!'], 'SI=F')
        self.assertEqual(mapping['SPCX'], 'SPCX')

    def test_different_market_dates_and_dst(self):
        now = datetime(2026, 9, 24, 12, tzinfo=timezone.utc)
        self.assertEqual(latest_date('IN', now), date(2026,9,24))
        self.assertEqual(latest_date('US', now), date(2026,9,23))
        self.assertEqual(latest_date('US', datetime(2026,1,6,22,30,tzinfo=timezone.utc)), date(2026,1,5))
        self.assertEqual(latest_date('US', datetime(2026,1,6,23,0,tzinfo=timezone.utc)), date(2026,1,6))

    def test_top_eight_and_twenty(self):
        rows = [dict(symbol=str(n), close=110+n, vah=100, val=90, monthly_avwap=100) for n in range(25)]
        self.assertEqual(len(rank(rows, 'proposed', 8)[0]), 8)
        self.assertEqual(len(rank(rows, 'proposed')[0]), 20)
        self.assertEqual(rank(rows, 'proposed', 8)[0][0]['symbol'], '24')
