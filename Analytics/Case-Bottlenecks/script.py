"""Case Duration and Bottlenecks: from an event log (case, activity, timestamp)
such as orders, claims, applications, tickets or patient visits, measure

  per case: start, end, duration, number of steps, rework (an activity done
  again), first and last activity and the route taken (variant);
  per handover (activity A followed by activity B): how often it happens and
  how long it takes (median, average, 90th percentile, total), ranked so the
  slowest and the costliest handovers come first;
  per activity: occurrences, cases, rework and the time until the next step.

Durations are in hours (or days). Events are ordered by time within each case;
ties keep their input order.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


case_f, act_f, time_f = opt("case_field"), opt("activity_field"), opt("time_field")
unit = opt("unit", "HOURS")
max_variant = int(opt("max_variant_steps", 12))
DIV = 3600.0 if unit == "HOURS" else 86400.0
U = "Hours" if unit == "HOURS" else "Days"

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the event log to the input.")
for f, lab in ((case_f, "case"), (act_f, "activity"), (time_f, "timestamp")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")


def to_ts(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s
    else:
        txt = s.astype(object).where(s.notna(), None).astype(str).str.strip()
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        d = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        d[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
        d[~iso & s.notna()] = pd.to_datetime(txt[~iso & s.notna()], errors="coerce", dayfirst=True, format="mixed")
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    return d.astype("datetime64[ns]")


w = pd.DataFrame({"c": df[case_f].astype(object), "a": df[act_f].astype(object), "t": to_ts(df[time_f]), "row": np.arange(len(df))})
bad = int(w[["c", "a", "t"]].isna().any(axis=1).sum())
w = w.dropna(subset=["c", "a", "t"])
w["c"], w["a"] = w["c"].map(str), w["a"].map(lambda v: str(v).strip())
w = w.sort_values(["c", "t", "row"], kind="mergesort").reset_index(drop=True)
w["next_a"] = w.groupby("c")["a"].shift(-1)
w["next_t"] = w.groupby("c")["t"].shift(-1)
w["gap"] = (w["next_t"] - w["t"]).dt.total_seconds() / DIV
w["seen"] = w.groupby(["c", "a"]).cumcount()

cases = w.groupby("c", sort=True).agg(start=("t", "min"), end=("t", "max"), steps=("a", "size"), distinct=("a", "nunique"),
                                      rework=("seen", lambda s: int((s > 0).sum())), first=("a", "first"), last=("a", "last"),
                                      route=("a", lambda s: " > ".join(list(s)[:max_variant]) + (" > ..." if len(s) > max_variant else ""))).reset_index()
cases[f"Duration ({U})"] = (cases["end"] - cases["start"]).dt.total_seconds() / DIV
vc = cases["route"].value_counts()
cases["Variant Rank"] = cases["route"].map({v: i + 1 for i, v in enumerate(vc.index)}).astype("int64")
cases_out = pd.DataFrame({str(case_f): cases["c"].astype(object), "Start": cases["start"], "End": cases["end"], f"Duration ({U})": cases[f"Duration ({U})"].astype("float64"),
                          "Steps": cases["steps"].astype("int64"), "Distinct Activities": cases["distinct"].astype("int64"), "Rework Steps": cases["rework"].astype("int64"),
                          "First Activity": cases["first"].astype(object), "Last Activity": cases["last"].astype(object), "Route": cases["route"].astype(object),
                          "Variant Rank": cases["Variant Rank"]})
for c in ("Start", "End"):
    cases_out[c] = pd.to_datetime(cases_out[c]).dt.tz_localize("UTC")
if len(cases_out):
    q90 = cases_out[f"Duration ({U})"].quantile(0.9)
    cases_out["Slowest 10%"] = np.where(cases_out[f"Duration ({U})"] >= q90, "Yes", "No")

tr = w.dropna(subset=["next_a"])
trans = tr.groupby(["a", "next_a"]).agg(n=("gap", "size"), cases=("c", "nunique"), med=("gap", "median"), mean=("gap", "mean"),
                                        p90=("gap", lambda s: float(np.percentile(s, 90))), total=("gap", "sum")).reset_index()
trans["self"] = trans["a"] == trans["next_a"]
trans = trans.sort_values("total", ascending=False, kind="mergesort").reset_index(drop=True)
tot_all = trans["total"].sum()
trans_out = pd.DataFrame({"From Activity": trans["a"], "To Activity": trans["next_a"], "Handovers": trans["n"].astype("int64"), "Cases": trans["cases"].astype("int64"),
                          f"Median {U}": trans["med"].astype("float64"), f"Average {U}": trans["mean"].astype("float64"), f"90th Percentile {U}": trans["p90"].astype("float64"),
                          f"Total {U}": trans["total"].astype("float64"), "Share Of All Waiting": (trans["total"] / tot_all if tot_all else np.nan),
                          "Rank By Total": np.arange(1, len(trans) + 1), "Rank By Median": trans["med"].rank(ascending=False, method="min").astype("int64") if len(trans) else [],
                          "Repeat Of Same Activity": np.where(trans["self"], "Yes", "No")})
trans_out["Share Of All Waiting"] = trans_out["Share Of All Waiting"].astype("float64")
trans_out["Rank By Total"] = trans_out["Rank By Total"].astype("int64")
acts = w.groupby("a").agg(occ=("a", "size"), cases=("c", "nunique"), rework=("seen", lambda s: int((s > 0).sum())), wait=("gap", "median"),
                          ends=("next_a", lambda s: int(s.isna().sum()))).reset_index().sort_values("occ", ascending=False, kind="mergesort")
act_out = pd.DataFrame({"Activity": acts["a"], "Occurrences": acts["occ"].astype("int64"), "Cases": acts["cases"].astype("int64"),
                        "Rework Occurrences": acts["rework"].astype("int64"), "Cases With Rework": [int(w[(w["a"] == a) & (w["seen"] > 0)]["c"].nunique()) for a in acts["a"]],
                        f"Median {U} To Next Step": acts["wait"].astype("float64"), "Times Last Step": acts["ends"].astype("int64")})
act_out["Cases With Rework"] = act_out["Cases With Rework"].astype("int64")
omniscope_api.write_output(cases_out, "cases")
omniscope_api.write_output(trans_out, "handovers")
omniscope_api.write_output(act_out, "activities")
msg = f"{len(cases_out):,} cases, {len(w):,} events"
if len(cases_out):
    msg += f": median duration {cases_out[f'Duration ({U})'].median():,.1f} {U.lower()}, {int((cases_out['Rework Steps'] > 0).sum()):,} cases with rework, {len(vc):,} variants"
if len(trans_out):
    t0 = trans_out.iloc[0]
    msg += f"; most waiting: {t0['From Activity']} to {t0['To Activity']} ({t0['Share Of All Waiting']:.0%})"
omniscope_api.close(msg + (f"; {bad:,} events without case, activity or valid time skipped" if bad else "") + ".")
