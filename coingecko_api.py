import re
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta


def get_epoch_seconds(date: datetime):
    return int(date.timestamp())


def get_midnight_aligned_date(date: datetime):
    return datetime(date.year, date.month, date.day)


def get_start_of_week_for(date: datetime):
    offset = get_midnight_aligned_date(date)
    return offset + relativedelta(days=-date.weekday())


def get_end_of_week_for(date: datetime):
    offset = get_midnight_aligned_date(date)
    return offset + relativedelta(days=+7 - date.weekday())


def get_iterative_mean(x, n, prev_mean):
    if n == 0:
        return x
    return prev_mean * (n - 1) / n + x / n


def get_name_from_map(coin_name: str):
    name_map = {"erd": "elrond"}
    if coin_name in name_map.keys():
        return name_map[coin_name]
    return "coin_not_found"


def get_custom_mapped_value(coin_name: str):
    coin_symbol = coin_name.split("(")[0].strip().lower()
    coin_id = re.sub('[^A-Za-z0-9]+', '', coin_symbol)
    return coin_id


class CoingeckoAPI:
    def __init__(self, vs_currency):
        self.weekly_averages_for_coin = {}
        self.current_price_for_coin = {}
        self.vs_currency = vs_currency
        self.coins_list = {}
        self.rate_counter = 0

    def get_coins_list(self):
        if not self.coins_list:
            uri = "https://api.coingecko.com/api/v3/coins/list"
            self.coins_list = requests.get(url=uri).json()
        return self.coins_list

    def get_token_weekly_price(self, coingecko_id: str, date: datetime):
        start_timestamp = get_epoch_seconds(get_start_of_week_for(date))
        if coingecko_id not in self.weekly_averages_for_coin.keys():
            self.weekly_averages_for_coin[coingecko_id] = {}
            self.populate_weekly_averages_for_coin(coingecko_id)

        if start_timestamp not in self.weekly_averages_for_coin[coingecko_id].keys():
            return 0
        return self.weekly_averages_for_coin[coingecko_id][start_timestamp]

    def populate_weekly_averages_for_coin(self, coingecko_id: str):
        uri = "https://api.coingecko.com/api/v3/coins/" + coingecko_id \
              + "/market_chart?vs_currency=" + self.vs_currency + "&days=max"
        r = requests.get(url=uri).json()
        price_list = r["prices"]
        self.rate_counter += 1
        n = 0
        period_mean_value = 0
        prev_start_timestamp = 0
        for ts, val in price_list:
            date = datetime.fromtimestamp(ts / 1000)
            start_timestamp = get_epoch_seconds(get_start_of_week_for(date))
            if start_timestamp != prev_start_timestamp:
                n = 0
                period_mean_value = 0
                prev_start_timestamp = start_timestamp

            period_mean_value = get_iterative_mean(val, n, period_mean_value)
            self.weekly_averages_for_coin[coingecko_id][start_timestamp] = period_mean_value
            n += 1

    def get_token_current_price(self, coingecko_id):
        if coingecko_id not in self.current_price_for_coin.keys():
            uri = "https://api.coingecko.com/api/v3/simple/price?ids=" + coingecko_id \
                  + "&vs_currencies=" + self.vs_currency
            r = requests.get(url=uri).json()
            self.current_price_for_coin[coingecko_id] = r[coingecko_id][self.vs_currency]
            self.rate_counter += 1
        return self.current_price_for_coin[coingecko_id]

    def get_coin_id_for_symbol(self, coin_name):
        coins_list = self.get_coins_list()
        coin_custom_name = get_custom_mapped_value(coin_name)
        custom_id = get_name_from_map(coin_name)
        if custom_id != "coin_not_found":
            return custom_id
        for coin in coins_list:
            if coin_custom_name.lower() == coin["symbol"].lower():
                return coin["id"]
        return "coin_not_found"
