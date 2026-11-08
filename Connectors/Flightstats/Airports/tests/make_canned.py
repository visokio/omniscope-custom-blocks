"""Writes the invented FlightStats Flex answers used by test_block.R (fictional airports, codes invented)."""
import json, pathlib

HERE = pathlib.Path(__file__).parent / "canned"
# fs, iata, icao, name, city, cityCode, countryCode, countryName, regionName, tz, utcOffset, lat, lon, elev, class
AIRPORTS = [
    ("KQB", "KQB", "EGXQ", "Kestrel Bay Airport", "Kestrel Bay", "KQB", "GB", "United Kingdom", "Europe",
     "Europe/London", 0.0, 54.61234, -3.20412, 98, 3),
    ("NMR", "NMR", "EGXN", "Northmoor International", "Northmoor", "NMR", "GB", "United Kingdom", "Europe",
     "Europe/London", 0.0, 53.47121, -2.31055, 257, 1),
    ("VLB", "VLB", "EGXV", "Valebridge Airport", "Valebridge", "VLB", "GB", "United Kingdom", "Europe",
     "Europe/London", 0.0, 52.10342, -1.88231, 312, 3),
    ("JNP", "JNP", "EIXJ", "Juniper Point Airport", "Juniper Point", "JNP", "IE", "Ireland", "Europe",
     "Europe/Dublin", 0.0, 53.30521, -6.40118, 210, 2),
    ("HBL", "HBL", "EGXH", "Harbourline Heliport", "Harbourline", "HBL", "GB", "United Kingdom", "Europe",
     "Europe/London", 0.0, 57.19813, -2.07725, 30, 5),
    ("LWX", "LWX", "EGXL", "Lowland Airport", "Glenmuir", "GLM", "GB", "United Kingdom", "Europe",
     "Europe/London", 0.0, 55.87102, -4.43391, 26, 2),
    ("ORB", "ORB", "ENXO", "Orrin Bay Airport", "Orrin Bay", "ORB", "NO", "Norway", "Europe",
     "Europe/Oslo", 1.0, 60.18877, 11.10291, 681, 2),
    ("MRW", "MRW", None, "Merrow Island Airstrip", "Merrow", "MRW", "GB", "United Kingdom", "Europe",
     "Europe/London", 0.0, 58.21455, -6.33102, 15, 5),
    ("TFD", None, "EGXT", "Thornfield Aerodrome", "Thornfield", "TFD", "GB", "United Kingdom", "Europe",
     "Europe/London", 0.0, 53.80211, -1.66012, 681, 4),
    ("RBK", "RBK", "EGXR", "Redbeck Airport", "Redbeck", "RBK", "GB", "United Kingdom", "Europe",
     "Europe/London", 0.0, 54.51109, -1.42934, 120, 3),
]
INACTIVE = [("PNH", "PNH", "EGXP", "Penhallow Airfield", "Penhallow", "PNH", "GB", "United Kingdom", "Europe",
             "Europe/London", 0.0, 50.21877, -5.01218, 340, 5, False)]
KEYS = ("fs", "iata", "icao", "name", "city", "cityCode", "countryCode", "countryName", "regionName",
        "timeZoneRegionName", "utcOffsetHours", "latitude", "longitude", "elevationFeet", "classification", "active")


def record(t):
    t = t + (True,) if len(t) == 15 else t
    r = {k: v for k, v in zip(KEYS, t) if v is not None}
    r["localTime"] = "2026-11-06T10:15:00.000" if r["utcOffsetHours"] == 0 else "2026-11-06T11:15:00.000"
    r["delayIndexUrl"] = "https://api.flightstats.com/flex/delayindex/rest/v1/json/airports/" + r["fs"] + "?codeType=fs"
    return r


HERE.mkdir(exist_ok=True)
(HERE / "active.json").write_text(json.dumps({"airports": [record(t) for t in AIRPORTS]}, indent=1) + "\n")
(HERE / "all.json").write_text(json.dumps({"airports": [record(t) for t in AIRPORTS + INACTIVE]}, indent=1) + "\n")
(HERE / "error-403.json").write_text(json.dumps({"error": {
    "httpStatusCode": 403, "errorId": "00000000-0000-0000-0000-000000000000",
    "errorMessage": "application is not active", "errorCode": "AUTH_FAILURE"}}, indent=1) + "\n")
