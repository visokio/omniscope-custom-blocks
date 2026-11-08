"""Yahoo Finance: for each record of the input, the price history of the ticker in a field (open, high, low,
close, volume, dividends, splits) between two dates at a chosen interval, from Yahoo Finance via the yfinance
library. Each distinct ticker is downloaded once."""
import re

import pandas as pd
import yfinance as yf
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

INTRADAY = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}
VALID = INTRADAY | {"1d", "5d", "1wk", "1mo", "3mo"}
PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits", "Capital Gains"]


def option_text(name):
    value = omniscope_api.get_option(name)
    return "" if value is None else str(value).strip()


def parse_date(text, title):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        omniscope_api.abort(f"{title} must be a date written YYYY-MM-DD, such as 2025-01-31; got '{text}'.")
    try:
        return pd.Timestamp(text)
    except ValueError:
        omniscope_api.abort(f"{title} '{text}' is not a valid date.")


def tidy(hist, intraday):
    """yfinance's frame (index: exchange-local times) -> a Date or Datetime field plus the price fields.
    Daily and longer bars keep the exchange's calendar date; intraday bars are converted to UTC."""
    hist = hist.copy()
    index = pd.DatetimeIndex(hist.index)
    if intraday:
        name = "Datetime"
        when = index.tz_convert("UTC") if index.tz is not None else index.tz_localize("UTC")
    else:
        name = "Date"
        local = index.tz_localize(None) if index.tz is not None else index
        when = local.normalize().tz_localize("UTC")
    hist.index = range(len(hist))
    out = pd.DataFrame({name: when})
    for c in PRICE_COLUMNS:
        if c in hist.columns:
            out[c] = hist[c].to_numpy()
    return out


ticker_field = omniscope_api.get_option("Ticker")
start_text, end_text = option_text("Start"), option_text("End")
interval = option_text("Interval") or "1d"

input_data = omniscope_api.read_input_records(input_number=0)
if input_data is None:
    omniscope_api.abort("Connect a block with a field of ticker symbols to the input.")
if not ticker_field or ticker_field not in input_data.columns:
    omniscope_api.abort("Choose the field that holds the ticker symbols in 'Ticker field'.")
if interval not in VALID:
    omniscope_api.abort(f"Unknown interval '{interval}'.")
if not start_text:
    omniscope_api.abort("Enter a start date (YYYY-MM-DD).")
start = parse_date(start_text, "Start date")
end = parse_date(end_text, "End date") if end_text else None
if end is not None and end <= start:
    omniscope_api.abort(f"End date {end_text} must be after the start date {start_text} (the end date is not "
                        "included).")
intraday = interval in INTRADAY

# Distinct tickers, in input order
tickers = []
for value in input_data[ticker_field].tolist():
    if value is None or value is pd.NA or (isinstance(value, float) and pd.isna(value)):
        continue
    text = str(value).strip().upper()
    if text and text not in tickers:
        tickers.append(text)

prices, missing, failed = {}, [], []
for n, ticker in enumerate(tickers, 1):
    omniscope_api.update_message(f"Ticker {n} of {len(tickers)}: {ticker}")
    try:
        hist = yf.Ticker(ticker).history(start=start_text, end=end_text or None, interval=interval)
    except Exception as e:  # yfinance raises its own classes; the rate limit one means stop now
        if type(e).__name__ == "YFRateLimitError":
            omniscope_api.abort("Yahoo Finance is limiting requests from this server (too many requests). "
                                "Try again later, or with fewer tickers.")
        failed.append(f"{ticker} ({type(e).__name__}: {e})")
        continue
    if hist is None or len(hist) == 0:
        missing.append(ticker)
        continue
    prices[ticker] = tidy(hist, intraday)

when_field = "Datetime" if intraday else "Date"
present = [c for c in PRICE_COLUMNS if any(c in p.columns for p in prices.values())] or PRICE_COLUMNS[:7]
out_fields = [when_field] + present
# The input's fields come first, renamed with " (input)" where they clash with a price field
renamed = {c: (f"{c} (input)" if c in out_fields else c) for c in input_data.columns}

parts = []
for idx in range(len(input_data)):
    value = input_data[ticker_field].iloc[idx]
    key = None if value is None or value is pd.NA or (isinstance(value, float) and pd.isna(value)) \
        else str(value).strip().upper()
    if key not in prices:
        continue
    p = prices[key].reindex(columns=out_fields)
    record = input_data.iloc[[idx] * len(p)].reset_index(drop=True).rename(columns=renamed)
    parts.append(pd.concat([record, p.reset_index(drop=True)], axis=1))

if parts:
    output = pd.concat(parts, ignore_index=True)
else:
    output = pd.concat([input_data.iloc[0:0].rename(columns=renamed).reset_index(drop=True),
                        pd.DataFrame({when_field: pd.Series(dtype="datetime64[ns, UTC]"),
                                      **{c: pd.Series(dtype="float64") for c in present}})], axis=1)
for c in present:
    if c == "Volume":
        output[c] = pd.to_numeric(output[c], errors="coerce").round().astype("Int64")
    else:
        output[c] = pd.to_numeric(output[c], errors="coerce").astype("float64")

omniscope_api.write_output_records(output, output_number=0)
message = f"{len(output)} price records for {len(prices)} of {len(tickers)} ticker(s), interval {interval}."
if missing:
    message += (f" No prices for {len(missing)}, such as '{missing[0]}' (unknown symbol, or no trading in the "
                "range" + ("; intraday prices reach back about 60 days at most" if intraday else "") + ").")
if failed:
    message += f" Failed: {failed[0]}" + (f" and {len(failed) - 1} more." if len(failed) > 1 else ".")
omniscope_api.close(message)
