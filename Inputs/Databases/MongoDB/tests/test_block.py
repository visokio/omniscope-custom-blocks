"""MongoDB block tests. No call reaches a MongoDB server: a stand-in `pymongo` module serves the canned documents saved
beside this file (enrolments.json, in MongoDB Extended JSON) as the driver would return them (ObjectId, Decimal128,
datetime, nested dicts and lists), applies simple equality and $gte queries, and records how the block connected."""
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
OPTS = {"database": "college", "collection": "enrolments"}


class ObjectId:
    def __init__(self, oid):
        self.oid = oid

    def __str__(self):
        return self.oid


class Decimal128:
    def __init__(self, text):
        self.text = text

    def to_decimal(self):
        return decimal.Decimal(self.text)

    def __str__(self):
        return self.text


def from_extended_json(value):
    if isinstance(value, dict):
        if "$oid" in value:
            return ObjectId(value["$oid"])
        if "$numberDecimal" in value:
            return Decimal128(value["$numberDecimal"])
        if "$date" in value:  # pymongo returns naive UTC datetimes by default
            return datetime.datetime.fromisoformat(value["$date"].replace("Z", "+00:00")).replace(tzinfo=None)
        return {k: from_extended_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [from_extended_json(v) for v in value]
    return value


def canned():
    with open(os.path.join(TESTS, "enrolments.json"), encoding="utf-8") as fh:
        return [from_extended_json(d) for d in json.load(fh)]


def matches(doc, query):
    for key, cond in (query or {}).items():
        value = doc
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(cond, dict) and "$gte" in cond:
            if not isinstance(value, (int, float)) or value < cond["$gte"]:
                return False
        elif value != cond:
            return False
    return True


class FakePymongo:
    def __init__(self, collections):
        self.collections = collections  # {(db, collection): [documents]}
        self.clients, self.finds, self.limits, self.closed = [], [], [], 0
        self.error = None
        fake = self

        class Cursor:
            def __init__(self, docs):
                self.docs = docs

            def limit(self, n):
                fake.limits.append(n)
                return Cursor(self.docs[:n] if n else self.docs)

            def __iter__(self):
                if fake.error:
                    raise fake.error
                return iter(self.docs)

        class Collection:
            def __init__(self, key):
                self.key = key

            def find(self, query=None):
                fake.finds.append((self.key, query))
                return Cursor([d for d in fake.collections.get(self.key, []) if matches(d, query)])

        class Database:
            def __init__(self, name):
                self.name = name

            def __getitem__(self, name):
                return Collection((self.name, name))

        class MongoClient:
            def __init__(self, *args, **kwargs):
                fake.clients.append((args, kwargs))

            def __getitem__(self, name):
                return Database(name)

            def close(self):
                fake.closed += 1

        self.module = types.ModuleType("pymongo")
        self.module.MongoClient = MongoClient

    class ServerSelectionTimeoutError(Exception):
        pass


@pytest.fixture
def mongo(monkeypatch):
    def install(docs=None):
        fake = FakePymongo({("college", "enrolments"): canned() if docs is None else docs})
        monkeypatch.setitem(sys.modules, "pymongo", fake.module)
        return fake
    return install


def test_reads_the_whole_collection(mongo):
    fake = mongo()
    res = run_block(HERE, None, OPTS).raise_for_error()
    out = res.output(0)
    assert len(out) == 10 and list(out.columns) == ["_id", "name", "age", "course", "fees", "enrolled", "address",
                                                    "modules"]
    assert fake.clients == [((), {"host": "127.0.0.1", "port": 27017, "serverSelectionTimeoutMS": 20000})]
    assert fake.finds == [(("college", "enrolments"), None)] and fake.closed == 1
    # ObjectId and Decimal128 (which the original passed through as driver objects) become text and numbers
    assert out["_id"].iloc[0] == "6650a1b2c3d4e5f6a7b8c900"
    assert out["fees"].tolist()[:3] == [9250.0, 9250.0, 11400.5]
    assert out["address"].iloc[0] == '{"town": "Leeds", "postcode": "LS2"}' and pd.isna(out["address"].iloc[7])
    assert out["modules"].iloc[6] == "[]" and json.loads(out["modules"].iloc[2])[1] == "Databases"
    assert pd.api.types.is_datetime64_any_dtype(out["enrolled"])
    # "age" holds a number in nine documents and "unknown" in one: text, so the field keeps every value
    assert out["age"].tolist()[4:6] == ["21", "unknown"]


def test_matches_the_placeholder_sample(mongo):
    mongo()
    out = run_block(HERE, None, OPTS).raise_for_error().output(0)
    got = pd.read_csv(pd.io.common.StringIO(out.to_csv(index=False)))
    pd.testing.assert_frame_equal(got, pd.read_csv(PLACEHOLDER))


def test_custom_query_and_limit(mongo):
    fake = mongo()
    q = '{"address.town": "Leeds"}'
    out = run_block(HERE, None, {**OPTS, "full_data": False, "query": q}).raise_for_error().output(0)
    assert out["name"].tolist() == ["Amira Haddad", "Chloe Evans", "Erin Walsh", "Jamal Reid"]
    assert fake.finds[-1][1] == {"address.town": "Leeds"}
    out = run_block(HERE, None, {**OPTS, "full_data": False, "query": q, "limit": 2}).raise_for_error().output(0)
    assert len(out) == 2 and fake.limits == [2]
    # Whole collection ticked: the query is ignored
    out = run_block(HERE, None, {**OPTS, "full_data": True, "query": q}).raise_for_error().output(0)
    assert len(out) == 10


def test_numbers_only_field_stays_numeric(mongo):
    mongo()
    out = run_block(HERE, None, {**OPTS, "full_data": False, "query": '{"age": {"$gte": 20}}'}).raise_for_error()
    ages = out.output(0)["age"]
    assert pd.api.types.is_numeric_dtype(ages) and ages.min() >= 20 and len(ages) == 7


def test_cleared_connection_url_uses_host_and_port(mongo):
    # The original passed an emptied URL ("") to MongoClient and ignored Host and Port
    fake = mongo()
    run_block(HERE, None, {**OPTS, "connection_url": "", "host": "db.example.com", "port": 27018}).raise_for_error()
    assert fake.clients[0] == ((), {"host": "db.example.com", "port": 27018, "serverSelectionTimeoutMS": 20000})
    url = "mongodb+srv://reader:secret@cluster0.example.net/"
    run_block(HERE, None, {**OPTS, "connection_url": url}).raise_for_error()
    assert fake.clients[1] == ((url,), {"serverSelectionTimeoutMS": 20000})


def test_user_and_password_without_authentication_database(mongo):
    # The original only signed in when the authentication database was filled in as well, and then forced
    # SCRAM-SHA-256, which older servers and users created with SCRAM-SHA-1 refuse
    fake = mongo()
    run_block(HERE, None, {**OPTS, "user": "reader", "password": "secret"}).raise_for_error()
    kwargs = fake.clients[0][1]
    assert kwargs["username"] == "reader" and kwargs["authSource"] == "admin" and "authMechanism" not in kwargs
    run_block(HERE, None, {**OPTS, "user": "reader", "password": "secret", "auth_source": "college"})
    assert fake.clients[1][1]["authSource"] == "college"


def test_empty_collection(mongo):
    mongo([])
    res = run_block(HERE, None, OPTS).raise_for_error()
    assert res.output(0) is None and res.final_message == "The collection is empty"


def test_bad_settings_abort_with_a_message(mongo):
    fake = mongo()
    res = run_block(HERE, None, {**OPTS, "full_data": False, "query": "{age: 20}"})
    assert res.status == "aborted" and "not valid JSON" in res.final_message
    res = run_block(HERE, None, {**OPTS, "full_data": False, "query": "[1, 2]"})
    assert res.status == "aborted" and "JSON object" in res.final_message
    for bad in ({"collection": ""}, {"database": None}, {"limit": -1}, {"user": "reader"}):
        assert run_block(HERE, None, {**OPTS, **bad}).status == "aborted", bad
    assert fake.clients == []
    fake.error = FakePymongo.ServerSelectionTimeoutError("db.example.com:27017: timed out, Timeout: 20.0s, "
                                                         "Topology Description: <...>")
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and res.final_message == ("MongoDB: ServerSelectionTimeoutError: "
                                                             "db.example.com:27017: timed out")


def test_large_collection(mongo):
    n = 100_000
    docs = [{"_id": ObjectId(f"{i:024x}"), "n": i, "tags": ["a", "b"], "meta": {"k": i % 7}} for i in range(n)]
    mongo(docs)
    t0 = time.time()
    out = run_block(HERE, None, OPTS).raise_for_error().output(0)
    assert time.time() - t0 < 60 and len(out) == n and out["n"].iloc[-1] == n - 1
