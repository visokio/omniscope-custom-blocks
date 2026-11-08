"""Writes the invented FlightStats Flex Schedules answers used by test_block.R.

Airlines, airports and flights are fictional. One file per request: <carrier>-<number>-<yyyy>-<mm>-<dd>.json.
A request with no file is answered with no scheduled flights (the block's "not in the schedules" case).
"""
import json, pathlib

HERE = pathlib.Path(__file__).parent / "canned" / "schedules"


def leg(carrier, number, dep, arr, dep_time, arr_time, equipment, stops=0, dep_term=None, arr_term=None,
        codeshare=False, codeshares=(), classes=("Y",), restrictions=(), ref="0"):
    r = {"carrierFsCode": carrier, "flightNumber": number, "departureAirportFsCode": dep,
         "arrivalAirportFsCode": arr, "stops": stops, "departureTime": dep_time + ".000",
         "arrivalTime": arr_time + ".000", "flightEquipmentIataCode": equipment, "isCodeshare": codeshare,
         "isWetlease": False, "serviceType": "J", "serviceClasses": list(classes),
         "trafficRestrictions": list(restrictions), "codeshares": [], "referenceCode": ref}
    if dep_term:
        r["departureTerminal"] = dep_term
    if arr_term:
        r["arrivalTerminal"] = arr_term
    r["codeshares"] = [{"carrierFsCode": c, "flightNumber": n, "serviceType": "J", "serviceClasses": ["Y"],
                        "trafficRestrictions": ["Q"], "referenceCode": 1000 + i}
                       for i, (c, n) in enumerate(codeshares)]
    return r


FLIGHTS = {
    ("ZQ", "214", "2026-11-16"): [leg("ZQ", "214", "KQB", "NMR", "2026-11-16T07:10:00", "2026-11-16T08:05:00",
                                      "AT7", dep_term="1", codeshares=[("XK", "5214")], classes=("Y", "J"))],
    ("XK", "88", "2026-11-17"): [leg("XK", "88", "NMR", "JNP", "2026-11-17T09:40:00", "2026-11-17T10:55:00",
                                     "320", dep_term="2", arr_term="1", classes=("Y", "J"))],
    ("XK", "88", "2026-11-24"): [leg("XK", "88", "NMR", "JNP", "2026-11-24T09:40:00", "2026-11-24T10:55:00",
                                     "320", dep_term="2", arr_term="1", classes=("Y", "J"))],
    ("J7", "1402", "2026-11-18"): [leg("J7", "1402", "JNP", "VLB", "2026-11-18T13:20:00", "2026-11-18T14:30:00",
                                       "E75", codeshare=True, codeshares=[("XK", "1402"), ("OY", "7402")],
                                       restrictions=("Q",))],
    ("LP", "6", "2026-11-18"): [leg("LP", "6", "LWX", "KQB", "2026-11-18T16:00:00", "2026-11-18T16:45:00",
                                    "SF3")],
    ("OY", "2210", "2026-11-20"): [leg("OY", "2210", "ORB", "NMR", "2026-11-20T08:30:00", "2026-11-20T10:05:00",
                                       "73H", arr_term="2", classes=("Y", "W", "J"))],
    ("TF", "77", "2026-11-25"): [
        leg("TF", "77", "RBK", "TFD", "2026-11-25T06:50:00", "2026-11-25T07:25:00", "DH4", ref="1"),
        leg("TF", "77", "TFD", "HBL", "2026-11-25T08:05:00", "2026-11-25T09:35:00", "DH4", ref="2"),
    ],
}

HERE.mkdir(parents=True, exist_ok=True)
for (carrier, number, date), legs in FLIGHTS.items():
    y, m, d = date.split("-")
    answer = {"request": {"departing": True, "url": "https://api.flightstats.com/flex/schedules/rest/v1/json/flight/"
                          f"{carrier}/{number}/departing/{y}/{int(m)}/{int(d)}",
                          "airline": {"requestedCode": carrier, "fsCode": carrier},
                          "flight": {"requested": number, "interpreted": number},
                          "date": {"year": y, "month": str(int(m)), "day": str(int(d)), "interpreted": date}},
              "scheduledFlights": legs, "appendix": {"airlines": [], "airports": [], "equipments": []}}
    (HERE / f"{carrier}-{number}-{date}.json").write_text(json.dumps(answer, indent=1) + "\n")
(HERE.parent / "error-403.json").write_text(json.dumps({"error": {
    "httpStatusCode": 403, "errorId": "00000000-0000-0000-0000-000000000000",
    "errorMessage": "application is not active", "errorCode": "AUTH_FAILURE"}}, indent=1) + "\n")
