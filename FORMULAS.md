# Formula guide

All calculations use completed **daily bars**. Indian and US universes are scanned separately. Indices are not ranked.

## Market tabs and symbols

India: 207 stocks, Top 20 per side, INR, dates in Asia/Kolkata; same-day scans after 16:00 IST.

US: the 47 supplied instruments (45 equities plus 2 futures proxies), Top 8 per side, USD. Dates use America/New_York with daylight saving. Same-day scans open at 18:00 New York time to allow the futures daily session to finish. This is a conservative cutoff on early-close days. Weekends roll back; select the prior session on exchange holidays.

BRK.A and BRK.B map to Yahoo BRK-A and BRK-B. SPCX is preserved as supplied. GC1! maps to Yahoo GC=F and SI1! to SI=F. These are labelled futures proxies, not identical TradingView continuous contracts. Vendor rolls/adjustments can differ. Futures use their own observed daily session dates; missing futures sessions cannot be independently verified, so US results carry a provisional note. Equity calendars use the market's benchmark (^NSEI or ^GSPC) plus equity dates; futures dates never add equity holidays.

Each market button downloads its entire universe again. Search, filters and downloads do not rerun the scan. Results and failures are isolated by market. No currency conversion is performed; ranking scores are percentages. Both markets use the same discovery and indicator formulas.

## Daily discovery — supplied PDF

For scan date t, HH3 = max(high of t−3, t−2, t−1 trading sessions). LL3 = min(low of those same sessions).

Range3 = HH3 − LL3. **VAH = HH3 − 0.15 × Range3**. **VAL = LL3 + 0.15 × Range3**.

Typical price = (High + Low + Close) / 3.

Monthly AVWAP = sum(Typical price × Volume) / sum(Volume), from the first trading session of the calendar month through the completed scan-date bar. This resets each month and uses daily bars, not individual intraday trades. VAH/VAL are range-derived levels, not volume-profile levels.

## Discovery ranking — separately approved in chat

Bullish: Close > VAH AND Close > monthly AVWAP. Score (%) = 100 × (Close / VAH − 1).

Bearish: Close < VAL AND Close < monthly AVWAP. Score (%) = 100 × (1 − Close / VAL).

Rank each side by score descending; alphabetical symbol breaks ties. Return up to 20 qualifiers per side in India and 8 in the US. Lists are not padded when fewer qualify. Equality is neutral. These qualification rules were approved separately; they are not stated in the PDF.

## EMA13 distance — supplied screenshot

α = 2 / (13 + 1) = 1/7.

EMA13[t] = α × Close[t] + (1 − α) × EMA13[t−1].

Distance (%) = 100 × (Close − EMA13) / EMA13.

Absolute distance (%) = |Distance (%)|.

Rank all stocks with available indicators by absolute distance ascending, closest first; alphabetical symbol breaks ties. The screenshot's rounded coefficients 0.142857 and 0.857143 are implemented as exact fractions. Positive distance means above EMA13; negative means below. Proximity alone is not a support/bounce signal.

## Darvas — screenshot and your breakout clarification

All five conditions must be true:

1. Close[t] > SMA10[t].
2. SMA10[t] > EMA20[t].
3. EMA20[t] > SMA50[t].
4. High[t] > max(High[t−20], …, High[t−1]).
5. Volume[t] > SMA20(Volume)[t].

SMA(N)[t] = sum of the latest N values / N, including t. EMA20 uses α = 2/21. The breakout maximum excludes today, as you approved; a strict high > maximum including itself cannot pass. The volume average includes today. Every comparison is strict.

This is the supplied five-condition Darvas screener. No additional box-pattern rule or bearish mirror has been added.

## Sandeep Master Trend v1 — supplied Pine script

Defaults: EMA length 20, ATR length 14, ATR multiplier 0.10.

EMA20[t] = (2/21) × Close[t] + (19/21) × EMA20[t−1].

TR[t] = max(High[t] − Low[t], |High[t] − Close[t−1]|, |Low[t] − Close[t−1]|).

First available TR = High − Low. ATR14 starts with the mean of the first 14 TR values. Then ATR14[t] = (13 × ATR14[t−1] + TR[t]) / 14 (Wilder RMA).

Upper band = EMA20 + 0.10 × ATR14.

Lower band = EMA20 − 0.10 × ATR14.

**Bullish / lime when Close ≥ EMA20. Bearish / red when Close < EMA20.** Equality is bullish. Bands do not define the trend and are not stop-loss or entry rules. Pine line widths and transparency affect chart styling only.

## History and missing data

Each click requests approximately 550 calendar days of daily history. EMA is seeded with the first available close and updated recursively. At least 50 bars and coverage of the most recent 50 inferred sessions are required for the combined indicator screen. Fewer than 200 bars produces a warm-up note.

History length, price adjustments and provider differences can cause differences from TradingView. Exact TradingView parity has not been verified. Yahoo OHLC uses auto_adjust=False; corporate actions can distort windows crossing those events.

Yahoo index and stock dates provide an inferred session calendar. Conflicts are marked provisional. Missing/invalid inputs are unavailable, not a false trading condition. Discovery can remain available when longer-history indicators are unavailable.

## Trader workflow

Review discovery side, EMA13 distance, Master Trend and the five Darvas conditions together. No combined score or automatic trade approval is added.

Market breadth/regime, sector leadership/weakness, EMA13 support confirmation, EMA9 rejection, entries, stops and risk limits still need exact definitions. They remain manual review items. The existing trading framework decides trades.

Sources: supplied PDF, two screenshots, Master Trend Pine script and chat approvals. [TradingView Pine v6 reference](https://www.tradingview.com/pine-script-reference/v6/).
