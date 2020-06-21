import pandas as pd
import psycopg2 as pg
import pandas.io.sql as psql
import numpy as np
import random
import datetime
from dateutil.relativedelta import relativedelta
import calendar
import os
import csv


def roll_list(list_numbers, new_value):
    list_numbers.pop(0)
    list_numbers.append(new_value)
    return list_numbers


def tag_current_day(std, current_day_ret):
    if current_day_ret >= 2 * std:
        return 'E'
    if current_day_ret < 2 * std and current_day_ret >= std:
        return 'C'
    if current_day_ret < std and current_day_ret >= 0:
        return 'A'
    if current_day_ret < 0 and current_day_ret >= -std:
        return 'B'
    if current_day_ret < -std and current_day_ret >= 2 * -std:
        return 'D'
    if current_day_ret < 2 * -std:
        return 'F'


def create_new_tag_pattern(current_tag_pattern, current_day_tag):
    return current_tag_pattern[1:] + current_day_tag


# Need to handle situations where the pattern doesn't exist. This means that this
# pattern has never ocurred If we can't find the pattern let's randomly
# select from the tag bin
def get_ret_bin(tag_pattern, tagged_returns_df, tag_returns_bin_df):
    try:
        return tagged_returns_df.loc[tag_pattern]
    except:
        # print(tag_pattern, end='', flush=True)
        current_tag = tag_pattern[-1]
        return tag_returns_bin_df.loc[current_tag]


def get_ret_bin_from_array(tag_pattern, tagged_returns, tag_returns):
    try:
        return tagged_returns[tag_pattern]
    except:
        current_tag = tag_pattern[-1]
        return tag_returns[current_tag]


def monthly_option_expiration(date):
    day = 21 - (calendar.weekday(date.year, date.month, 1) + 2) % 7
    return datetime.datetime(date.year, date.month, day)


def upcoming_friday(test_date):
    return test_date + datetime.timedelta((4-test_date.weekday()+7) % 7)


def generate_expiry_dates(today):
    expiry_dates = []
    # Add upcoming friday
    expiry_dates.append(upcoming_friday(today))
    # Add following friday
    expiry_dates.append(upcoming_friday(today + datetime.timedelta(7)))
    # Current month expiry
    # This could be before today is we're past the third friday of the month
    # Need to error when using this list
    expiry_dates.append(monthly_option_expiration(today).date())
    # Next month expiry
    next_month = today.replace(day=1) + relativedelta(months=1)
    expiry_dates.append(monthly_option_expiration(next_month).date())
    # Following month expiry
    following_month = today.replace(day=1) + relativedelta(months=2)
    expiry_dates.append(monthly_option_expiration(following_month).date())
    return expiry_dates


def following_month_expiry(date):
    # finds the options exipiry date two months out
    following_month = date.replace(day=1) + relativedelta(months=2)
    return monthly_option_expiration(following_month).date()


# def generate_projected_returns(filepath, ticker_symbol, generations, days_ahead, expiry_date):
#     # Build dataframe for returns by tag patterns
#     df = pd.read_csv(filepath)
#     tagged_returns_df = df.groupby(['tag_pattern'])[
#         'next_ret'].apply(list)
#     # Build dataframe for return by tag
#     # We use this as a fallback in case a tag pattern doesn't exist
#     tag_returns_bin_df = df.groupby(['tag'])['next_ret'].apply(list)
#     last_20_returns = df.tail(20)['ret'].to_list()
#     # Init rojected returns dataframe
#     projected_returns_df = pd.DataFrame(
#         columns=['generation', 'day', 'tag_pattern', 'ret', 'price'])
#     for i in range(1, generations + 1):
#         print(".", end="", flush=True)
#         current_tag_pattern = df.iloc[-1]['tag_pattern']
#         price = df.iloc[-1]['adj_close']
#         for j in range(1, days_ahead + 1):
#             # Find bin of next returns by tag pattern
#             next_ret_bin = get_ret_bin(
#                 current_tag_pattern, tagged_returns_df, tag_returns_bin_df)
#             current_ret = random.choice(next_ret_bin)
#             current_std = np.std(last_20_returns)
#             current_tag = tag_current_day(current_std, current_ret)
#             current_tag_pattern = create_new_tag_pattern(
#                 current_tag_pattern, current_tag)
#             price = price * (1 + current_ret)
#             last_20_returns = roll_list(last_20_returns, current_ret)
#             projected_returns_df = projected_returns_df.append(
#                 {
#                     'generation': i,
#                     'day': j,
#                     'tag_pattern': current_tag_pattern,
#                     'ret': current_ret,
#                     'price': price
#                 }, ignore_index=True)
#     now_ts = str(datetime.datetime.now())
#     projected_returns_df['timestamp'] = now_ts
#     projected_returns_df['ticker'] = ticker_symbol
#     projected_returns_df['expiry_date'] = str(expiry_date)
#     returns_path = "/tmp/%s_projected_returns.csv" % ticker_symbol
#     projected_returns_df.to_csv(returns_path, index=False)

def generate_projected_returns(filepath, ticker_symbol, generations, days_ahead, expiry_date):
    # Build dataframe for returns by tag patterns
    # df = pd.read_csv(filepath)
    with open(filepath) as f:
        reader = csv.reader(f)
        next(reader)
        # tag_pattern_returns = generate_tagged_returns(reader)
        returns = read_returns_from_reader(reader)
    tag_pattern_returns = generate_tagged_returns(returns)
    tag_returns = generate_tag_returns(returns)
    last_20_returns = list(map(lambda x: x['ret'], returns[-20:]))
    projected_returns = []
    now_ts = str(datetime.datetime.now())
    for i in range(1, generations + 1):
        print(".", end="", flush=True)
        current_tag_pattern = returns[-1]['tag_pattern']
        price = returns[-1]['adj_close']
        for j in range(1, days_ahead + 1):
            next_ret_bin = get_ret_bin_from_array(
                current_tag_pattern, tag_pattern_returns, tag_returns)
            current_ret = random.choice(next_ret_bin)
            current_std = np.std(last_20_returns)
            current_tag = tag_current_day(current_std, current_ret)
            current_tag_pattern = create_new_tag_pattern(
                current_tag_pattern, current_tag)
            price = price * (1 + current_ret)
            last_20_returns = roll_list(last_20_returns, current_ret)
            projected_returns.append(
                {
                    'generation': i,
                    'day': j,
                    'tag_pattern': current_tag_pattern,
                    'ret': current_ret,
                    'price': price,
                    'timestamp': now_ts,
                    'ticker': ticker_symbol,
                    'expiry_date': str(expiry_date)
                })
    returns_path = "/tmp/%s_projected_returns.csv" % ticker_symbol
    write_returns(returns_path, projected_returns)


def read_returns_from_reader(reader):
    returns = []
    for row in reader:
        d = {
            "idx": row[0],
            "dt": row[1],
            "adj_close": float(row[2]),
            "ret": float(row[3]),
            "next_ret": float(row[4]),
            "abs_ret": float(row[5]),
            "std_dev": float(row[6]),
            "tag": row[7],
            "tag_pattern": row[8]
        }
        returns.append(d)
    return returns


def generate_tagged_returns(returns):
    hash_map = {}
    for ret in returns:
        k = ret['tag_pattern']
        v = ret['next_ret']
        # print(k)
        if k not in hash_map:
            hash_map[k] = [v]
        else:
            hash_map[k].append(v)
    return hash_map


def generate_tag_returns(returns):
    hash_map = {}
    for ret in returns:
        k = ret['tag']
        v = ret['next_ret']
        # print(k)
        if k not in hash_map:
            hash_map[k] = [v]
        else:
            hash_map[k].append(v)
    return hash_map


def write_returns(returns_path, projected_returns):
    with open(returns_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        for p in projected_returns:
            writer.writerow([p['generation'], p['day'], p['tag_pattern'], p['ret'],
                             p['price'], p['timestamp'], p['ticker'], p['expiry_date']])


# def generate_projected_returns(filepath, ticker_symbol, generations, days_ahead, expiry_date):
#     command_string = """RUST_LOG=debug clotho -f {filepath} -x {expiry_date} -t {ticker_symbol} -g {generations} -d {days}"""
#     args = command_string.format(
#         filepath=filepath,
#         expiry_date=expiry_date,
#         ticker_symbol=ticker_symbol,
#         generations=generations,
#         days=days_ahead
#     )
#     cmd = os.popen(args)
if __name__ == "__main__":
    print("Initializing")
    today = datetime.date.today()
    ticker_symbol = "AAPL"
    expiry_date = following_month_expiry(today)
    formatted_ticker = "[%s]" % ticker_symbol
    print(formatted_ticker, "Updating model")
    print(formatted_ticker, "Generating data for expiry date: ", expiry_date)
    # Number of projections you want to run
    generations = 500
    filepath = '/tmp/aapl.csv'
    # Number of days ahead you want to project
    days_ahead = np.busday_count(today, expiry_date)
    generate_projected_returns(
        filepath, ticker_symbol, generations, days_ahead, expiry_date)
