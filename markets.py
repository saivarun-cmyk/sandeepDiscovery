from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

MARKETS = {
    'IN': dict(label='Indian stocks', universe='universe.csv', timezone='Asia/Kolkata',
               ready_hour=16, top_n=20, benchmark='^NSEI', currency='INR'),
    'US': dict(label='US stocks', universe='us_universe.csv', timezone='America/New_York',
               ready_hour=18, top_n=8, benchmark='^GSPC', currency='USD'),
}


def latest_date(market, now=None):
    config = MARKETS[market]
    local = (now or datetime.now(ZoneInfo(config['timezone']))).astimezone(ZoneInfo(config['timezone']))
    day = local.date() if local.hour >= config['ready_hour'] else local.date() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day
