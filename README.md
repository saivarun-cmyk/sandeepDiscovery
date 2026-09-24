# Sandeep Discovery

Daily research scanner for the 207 enabled stocks in the supplied September 2026 workbook. Implements the PDF calculations and the qualification/ranking rules approved separately by the user.

The app now has separate **Indian stocks** and **US stocks** tabs. India scans 207 stocks and returns up to 20 bullish and 20 bearish candidates. US scans all 47 supplied instruments and returns up to 8 on each side. Each tab has its own Run Scan button, date, results, indicator views and CSV downloads; one market's scan does not replace the other's results.

US daily dates use America/New_York (including daylight saving), with a conservative 18:00 cutoff for same-day scans because the list includes futures. India retains its 16:00 IST cutoff. Weekends roll back; choose the prior session on holidays. Prices remain in INR or USD without conversion.

The US universe is in data/us_universe.csv. It includes 45 equities and 2 labelled COMEX futures proxies: GC1! → GC=F and SI1! → SI=F. Yahoo futures contracts can roll differently from TradingView continuous symbols. Futures use their own observed sessions, which cannot detect missing vendor dates independently; US runs are marked provisional. BRK.A/BRK.B map to BRK-A/BRK-B. SPCX is preserved unchanged. Exchange labels come from the supplied list. Missing symbols stay visible in Data issues.

Deployment must also include markets.py and data/us_universe.csv. The original CLI remains Indian discovery-only; both markets and indicators are available through app.py.

## Run daily

### Streamlit UI and deployment

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Install the requirements, then run `streamlit run app.py` from this folder. Every click of **Run Scan** downloads data again for the entire enabled universe and recalculates the scan. A progress bar tracks the download. Results remain in the current browser session while you search or download CSVs; those interactions do not trigger another scan. Failed runs clear the old results and show an error. Each result shows its scan date and completion time.

The UI includes Bullish Top 20, Bearish Top 20, All stocks (including failed stocks), Data issues, EMA13 distance, Darvas, Master Trend, Trader workflow and Formula guide. The guide is available before a scan. Every scan fetches approximately 550 calendar days for the indicator calculations. Prices are daily closing bars, not streaming intraday quotes. Yahoo controls data availability and delays.

To deploy on Streamlit Community Cloud, upload this project to your GitHub repository, select that repository and branch in Streamlit, and use `app.py` as the entry point with Python 3.12. Include `discovery.py`, `scan_service.py`, `indicators.py`, `FORMULAS.md`, `requirements.txt`, `data/universe.csv`, and `.streamlit/config.toml`. No Yahoo API key is required. Do not upload virtual environments or cache directories. This package is prepared for deployment; no public deployment has been created.

See https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app for the deployment workflow.

From this folder, with Python 3.10+:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python discovery.py --yahoo --as-of 2026-09-23
```

Replace the date with a completed NSE trading session. Same-day scans require 16:00 IST or later. On Windows use `.venv\Scripts\python.exe`. Open `runs/YYYY-MM-DD/report.html` after completion. No server is needed. No automatic schedule has been installed.

## Formula definitions

The three-day window contains the three trading sessions BEFORE the scan date, excluding the scan date. Highest high = maximum of their highs; lowest low = minimum of their lows; range = highest high minus lowest low. VAH = highest high minus 0.15 times range. VAL = lowest low plus 0.15 times range.

Typical price = (high + low + close) / 3. Monthly AVWAP = sum(typical price times volume) / sum(volume), from the first trading session of the scan month through the completed scan-date bar. This is a daily-bar approximation. VAH/VAL are the PDF's range-derived levels, not volume-profile calculations.

User-approved rules, additional to the PDF:

- Bullish: close strictly above both VAH and AVWAP. Score = 100 times (close / VAH - 1).
- Bearish: close strictly below both VAL and AVWAP. Score = 100 times (1 - close / VAL).
- Rank each group by descending score, with alphabetical symbol ties. Return up to 20 qualifiers. Equality is neutral.

Use `--ranking none` to disable discovery ranking in the original CLI. The Streamlit scan additionally implements EMA13 distance, the supplied five-condition Darvas screen, and Master Trend EMA20 ± 0.10 × ATR14. See FORMULAS.md for all formulas, strict/equality comparisons, history conventions and source attribution. Darvas breakout uses the prior 20 sessions, excluding today, as approved. EMA13 ranking includes stocks only. The original CLI report remains a discovery-only output.

Top-down market/sector research, EMA13 support confirmation, EMA9 rejection and final trading decisions remain manual because exact rules have not been supplied. No orders are placed.

## Inputs and outputs

`data/universe.csv` preserves the workbook's NSE symbols, Yahoo symbols and YES flags. Update it when the universe changes. It is the supplied snapshot, not a live validation of F&O membership.

Yahoo OHLC uses `auto_adjust=False`. Review corporate actions when a calculation window crosses a split or other price discontinuity. The union of Yahoo NIFTY and stock dates provides an inferred session calendar. Disagreements are flagged as provisional. A provider-wide missing session cannot be detected from the same provider alone. In the original CLI, use `--sessions verified_sessions.csv` to override with a verified calendar.

CSV fallback:

```sh
python3 discovery.py --prices prices.csv --sessions sessions.csv --as-of 2026-09-23
```

Price headers: `symbol,date,open,high,low,close,volume`. Dates: YYYY-MM-DD. Symbols: NSE names. Session file header: `date`. Include all exchange sessions from at least three sessions before month start through the scan date, with matching price bars. Missing, duplicate, invalid or stale bars exclude that stock and appear in `data_issues.csv`.

Each run produces full calculations, bullish/bearish Top 20 CSVs, data issues, metadata in `run.json` and `report.html`. Yahoo runs save source prices and sessions for reproducibility. Repeating the same date overwrites its report; choose `--output PATH` to keep separate versions. Exit code 0 means complete, 2 means stocks were excluded for data issues, and 1 means the run failed.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests cover window exclusion, month reset, weighted AVWAP, missing/duplicate sessions, invalid volume, stale data, ranking boundaries and universe size.

Sources: Sandeep_Discovery_Framework_v1.pdf; NSE_FO_Stock_Universe_Sep_2026.xlsx. Yahoo integration reference: https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html
