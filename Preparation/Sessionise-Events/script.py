"""Sessionise Events: split each user's (or device's) stream of timestamped
events into sessions: a new session starts when the gap since the previous
event exceeds a timeout (30 minutes by default, as in web analytics), or when
a session reaches a maximum length.

Outputs
  1 events: the input with Session ID, Session Number, Event Number In Session,
    Seconds Since Previous Event and Is Session Start
  2 sessions: one row per session with start, end, duration, events, first and
    last event (landing / exit), total value and a bounce flag
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


user_field = opt("user_field")
time_field = opt("time_field")
event_field = opt("event_field")
value_field = opt("value_field")
gap_minutes = float(opt("gap_minutes", 30))
max_hours = float(opt("max_session_hours", 0) or 0)
day_first = opt("day_first", True)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the events to the input.")
for f, label in ((user_field, "user"), (time_field, "timestamp")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
for f in (event_field, value_field):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")
if gap_minutes <= 0:
    omniscope_api.abort("The inactivity gap must be more than 0 minutes.")

s = df[time_field]
orig_tz = s.dt.tz if pd.api.types.is_datetime64_any_dtype(s) else None
if pd.api.types.is_datetime64_any_dtype(s):
    ts = s.dt.tz_localize(None) if orig_tz is not None else s
else:
    txt = s.astype(object).where(s.notna(), None).astype(str).str.strip()
    iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
    ts = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    if iso.any():
        ts[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
    rest = ~iso & s.notna()
    if rest.any():
        ts[rest] = pd.to_datetime(txt[rest], errors="coerce", dayfirst=bool(day_first), format="mixed")

work = pd.DataFrame({"u": df[user_field].astype(object), "t": ts, "row": np.arange(len(df))})
ok = work["u"].notna() & work["t"].notna()
skipped = int((~ok).sum())
w = work[ok].sort_values(["u", "t", "row"], kind="mergesort")

u = w["u"].to_numpy()
t = w["t"].to_numpy(dtype="datetime64[ns]")
new_user = np.ones(len(w), dtype=bool)
new_user[1:] = u[1:] != u[:-1]
gap = np.full(len(w), np.nan)
if len(w) > 1:
    gap[1:] = (t[1:] - t[:-1]) / np.timedelta64(1, "s")
gap[new_user] = np.nan
start = new_user | (gap > gap_minutes * 60)
if max_hours > 0:
    # split sessions that run longer than the cap (checked in one pass)
    limit = np.timedelta64(int(max_hours * 3600), "s")
    s_start = t[0] if len(t) else None
    for i in range(len(t)):
        if start[i]:
            s_start = t[i]
        elif t[i] - s_start > limit:
            start[i] = True
            s_start = t[i]
sess_global = np.cumsum(start)
# session number within user
first_sess_of_user = pd.Series(sess_global).where(new_user).ffill().to_numpy()
sess_num = (sess_global - first_sess_of_user + 1).astype(int)
evt_num = pd.Series(np.ones(len(w))).groupby(sess_global).cumsum().astype(int).to_numpy()

ev = pd.DataFrame(index=w["row"].to_numpy())
ev["Session ID"] = [f"{uu}-{n}" for uu, n in zip(u, sess_num)]
ev["Session Number"] = sess_num
ev["Event Number In Session"] = evt_num
ev["Seconds Since Previous Event"] = gap
ev["Is Session Start"] = np.where(start, "Yes", "No")
ev = ev.sort_index()

out = df.copy()
out["Session ID"] = pd.Series([None] * len(df), dtype=object)
out.loc[ev.index, "Session ID"] = ev["Session ID"].to_numpy()
for c in ("Session Number", "Event Number In Session"):
    arr = np.full(len(df), np.nan)
    arr[ev.index] = ev[c].to_numpy()
    out[c] = pd.array(arr, dtype="Float64").astype("Int64")
arr = np.full(len(df), np.nan)
arr[ev.index] = ev["Seconds Since Previous Event"].to_numpy()
out["Seconds Since Previous Event"] = pd.Series(arr, dtype="float64")
flag = np.full(len(df), None, dtype=object)
flag[ev.index] = ev["Is Session Start"].to_numpy()
out["Is Session Start"] = flag

# sessions summary
sw = pd.DataFrame({"u": u, "sid": ev.loc[w["row"].to_numpy(), "Session ID"].to_numpy(), "n": sess_num, "t": t, "k": sess_global})
if event_field:
    sw["e"] = df[event_field].to_numpy(dtype=object)[w["row"].to_numpy()]
if value_field:
    sw["v"] = pd.to_numeric(df[value_field], errors="coerce").to_numpy(dtype=float)[w["row"].to_numpy()]
g = sw.groupby("k", sort=True)
sess = pd.DataFrame({
    str(user_field): g["u"].first().to_numpy(dtype=object),
    "Session ID": g["sid"].first().to_numpy(dtype=object),
    "Session Number": pd.array(g["n"].first().to_numpy(), dtype="Int64"),
    "Session Start": pd.to_datetime(g["t"].min().to_numpy()),
    "Session End": pd.to_datetime(g["t"].max().to_numpy()),
    "Events": pd.array(g.size().to_numpy(), dtype="Int64"),
})
sess["Duration (seconds)"] = ((sess["Session End"] - sess["Session Start"]).dt.total_seconds()).astype("float64")
if event_field:
    sess["First Event"] = g["e"].first().to_numpy(dtype=object)
    sess["Last Event"] = g["e"].last().to_numpy(dtype=object)
if value_field:
    sess["Total Value"] = g["v"].sum().to_numpy(dtype=float)
sess["Bounce"] = np.where(sess["Events"].to_numpy(dtype=float) == 1, "Yes", "No")
if orig_tz is not None:
    sess["Session Start"] = sess["Session Start"].dt.tz_localize(orig_tz)
    sess["Session End"] = sess["Session End"].dt.tz_localize(orig_tz)

omniscope_api.write_output(out, "events")
omniscope_api.write_output(sess, "sessions")
users = sess[str(user_field)].nunique()
omniscope_api.close(f"{len(sess):,} sessions from {int(ok.sum()):,} events by {users:,} users (gap {gap_minutes:g} min)"
                    + (f"; {skipped:,} events without user or valid time." if skipped else "."))
