"""Principal Component Analysis: summarise many correlated numeric fields with
a few components, for segmentation, index building, visualising similarity
(score plots) and reducing predictors before modelling.

  Standardised (correlation) PCA by default, so fields in different units count
  equally; or covariance PCA on centred values.
  Components kept: a fixed number, or automatically (eigenvalue above 1 for
  standardised data, the Kaiser rule; otherwise enough to explain the target
  share of variance).
  Signs are fixed so that each component's largest loading is positive, making
  results repeatable.

Outputs: explained variance per component, loadings (field x component, with
the correlation of each field with each component), and the input rows with
their component scores. Rows with a missing value in a chosen field get no score.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


fields = list(opt("fields", []) or [])
standardise = bool(opt("standardise", True))
n_comp = int(opt("components", 0) or 0)
target_share = float(opt("variance_target", 0.8))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
miss = [f for f in fields if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")
if not fields:
    fields = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]
if len(fields) < 2:
    omniscope_api.abort("Choose at least two numeric fields.")
X = pd.DataFrame({f: pd.to_numeric(df[f], errors="coerce").astype("float64") for f in fields})
bad = [f for f in fields if df[f].notna().any() and X[f].isna().all()]
if bad:
    omniscope_api.abort(f"Fields must be numeric: {', '.join(bad)}")
ok = X.notna().all(axis=1).to_numpy()
Xm = X[ok].to_numpy()
n, p = Xm.shape
if n < 3:
    omniscope_api.abort(f"Only {n} complete rows; PCA needs at least 3.")
mean = Xm.mean(axis=0)
sd = Xm.std(axis=0, ddof=1)
const = [fields[j] for j in range(p) if sd[j] == 0]
if const:
    omniscope_api.abort(f"Fields with no variation cannot be used: {', '.join(const)}")
Z = (Xm - mean) / sd if standardise else Xm - mean
U, S, Vt = np.linalg.svd(Z, full_matrices=False)
eig = S ** 2 / (n - 1)
share = eig / eig.sum()
for k in range(Vt.shape[0]):  # repeatable signs: largest absolute loading positive
    j = np.argmax(np.abs(Vt[k]))
    if Vt[k, j] < 0:
        Vt[k] *= -1
        U[:, k] *= -1
if n_comp > 0:
    k_keep = min(n_comp, len(eig))
    rule = f"fixed at {k_keep}"
elif standardise:
    k_keep = max(1, int((eig > 1).sum()))
    rule = "eigenvalue above 1 (Kaiser)"
else:
    k_keep = int(np.searchsorted(np.cumsum(share), target_share) + 1)
    rule = f"{target_share:.0%} of variance"
k_keep = min(k_keep, len(eig))

comp = pd.DataFrame({"Component": [f"PC{i + 1}" for i in range(len(eig))], "Eigenvalue": eig, "Variance Share": share,
                     "Cumulative Share": np.cumsum(share), "Kept": ["Yes" if i < k_keep else "No" for i in range(len(eig))]})
comp["Number"] = np.arange(1, len(eig) + 1).astype("int64")
comp = comp[["Number", "Component", "Eigenvalue", "Variance Share", "Cumulative Share", "Kept"]]
for c in ("Eigenvalue", "Variance Share", "Cumulative Share"):
    comp[c] = comp[c].astype("float64")

load_rows = []
for k in range(k_keep):
    for j, f in enumerate(fields):
        corr = Vt[k, j] * np.sqrt(eig[k]) / (1.0 if standardise else sd[j])
        load_rows.append({"Component": f"PC{k + 1}", "Field": f, "Loading": float(Vt[k, j]), "Correlation With Component": float(corr),
                          "Squared Correlation": float(corr ** 2)})
loads = pd.DataFrame(load_rows)
loads["Abs"] = loads["Correlation With Component"].abs()
loads["Rank In Component"] = loads.groupby("Component")["Abs"].rank(ascending=False, method="first").astype("int64")
loads = loads.drop(columns=["Abs"])
top = loads[loads["Rank In Component"] <= 3].sort_values(["Component", "Rank In Component"])
labels = top.groupby("Component", sort=False).apply(lambda g: ", ".join(f"{'+' if c > 0 else '-'}{f}" for f, c in zip(g["Field"], g["Correlation With Component"])),
                                                    include_groups=False)
loads["Main Fields Of Component"] = loads["Component"].map(labels)

scores = df.copy()
Zall = (X.to_numpy() - mean) / sd if standardise else X.to_numpy() - mean
proj = Zall @ Vt[:k_keep].T
for k in range(k_keep):
    scores[f"PC{k + 1}"] = np.where(ok, proj[:, k], np.nan).astype("float64")
# a compact reconstruction error per row: how much of the row the kept components miss
recon = proj @ Vt[:k_keep]
err = np.sqrt(((Zall - recon) ** 2).sum(axis=1))
scores["Unexplained Distance"] = np.where(ok, err, np.nan).astype("float64")

omniscope_api.write_output(comp, "components")
omniscope_api.write_output(loads, "loadings")
omniscope_api.write_output(scores, "scores")
omniscope_api.close(f"{p} fields, {n:,} complete rows ({'standardised' if standardise else 'covariance'} PCA): kept {k_keep} component(s) by {rule}, "
                    f"explaining {comp['Cumulative Share'].iloc[k_keep - 1]:.0%} of the variance" + (f"; {int((~ok).sum()):,} rows with missing values not scored" if (~ok).any() else "") + ".")
