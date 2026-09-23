"""Uncached scan entry point shared by the Streamlit UI and its tests."""
from datetime import datetime
from zoneinfo import ZoneInfo
from discovery import ROOT, universe, download, calculate, rank
from indicators import indicators


def run_scan(as_of, progress=None):
    now = datetime.now(ZoneInfo('Asia/Kolkata'))
    if as_of > now.date() or (as_of == now.date() and (now.hour, now.minute) < (16, 0)):
        raise ValueError('Select a completed session. Today is available after 16:00 IST.')
    active = universe(ROOT / 'data/universe.csv')
    prices, sessions, errors, note, provisional = download(active, as_of, progress, history_days=550)
    if as_of not in sessions:
        raise ValueError('No session data for this date. Select the previous trading session.')
    if len([d for d in sessions if d < as_of.replace(day=1)]) < 3:
        raise ValueError('Insufficient calendar history before the scan month.')
    grouped = {}
    for row in prices:
        grouped.setdefault(row['symbol'], []).append(row)
    failed = {r['symbol'] for r in errors}
    results = []
    indicator_rows, indicator_errors = [], []
    for item in active:
        symbol = item['symbol']
        if symbol in failed:
            indicator_errors.append({'symbol': symbol, 'issue': 'Price download failed'})
            continue
        metrics = {}
        try:
            metrics = indicators(grouped.get(symbol, []), as_of, sessions)
            last = next(r for r in grouped[symbol] if r['date'] == str(as_of))
            indicator_rows.append(dict(symbol=symbol, date=str(as_of), close=float(last['close']), **metrics))
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            indicator_errors.append({'symbol': symbol, 'issue': str(exc)})
        try:
            results.append(dict(calculate(symbol, grouped.get(symbol, []), as_of, sessions), **metrics))
        except (ValueError, KeyError, TypeError) as exc:
            errors.append({'symbol': symbol, 'issue': str(exc)})
    bullish, bearish = rank(results, 'proposed')
    ema13_ranked = sorted(indicator_rows, key=lambda r: (r['ema13_abs_distance_pct'], r['symbol']))
    for position, row in enumerate(ema13_ranked, 1):
        row['ema13_rank'] = position
    return dict(as_of=str(as_of), completed_at=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),
                universe=active, results=results, errors=errors, bullish=bullish, bearish=bearish,
                indicator_rows=indicator_rows, indicator_errors=indicator_errors, ema13_ranked=ema13_ranked,
                calendar_note=note, provisional=provisional)
