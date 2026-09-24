"""Uncached scan entry point shared by the Streamlit UI and its tests."""
from datetime import datetime, date
from zoneinfo import ZoneInfo
from discovery import ROOT, universe, download, calculate, rank
from indicators import indicators
from markets import MARKETS, latest_date
SCAN_API_VERSION = 2


def run_scan(as_of, progress=None, market='IN'):
    config = MARKETS[market]
    if as_of > latest_date(market):
        raise ValueError(f"Select a completed session. Same-day scans open at {config['ready_hour']}:00 in {config['timezone']}.")
    active = universe(ROOT / 'data' / config['universe'])
    prices, sessions, errors, note, provisional = download(active, as_of, progress, history_days=550, benchmark_symbol=config['benchmark'])
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
        own_sessions = sessions
        if item.get('asset_type') == 'Futures proxy':
            # Futures have different holidays/session labels from cash equities.
            own_sessions = {date.fromisoformat(r['date']) for r in grouped.get(symbol, [])}
        identity = dict(exchange=item.get('exchange', 'NSE'), asset_type=item.get('asset_type', 'Stock'),
                        yahoo_symbol=item['yahoo_symbol'], currency=config['currency'])
        try:
            metrics = indicators(grouped.get(symbol, []), as_of, own_sessions)
            last = next(r for r in grouped[symbol] if r['date'] == str(as_of))
            indicator_rows.append(dict(symbol=symbol, date=str(as_of), close=float(last['close']), **identity, **metrics))
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            indicator_errors.append({'symbol': symbol, 'issue': str(exc)})
        try:
            results.append(dict(calculate(symbol, grouped.get(symbol, []), as_of, own_sessions), **identity, **metrics))
        except (ValueError, KeyError, TypeError) as exc:
            errors.append({'symbol': symbol, 'issue': str(exc)})
    bullish, bearish = rank(results, 'proposed', top_n=config['top_n'])
    ema13_ranked = sorted(indicator_rows, key=lambda r: (r['ema13_abs_distance_pct'], r['symbol']))
    for position, row in enumerate(ema13_ranked, 1):
        row['ema13_rank'] = position
    if market == 'US':
        note += ' GC1!/SI1! use Yahoo GC=F/SI=F futures proxies. Futures use their own observed sessions; missing futures sessions cannot be independently verified. Rolls may differ from TradingView.'
        provisional = True
    return dict(market=market, top_n=config['top_n'], as_of=str(as_of), completed_at=datetime.now(ZoneInfo(config['timezone'])).isoformat(),
                universe=active, results=results, errors=errors, bullish=bullish, bearish=bearish,
                indicator_rows=indicator_rows, indicator_errors=indicator_errors, ema13_ranked=ema13_ranked,
                calendar_note=note, provisional=provisional)
