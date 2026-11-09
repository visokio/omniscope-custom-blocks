"""Funnel Analysis: from raw events (user, event name, time), count how many
users reach each step of a funnel such as view -> basket -> checkout ->
purchase, in order and optionally within a time window from the first step,
per segment (device, channel, campaign). Reports conversion from the start and
from the previous step, drop-off, and the median time between steps; plus one
row per user with the furthest step reached.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


user_f = opt("user_field")
event_f = opt("event_field")
time_f = opt("time_field")
steps_txt = opt("steps", "")
segments = opt("segment_fields", []) or []
ordered = opt("ordered", True)
window_h = float(opt("window_hours", 0) or 0)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the events to the input.")
for f, label in ((user_f, "user"), (event_f, "event"), (time_f, "time")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
miss = [s for s in segments if s not in df.columns]
if miss:
    omniscope_api.abort(f"Segment fields not in the input: {', '.join(miss)}")
steps = [s.strip() for s in re.split(r"[,;\n]|->", steps_txt or "") if s.strip()]
if len(steps) < 2:
    omniscope_api.abort("List at least two funnel steps in order, for example: view_product, add_to_basket, checkout, purchase")

t = df[time_f]
if pd.api.types.is_datetime64_any_dtype(t):
    ts = t.dt.tz_localize(None) if t.dt.tz is not None else t
else:
    txt = t.astype(object).where(t.notna(), None).astype(str).str.strip()
    iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
    ts = pd.Series(pd.NaT, index=t.index, dtype="datetime64[ns]")
    ts[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
    ts[~iso & t.notna()] = pd.to_datetime(txt[~iso & t.notna()], errors="coerce", dayfirst=True, format="mixed")

norm = {s.lower(): i for i, s in enumerate(steps)}
ev = pd.DataFrame({"u": df[user_f].astype(object), "e": df[event_f].astype(str).str.strip().str.lower().map(norm), "t": ts})
ev = ev.dropna(subset=["u", "e", "t"])
ev["e"] = ev["e"].astype(int)
unknown = sorted(set(df[event_f].dropna().astype(str).str.strip().str.lower()) - set(norm))

# segment per user: taken from the user's first event
seg_of = None
if segments:
    first_idx = ev.sort_values("t").groupby("u").head(1).index
    seg_of = df.loc[first_idx, segments + [user_f]].drop_duplicates(user_f).set_index(user_f)
    for s in segments:
        seg_of[s] = seg_of[s].astype(object).where(seg_of[s].notna(), "(blank)")

reach = {}
s0 = ev[ev["e"] == 0].groupby("u")["t"].min()
reach[0] = s0
prev = s0
for k in range(1, len(steps)):
    cand = ev[ev["e"] == k][["u", "t"]].merge(prev.rename("tp").rename_axis(None), left_on="u", right_index=True, how="inner")
    if ordered:
        cand = cand[cand["t"] >= cand["tp"]]
    if window_h > 0:
        cand = cand.merge(s0.rename("t0").rename_axis(None), left_on="u", right_index=True)
        cand = cand[cand["t"] <= cand["t0"] + pd.Timedelta(hours=window_h)]
    cur = cand.groupby("u")["t"].min()
    reach[k] = cur
    prev = cur

users = pd.DataFrame(index=s0.index)
for k, st in enumerate(steps):
    users[f"{st} Time"] = reach[k].reindex(users.index)
reached = np.column_stack([users[f"{st} Time"].notna().to_numpy() for st in steps]) if len(users) else np.zeros((0, len(steps)), dtype=bool)
furthest = reached.sum(axis=1)
users_out = pd.DataFrame({str(user_f): users.index.to_numpy(dtype=object)})
if seg_of is not None:
    for s in segments:
        users_out[s] = seg_of.reindex(users.index)[s].to_numpy(dtype=object)
users_out["Steps Reached"] = pd.array(furthest, dtype="Int64")
users_out["Furthest Step"] = [steps[n - 1] for n in furthest]
users_out["Converted"] = np.where(furthest == len(steps), "Yes", "No")
for st in steps:
    users_out[f"{st} Time"] = pd.to_datetime(users[f"{st} Time"].to_numpy()).tz_localize("UTC")
users_out["Hours To Convert"] = ((users[f"{steps[-1]} Time"] - users[f"{steps[0]} Time"]).dt.total_seconds() / 3600).to_numpy()

funnel_rows = []
seg_keys = [()] if not segments else sorted(set(map(tuple, users_out[segments].astype(str).to_numpy())))
for sk in seg_keys:
    mask = np.ones(len(users_out), dtype=bool)
    for i, s in enumerate(segments):
        mask &= users_out[s].astype(str).to_numpy() == sk[i]
    r = reached[mask]
    n0 = int(r[:, 0].sum()) if len(r) else 0
    for k, st in enumerate(steps):
        nk = int(r[:, k].sum()) if len(r) else 0
        nprev = int(r[:, k - 1].sum()) if k and len(r) else nk
        dt = (users[f"{st} Time"] - users[f"{steps[k - 1]} Time"]).dt.total_seconds()[mask] / 3600 if k else pd.Series(dtype=float)
        funnel_rows.append({**{s: sk[i] for i, s in enumerate(segments)}, "Step Number": k + 1, "Step": st, "Users": nk,
                            "Conversion From Start": nk / n0 if n0 else np.nan, "Conversion From Previous": nk / nprev if nprev else np.nan,
                            "Drop-off From Previous": nprev - nk if k else 0,
                            "Median Hours From Previous": float(dt.median()) if k and dt.notna().any() else np.nan})
fn = pd.DataFrame(funnel_rows)
fn["Step Number"] = fn["Step Number"].astype("int64")
fn["Users"] = fn["Users"].astype("int64")
fn["Drop-off From Previous"] = fn["Drop-off From Previous"].astype("int64")
for c in ("Conversion From Start", "Conversion From Previous", "Median Hours From Previous"):
    fn[c] = fn[c].astype("float64")
users_out["Hours To Convert"] = users_out["Hours To Convert"].astype("float64")

omniscope_api.write_output(fn, "funnel")
omniscope_api.write_output(users_out, "users")
overall = fn[fn["Step Number"] == len(steps)]["Users"].sum() / max(1, fn[fn["Step Number"] == 1]["Users"].sum())
omniscope_api.close(f"{len(users_out):,} users started the funnel; {overall:.1%} reached '{steps[-1]}'"
                    + (f"; events not in the funnel ignored: {', '.join(unknown[:5])}" if unknown else "") + ".")
