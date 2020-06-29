import math

import pandas as pd
import matplotlib.pyplot as plt
from dateutil.parser import parse
from coingecko_api import *


def show_formatted(number, icon):
    if icon == "%":
        number *= 100
    return "{:0>2.2f}".format(number) + " " + icon


class PortfolioParser:
    def __init__(self, csv_filepath, vs_currency):
        self.data_ = pd.read_csv(csv_filepath)
        self.api_ = CoingeckoAPI(vs_currency)
        self.balances_ = {}
        self.weekly_valuation_ = {}
        self.valuation_ = {}
        self.earned_values_ = {}
        self.donated_values_ = {}
        self.invested_values_ = {}
        self.yearly_valuation_ = {}
        self.yearly_invested_ = {}
        self.yearly_earned_ = {}
        self.yearly_donated_ = {}
        self.pl_values = {}
        self.populate_balances()
        self.populate_valuation()
        self.populate_yearly_valuation()

    def add_to_weekly_valuation(self, dt):
        for coin_symbol in self.balances_.keys():
            coin_id = self.api_.get_coin_id_for_symbol(coin_symbol)
            price = self.api_.get_token_weekly_price(coin_id, dt)
            if price == 0:
                continue
            if dt not in self.weekly_valuation_.keys():
                self.weekly_valuation_[dt] = 0
            self.weekly_valuation_[dt] += self.balances_[coin_symbol] * price

    def add_to_balances(self, coin_symbol, coin_amount, sign):
        if coin_symbol not in self.balances_.keys():
            self.balances_[coin_symbol] = coin_amount
        else:
            change_amount = sign * coin_amount
            self.balances_[coin_symbol] += change_amount

    def populate_balances(self):
        for i, row in self.data_.iterrows():
            coin_symbol = get_custom_mapped_value(row["Base currency"])
            coin_amount = row["Base amount"]
            dt = parse(row["Date"])
            sign = int(row["Type"] == "BUY") * 2 - 1
            self.add_to_balances(coin_symbol, coin_amount, sign)
            self.add_to_weekly_valuation(dt)
        self.add_to_weekly_valuation(datetime.now())
        self.populate_earned_amounts()

    def populate_valuation(self):
        for key, val in self.balances_.items():
            coin_id = self.api_.get_coin_id_for_symbol(key)
            self.valuation_[key] = self.api_.get_token_current_price(coin_id) * val

    def get_current_valuation(self):
        return self.valuation_

    def get_current_valuation_sum(self):
        return sum(list(self.valuation_.values())) - self.get_donated_sum()

    def get_current_holdings(self):
        return self.balances_

    def get_weekly_valuation(self):
        return self.weekly_valuation_

    def populate_earned_amounts(self):
        for i, row in self.data_.iterrows():
            coin_symbol = get_custom_mapped_value(row["Base currency"])
            coin_amount = row["Base amount"]
            cost = row["Costs/Proceeds"]
            dt = parse(row["Date"])
            date_year_end = datetime(dt.year, 12, 26)
            sign = int(row["Type"] == "BUY") * 2 - 1
            if coin_symbol not in self.earned_values_.keys():
                self.earned_values_[coin_symbol] = 0
                self.donated_values_[coin_symbol] = 0
                self.invested_values_[coin_symbol] = 0
            if date_year_end not in self.yearly_invested_:
                self.yearly_invested_[date_year_end] = 0
                self.yearly_earned_[date_year_end] = 0
                self.yearly_donated_[date_year_end] = 0

            coin_id = self.api_.get_coin_id_for_symbol(coin_symbol)
            price = self.api_.get_token_weekly_price(coin_id, dt)
            if cost == 0:
                if sign > 0:
                    self.earned_values_[coin_symbol] += coin_amount * price
                    self.yearly_earned_[date_year_end] += coin_amount * price
                else:
                    self.donated_values_[coin_symbol] += coin_amount * price
                    self.yearly_donated_[date_year_end] += coin_amount * price
            else:
                self.invested_values_[coin_symbol] += sign * coin_amount * price
                self.yearly_invested_[date_year_end] += sign * coin_amount * price

    def get_earned_amounts(self):
        return self.earned_values_

    def get_earned_sum(self):
        return sum(list(self.earned_values_.values()))

    def get_donated_amounts(self):
        return self.donated_values_

    def get_donated_sum(self):
        return sum(list(self.donated_values_.values()))

    def get_invested_amounts(self):
        return self.invested_values_

    def get_invested_sum(self):
        return sum(list(self.invested_values_.values()))

    def populate_yearly_valuation(self):
        for dt in self.weekly_valuation_.keys():
            date_year_end = datetime(dt.year, 12, 26)
            self.yearly_valuation_[date_year_end] = self.weekly_valuation_[dt]

    def get_yoy_growth(self):
        yoy = {}
        prev_val = 0
        for dt in self.yearly_valuation_.keys():
            if prev_val == 0:
                yoy[dt] = 0
            else:
                yoy[dt] = self.yearly_valuation_[dt] / prev_val
            prev_val = self.yearly_valuation_[dt]

    def get_yearly_pl(self):
        yoy_pl = {}
        for dt in self.yearly_valuation_.keys():
            yoy_pl[dt] = (self.yearly_valuation_[dt]) \
                         / (self.yearly_invested_[dt] + self.yearly_earned_[dt]) - 1
        return yoy_pl

    def get_yearly_pl_without_earnings(self):
        yoy_pl = {}
        for dt in self.yearly_valuation_.keys():
            yoy_pl[dt] = (self.yearly_valuation_[dt] - self.yearly_earned_[dt]) \
                         / (self.yearly_invested_[dt]) - 1
        return yoy_pl

    def get_yearly_earnings(self):
        return self.yearly_earned_

    def get_yearly_invested(self):
        return self.yearly_invested_

    def get_total_pl_to_date(self):
        pl = self.get_current_valuation_sum() / (self.get_invested_sum() + self.get_earned_sum()) - 1
        return pl

    def get_cagr(self):
        ts = next(iter(self.yearly_valuation_))
        starting_valuation = self.yearly_valuation_[ts]
        years_passed = datetime.now().year - ts.year
        cagr = math.pow(self.get_current_valuation_sum() / starting_valuation, 1 / years_passed) - 1
        return cagr


if __name__ == '__main__':
    delta_csv_filepath = "csv/Main Portfolio.csv"
    base_currency = "usd"
    base_currency_icon = "$"
    pp = PortfolioParser(delta_csv_filepath, base_currency)
    holdings = pp.get_current_holdings()
    valuation = pp.get_current_valuation()
    valuation_history = pp.get_weekly_valuation()
    yearly_invested = pp.get_yearly_invested()
    yearly_earned = pp.get_yearly_earnings()
    yearly_pl = pp.get_yearly_pl()
    yearly_pl_without_earnings = pp.get_yearly_pl_without_earnings()

    print("Total amount earned: ", show_formatted(pp.get_earned_sum(), base_currency_icon))
    print("Total amount invested: ", show_formatted(pp.get_invested_sum(), base_currency_icon))
    print("Total donations: ", show_formatted(pp.get_donated_sum(), base_currency_icon))
    print("Total valuation: ", show_formatted(pp.get_current_valuation_sum(), base_currency_icon))
    print("Total P/L: ", show_formatted(pp.get_total_pl_to_date(), "%"))
    print("Total CAGR: ", show_formatted(pp.get_cagr(), "%"))
    print()
    print("Portfolio breakdown:")
    header_template = "{0:8} | {1:20} | {2:20} | {3:10}"
    template = "{0:8} | {1:>20.4f} | {2:>20.4f} | {3:>10.4f}"
    print(header_template.format("Name", "Units", "Value", "Price"))
    for ticker in valuation.keys():
        print(template.format(ticker,
                              holdings[ticker],
                              valuation[ticker],
                              pp.api_.get_token_current_price(pp.api_.get_coin_id_for_symbol(ticker))))

    print()
    template = "{0:8} | {1:20}"
    print("Yearly invested:")
    for date in yearly_invested.keys():
        print(template.format(date.year, show_formatted(yearly_invested[date], base_currency_icon)))

    print("Yearly earnings:")
    for date in yearly_earned.keys():
        print(template.format(date.year, show_formatted(yearly_earned[date], base_currency_icon)))

    print("Yearly P/L:")
    for date in yearly_pl.keys():
        print(template.format(date.year, show_formatted(yearly_pl[date], "%")))

    print("Yearly P/L without earnings:")
    for date in yearly_pl.keys():
        print(template.format(date.year, show_formatted(yearly_pl_without_earnings[date], "%")))

    plt.plot(list(valuation_history.keys()), list(valuation_history.values()))
    plt.ylabel('Weekly valuation')
    plt.show()
