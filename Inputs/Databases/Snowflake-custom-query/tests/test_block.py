"""Snowflake Custom Query block tests. No call reaches Snowflake: a stand-in `snowflake.connector` module answers from
the canned result saved beside this file (query-result.json) with the Python types the real connector returns
(int, Decimal, datetime.date, time-zone-aware datetime), and records the connection settings and the SQL."""
import datetime
import decimal
import json
import os
import sys
import time
import types

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
TESTS = os.path.join(HERE, "tests")
PLACEHOLDER = os.path.join(HERE, "sample-data", "placeholder.csv")
OPTS = {"account": "myorg-myaccount", "user": "OMNI_READER", "password": "not-a-real-password",
        "warehouse": "COMPUTE_WH", "database": "SUPPORT"}


def canned():
    with open(os.path.join(TESTS, "query-result.json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    convert = {"TEXT": str, "FIXED0": int, "FIXED2": decimal.Decimal, "DATE": datetime.date.fromisoformat,
               "TIMESTAMP_TZ": datetime.datetime.fromisoformat, "TIME": datetime.time.fromisoformat}
    kinds = [k for _, k in payload["description"]]
    rows = [tuple(None if v is None else convert[k](v) for v, k in zip(r, kinds)) for r in payload["rows"]]
    names = [n for n, _ in payload["description"]]
    return payload["sql"], names, rows


class FakeSnowflake:
    def __init__(self):
        self.connects, self.executed, self.closed = [], [], 0
        self.results = {}  # sql -> (column names, rows) or an exception
        self.connect_error = None
        fake = self

        class Cursor:
            description = None

            def execute(self, sql):
                fake.executed.append(sql)
                result = fake.results.get(sql)
                if result is None:
                    raise FakeSnowflake.ProgrammingError(
                        "001003 (42000): SQL compilation error:\nsyntax error line 1 at position 0 unexpected 'SELEC'.")
                names, self.rows = result
                self.description = None if names is None else [(n, 0, None, None, None, None, True) for n in names]

            def fetchall(self):
                return list(self.rows)

        class Connection:
            def cursor(self):
                return Cursor()

            def close(self):
                fake.closed += 1

        def connect(**params):
            fake.connects.append(params)
            if fake.connect_error:
                raise fake.connect_error
            return Connection()

        self.connector = types.ModuleType("snowflake.connector")
        self.connector.connect = connect

    class ProgrammingError(Exception):
        pass


@pytest.fixture
def sf(monkeypatch):
    fake = FakeSnowflake()
    pkg = types.ModuleType("snowflake")
    pkg.connector = fake.connector
    monkeypatch.setitem(sys.modules, "snowflake", pkg)
    monkeypatch.setitem(sys.modules, "snowflake.connector", fake.connector)
    return fake


def sample(sf):
    sql, names, rows = canned()
    sf.results[sql] = (names, rows)
    return sql


def test_runs_the_query_and_maps_types(sf):
    sql = sample(sf)
    res = run_block(HERE, None, {**OPTS, "custom_sql": sql}).raise_for_error()
    out = res.output(0)
    assert len(out) == 16 and list(out.columns) == ["TEAM", "WEEK_START", "TICKETS", "AVG_HOURS_TO_CLOSE",
                                                    "LAST_UPDATED"]
    assert sf.connects == [{"account": "myorg-myaccount", "user": "OMNI_READER", "application": "Omniscope",
                            "password": "not-a-real-password", "warehouse": "COMPUTE_WH", "database": "SUPPORT"}]
    assert sf.executed == [sql] and sf.closed == 1
    # NUMBER(10,2) arrives as Decimal: now a decimal field; mixed time-zone offsets: one UTC date field
    assert out["AVG_HOURS_TO_CLOSE"].dtype == "float64"
    assert str(out["LAST_UPDATED"].dt.tz) == "UTC"
    assert out["LAST_UPDATED"].iloc[2] == pd.Timestamp("2026-02-02T22:12:00Z")  # 17:12 at -05:00
    assert pd.api.types.is_datetime64_any_dtype(out["WEEK_START"])
    assert pd.api.types.is_integer_dtype(out["TICKETS"]) and out["TICKETS"].sum() == 1404


def test_matches_the_placeholder_sample(sf):
    out = run_block(HERE, None, {**OPTS, "custom_sql": sample(sf)}).raise_for_error().output(0)
    got = pd.read_csv(pd.io.common.StringIO(out.to_csv(index=False)))
    pd.testing.assert_frame_equal(got, pd.read_csv(PLACEHOLDER))


def test_query_errors_abort_with_snowflakes_message(sf):
    # The original called omniscope_api.error(), which does not exist, so the real message was lost
    # behind "'OmniscopeApi' object has no attribute 'error'"
    res = run_block(HERE, None, {**OPTS, "custom_sql": "SELEC 1"})
    assert res.status == "aborted" and "SQL compilation error" in res.final_message and sf.closed == 1


def test_empty_result_keeps_its_fields(sf):
    # The original wrote no output for an empty result
    sf.results["q"] = (["TEAM", "TICKETS"], [])
    out = run_block(HERE, None, {**OPTS, "custom_sql": "q"}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["TEAM", "TICKETS"]


def test_key_pair_sign_in_and_optional_context(sf, tmp_path):
    key = tmp_path / "rsa_key.p8"
    key.write_text("-----BEGIN ENCRYPTED PRIVATE KEY-----\n...\n")
    sql = sample(sf)
    opts = {"account": "myorg-myaccount", "user": "OMNI_SERVICE", "private_key_file": str(key),
            "private_key_password": "passphrase", "schema": "PUBLIC", "role": "ANALYST", "custom_sql": sql}
    run_block(HERE, None, opts).raise_for_error()
    assert sf.connects[0] == {"account": "myorg-myaccount", "user": "OMNI_SERVICE", "application": "Omniscope",
                              "private_key_file": str(key), "private_key_file_pwd": "passphrase",
                              "schema": "PUBLIC", "role": "ANALYST"}


def test_duplicate_column_names_are_numbered(sf):
    sf.results["q"] = (["ID", "ID", "NAME"], [(1, 2, "a")])
    out = run_block(HERE, None, {**OPTS, "custom_sql": "q"}).raise_for_error().output(0)
    assert list(out.columns) == ["ID", "ID_2", "NAME"]


def test_time_and_missing_values(sf):
    rows = [(datetime.time(9, 30), None, decimal.Decimal("1.50")), (None, None, None)]
    sf.results["q"] = (["OPENS", "NOTHING", "PRICE"], rows)
    out = run_block(HERE, None, {**OPTS, "custom_sql": "q"}).raise_for_error().output(0)
    assert out["OPENS"].iloc[0] == "09:30:00" and out["PRICE"].tolist()[0] == 1.5 and pd.isna(out["PRICE"].iloc[1])


def test_statement_without_a_table(sf):
    sf.results["USE ROLE ANALYST"] = (None, [])
    res = run_block(HERE, None, {**OPTS, "custom_sql": "USE ROLE ANALYST"}).raise_for_error()
    assert res.output(0) is None and "no table" in res.final_message


def test_bad_settings_abort_before_connecting(sf, tmp_path):
    for bad in ({"account": ""}, {"user": None}, {"password": None}, {"custom_sql": "  "},
                {"password": None, "private_key_file": str(tmp_path / "missing.p8")}):
        res = run_block(HERE, None, {**OPTS, "custom_sql": "q", **bad})
        assert res.status == "aborted", bad
    assert sf.connects == []
    sf.connect_error = FakeSnowflake.ProgrammingError("250001: Incorrect username or password was specified.")
    res = run_block(HERE, None, {**OPTS, "custom_sql": "q"})
    assert res.status == "aborted" and "Could not connect" in res.final_message and "Incorrect" in res.final_message


def test_large_result(sf):
    n = 200_000
    rows = [(i, decimal.Decimal(i) / 100, datetime.date(2026, 1, 1 + i % 28)) for i in range(n)]
    sf.results["big"] = (["ID", "AMOUNT", "DAY"], rows)
    t0 = time.time()
    out = run_block(HERE, None, {**OPTS, "custom_sql": "big"}).raise_for_error().output(0)
    assert time.time() - t0 < 30 and len(out) == n and out["AMOUNT"].dtype == "float64"
