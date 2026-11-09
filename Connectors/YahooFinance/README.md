# Yahoo Finance

For each record, loads the price history of the ticker in a field from Yahoo Finance: open, high, low, close, volume, dividends and splits per day, week, month or shorter interval, between two dates.

The block reads the ticker symbol of every input record, downloads each distinct symbol's history once through the open-source **yfinance** library, and writes one record per period for every input record with that symbol: the input record's own fields first (holding, account, number of shares...), then the prices.

- **Dates**: daily, weekly and monthly bars carry the exchange's own calendar date (a London and a New York close on 1 July both have Date 1 July). Intraday bars (1 hour and shorter) have a **Datetime** field in UTC instead.
- **Prices** are in the currency the exchange quotes (London shares usually in pence), adjusted for splits and dividends (yfinance's default). **Volume** is a whole number; **Dividends** and **Stock Splits** are 0 except on the days they happen; funds may also have **Capital Gains**.
- Symbols are trimmed and upper-cased; empty values are skipped. Symbols with no prices (unknown, delisted, or no trading in the range) are counted in the block's message.
- If Yahoo Finance limits the server's requests, the block stops with a message rather than writing a partial result.

Yahoo Finance offers no official API for this: yfinance reads the data the Yahoo Finance website uses and is not affiliated with Yahoo. Its documentation says the data is intended for personal use and points to Yahoo's terms of use. It can change or stop without notice; check the terms before relying on it for business use.

## Language and libraries

Python. It uses yfinance (Apache License 2.0) and pandas (BSD 3-Clause). Omniscope installs yfinance on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

- **Input 1**: records with a text field of ticker symbols as Yahoo Finance writes them: `AAPL`, `VOD.L` (London), `BMW.DE` (Frankfurt), `^FTSE` (an index), `GBPUSD=X` (an exchange rate).

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Ticker field | `Ticker` | Field | The field with the ticker symbols. From input 1. |
| Start date | `Start` | Text | The first day, written YYYY-MM-DD (included). Default 2025-01-01. |
| End date | `End` | Text | The day after the last one, written YYYY-MM-DD (not included). Empty: up to today. |
| Interval | `Interval` | Choice | One record per 3 months, 1 month (the default), 1 week, 5 days, 1 day, 1 hour, 30, 15 or 5 minutes (`3mo`, `1mo`, `1wk`, `5d`, `1d`, `1h`, `30m`, `15m`, `5m`). |

## Outputs

- **Prices** (`Output Data`): the input's fields (a field named like a price field gets ` (input)` added), then **Date** (or **Datetime** for intraday intervals), **Open**, **High**, **Low**, **Close**, **Volume**, **Dividends**, **Stock Splits**, and **Capital Gains** when any symbol has them. Input records whose symbol has no prices are left out.

## Limits

- Intraday intervals reach back about 60 days (1 hour: about two years); older ranges return no prices.
- Each distinct symbol is one download; Yahoo Finance may refuse many requests in a short time.
- Prices are not converted between currencies; join to an exchange-rate history (for example the `GBPUSD=X` symbol through this block) to compare.

## Source

[script.py](script.py)

The tests in `tests/` run the script against invented price histories for fictional companies (`tests/canned/`, written by `tests/make_canned.py`, which also writes `sample-data/holdings.csv`), with a stand-in for the yfinance library. `sample-data/placeholder.csv` is the block's output for those histories, for trying a workflow without a connection to Yahoo Finance.
