"""Path Analysis: the most common sequences of events per user or session
(page views, app screens, case stages, patient pathways, machine states), and
the step-to-step transitions behind them.

  Events are ordered by time within each path; repeated consecutive events can
  be collapsed (home > home > product becomes home > product). Paths can start
  at the first occurrence of a chosen event and stop at the first of chosen end
  events (for example purchase), and are cut to a maximum number of steps.

Outputs: the top paths with counts, share, how many reach an end event and the
median duration; step-numbered transitions for Sankey charts (1. home ->
2. product), with (exit) where paths stop; and the next-step probabilities
(a Markov transition table) between events.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


path_f = opt("path_field")
event_f = opt("event_field")
time_f = opt("time_field")
max_len = int(opt("max_steps", 5))
collapse = bool(opt("collapse_repeats", True))
start_ev = (opt("start_event", "") or "").strip()
end_txt = opt("end_events", "")
top_n = int(opt("top_n", 50) or 0)
sep = " > "

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the events to the input.")
for f, lab in ((path_f, "user or session"), (event_f, "event")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
if time_f and time_f not in df.columns:
    omniscope_api.abort(f"Field '{time_f}' is not in the input.")
if not 1 <= max_len <= 50:
    omniscope_api.abort("Maximum steps must be 1 to 50.")
ends = {e.strip().lower() for e in (end_txt or "").replace(";", ",").split(",") if e.strip()}


def to_date(s):
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


w = pd.DataFrame({"p": df[path_f].astype(object), "e": df[event_f].astype(object).where(df[event_f].notna(), None), "row": np.arange(len(df))})
w["e"] = w["e"].map(lambda v: None if v is None else str(v).strip()).replace("", None)
w["t"] = to_date(df[time_f]) if time_f else pd.NaT
w = w.dropna(subset=["p", "e"])
if time_f:
    w = w.dropna(subset=["t"])
w = w.sort_values(["p", "t", "row"] if time_f else ["p", "row"], kind="mergesort")

paths, durs, reached = [], [], []
n_no_start = 0
for pid, g in w.groupby("p", sort=False):
    ev = g["e"].tolist()
    tt = g["t"].tolist()
    if collapse:
        keep = [i for i in range(len(ev)) if i == 0 or ev[i] != ev[i - 1]]
        ev, tt = [ev[i] for i in keep], [tt[i] for i in keep]
    if start_ev:
        low = [x.lower() for x in ev]
        if start_ev.lower() not in low:
            n_no_start += 1
            continue
        k = low.index(start_ev.lower())
        ev, tt = ev[k:], tt[k:]
    hit = False
    if ends:
        for i, x in enumerate(ev):
            if x.lower() in ends:
                ev, tt, hit = ev[:i + 1], tt[:i + 1], True
                break
    truncated = len(ev) > max_len
    full = tuple(ev)
    paths.append((pid, tuple(ev[:max_len]), truncated, len(ev), full))
    reached.append(hit)
    durs.append((tt[-1] - tt[0]).total_seconds() / 60 if time_f and len(tt) > 1 else (0.0 if time_f else np.nan))

P = pd.DataFrame({"pid": [p[0] for p in paths], "seq": [p[1] for p in paths], "trunc": [p[2] for p in paths], "steps": [p[3] for p in paths], "full": [p[4] for p in paths],
                  "hit": reached, "dur": durs})
n_paths = len(P)
if n_paths:
    P["path"] = [sep.join(s) + (sep + "..." if t else "") for s, t in zip(P["seq"], P["trunc"])]
    agg = P.groupby("path", sort=False).agg(n=("pid", "size"), hit=("hit", "sum"), steps=("steps", "mean"), dur=("dur", "median"),
                                             first=("seq", "first")).reset_index()
    agg = agg.sort_values(["n", "path"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
else:
    agg = pd.DataFrame(columns=["path", "n", "hit", "steps", "dur", "first"])
agg["Rank"] = np.arange(1, len(agg) + 1)
top = agg if not top_n else agg.head(top_n)
cum = top["n"].cumsum()
paths_out = pd.DataFrame({"Rank": top["Rank"].astype("int64"), "Path": top["path"].astype(object), "Steps Shown": [len(s) for s in top["first"]],
                          "Paths": top["n"].astype("int64"), "Share": top["n"] / n_paths if n_paths else np.nan,
                          "Cumulative Share": cum / n_paths if n_paths else np.nan,
                          "First Event": [s[0] if len(s) else None for s in top["first"]], "Last Event": [s[-1] if len(s) else None for s in top["first"]]})
paths_out["Steps Shown"] = paths_out["Steps Shown"].astype("int64")
if ends:
    paths_out["Reached End Event"] = top["hit"].astype("int64").to_numpy()
    paths_out["Reached End Share"] = (top["hit"] / top["n"]).astype("float64").to_numpy()
paths_out["Average Steps (untruncated)"] = top["steps"].astype("float64").to_numpy()
if time_f:
    paths_out["Median Minutes"] = top["dur"].astype("float64").to_numpy()
for c in ("Share", "Cumulative Share"):
    paths_out[c] = paths_out[c].astype("float64")

# Sankey transitions: step-numbered nodes, (exit) where a path stops within the shown steps
trows = {}
for s, t in zip(P["seq"] if n_paths else [], P["trunc"] if n_paths else []):
    for i in range(len(s)):
        src = f"{i + 1}. {s[i]}"
        if i + 1 < len(s):
            dst = f"{i + 2}. {s[i + 1]}"
        elif t:
            dst = f"{i + 2}. (more)"
        else:
            dst = f"{i + 2}. (exit)"
        k = (i + 1, src, dst)
        trows[k] = trows.get(k, 0) + 1
trans = pd.DataFrame([(k[0], k[1], k[2], v) for k, v in trows.items()], columns=["Step", "From", "To", "Paths"])
trans = trans.sort_values(["Step", "Paths", "From", "To"], ascending=[True, False, True, True], kind="mergesort").reset_index(drop=True)
trans["Step"] = trans["Step"].astype("int64")
trans["Paths"] = trans["Paths"].astype("int64")
trans["Share Of Step"] = (trans["Paths"] / trans.groupby("Step")["Paths"].transform("sum")).astype("float64") if len(trans) else pd.Series(dtype="float64")
trans["From Event"] = trans["From"].str.split(". ", n=1, regex=False).str[1] if len(trans) else pd.Series(dtype=object)
trans["To Event"] = trans["To"].str.split(". ", n=1, regex=False).str[1] if len(trans) else pd.Series(dtype=object)

# Markov next-step table over the full (uncut) collapsed sequences
mrows = {}
for s in (P["full"] if n_paths else []):
    for i in range(len(s)):
        if i + 1 == len(s) and ends and s[i].lower() in ends:
            continue  # paths are cut at end events, so what follows them is unknown
        nxt = s[i + 1] if i + 1 < len(s) else "(exit)"
        mrows[(s[i], nxt)] = mrows.get((s[i], nxt), 0) + 1
mk = pd.DataFrame([(a, b, v) for (a, b), v in mrows.items()], columns=["From", "To", "Transitions"])
if len(mk):
    mk["Probability"] = (mk["Transitions"] / mk.groupby("From")["Transitions"].transform("sum")).astype("float64")
    mk = mk.sort_values(["From", "Probability", "To"], ascending=[True, False, True], kind="mergesort").reset_index(drop=True)
else:
    mk["Probability"] = pd.Series(dtype="float64")
mk["Transitions"] = mk["Transitions"].astype("int64")

omniscope_api.write_output(paths_out, "paths")
omniscope_api.write_output(trans, "transitions")
omniscope_api.write_output(mk, "next_step")
msg = f"{n_paths:,} paths, {len(agg):,} distinct"
if len(paths_out):
    msg += f"; top path ({paths_out['Share'].iloc[0]:.1%}): {paths_out['Path'].iloc[0]}"
if ends and n_paths:
    msg += f"; {int(P['hit'].sum()):,} reached {', '.join(sorted(ends))}"
if n_no_start:
    msg += f"; {n_no_start:,} paths without '{start_ev}' left out"
omniscope_api.close(msg + ".")
