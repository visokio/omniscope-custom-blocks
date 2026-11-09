"""Writes the invented FlightStats Flex answers used by test_block.R (fictional airlines, codes invented)."""
import json, pathlib

HERE = pathlib.Path(__file__).parent / "canned"
AIRLINES = [
    # fs, iata, icao, name, phone, active. Phone numbers are from ranges reserved for drama and fiction
    # (Ofcom: 020 7946 0xxx, 0161 496 0xxx, 0113, 0117 and 0141 496 0xxx; ComReg: 020 91x xxxx), so none can be real.
    ("ZQ", "ZQ", "ZQA", "Kestrel Coastal Airways", "+44 20 7946 0101", True),
    ("XK", "XK", "XKN", "Northmoor Air", "+44 161 496 0102", True),
    ("QV", "QV", "QVL", "Valebridge Aviation", None, True),
    ("J7", "J7", "JSV", "Juniper Sky", "+353 20 910 0103", True),
    ("WY*", None, "WYF", "Westry Freight", None, True),
    ("H3", "H3", None, "Harbourline Commuter", "+44 113 496 0104", True),
    ("LP", "LP", "LPX", "Lowland Express", "+44 141 496 0105", True),
    ("RB", "RB", "RBR", "Redbeck Regional", None, True),
    ("TF", "TF", "TFA", "Thornfield Air Charter", "+44 113 496 0106", True),
    ("MZ", "MZ", "MZE", "Merrow Island Air", None, True),
    ("OY", "OY", "OYP", "Orrin Bay Airlines", "+44 117 496 0107", True),
    ("KD", "KD", "KDS", "Kingsdale Shuttle", None, True),
]
INACTIVE = [("PX", "PX", "PXO", "Penhallow Airways", None, False),
            ("GA*", None, "GAH", "Glenhaven Air Taxi", None, False)]


def record(t):
    keys = ("fs", "iata", "icao", "name", "phoneNumber", "active")
    return {k: v for k, v in zip(keys, t) if v is not None}


HERE.mkdir(exist_ok=True)
(HERE / "active.json").write_text(json.dumps({"airlines": [record(t) for t in AIRLINES]}, indent=1) + "\n")
(HERE / "all.json").write_text(json.dumps({"airlines": [record(t) for t in AIRLINES + INACTIVE]}, indent=1) + "\n")
(HERE / "error-403.json").write_text(json.dumps({"error": {
    "httpStatusCode": 403, "errorId": "00000000-0000-0000-0000-000000000000",
    "errorMessage": "application is not active", "errorCode": "AUTH_FAILURE"}}, indent=1) + "\n")
