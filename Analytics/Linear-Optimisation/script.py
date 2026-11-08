"""Linear Optimisation: find the best plan (product mix, allocation, blend,
staffing) that maximises or minimises a linear objective subject to linear
constraints, with the model given as data:

  Input 1, decision variables: one row per variable with its objective
           coefficient (profit, cost) and optional lower / upper bounds and an
           integer flag.
  Input 2, constraints (long format): one row per constraint and variable with
           the coefficient (resource use), plus the constraint's sense
           (<=, >=, =) and limit (repeated on each row of the constraint).

Uses scipy's HiGHS solver (linprog for continuous models, milp when any
variable must be whole). scipy is installed through the block's dependencies.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


sense_obj = opt("objective_sense", "MAXIMISE")
var_name = opt("var_name_field")
obj_field = opt("objective_field")
lb_field = opt("lower_field")
ub_field = opt("upper_field")
int_field = opt("integer_field")
all_integer = opt("all_integer", False)
c_name = opt("constraint_field")
c_var = opt("constraint_var_field")
c_coef = opt("coefficient_field")
c_sense = opt("sense_field")
c_rhs = opt("limit_field")
time_limit = float(opt("time_limit", 60))

V = omniscope_api.read_input_records(input_number=0)
C = omniscope_api.read_input_records(input_number=1)
if V is None or C is None:
    omniscope_api.abort("Connect the decision variables to input 1 and the constraints to input 2.")
for f, df, label in ((var_name, V, "variable name"), (obj_field, V, "objective coefficient"),
                     (c_name, C, "constraint name"), (c_var, C, "constraint variable"), (c_coef, C, "coefficient"),
                     (c_sense, C, "sense"), (c_rhs, C, "limit")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
for f in (lb_field, ub_field, int_field):
    if f and f not in V.columns:
        omniscope_api.abort(f"Field '{f}' is not in the variables input.")

try:
    from scipy.optimize import Bounds, LinearConstraint, linprog, milp
except ImportError:
    omniscope_api.abort("scipy is needed: add 'scipy' to the block's dependencies (it is listed by default).")
    raise SystemExit

names = V[var_name].astype(str).str.strip().tolist()
if len(set(names)) != len(names):
    dup = sorted({n for n in names if names.count(n) > 1})
    omniscope_api.abort(f"Variable names must be unique; repeated: {', '.join(dup[:5])}")
idx = {n: i for i, n in enumerate(names)}
n = len(names)
if n == 0:
    omniscope_api.abort("There are no decision variables.")
c = pd.to_numeric(V[obj_field], errors="coerce")
if c.isna().any():
    omniscope_api.abort(f"Objective coefficient missing or not a number for: {', '.join(np.array(names)[c.isna()][:5])}")
c = c.to_numpy(dtype=float)
lb = pd.to_numeric(V[lb_field], errors="coerce").fillna(0.0).to_numpy(dtype=float) if lb_field else np.zeros(n)
ub = pd.to_numeric(V[ub_field], errors="coerce").fillna(np.inf).to_numpy(dtype=float) if ub_field else np.full(n, np.inf)
TRUE = {"1", "1.0", "true", "yes", "y", "integer", "int", "whole"}
integ = np.ones(n, dtype=bool) if all_integer else (
    V[int_field].astype(str).str.strip().str.lower().isin(TRUE).to_numpy() if int_field else np.zeros(n, dtype=bool))

cons = C.copy()
cons["__name"] = cons[c_name].astype(str).str.strip()
cons["__var"] = cons[c_var].astype(str).str.strip()
cons["__coef"] = pd.to_numeric(cons[c_coef], errors="coerce").fillna(0.0)
SENSE = {"<=": "<=", "=<": "<=", "<": "<=", "max": "<=", "at most": "<=", "le": "<=",
         ">=": ">=", "=>": ">=", ">": ">=", "min": ">=", "at least": ">=", "ge": ">=",
         "=": "=", "==": "=", "eq": "=", "equal": "=", "exactly": "="}
unknown = sorted(set(cons["__var"]) - set(idx))
if unknown:
    omniscope_api.abort(f"Constraints refer to variables not in input 1: {', '.join(unknown[:5])}")
cnames = list(dict.fromkeys(cons["__name"]))
A = np.zeros((len(cnames), n))
senses, rhs = [], []
for k, cn in enumerate(cnames):
    sub = cons[cons["__name"] == cn]
    for v_, a in zip(sub["__var"], sub["__coef"]):
        A[k, idx[v_]] += a
    s_raw = str(sub[c_sense].iloc[0]).strip().lower()
    if s_raw not in SENSE:
        omniscope_api.abort(f"Constraint '{cn}': sense '{sub[c_sense].iloc[0]}' not understood; use <=, >= or =.")
    senses.append(SENSE[s_raw])
    r = pd.to_numeric(sub[c_rhs], errors="coerce").iloc[0]
    if pd.isna(r):
        omniscope_api.abort(f"Constraint '{cn}': limit is missing or not a number.")
    rhs.append(float(r))
senses, rhs = np.array(senses), np.array(rhs)

maximise = sense_obj == "MAXIMISE"
cc = -c if maximise else c
omniscope_api.update_message(f"Solving: {n} variables, {len(cnames)} constraints" + (", integer" if integ.any() else ""))
duals = reduced = None
if integ.any():
    lo = np.where(senses == ">=", rhs, np.where(senses == "=", rhs, -np.inf))
    hi = np.where(senses == "<=", rhs, np.where(senses == "=", rhs, np.inf))
    res = milp(cc, constraints=LinearConstraint(A, lo, hi) if len(cnames) else None, integrality=integ.astype(int),
               bounds=Bounds(lb, ub), options={"time_limit": time_limit})
    x, ok, msg = res.x, res.status == 0, res.message
    status = {0: "Optimal", 1: "Time limit reached", 2: "Infeasible", 3: "Unbounded"}.get(res.status, "Not solved")
else:
    le, ge, eq = senses == "<=", senses == ">=", senses == "="
    A_ub = np.vstack([A[le], -A[ge]]) if (le.any() or ge.any()) else None
    b_ub = np.concatenate([rhs[le], -rhs[ge]]) if A_ub is not None else None
    res = linprog(cc, A_ub=A_ub, b_ub=b_ub, A_eq=A[eq] if eq.any() else None, b_eq=rhs[eq] if eq.any() else None,
                  bounds=list(zip(lb, [None if not np.isfinite(u) else u for u in ub])), method="highs",
                  options={"time_limit": time_limit})
    x, ok, msg = res.x, res.status == 0, res.message
    status = {0: "Optimal", 1: "Iteration / time limit", 2: "Infeasible", 3: "Unbounded"}.get(res.status, "Not solved")
    if ok:
        sign = -1.0 if maximise else 1.0
        d = np.zeros(len(cnames))
        if A_ub is not None:
            m_ub = res.ineqlin.marginals
            nle = int(le.sum())
            d[np.flatnonzero(le)] = m_ub[:nle]
            d[np.flatnonzero(ge)] = -m_ub[nle:]
        if eq.any():
            d[np.flatnonzero(eq)] = res.eqlin.marginals
        duals = sign * d
        reduced = sign * (res.lower.marginals + res.upper.marginals)

sol = V.copy()
if ok and x is not None:
    xv = np.where(integ, np.round(x), x)
    sol["Optimal Value"] = xv.astype("float64")
    sol["Objective Contribution"] = (xv * c).astype("float64")
    sol["At Bound"] = np.where(np.isclose(xv, lb), "Lower", np.where(np.isfinite(ub) & np.isclose(xv, ub), "Upper", ""))
    sol["Reduced Cost"] = reduced.astype("float64") if reduced is not None else np.nan
    lhs = A @ xv
else:
    sol["Optimal Value"] = np.nan
    sol["Objective Contribution"] = np.nan
    sol["At Bound"] = ""
    sol["Reduced Cost"] = np.nan
    lhs = np.full(len(cnames), np.nan)
sol["Reduced Cost"] = sol["Reduced Cost"].astype("float64")

crep = pd.DataFrame({"Constraint": cnames, "Sense": senses, "Limit": rhs, "Used": lhs})
crep["Slack"] = np.where(crep["Sense"] == ">=", crep["Used"] - crep["Limit"], crep["Limit"] - crep["Used"])
crep.loc[crep["Sense"] == "=", "Slack"] = 0.0
crep["Binding"] = np.where(np.isfinite(crep["Slack"]) & (np.abs(crep["Slack"]) <= 1e-6 * np.maximum(1, np.abs(crep["Limit"]))), "Yes", "No")
crep["Shadow Price"] = duals if duals is not None else np.nan
crep["Shadow Price"] = crep["Shadow Price"].astype("float64")
for col in ("Limit", "Used", "Slack"):
    crep[col] = crep[col].astype("float64")

objective = float(np.dot(c, sol["Optimal Value"].to_numpy(dtype=float))) if ok else np.nan
summ = pd.DataFrame({"Status": [status], "Objective": [("Maximise" if maximise else "Minimise")], "Objective Value": [objective],
                     "Variables": [n], "Integer Variables": [int(integ.sum())], "Constraints": [len(cnames)],
                     "Binding Constraints": [int((crep["Binding"] == "Yes").sum()) if ok else 0], "Solver Message": [str(msg)]})
summ["Objective Value"] = summ["Objective Value"].astype("float64")

omniscope_api.write_output(sol, "solution")
omniscope_api.write_output(crep, "constraints")
omniscope_api.write_output(summ, "summary")
if ok:
    omniscope_api.close(f"{status}: objective {objective:,.4g} with {int((crep['Binding'] == 'Yes').sum())} binding constraint(s).")
else:
    omniscope_api.close(f"{status}: {msg}")
