import os
import time

import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "orders.csv")


def run(inp=None, **opts):
    return run_block(HERE, inp, opts)


def day(c, d):
    return c[c["Date"].dt.strftime("%Y-%m-%d") == d].iloc[0]


def test_calendar_iso_and_month_fields():
    res = run(start_date="2026-12-28", end_date="2027-01-04").raise_for_error()
    c = res.output(0)
    assert len(c) == 8
    assert day(c, "2027-01-01")["ISO Year Week"] == "2026-W53" and day(c, "2027-01-04")["ISO Year Week"] == "2027-W01"
    assert day(c, "2026-12-31")["Is Year End"] == "Yes" and day(c, "2026-12-31")["Is Quarter End"] == "Yes"
    assert day(c, "2027-01-02")["Day Name"] == "Saturday" and day(c, "2027-01-02")["Is Weekend"] == "Yes"
    assert day(c, "2027-01-01")["Week Start (Monday)"].strftime("%Y-%m-%d") == "2026-12-28"


def test_england_and_scotland_holidays():
    h = run(start_date="2025-01-01", end_date="2025-12-31").raise_for_error().output(1)
    assert len(h) == 8 and "Summer bank holiday" in h["Holiday Name"].tolist()
    s = run(start_date="2025-01-01", end_date="2025-12-31", region="SCOTLAND").raise_for_error().output(1)
    names = dict(zip(s["Date"].dt.strftime("%Y-%m-%d"), s["Holiday Name"]))
    assert names["2025-12-01"] == "St Andrew's Day (substitute day)" and names["2025-08-04"] == "Summer bank holiday"
    assert "Easter Monday" not in names.values()
    us = run(start_date="2025-01-01", end_date="2025-12-31", region="US").raise_for_error().output(1)
    assert "Thanksgiving Day" in us["Holiday Name"].tolist()


def test_working_days_and_custom_holidays():
    c = run(start_date="2025-12-01", end_date="2025-12-31", custom_holidays="2025-12-24=Christmas Eve").raise_for_error().output(0)
    assert day(c, "2025-12-24")["Is Working Day"] == "No" and day(c, "2025-12-24")["Holiday Name"] == "Christmas Eve"
    assert day(c, "2025-12-01")["Working Days In Month"] == 20  # 23 weekdays less 25th, 26th, 24th
    assert day(c, "2025-12-31")["Is Last Working Day Of Month"] == "Yes"
    assert day(c, "2025-12-25")["Next Working Day"].strftime("%Y-%m-%d") == "2025-12-29"
    assert day(c, "2025-12-25")["Previous Working Day"].strftime("%Y-%m-%d") == "2025-12-23"
    assert day(c, "2025-12-02")["Working Day Of Month"] == 2 and pd.isna(day(c, "2025-12-06")["Working Day Of Month"])
    f = run(start_date="2025-12-01", end_date="2025-12-07", weekend="FRI_SAT", region="NONE").raise_for_error().output(0)
    assert day(f, "2025-12-05")["Is Weekend"] == "Yes" and day(f, "2025-12-07")["Is Working Day"] == "Yes"


def test_fiscal_years_and_reference():
    c = run(start_date="2025-03-31", end_date="2025-04-01", fiscal_year_start=4).raise_for_error().output(0)
    assert c["Fiscal Year Name"].tolist() == ["FY2025", "FY2026"] and c["Fiscal Month"].tolist() == [12, 1]
    c = run(start_date="2025-03-31", end_date="2025-04-01", fiscal_year_start=4, fiscal_label="SPAN").raise_for_error().output(0)
    assert c["Fiscal Year Name"].tolist() == ["FY 2024/25", "FY 2025/26"] and c["Fiscal Year Quarter"].tolist()[1] == "FY 2025/26 Q1"
    c = run(start_date="2025-07-01", end_date="2025-07-01", fiscal_year_start=7, fiscal_label="START_YEAR", reference_date="2025-08-15").raise_for_error().output(0)
    assert c["Fiscal Year"].iloc[0] == 2025 and c["Fiscal Day Of Year"].iloc[0] == 1
    assert c["Days From Reference"].iloc[0] == -45 and c["Months From Reference"].iloc[0] == -1 and c["Is Past"].iloc[0] == "Yes"
    c = run(start_date="2025-01-01", end_date="2025-01-01").raise_for_error().output(0)
    assert c["Fiscal Year Name"].iloc[0] == "FY2025" and "Days From Reference" not in c.columns


def test_range_from_input():
    res = run(SAMPLE, date_field="Order Date").raise_for_error()
    c = res.output(0)
    assert c["Date"].min().strftime("%Y-%m-%d") == "2024-01-01" and c["Date"].max().strftime("%Y-%m-%d") == "2025-12-31"
    exact = run(SAMPLE, date_field="Order Date", whole_years=False).raise_for_error().output(0)
    assert len(exact) < len(c)


def test_bad_inputs():
    assert run().status == "aborted"
    assert run(start_date="2025-02-01", end_date="2025-01-01").status == "aborted"
    assert run(start_date="nonsense", end_date="2025-01-01").status == "aborted"
    assert run(pd.DataFrame({"d": ["x", None]}), date_field="d").status == "aborted"
    assert run(start_date="2025-01-01", end_date="2025-01-02", fiscal_year_start=13).status == "aborted"
    c = run(start_date="01/02/2025", end_date="03/02/2025").raise_for_error().output(0)  # day first
    assert len(c) == 3 and c["Month"].iloc[0] == 2


def test_large_range_is_fast():
    t0 = time.time()
    c = run(start_date="1950-01-01", end_date="2100-12-31").raise_for_error().output(0)
    assert time.time() - t0 < 60 and len(c) == 55152
