"""Tests for the Yahoo Finance block against invented price histories (tests/canned/<ticker>.csv, written by
tests/make_canned.py). No test calls Yahoo: the yfinance module is replaced by a fake whose Ticker.history
answers from the canned files the way yfinance does (exchange-local times, empty frame for an unknown symbol)."""
import os
import sys
import time
import types

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
SAMPLE = pd.read_csv(os.path.join(HERE, "sample-data", "holdings.csv"))
ZONES = {"QLMK": "America/New_York", "HLDW.L": "Europe/London", "LGRW.DE": "Europe/Berlin"}
Q3 = {"Ticker": "Ticker", "Start": "2026-07-01", "End": "2026-10-01", "Interval": "1d"}
WEEKDAYS = pd.bdate_range("2026-07-01", "2026-09-30")
# Each exchange's own weekday closures in the quarter (tests/make_canned.py leaves those days out).
CLOSED = {"QLMK": ["2026-07-03", "2026-09-07"], "HLDW.L": ["2026-08-31"], "LGRW.DE": []}
DAYS = {t: len(WEEKDAYS) - len(c) for t, c in CLOSED.items()}  # 64 New York, 65 London, 66 Frankfurt
TOTAL = 2 * DAYS["QLMK"] + DAYS["HLDW.L"] + DAYS["LGRW.DE"]  # H-1 and H-4 hold QLMK: 259


class YFRateLimitError(Exception):
    pass


def daily(symbol):
    df = pd.read_csv(os.path.join(CANNED, f"{symbol}.csv"))
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("Date"), utc=True).dt.tz_convert(ZONES[symbol]), name="Date")
    return df


def fake_yfinance(calls):
    class Ticker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, start=None, end=None, interval="1d", **kw):
            calls.append({"symbol": self.symbol, "start": start, "end": end, "interval": interval, **kw})
            if self.symbol == "LIMIT":
                raise YFRateLimitError("Too Many Requests. Rate limited. Try after a while.")
            if self.symbol == "BOOM":
                raise ValueError("unexpected answer")
            if self.symbol not in ZONES:
                return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits"])
            df = daily(self.symbol)
            local = df.index.tz_localize(None)
            keep = local >= pd.Timestamp(start)
            if end:
                keep &= local < pd.Timestamp(end)
            df = df[keep]
            if interval in ("1wk", "1mo"):
                key = df.index.tz_localize(None).to_period("W-SUN" if interval == "1wk" else "M").start_time
                g = df.groupby(key)
                df = pd.DataFrame({"Open": g["Open"].first(), "High": g["High"].max(), "Low": g["Low"].min(),
                                   "Close": g["Close"].last(), "Volume": g["Volume"].sum(),
                                   "Dividends": g["Dividends"].sum(), "Stock Splits": g["Stock Splits"].sum()})
                df.index = pd.DatetimeIndex(df.index).tz_localize(ZONES[self.symbol]).rename("Date")
            elif interval == "1h":
                bars = []
                for day, row in df.tail(2).iterrows():
                    for h in range(7):
                        bars.append((day.replace(hour=9, minute=30) + pd.Timedelta(hours=h), row))
                df = pd.DataFrame([r for _, r in bars], index=pd.DatetimeIndex([t for t, _ in bars], name="Datetime"))
            return df

    module = types.ModuleType("yfinance")
    module.Ticker = Ticker
    return module


@pytest.fixture
def yahoo(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "yfinance", fake_yfinance(calls))
    return calls


def run(df=SAMPLE, **options):
    return run_block(HERE, [df], {**Q3, **options})


def test_daily_prices_of_the_sample(yahoo):
    res = run().raise_for_error()
    out = res.output(0)
    assert out.columns.tolist() == ["Holding", "Account", "Ticker", "Company", "Shares", "Date", "Open", "High",
                                    "Low", "Close", "Volume", "Dividends", "Stock Splits"]
    assert out.groupby("Holding").size().to_dict() == {"H-1": DAYS["QLMK"], "H-2": DAYS["HLDW.L"],
                                                   "H-3": DAYS["LGRW.DE"], "H-4": DAYS["QLMK"]}
    assert len(out) == TOTAL == 259
    assert str(out["Volume"].dtype) == "Int64" and str(out["Close"].dtype) == "float64"
    assert out.loc[out["Ticker"] == "HLDW.L", "Dividends"].sum() == pytest.approx(9.8 * 1)
    assert res.final_message == (f"{TOTAL} price records for 3 of 4 ticker(s), interval 1d. No prices for 1, "
                                 "such as 'MRBY' (unknown symbol, or no trading in the range).")


def test_exchanges_in_different_time_zones_give_one_date_field(yahoo):
    # The original concatenated New York, London and Frankfurt times: a Date field of mixed time zones
    # (pandas object dtype), which does not arrive in Omniscope as a date.
    out = run().raise_for_error().output(0)
    assert str(out["Date"].dt.tz) == "UTC"
    first = out.groupby("Ticker")["Date"].min()
    assert (first == pd.Timestamp("2026-07-01", tz="UTC")).all()  # the exchange's own date, not shifted
    assert out["Date"].max() == pd.Timestamp("2026-09-30", tz="UTC")


def test_each_exchange_keeps_its_own_trading_days(yahoo):
    # The invented histories follow each exchange's calendar: no New York bar on 3 July or 7 September,
    # no London bar on 31 August, and Frankfurt open on all three; the block passes these dates through.
    out = run().raise_for_error().output(0)
    dates = {t: set(g["Date"].dt.strftime("%Y-%m-%d")) for t, g in out.groupby("Ticker")}
    for ticker, closed in CLOSED.items():
        assert len(dates[ticker]) == DAYS[ticker]
        assert not dates[ticker] & set(closed), ticker
    assert {"2026-07-03", "2026-08-31", "2026-09-07"} <= dates["LGRW.DE"]
    assert "2026-08-31" in dates["QLMK"] and "2026-07-03" in dates["HLDW.L"]


def test_each_ticker_is_downloaded_once(yahoo):
    run().raise_for_error()
    assert [c["symbol"] for c in yahoo] == ["QLMK", "HLDW.L", "LGRW.DE", "MRBY"]
    assert yahoo[0]["start"] == "2026-07-01" and yahoo[0]["end"] == "2026-10-01" and yahoo[0]["interval"] == "1d"


def test_symbols_are_trimmed_and_upper_cased(yahoo):
    df = pd.DataFrame({"Ticker": [" qlmk ", "QLMK", None, ""], "Note": ["a", "b", "c", "d"]})
    out = run(df).raise_for_error().output(0)
    assert out.groupby("Note").size().to_dict() == {"a": DAYS["QLMK"], "b": DAYS["QLMK"]}
    assert len(yahoo) == 1


def test_weekly_interval(yahoo):
    out = run(Interval="1wk").raise_for_error().output(0)
    nw = out[out["Holding"] == "H-1"]
    assert len(nw) == 14 and (nw["Date"].dt.dayofweek == 0).all()
    assert yahoo[0]["interval"] == "1wk"


def test_intraday_times_are_utc(yahoo):
    out = run(pd.DataFrame({"Ticker": ["QLMK"]}), Interval="1h", Start="2026-09-01").raise_for_error().output(0)
    assert out.columns[1] == "Datetime" and "Date" not in out.columns
    assert out["Datetime"].iloc[0] == pd.Timestamp("2026-09-29 13:30", tz="UTC")  # 09:30 New York


def test_end_date_may_be_empty(yahoo):
    run(pd.DataFrame({"Ticker": ["QLMK"]}), End="").raise_for_error()
    assert yahoo[0]["end"] is None


def test_bad_dates_abort(yahoo):
    for opts, text in [({"Start": "01/07/2026"}, "Start date must be a date written YYYY-MM-DD"),
                       ({"Start": "2026-02-30"}, "is not a valid date"),
                       ({"End": "2026-06-30"}, "must be after the start date"),
                       ({"Start": ""}, "Enter a start date")]:
        res = run(**opts)
        assert res.status == "aborted" and text in res.final_message, opts
    assert yahoo == []


def test_no_prices_at_all_gives_empty_output_with_fields(yahoo):
    out = run(pd.DataFrame({"Ticker": ["MRBY", "ZZZZ"]})).raise_for_error().output(0)
    assert len(out) == 0 and out.columns.tolist()[:3] == ["Ticker", "Date", "Open"]


def test_empty_input(yahoo):
    out = run(SAMPLE.iloc[0:0]).raise_for_error().output(0)
    assert len(out) == 0 and "Close" in out.columns and "Company" in out.columns and yahoo == []


def test_input_field_named_like_a_price_field(yahoo):
    df = pd.DataFrame({"Ticker": ["LGRW.DE"], "Close": [50.0]})
    out = run(df).raise_for_error().output(0)
    assert out.columns.tolist()[:3] == ["Ticker", "Close (input)", "Date"] and out["Close (input)"].eq(50.0).all()


def test_rate_limit_stops_other_errors_are_reported(yahoo):
    res = run(pd.DataFrame({"Ticker": ["QLMK", "LIMIT", "LGRW.DE"]}))
    assert res.status == "aborted" and "limiting requests" in res.final_message
    res = run(pd.DataFrame({"Ticker": ["BOOM", "QLMK"]})).raise_for_error()
    assert len(res.output(0)) == DAYS["QLMK"] and "Failed: BOOM (ValueError: unexpected answer)" in res.final_message


def test_wrong_types_and_missing_choices(yahoo):
    res = run(pd.DataFrame({"Ticker": [1, 2]})).raise_for_error()  # numbers are tried as symbols
    assert len(res.output(0)) == 0 and "No prices for 2" in res.final_message
    assert run_block(HERE, None, Q3).status == "aborted"
    res = run_block(HERE, [SAMPLE], {**Q3, "Ticker": None})
    assert res.status == "aborted" and "Ticker field" in res.final_message


def test_many_records(yahoo):
    df = pd.concat([SAMPLE] * 600, ignore_index=True)  # 3,000 records, 4 distinct tickers
    started = time.perf_counter()
    out = run(df).raise_for_error().output(0)
    assert len(out) == 600 * TOTAL and len(yahoo) == 4
    assert time.perf_counter() - started < 60
