from pytrends.request import TrendReq
from datetime import datetime, timedelta

class SleepingTrendReq(TrendReq):
    def __init__(self, hl='en-US', tz=360, geo='', proxies='', sleep_time=0):
        TrendReq.__init__(self, hl, tz, geo, proxies)
        self.sleep_time = sleep_time
        self.last_req_time = datetime(1990,1,1,0,0,0)

    def update_last_req_time(self):
        self.last_req_time = datetime.now()