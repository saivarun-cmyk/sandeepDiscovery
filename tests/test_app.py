import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from discovery import ROOT, universe


class AppFlow(unittest.TestCase):
    def test_each_click_runs_again_and_search_does_not(self):
        data = dict(as_of='2026-01-05', completed_at='2026-01-05T17:00:00+05:30',
                    universe=universe(ROOT/'data/universe.csv'), results=[], errors=[],
                    bullish=[], bearish=[], calendar_note='', provisional=False)
        with patch('scan_service.run_scan', return_value=data) as run:
            app = AppTest.from_file(str(ROOT/'app.py')).run()
            self.assertFalse(app.exception)
            self.assertEqual(run.call_count, 0)
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(len(app.tabs), 9)
            self.assertEqual(app.tabs[8].label, 'Formula guide')
            app.text_input[0].set_value('HDFC').run()
            self.assertEqual(run.call_count, 1)
            app.button[0].click().run()
            self.assertEqual(run.call_count, 2)
            run.side_effect = ValueError('Provider unavailable')
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertIn('Provider unavailable', app.error[0].value)
            self.assertEqual(run.call_count, 3)
            app.run()
            self.assertEqual(run.call_count, 3)
            self.assertEqual(len(app.tabs), 9)
            self.assertEqual(len(app.metric), 1)


if __name__ == '__main__':
    unittest.main()
