"""Daily, end-of-day discovery calculations. Core uses Python's standard library."""
import argparse
import csv
import html
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent


def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields):
    with open(path, 'w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def universe(path):
    rows = read_csv(path)
    seen = set()
    active = []
    for row in rows:
        symbol = row['symbol'].strip()
        if not symbol or symbol in seen:
            raise ValueError('Missing or duplicate universe symbol: ' + symbol)
        seen.add(symbol)
        if row['enabled'].strip().upper() == 'YES':
            active.append(dict(row, symbol=symbol))
    if not active:
        raise ValueError('Universe contains no enabled stocks')
    return active


def calculate(symbol, raw, as_of, sessions):
    """Previous three sessions exclude as_of; AVWAP includes completed as_of bar."""
    month = as_of.replace(day=1)
    previous = sorted(d for d in sessions if d < as_of)[-3:]
    if as_of not in sessions or len(previous) != 3:
        raise ValueError('Calendar must include scan date and three preceding sessions')
    required = set(previous) | {d for d in sessions if month <= d <= as_of}
    bars = {}
    for row in raw:
        day = date.fromisoformat(row['date'])
        if day not in required:
            continue
        if day in bars:
            raise ValueError('Duplicate bar: ' + day.isoformat())
        values = {key: float(row[key]) for key in ('open', 'high', 'low', 'close', 'volume')}
        if not all(math.isfinite(v) for v in values.values()):
            raise ValueError('Non-finite OHLCV: ' + day.isoformat())
        if min(values[k] for k in ('open', 'high', 'low', 'close')) <= 0 or values['volume'] <= 0:
            raise ValueError('Non-positive price or volume: ' + day.isoformat())
        if not (values['low'] <= min(values['open'], values['close']) <= max(values['open'], values['close']) <= values['high']):
            raise ValueError('Inconsistent OHLC: ' + day.isoformat())
        bars[day] = values
    missing = required - bars.keys()
    if missing:
        raise ValueError('Missing required sessions: ' + ', '.join(str(d) for d in sorted(missing)))
    high = max(bars[d]['high'] for d in previous)
    low = min(bars[d]['low'] for d in previous)
    width = high - low
    vah, val = high - .15 * width, low + .15 * width
    monthly = [v for d, v in bars.items() if month <= d <= as_of]
    volume = sum(v['volume'] for v in monthly)
    avwap = sum((v['high'] + v['low'] + v['close']) / 3 * v['volume'] for v in monthly) / volume
    close = bars[as_of]['close']
    return dict(symbol=symbol, date=str(as_of), close=close, previous_3_high=high,
                previous_3_low=low, range_3=width, vah=vah, val=val, monthly_avwap=avwap,
                monthly_sessions=len(monthly), monthly_volume=volume,
                previous_window_start=str(previous[0]), previous_window_end=str(previous[-1]))


def rank(results, mode):
    """Optional proposed rule, deliberately separate from PDF calculations."""
    bullish, bearish = [], []
    for row in results:
        row.update(classification='UNRANKED', score_pct='', rank='')
        if mode == 'none':
            continue
        close = row['close']
        row['classification'] = 'NEUTRAL'
        if close > row['vah'] and close > row['monthly_avwap']:
            row['classification'] = 'BULLISH'
            row['score_pct'] = (close / row['vah'] - 1) * 100
            bullish.append(row)
        elif close < row['val'] and close < row['monthly_avwap']:
            row['classification'] = 'BEARISH'
            row['score_pct'] = (1 - close / row['val']) * 100
            bearish.append(row)
    for group in (bullish, bearish):
        group.sort(key=lambda r: (-r['score_pct'], r['symbol']))
        for n, row in enumerate(group, 1):
            row['rank'] = n
    return bullish[:20], bearish[:20]


FIELDS = ['symbol', 'date', 'close', 'previous_3_high', 'previous_3_low', 'range_3',
          'vah', 'val', 'monthly_avwap', 'monthly_sessions', 'monthly_volume',
          'previous_window_start', 'previous_window_end', 'classification', 'score_pct', 'rank']


def report(folder, results, errors, bullish, bearish, metadata):
    folder.mkdir(parents=True, exist_ok=True)
    write_csv(folder / 'calculations.csv', results, FIELDS)
    write_csv(folder / 'bullish_top20.csv', bullish, FIELDS)
    write_csv(folder / 'bearish_top20.csv', bearish, FIELDS)
    write_csv(folder / 'data_issues.csv', errors, ['symbol', 'issue'])
    (folder / 'run.json').write_text(json.dumps(metadata, indent=2))
    def table(rows, fields):
        if not rows:
            return '<p>No rows.</p>'
        def cell(value):
            return html.escape(f'{value:,.4f}' if isinstance(value, float) else str(value))
        return '<div class="scroll"><table><thead><tr>' + ''.join('<th>'+html.escape(k.replace('_', ' '))+'</th>' for k in fields) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>'+cell(r.get(k, ''))+'</td>' for k in fields) + '</tr>' for r in rows) + '</tbody></table></div>'
    columns = ['rank', 'symbol', 'close', 'vah', 'val', 'monthly_avwap', 'score_pct']
    body = '<h1>Sandeep Discovery</h1><p>Daily research shortlist · ' + html.escape(metadata['as_of']) + '</p>'
    body += '<p class="notice">Discovery only. Trading decisions remain with the existing framework.</p>'
    body += '<p>' + html.escape(metadata['rule_description']) + '</p>'
    body += '<p>' + html.escape(metadata['calendar_note']) + '</p>'
    body += f'<p>Universe: {metadata["universe_count"]} · Calculated: {len(results)} · Data issues: {len(errors)}</p>'
    for title, rows, fields in [('Bullish Top 20', bullish, columns), ('Bearish Top 20', bearish, columns), ('All calculations', results, FIELDS), ('Data issues', errors, ['symbol', 'issue'])]:
        body += '<h2>'+title+'</h2>'+table(rows, fields)
    (folder / 'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Sandeep Discovery</title><style>body{font:15px system-ui;background:#f4f6fa;color:#192b43;margin:36px auto;padding:0 24px;max-width:1400px}h1{font-size:36px}h2{margin-top:34px}.notice{padding:16px;background:#e1ebf7;border-left:4px solid #396b9f}.scroll{overflow:auto;background:white;border:1px solid #dce2eb;border-radius:8px}table{border-collapse:collapse;width:100%;white-space:nowrap}th,td{padding:12px;text-align:right;border-bottom:1px solid #e6eaf0}th{background:#192b43;color:white;text-transform:capitalize}td:first-child,th:first-child{text-align:left}</style><body>'+body+'</body></html>', encoding='utf-8')


def download(active, as_of, progress=None, history_days=550):
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ValueError('Install requirements.txt to use Yahoo, or use --prices CSV') from exc
    yf.set_tz_cache_location(str(ROOT / '.cache'))
    # Longer history supports SMA50 and EMA/ATR warm-up for the setup scans.
    start = min(as_of.replace(day=1) - timedelta(days=20), as_of - timedelta(days=history_days))
    end = as_of + timedelta(days=1)
    benchmark = yf.download('^NSEI', start=str(start), end=str(end), auto_adjust=False,
                            progress=False, multi_level_index=False)
    if benchmark is None or benchmark.empty:
        raise ValueError('Yahoo returned no NIFTY calendar data; cannot verify sessions')
    sessions = {stamp.date() for stamp, row in benchmark.iterrows() if math.isfinite(float(row['Close']))}
    rows, failures = [], []
    for n, item in enumerate(active, 1):
        print(f'Fetching {n}/{len(active)} {item["symbol"]}', flush=True)
        try:
            frame = yf.download(item['yahoo_symbol'], start=str(start), end=str(end),
                                auto_adjust=False, progress=False, multi_level_index=False,
                                timeout=15)
            if frame is None or frame.empty:
                raise ValueError('No daily bars returned')
            for stamp, row in frame.iterrows():
                rows.append(dict(symbol=item['symbol'], date=str(stamp.date()),
                                 **{key: float(row[key.title()]) for key in ('open','high','low','close','volume')}))
        except Exception as exc:
            failures.append({'symbol': item['symbol'], 'issue': 'Download failed: '+str(exc)})
        if progress:
            progress(n, len(active), item['symbol'])
    stock_dates = {date.fromisoformat(row['date']) for row in rows if math.isfinite(row['close']) and row['volume'] > 0}
    extra = sorted(stock_dates - sessions)
    sessions |= stock_dates
    note = 'Sessions inferred from Yahoo NIFTY and stock daily bars; verify provider completeness.'
    if extra:
        note = 'PROVISIONAL: stock dates absent from NIFTY calendar: ' + ', '.join(map(str, extra)) + '. Union of dates used; verify exchange calendar before using shortlists.'
    return rows, sessions, failures, note, bool(extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--universe', type=Path, default=ROOT/'data/universe.csv')
    parser.add_argument('--as-of', required=True, type=date.fromisoformat, help='Completed NSE session YYYY-MM-DD')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--prices', type=Path, help='CSV: symbol,date,open,high,low,close,volume')
    source.add_argument('--yahoo', action='store_true')
    parser.add_argument('--sessions', type=Path, help='CSV with date header: all exchange sessions from before month start through scan date')
    parser.add_argument('--ranking', choices=['none', 'proposed'], default='proposed')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        now = datetime.now(ZoneInfo('Asia/Kolkata'))
        if args.as_of > now.date() or (args.as_of == now.date() and (now.hour, now.minute) < (16, 0)):
            raise ValueError('Choose a completed session; same-day scans are enabled after 16:00 IST')
        active = universe(args.universe)
        if args.yahoo:
            prices, sessions, errors, note, provisional = download(active, args.as_of)
        else:
            prices, errors, provisional = read_csv(args.prices), [], False
            if not args.sessions:
                raise ValueError('--sessions is required with CSV prices to validate full-month coverage')
            sessions = set()
            note = 'Sessions supplied in CSV. This calendar must include every exchange session in the month and three preceding sessions.'
        if args.sessions:
            provisional = False
            session_rows = read_csv(args.sessions)
            sessions = {date.fromisoformat(row['date']) for row in session_rows}
            if len(sessions) != len(session_rows):
                raise ValueError('Duplicate dates in sessions file')
            note = 'Coverage checked against supplied exchange sessions. Calendar correctness remains dependent on that file.'
        if args.as_of not in sessions:
            raise ValueError('Scan date is missing from session calendar; choose an actual trading session')
        if len([d for d in sessions if d < args.as_of.replace(day=1)]) < 3:
            raise ValueError('Calendar must start at least three trading sessions before the scan month')
        by_symbol = {}
        for row in prices:
            by_symbol.setdefault(row['symbol'].strip(), []).append(row)
        results = []
        failed = {r['symbol'] for r in errors}
        for item in active:
            symbol = item['symbol']
            if symbol in failed:
                continue
            try:
                results.append(calculate(symbol, by_symbol.get(symbol, []), args.as_of, sessions))
            except (ValueError, KeyError, TypeError) as exc:
                errors.append(dict(symbol=symbol, issue=str(exc)))
        bullish, bearish = rank(results, args.ranking)
        output = args.output or ROOT/'runs'/str(args.as_of)
        metadata = dict(as_of=str(args.as_of), generated_at=now.isoformat(), universe_count=len(active),
                        calculated=len(results), data_issues=len(errors), source='yahoo' if args.yahoo else str(args.prices),
                        ranking=args.ranking, calendar_note=note,
                        rule_description='Ranking disabled: PDF does not define qualification or scoring.' if args.ranking == 'none' else 'USER-APPROVED RULE: close above VAH and monthly AVWAP = bullish; below VAL and AVWAP = bearish. Score is percentage distance beyond VAH/VAL, descending; ties use symbol.',
                        status='provisional' if provisional else ('complete' if not errors else 'incomplete'))
        report(output, results, errors, bullish, bearish, metadata)
        if args.yahoo:
            write_csv(output/'source_prices.csv', prices, ['symbol','date','open','high','low','close','volume'])
            write_csv(output/'source_sessions.csv', [{'date':str(d)} for d in sorted(sessions)], ['date'])
        print(json.dumps(metadata, indent=2))
        print('Report: ' + str(output/'report.html'))
        return 0 if not errors and not provisional else 2
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
