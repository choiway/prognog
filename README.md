# 80x faster Rust code?! 

Projecting security prices using brut force methods is expensive but some times it's the only way to satisfy a curiousity. I was curious about how current volatility would affect future prices so I wrote a Python script to project Apple stock prices. After prototyping the algorithm in Python, I optmized the price generation part of the code in Rust. 

The actual projections aren't as interesting as the near 99% decrease in execution time it took to generate prices. In Python it took `2 minutes and 3 seconds` to generate prices while in Rust it took a mere `1.5 seconds`. 

I only have a vague notion as to why the Rust implementation is so much faster. I consider myself a naive user of both languages and didn't implement any language level optimizations. I do use Pandas in the Python code and I have no idea if Pandas is optimized for certain types of computations and not for others.

**Update 2020-06-20** Figured out where the bottleneck was in the Python. It had to do with Pandas and how I was updating a data frame from which I would write to a csv. I refactored to using a Python list and got the time down to `1.7s` with just Python code. The Rust code is still faster but not by much. 

## Projected Prices

The algorithm used to project future prices generates a price for each projected day by randomly selecting a return from historical returns. The historical returns are categorized by 3-day volatility patterns based on the current day return relative to the standard deviation of returns over the previous 20 days.

For each day projected day, we randomly select from a list of returns associated with a 3-day volatility pattern and multiply the current price by 1 + the return. For this analysis, we projected prices for 49 days 500 times resulting in 24,500 projected prices. In Python I used a dataframe for this look up while in Rust, I used a HashMap.

## The Optimization

The part of the code of that was optmized in Rust does the following:

1. Opens a csv file of historical returns
2. Groups the returns to a hashmap where the key is tag pattern and the value is a list of returns 
3. Creates another hash map with the current day tag and a corresponding list of returns (This is used as a fallback if the tag pattern doesn't exist)
4. For each generation it generates prices for the number of days and pushes it into an array of projected prices. The only significant calculation it performs here is one standard deviation calculation.
5. Write the array of projected prices to a csv file

Again, I didn't optimize code in either language. When writing the Rust code, I had an idea of data that I wanted to reference because I thought moves would be expensive and just did what the Rust compiler told me to until my code worked. 

Here's the primary Python function that got ported to Rust. 

```python
def generate_projected_returns(filepath, ticker_symbol, generations, days_ahead, expiry_date):
    df = pd.read_csv(filepath)
    tagged_returns_df = df.groupby(['tag_pattern'])[
        'next_ret'].apply(list)
    tag_returns_bin_df = df.groupby(['tag'])['next_ret'].apply(list)
    last_20_returns = df.tail(20)['ret'].to_list()
    projected_returns_df = pd.DataFrame(
        columns=['generation', 'day', 'tag_pattern', 'ret', 'price'])
    for i in range(1, generations + 1):
        print(".", end="", flush=True)
        current_tag_pattern = df.iloc[-1]['tag_pattern']
        price = df.iloc[-1]['adj_close']
        for j in range(1, days_ahead + 1):
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

You can find the full python code in the `prog.py` file in this repository.

To run the Rust binary, `clotho`, from the Python script I use `os.popen`. Once I had the Rust implementation working, I used the same function call and executed the Rust binary.

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

## Take Aways

I'm still suprised by how much faster the Rust code given that it's not taking advantage of concurrency. 

I figure the read and write is constrained by the hard drive so I'm guessing most of the gain comes from the look ups which probably benefits from manual memory management in Rust.

Ignoring the fact that I don't know how I would optimize the Python code, I do wonder what the performance difference would be if I looked into optimizing the Python code before writing it in Rust. 

I really like working with Rust's ecosystem. Online documentation is good and Cargo is great. 

I used `peroxide` to calculate standard deviations but was surprised that there aren't more math/data science libraries for Rust.

The `clap` Crate is awesome and really simplified the passing and parsing of commnand line arguments in Rust. 

The big takeaway is that, as someone with more of a finance background, I'm pleasantly suprised by how Rust makes writing performant code accessible. 
