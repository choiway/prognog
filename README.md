# Two minute Python job, 1.5 seconds with Rust

Projecting security prices using brut force methods is expensive but often times it's the only way satisfy a curiousity. This time around, I was curious about how current volatility would affect future prices so I projected prices of a Apple stock for 60 days 500 times. I prototyped the algorithms in Python but then refactored the actual price generator in Rust. 

I didn't find the actual projections as interesting at the near 99% decrease in time it took to generate the price. In Python it took 2 minutes and 3 seconds to generate prices while in Rust it took a mere 1.5 seconds. 

### Python Timing

```
time python prog.py

Initializing
[AAPL] Updating model
[AAPL] Generating data for expiry date:  2020-08-21
[AAPL] saving csv to:  /tmp/AAPL_projected_returns.csv

real    2m3.124s
user    2m2.566s
sys     0m0.556s

wc -l AAPL_projected_returns.csv
24501 AAPL_projected_returns.csv  # writes a header
```


### Rust Timing

```
Initializing
[AAPL] Updating model
[AAPL] Generating data for expiry date:  2020-08-21
[2020-06-15T20:13:04Z INFO  clotho] [AAPL] from /tmp/aapl.csv
[2020-06-15T20:13:04Z INFO  clotho] [AAPL] Writing csv

real    0m1.502s
user    0m0.690s
sys     0m0.813s

wc -l AAPL_projected_returns.csv
24500 AAPL_projected_returns.csv
```

I'll say upfront I only have a vague idea of why the Rust implementation is so much faster but will say that I would consider myself an average user of both languages and didn't do any optmizations in either language. I do use Pandas in the Python code but the part of Python code that I rewrote in Rust is effectively two for loops.

## Projected Prices

The algorithm used to project future prices generates a price for each day by randomly selecting a return from historical returns. The historical returns are categorized by 3-day volatility patterns based on the current day return relative to the 20-day standard deviation of returns. 

For each day that we need to project forward, we randomly select from a list of returns associated with a 3-day volatility pattern and multiply the current price by 1 + the return. For this analysis, projected prices for 49 days 500 times resulting in 24,500 projected prices.

## The Optimization

The part of the code of that was optmized in Rust does the following:

1. Opens a csv file of historical returns
2. Groups the returns to a hashmap where the key is tag pattern and the value is a list of returns 
3. Creates another hash map with the current day tag (This is used as a fallback if the tag pattern doesn't exist)
4. For each generation is generates prices for the number of days and pushes it into an array
5. Write the prices stored in the array to a csv

Here's the primary function that got ported to Rust. 

```python
def generate_projected_returns(filepath, ticker_symbol, generations, days_ahead, expiry_date):
    # Build dataframe for returns by tag patterns
    df = pd.read_csv(filepath)
    tagged_returns_df = df.groupby(['tag_pattern'])[
        'next_ret'].apply(list)
    # Build dataframe for return by tag
    # We use this as a fallback in case a tag pattern doesn't exist
    tag_returns_bin_df = df.groupby(['tag'])['next_ret'].apply(list)
    last_20_returns = df.tail(20)['ret'].to_list()
    # Init rojected returns dataframe
    projected_returns_df = pd.DataFrame(
        columns=['generation', 'day', 'tag_pattern', 'ret', 'price'])
    for i in range(1, generations + 1):
        print(".", end="", flush=True)
        current_tag_pattern = df.iloc[-1]['tag_pattern']
        price = df.iloc[-1]['adj_close']
        for j in range(1, days_ahead + 1):
            # Find bin of next returns by tag pattern
            next_ret_bin = get_ret_bin(
                current_tag_pattern, tagged_returns_df, tag_returns_bin_df)
            current_ret = random.choice(next_ret_bin)
            current_std = np.std(last_20_returns)
            current_tag = tag_current_day(current_std, current_ret)
            current_tag_pattern = create_new_tag_pattern(
                current_tag_pattern, current_tag)
            price = price * (1 + current_ret)
            last_20_returns = roll_list(last_20_returns, current_ret)
            projected_returns_df = projected_returns_df.append(
                {
                    'generation': i,
                    'day': j,
                    'tag_pattern': current_tag_pattern,
                    'ret': current_ret,
                    'price': price
                }, ignore_index=True)
    now_ts = str(datetime.datetime.now())
    projected_returns_df['timestamp'] = now_ts
    projected_returns_df['ticker'] = ticker_symbol
    projected_returns_df['expiry_date'] = str(expiry_date)
    returns_path = "/tmp/%s_projected_returns.csv" % ticker_symbol
    projected_returns_df.to_csv(returns_path, index=False)
```

You can find the full python in the `prog.py` file of this directory.

The run the Rust binary, `clotho`, from the Python script I use `os.popen`. Which is cool but would be better if it just accepted an array of commands.

```python
def generate_projected_returns(filepath, ticker_symbol, generations, days_ahead, expiry_date):
    command_string = """RUST_LOG=debug clotho -f {filepath} -x {expiry_date} -t {ticker_symbol} -g {generations} -d {days}"""
    args = command_string.format(
        filepath=filepath,
        expiry_date=expiry_date,
        ticker_symbol=ticker_symbol,
        generations=generations,
        days=days_ahead
    )
    cmd = os.popen(args)
```

The Rust code is verbose so I'm not including it here but here's a [gist](https://gist.github.com/choiway/a1bb9d92f5753a5b7781b3814e40ba77). 




