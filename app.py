from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from discovery import ROOT, universe, FIELDS
from scan_service import run_scan
from indicators import INDICATOR_FIELDS

st.set_page_config(page_title='Sandeep Discovery', page_icon='📊', layout='wide')
st.title('Sandeep Discovery')
st.caption('Daily stock discovery · Three-session levels and monthly anchored VWAP')
active = universe(ROOT / 'data/universe.csv')
now = datetime.now(ZoneInfo('Asia/Kolkata'))
latest = now.date() if (now.hour, now.minute) >= (16, 0) else now.date() - timedelta(days=1)
while latest.weekday() >= 5:
    latest -= timedelta(days=1)
with st.sidebar:
    st.header('Scan settings')
    as_of = st.date_input('Completed trading session', value=latest, max_value=latest)
    st.caption('Daily closing bars. For exchange holidays, select the previous trading session.')
    st.metric('Stocks in universe', len(active))
    st.caption('Every Run Scan click requests Yahoo data again for every enabled stock. Prices may be delayed by Yahoo.')
    clicked = st.button('Run Scan', type='primary', width="stretch")
    with st.expander('Qualification rules'):
        st.write('Bullish: close > VAH and monthly AVWAP. Bearish: close < VAL and monthly AVWAP.')
        st.write('Rank by percentage distance beyond VAH or VAL. Previous three sessions exclude the scan date.')
        st.caption('Discovery only. Apply your existing trading framework before making decisions.')

if clicked:
    # Clear old results before attempting a new scan. Never reuse a cached scan.
    st.session_state.pop('scan', None)
    st.session_state.pop('scan_error', None)
    bar = st.progress(0, text=f'Requesting fresh data for {len(active)} stocks…')
    try:
        st.session_state['scan'] = run_scan(as_of, lambda n, total, symbol: bar.progress(n / total, text=f'{n}/{total} stocks fetched · {symbol}'))
    except Exception as exc:
        st.session_state['scan_error'] = str(exc)
    finally:
        bar.empty()

if st.session_state.get('scan_error'):
    st.error('Scan failed: ' + st.session_state.scan_error)
    st.info('Check the selected session and Yahoo availability, then click Run Scan to retry all stocks.')

scan = st.session_state.get('scan')
tabs = st.tabs(['Bullish Top 20', 'Bearish Top 20', 'All stocks', 'Data issues',
                'EMA13 distance', 'Darvas', 'Master Trend', 'Trader workflow', 'Formula guide'])
with tabs[8]:
    st.markdown((ROOT / 'FORMULAS.md').read_text())
if scan:
    st.subheader(f'Results for {scan["as_of"]}')
    st.caption('Completed ' + scan['completed_at'] + ' · Yahoo Finance')
    if scan['as_of'] != str(as_of):
        st.info('The date selection changed. Click Run Scan to calculate the selected date. Results below retain their original date.')
    if scan['provisional']:
        st.warning(scan['calendar_note'])
    if scan['errors']:
        st.warning(f'{len(scan["errors"])} stocks could not be calculated. See Data issues. Rankings cover available stocks only.')
    if scan.get('indicator_errors'):
        st.warning(f'{len(scan["indicator_errors"])} stocks have unavailable indicators. See indicator history issues; missing indicators are not failed conditions.')
    cols = st.columns(4)
    cols[0].metric('Scanned', len(scan['universe']))
    cols[1].metric('Calculated', len(scan['results']))
    cols[2].metric('Bullish', sum(r['classification'] == 'BULLISH' for r in scan['results']))
    cols[3].metric('Bearish', sum(r['classification'] == 'BEARISH' for r in scan['results']))
    if 'indicator_rows' not in scan:
        st.info('Run Scan again to calculate the newly added indicators.')
    def show(rows, fields, name):
        frame = pd.DataFrame(rows, columns=fields).replace('', None)
        if frame.empty:
            st.info('No matching stocks for this scan.')
        else:
            st.dataframe(frame, hide_index=True, width="stretch",
                         column_config={k: st.column_config.NumberColumn(format='%.2f') for k in ['close','vah','val','monthly_avwap','score_pct'] if k in fields})
        st.download_button('Download CSV', frame.to_csv(index=False).encode('utf-8'),
                           file_name=f'{name}_{scan["as_of"]}.csv', mime='text/csv', key=name)
    with tabs[0]:
        show(scan['bullish'], FIELDS, 'bullish_top20')
    with tabs[1]:
        show(scan['bearish'], FIELDS, 'bearish_top20')
    with tabs[2]:
        search = st.text_input('Search NSE symbol').strip().upper()
        computed = {r['symbol']: r for r in scan['results']}
        errors = {r['symbol']: r['issue'] for r in scan['errors']}
        technical_errors = {r['symbol']: r['issue'] for r in scan.get('indicator_errors', [])}
        all_rows = [dict(computed.get(item['symbol'], {'symbol': item['symbol'], 'classification': 'DATA ISSUE'}), issue=errors.get(item['symbol'], '')) for item in scan['universe']]
        metrics = {r['symbol']: r for r in scan.get('indicator_rows', [])}
        for row in all_rows:
            row.update({k: v for k, v in metrics.get(row['symbol'], {}).items() if k in INDICATOR_FIELDS})
            row['indicator_issue'] = technical_errors.get(row['symbol'], '')
        show([r for r in all_rows if search in r['symbol']], FIELDS + INDICATOR_FIELDS + ['issue', 'indicator_issue'], 'all_stocks')
    with tabs[3]:
        if not scan['errors']:
            st.success('All stocks have the required bars for the inferred session calendar.')
        show(scan['errors'], ['symbol', 'issue'], 'data_issues')
        st.subheader('Indicator history issues')
        show(scan.get('indicator_errors', []), ['symbol', 'issue'], 'indicator_issues')
    with tabs[4]:
        st.caption('Stocks only. Ranked by absolute distance to EMA13, closest first.')
        show(scan.get('ema13_ranked', []),
             ['ema13_rank', 'symbol', 'close', 'ema13', 'ema13_distance_pct', 'ema13_abs_distance_pct', 'history_bars', 'warmup_note'], 'ema13_distance')
    with tabs[5]:
        st.caption('All five strict conditions must pass. High breakout uses the previous 20 sessions, excluding today.')
        only_pass = st.checkbox('Show only Darvas matches', value=True)
        rows = scan.get('indicator_rows', [])
        show([r for r in rows if r['darvas_pass'] or not only_pass],
             ['symbol', 'close', 'darvas_pass', 'sma10', 'ema20', 'sma50', 'previous_20_high', 'volume_sma20'] +
             [k for k in INDICATOR_FIELDS if k.startswith('darvas_') and k != 'darvas_pass'], 'darvas')
        st.caption(f"{sum(r['darvas_pass'] for r in rows)} matches among {len(rows)} stocks with available indicators.")
    with tabs[6]:
        st.caption('Pine defaults: EMA20, Wilder ATR14, bands ±0.10 × ATR. Close = EMA20 is bullish.')
        side = st.selectbox('Master Trend direction', ['All', 'BULLISH', 'BEARISH'])
        show([r for r in scan.get('indicator_rows', []) if side == 'All' or r['master_trend'] == side],
             ['symbol', 'close', 'ema20', 'atr14', 'master_upper', 'master_lower', 'master_trend', 'warmup_note'], 'master_trend')
    with tabs[7]:
        st.subheader('Shortlist review')
        st.caption('Discovery Top 20 lists with your setup indicators. These are review candidates, not trade approvals.')
        show(scan['bullish'] + scan['bearish'],
             ['symbol', 'classification', 'rank', 'score_pct', 'close', 'ema13_distance_pct', 'master_trend', 'darvas_pass'] +
             [k for k in INDICATOR_FIELDS if k.startswith('darvas_') and k != 'darvas_pass'], 'trader_review')
        st.info('Manual review remains required for market regime, sector confidence, EMA13 support, EMA9 rejection, entry, stop and risk. Exact rules for these checks have not yet been supplied.')
else:
    with tabs[0]:
        st.info(f'Choose a completed session and click Run Scan to calculate all {len(active)} stocks. The Formula guide is available before running.')
    with tabs[2]:
        st.dataframe(pd.DataFrame(active), hide_index=True, width="stretch")
