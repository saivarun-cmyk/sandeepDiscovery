"""Daily indicators from the user's screenshots and Master Trend Pine script."""
from datetime import date
import math


INDICATOR_FIELDS = ['ema13', 'ema13_distance_pct', 'ema13_abs_distance_pct',
                    'sma10', 'ema20', 'sma50', 'atr14', 'master_upper', 'master_lower',
                    'master_trend', 'darvas_close_gt_sma10', 'darvas_sma10_gt_ema20',
                    'darvas_ema20_gt_sma50', 'darvas_high_breakout', 'darvas_volume_gt_sma20',
                    'darvas_pass', 'previous_20_high', 'volume_sma20', 'history_bars', 'warmup_note']


def ema(values, length):
    alpha = 2 / (length + 1)
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1 - alpha) * result
    return result


def rma(values, length):
    if len(values) < length:
        raise ValueError(f'Need {length} values for Wilder smoothing')
    result = sum(values[:length]) / length
    for value in values[length:]:
        result = (result * (length - 1) + value) / length
    return result


def indicators(raw, as_of, sessions, prior_breakout=True):
    bars = {}
    for row in raw:
        day = date.fromisoformat(row['date'])
        if day > as_of:
            continue
        if day in bars:
            raise ValueError(f'Duplicate indicator bar: {day}')
        v = {key: float(row[key]) for key in ('open','high','low','close','volume')}
        if not all(math.isfinite(x) for x in v.values()):
            raise ValueError(f'Non-finite indicator bar: {day}')
        if min(v[k] for k in ('open','high','low','close')) <= 0 or v['volume'] < 0:
            raise ValueError(f'Invalid indicator price/volume: {day}')
        if not v['low'] <= min(v['open'], v['close']) <= max(v['open'], v['close']) <= v['high']:
            raise ValueError(f'Inconsistent indicator OHLC: {day}')
        bars[day] = v
    if as_of not in bars or len(bars) < 50:
        raise ValueError('Need scan-date bar and at least 50 historical sessions')
    required = sorted(d for d in sessions if d <= as_of)[-50:]
    missing = set(required) - bars.keys()
    if missing:
        raise ValueError('Missing indicator sessions: ' + ', '.join(map(str, sorted(missing))))
    ordered = [bars[d] for d in sorted(bars)]
    closes = [r['close'] for r in ordered]
    e13, e20 = ema(closes, 13), ema(closes, 20)
    s10, s50 = sum(closes[-10:])/10, sum(closes[-50:])/50
    tr = [ordered[0]['high'] - ordered[0]['low']]
    for previous, row in zip(ordered, ordered[1:]):
        tr.append(max(row['high']-row['low'], abs(row['high']-previous['close']), abs(row['low']-previous['close'])))
    atr = rma(tr, 14)
    last = ordered[-1]
    high20 = max(r['high'] for r in ordered[-21:-1])
    threshold = high20 if prior_breakout else max(r['high'] for r in ordered[-20:])
    volume20 = sum(r['volume'] for r in ordered[-20:])/20
    conditions = dict(darvas_close_gt_sma10=last['close'] > s10,
                      darvas_sma10_gt_ema20=s10 > e20,
                      darvas_ema20_gt_sma50=e20 > s50,
                      darvas_high_breakout=last['high'] > threshold,
                      darvas_volume_gt_sma20=last['volume'] > volume20)
    distance = 100 * (last['close'] - e13) / e13
    return dict(ema13=e13, ema13_distance_pct=distance, ema13_abs_distance_pct=abs(distance),
                sma10=s10, ema20=e20, sma50=s50, atr14=atr,
                master_upper=e20 + .10 * atr, master_lower=e20 - .10 * atr,
                master_trend='BULLISH' if last['close'] >= e20 else 'BEARISH',
                **conditions, darvas_pass=all(conditions.values()),
                previous_20_high=high20, volume_sma20=volume20, history_bars=len(ordered),
                warmup_note='' if len(ordered) >= 200 else 'Under 200 bars: EMA/ATR warm-up may differ from TradingView')
