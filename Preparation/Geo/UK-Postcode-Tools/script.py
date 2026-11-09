"""UK Postcode Tools: validate and standardise UK postcodes, optionally pull
them out of free-text address fields, split them into area, district, sector
and unit, and add the postcode area's name and country. Offline: format rules
and the list of postcode areas only, no lookup service (so a well-formed but
unused postcode is still reported as valid format).
"""
import re

import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


field = opt("postcode_field")
extract = opt("extract_from_text", False)
replace = opt("replace_field", False)
prefix = opt("prefix", "Postcode")

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
if not field or field not in df.columns:
    omniscope_api.abort(f"Choose the postcode (or address) field (got '{field}').")

AREAS = {
    "AB": ("Aberdeen", "Scotland"), "AL": ("St Albans", "England"), "B": ("Birmingham", "England"), "BA": ("Bath", "England"),
    "BB": ("Blackburn", "England"), "BD": ("Bradford", "England"), "BH": ("Bournemouth", "England"), "BL": ("Bolton", "England"),
    "BN": ("Brighton", "England"), "BR": ("Bromley", "England"), "BS": ("Bristol", "England"), "BT": ("Belfast", "Northern Ireland"),
    "CA": ("Carlisle", "England"), "CB": ("Cambridge", "England"), "CF": ("Cardiff", "Wales"), "CH": ("Chester", "England / Wales (cross-border)"),
    "CM": ("Chelmsford", "England"), "CO": ("Colchester", "England"), "CR": ("Croydon", "England"), "CT": ("Canterbury", "England"),
    "CV": ("Coventry", "England"), "CW": ("Crewe", "England"), "DA": ("Dartford", "England"), "DD": ("Dundee", "Scotland"),
    "DE": ("Derby", "England"), "DG": ("Dumfries", "Scotland"), "DH": ("Durham", "England"), "DL": ("Darlington", "England"),
    "DN": ("Doncaster", "England"), "DT": ("Dorchester", "England"), "DY": ("Dudley", "England"), "E": ("London E", "England"),
    "EC": ("London EC", "England"), "EH": ("Edinburgh", "Scotland"), "EN": ("Enfield", "England"), "EX": ("Exeter", "England"),
    "FK": ("Falkirk", "Scotland"), "FY": ("Blackpool", "England"), "G": ("Glasgow", "Scotland"), "GL": ("Gloucester", "England"),
    "GU": ("Guildford", "England"), "GY": ("Guernsey", "Channel Islands"), "HA": ("Harrow", "England"), "HD": ("Huddersfield", "England"),
    "HG": ("Harrogate", "England"), "HP": ("Hemel Hempstead", "England"), "HR": ("Hereford", "England / Wales (cross-border)"),
    "HS": ("Outer Hebrides", "Scotland"), "HU": ("Hull", "England"), "HX": ("Halifax", "England"), "IG": ("Ilford", "England"),
    "IM": ("Isle of Man", "Isle of Man"), "IP": ("Ipswich", "England"), "IV": ("Inverness", "Scotland"), "JE": ("Jersey", "Channel Islands"),
    "KA": ("Kilmarnock", "Scotland"), "KT": ("Kingston upon Thames", "England"), "KW": ("Kirkwall", "Scotland"), "KY": ("Kirkcaldy", "Scotland"),
    "L": ("Liverpool", "England"), "LA": ("Lancaster", "England"), "LD": ("Llandrindod Wells", "Wales"), "LE": ("Leicester", "England"),
    "LL": ("Llandudno", "Wales"), "LN": ("Lincoln", "England"), "LS": ("Leeds", "England"), "LU": ("Luton", "England"),
    "M": ("Manchester", "England"), "ME": ("Rochester", "England"), "MK": ("Milton Keynes", "England"), "ML": ("Motherwell", "Scotland"),
    "N": ("London N", "England"), "NE": ("Newcastle upon Tyne", "England"), "NG": ("Nottingham", "England"), "NN": ("Northampton", "England"),
    "NP": ("Newport", "Wales"), "NR": ("Norwich", "England"), "NW": ("London NW", "England"), "OL": ("Oldham", "England"),
    "OX": ("Oxford", "England"), "PA": ("Paisley", "Scotland"), "PE": ("Peterborough", "England"), "PH": ("Perth", "Scotland"),
    "PL": ("Plymouth", "England"), "PO": ("Portsmouth", "England"), "PR": ("Preston", "England"), "RG": ("Reading", "England"),
    "RH": ("Redhill", "England"), "RM": ("Romford", "England"), "S": ("Sheffield", "England"), "SA": ("Swansea", "Wales"),
    "SE": ("London SE", "England"), "SG": ("Stevenage", "England"), "SK": ("Stockport", "England"), "SL": ("Slough", "England"),
    "SM": ("Sutton", "England"), "SN": ("Swindon", "England"), "SO": ("Southampton", "England"), "SP": ("Salisbury", "England"),
    "SR": ("Sunderland", "England"), "SS": ("Southend-on-Sea", "England"), "ST": ("Stoke-on-Trent", "England"), "SW": ("London SW", "England"),
    "SY": ("Shrewsbury", "England / Wales (cross-border)"), "TA": ("Taunton", "England"), "TD": ("Galashiels", "Scotland / England (cross-border)"),
    "TF": ("Telford", "England"), "TN": ("Tonbridge", "England"), "TQ": ("Torquay", "England"), "TR": ("Truro", "England"),
    "TS": ("Cleveland", "England"), "TW": ("Twickenham", "England"), "UB": ("Southall", "England"), "W": ("London W", "England"),
    "WA": ("Warrington", "England"), "WC": ("London WC", "England"), "WD": ("Watford", "England"), "WF": ("Wakefield", "England"),
    "WN": ("Wigan", "England"), "WR": ("Worcester", "England"), "WS": ("Walsall", "England"), "WV": ("Wolverhampton", "England"),
    "YO": ("York", "England"), "ZE": ("Lerwick (Shetland)", "Scotland"), "BF": ("British Forces (BFPO)", "Non-geographic"),
    "BX": ("Non-geographic", "Non-geographic"), "GIR": ("Girobank", "Non-geographic"),
}
# UK government-published format pattern (outward + inward)
FULL = re.compile(r"^(GIR0AA|[A-PR-UWYZ](?:[0-9]{1,2}|[A-HK-Y][0-9](?:[0-9ABEHMNPRV-Y])?|[0-9][A-HJKPS-UW])[0-9][ABD-HJLNP-UW-Z]{2})$")
FIND = re.compile(r"\b(GIR ?0AA|[A-PR-UWYZ](?:[0-9]{1,2}|[A-HK-Y][0-9](?:[0-9ABEHMNPRV-Y])?|[0-9][A-HJKPS-UW]) ?[0-9][ABD-HJLNP-UW-Z]{2})\b")
OUTWARD = re.compile(r"^[A-Z]{1,2}[0-9][A-Z0-9]?$")


def analyse(v):
    if v is None or (isinstance(v, float) and v != v) or str(v).strip() == "":
        return {"pc": None, "valid": "No", "reason": "Missing"}
    raw = str(v).upper()
    if extract:
        m = FIND.search(re.sub(r"\s+", " ", raw))
        if not m:
            return {"pc": None, "valid": "No", "reason": "No postcode found in the text"}
        raw = m.group(1)
    s = re.sub(r"[^A-Z0-9]", "", raw)
    # common keying slips: letter O for zero / I for one in the digit position of the inward code
    if len(s) >= 5 and s[-3] in "OI":
        s = s[:-3] + {"O": "0", "I": "1"}[s[-3]] + s[-2:]
    if not 5 <= len(s) <= 7:
        return {"pc": None, "valid": "No", "reason": "Wrong length"}
    if not FULL.match(s):
        out = s[:-3]
        if not re.search(r"[0-9][A-Z]{2}$", s):
            reason = "Inward code (last three characters) not valid"
        elif not OUTWARD.match(out):
            reason = "Outward code (first part) not valid"
        else:
            reason = "Letters or digits not allowed in this position"
        return {"pc": None, "valid": "No", "reason": reason}
    out, inn = s[:-3], s[-3:]
    area = re.match(r"^[A-Z]+", out).group(0)
    if area not in AREAS:
        return {"pc": f"{out} {inn}", "valid": "No", "reason": f"Unknown postcode area {area}"}
    return {"pc": f"{out} {inn}", "valid": "Yes", "reason": "", "area": area, "district": out, "sector": f"{out} {inn[0]}",
            "inward": inn, "name": AREAS[area][0], "country": AREAS[area][1]}


res = [analyse(v) for v in df[field].tolist()]
out = df.copy()
col = (lambda k: f"{prefix} {k}") if prefix else (lambda k: k)
formatted = [r.get("pc") for r in res]
if replace and not extract:
    out[field] = [f if f else v for f, v in zip(formatted, df[field].tolist())]
else:
    out[col("Formatted")] = formatted
out[col("Valid")] = [r["valid"] for r in res]
out[col("Problem")] = [r["reason"] for r in res]
out[col("Area")] = [r.get("area") for r in res]
out[col("District")] = [r.get("district") for r in res]
out[col("Sector")] = [r.get("sector") for r in res]
out[col("Area Name")] = [r.get("name") for r in res]
out[col("Country")] = [r.get("country") for r in res]
for c in out.columns:
    if c not in df.columns:
        out[c] = out[c].astype(object)

valid = out[out[col("Valid")] == "Yes"]
summ = valid.groupby([col("Country"), col("Area"), col("Area Name")]).size().rename("Records").reset_index().sort_values("Records", ascending=False)
summ["Records"] = summ["Records"].astype("int64")
summ["Share"] = (summ["Records"] / max(1, len(out))).astype("float64")
problems = out[out[col("Valid")] == "No"].groupby(col("Problem")).size().rename("Records").reset_index()
problems.insert(0, col("Country"), "(invalid)")
problems.insert(1, col("Area"), None)
problems = problems.rename(columns={col("Problem"): col("Area Name")})
problems["Records"] = problems["Records"].astype("int64")
problems["Share"] = (problems["Records"] / max(1, len(out))).astype("float64")
summ = pd.concat([summ, problems], ignore_index=True)
for c in (col("Country"), col("Area"), col("Area Name")):
    summ[c] = summ[c].astype(object)

omniscope_api.write_output(out, "postcodes")
omniscope_api.write_output(summ, "areas")
nv = len(valid)
omniscope_api.close(f"{nv:,} of {len(out):,} postcodes valid ({nv / max(1, len(out)):.0%}); {summ[col('Area')].notna().sum():,} postcode areas.")
