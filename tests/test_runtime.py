import inspect
import unittest
from unittest.mock import patch
from datetime import date, timedelta
import discovery
import scan_service
from runtime_bootstrap import load_scan_service


class DeploymentReload(unittest.TestCase):
    def test_legacy_loaded_helpers_refresh_before_use(self):
        # Reproduce the exact screenshot: older function has no market keyword.
        def legacy_scan(as_of, progress=None):
            raise AssertionError('Stale service must not execute')
        with patch.object(scan_service, 'SCAN_API_VERSION', 0), \
             patch.object(scan_service, 'run_scan', legacy_scan), \
             patch.object(discovery, 'MARKET_API_VERSION', 0):
            service = load_scan_service()
            self.assertIn('market', inspect.signature(service.run_scan).parameters)
            self.assertIn('benchmark_symbol', inspect.signature(discovery.download).parameters)
            self.assertIn('top_n', inspect.signature(discovery.rank).parameters)

    def test_real_service_market_keyword_with_fixture_prices(self):
        days = [date(2025, 10, 1) + timedelta(days=n) for n in range(100)]
        prices = [dict(symbol='TEST', date=str(day), open=100+n, high=102+n,
                       low=99+n, close=101+n, volume=100) for n, day in enumerate(days)]
        item = dict(symbol='TEST', yahoo_symbol='TEST', enabled='YES')
        service = load_scan_service()
        with patch.object(service, 'universe', return_value=[item]), \
             patch.object(service, 'download', return_value=(prices, set(days), [], '', False)) as fetch:
            for market, benchmark, count in [('IN', '^NSEI', 20), ('US', '^GSPC', 8)]:
                result = service.run_scan(days[-1], market=market)
                self.assertEqual(result['market'], market)
                self.assertEqual(result['top_n'], count)
                self.assertEqual(len(result['results']), 1)
                self.assertEqual(fetch.call_args.kwargs['benchmark_symbol'], benchmark)
