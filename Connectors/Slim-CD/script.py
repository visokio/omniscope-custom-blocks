from __future__ import annotations

from typing import Any, Dict, List, Optional
import json

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

SLIMCD_URL = "https://stats.slimcd.com/soft/json/jsonscript.asp"
SERVICE = "SearchTransactions2"
TIMEOUT_S = 60


def _opt(api: OmniscopeApi, name: str) -> Any:
    return api.get_option(name)


def _as_str_or_none(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _as_bool(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "t", "yes", "y", "on")


class SlimCDError(Exception):
    pass


def _fetch_json(params: Dict[str, str]) -> Dict[str, Any]:
    # The credentials travel as URL parameters, so no message may include the URL (requests' own messages do)
    try:
        r = requests.get(SLIMCD_URL, params=params, timeout=TIMEOUT_S)
    except requests.RequestException as e:
        raise SlimCDError(f"Could not reach Slim CD: {type(e).__name__}.") from None
    if r.status_code != 200:
        raise SlimCDError(f"Slim CD answered HTTP {r.status_code}.")

    txt = r.text.strip()
    try:
        obj = json.loads(txt)
    except Exception:
        obj = None
    if not isinstance(obj, dict) or not isinstance(obj.get("reply"), dict):
        raise SlimCDError("Slim CD's answer was not the expected JSON reply (check the account and Site ID).")
    return obj


def _build_params(api: OmniscopeApi) -> Dict[str, str]:
    params: Dict[str, str] = {"service": SERVICE}

    username = _as_str_or_none(_opt(api, "username"))
    password = _opt(api, "password")  # allow empty string for API access credential
    siteid = _as_str_or_none(_opt(api, "siteid"))

    if not username:
        raise SlimCDError("Enter the Slim CD username.")
    if password is None:
        raise SlimCDError("Enter the Slim CD password (it can be empty for API access credentials).")
    if not siteid:
        raise SlimCDError("Enter the Site ID.")

    params["username"] = username
    params["password"] = str(password)
    params["siteid"] = siteid

    # IMPORTANT: Only include recordcountonly when enabled (presence may trigger count-mode)
    if _as_bool(_opt(api, "recordcountonly")):
        params["recordcountonly"] = ""

    maxrecords = _as_str_or_none(_opt(api, "maxrecords"))
    if maxrecords:
        if not maxrecords.isdigit() or int(maxrecords) < 1:
            raise SlimCDError(f"Max records must be a whole number above 0; got '{maxrecords}'.")
        params["maxrecords"] = maxrecords

    if _as_bool(_opt(api, "reverseorder")):
        params["reverseorder"] = ""

    startdate = _as_str_or_none(_opt(api, "startdate"))
    enddate = _as_str_or_none(_opt(api, "enddate"))
    if startdate:
        params["startdate"] = startdate
    if enddate:
        params["enddate"] = enddate

    clientid = _as_str_or_none(_opt(api, "clientid"))
    if clientid:
        params["clientid"] = clientid

    for k in (
        "firstname",
        "lastname",
        "city",
        "state",
        "zip",
        "email",
        "amount",
        "clienttransref",
        "transtype",
        "cardnumber",
        "cardid",
        "cardpart",
        "clerkname",
        "gateid",
    ):
        v = _as_str_or_none(_opt(api, k))
        if v:
            params[k] = v

    return params


def _check_reply(payload: Dict[str, Any]) -> Dict[str, Any]:
    reply = payload.get("reply", {})
    responsecode = str(reply.get("responsecode", "")).strip()
    if responsecode and responsecode != "0":
        desc = reply.get("description") or reply.get("response") or "no description"
        raise SlimCDError(f"Slim CD refused the request (response code {responsecode}): {desc}")
    return reply


def _extract_transactions(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    reply = _check_reply(payload)

    datablock = reply.get("datablock", {})
    if not isinstance(datablock, dict):
        return []

    txs = datablock.get("Transactions", {})
    if not isinstance(txs, dict):
        return []

    tx = txs.get("Transaction")
    if isinstance(tx, list):
        return [t for t in tx if isinstance(t, dict)]
    if isinstance(tx, dict):
        return [tx]
    return []


# Stable schema even with 0 rows
KNOWN_TX_COLUMNS: List[str] = [
    "gateid",
    "transactiondate",
    "transtype",
    "processor",
    "siteid",
    "batchno",
    "approved",
    "cardtype",
    "cardpresent",
    "proc_code",
    "cardid",
    "cardnumber",
    "amount",
    "authcode",
    "cvv2reply",
    "avsreply",
    "checkid",
    "checkno",
    "routeno",
    "accountnumber",
    "trackindicator",
    "voided",
    "requestingip",
    "remoteip",
    "firstname",
    "lastname",
    "address",
    "city",
    "state",
    "zip",
    "country",
    "phone",
    "email",
    "proc_response",
    "clerkname",
    "po",
    "salestax",
    "salestaxtype",
    "tip",
    "clienttransref",
    "giftbalance",
    "cashback",
]


def _convert_types(df: pd.DataFrame) -> pd.DataFrame:
    # Converted even when empty, so the output's field types are the same whether or not records came back.
    # zip stays text: ZIP codes have leading zeros (02134) and ZIP+4 forms (02134-1234).

    # Date
    if "transactiondate" in df.columns:
        df["transactiondate"] = pd.to_datetime(df["transactiondate"], errors="coerce", format="mixed")

    # Int-ish (nullable)
    int_fields = [
        "siteid",
        "gateid",
        "cardid",
        "batchno",
        "trackindicator",
        "voided",
        "checkid",
        "salestaxtype",
    ]
    for c in int_fields:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    # Decimal-ish
    dec_fields = ["amount", "salestax", "tip", "giftbalance", "cashback"]
    for c in dec_fields:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")

    # Boolean-ish
    if "cardpresent" in df.columns:
        df["cardpresent"] = (
            df["cardpresent"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False, "1": True, "0": False, "y": True, "n": False,
                  "yes": True, "no": False})
            .astype("boolean")
        )

    return df


def _force_all_text(df: pd.DataFrame) -> pd.DataFrame:
    # Missing values stay missing (astype(str) would write the text "None" or "nan")
    for c in df.columns:
        df[c] = df[c].map(lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else str(v))
        df[c] = df[c].astype(object)
    return df


api = OmniscopeApi()

try:
    recordcountonly_enabled = _as_bool(_opt(api, "recordcountonly"))
    treat_all_text = _as_bool(_opt(api, "treat_all_output_as_text"))

    params = _build_params(api)
    payload = _fetch_json(params)

    if recordcountonly_enabled:
        # One record with the count; an error reply stops the block like a transaction search does
        reply = _check_reply(payload)
        datablock = reply.get("datablock", {})
        recordcount = None
        if isinstance(datablock, dict):
            rc = datablock.get("RecordCount")
            if isinstance(rc, int):
                recordcount = rc
            elif isinstance(rc, str) and rc.strip().isdigit():
                recordcount = int(rc.strip())

        out = pd.DataFrame([{
            "recordcount": recordcount,
            "siteid": params.get("siteid"),
            "clientid": params.get("clientid"),
            "startdate": params.get("startdate"),
            "enddate": params.get("enddate"),
        }])
        out["recordcount"] = out["recordcount"].astype("Int64")
        api.write_output_records(out, output_number=0)
        api.close()
        raise SystemExit(0)

    rows = _extract_transactions(payload)

    # An empty search gives the known fields with no records, typed the same way as a full one
    out = pd.DataFrame(rows) if rows else pd.DataFrame(columns=KNOWN_TX_COLUMNS, dtype=object)

    # Ensure stable columns
    for c in KNOWN_TX_COLUMNS:
        if c not in out.columns:
            out[c] = None
    out = out[KNOWN_TX_COLUMNS + [c for c in out.columns if c not in KNOWN_TX_COLUMNS]]

    out = _force_all_text(out) if treat_all_text else _convert_types(out)

    api.write_output_records(out, output_number=0)
    api.close(f"{len(out)} transaction(s).")

except SlimCDError as e:
    api.abort(str(e))