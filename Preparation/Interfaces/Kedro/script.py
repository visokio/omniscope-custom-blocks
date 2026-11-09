"""Kedro block: runs a Kedro project's pipeline on the block's inputs and outputs datasets it produces.

Each connected input is saved to the catalog dataset named in its option (or, for a name the catalog does not
declare, to data/01_raw/<name>.csv as earlier versions of this block did); the pipeline is run with Kedro's
session API; each output option names a dataset to read back: a free output of the run, a catalog dataset, or
data/08_reporting/<name>.csv.
"""
import os
import sys

import pandas as pd

from omniscope.api import OmniscopeApi

N_INPUTS = 3
N_OUTPUTS = 2

omniscope_api = OmniscopeApi()


def text_option(name):
    value = omniscope_api.get_option(name)
    if value is None:
        return ""
    return str(value).strip()


def in_catalog(catalog, name):
    try:
        return name in catalog
    except TypeError:  # very old catalogs have no __contains__
        return name in catalog.list()


def as_frame(value, name):
    if hasattr(value, "load") and not isinstance(value, pd.DataFrame):
        value = value.load()  # a dataset object rather than its data
    if isinstance(value, pd.Series):
        value = value.to_frame()
    if not isinstance(value, pd.DataFrame):
        omniscope_api.abort(f"Dataset '{name}' is a {type(value).__name__}, not a table, so it can't be "
                            "output. Choose a dataset the pipeline writes as a table (a pandas DataFrame).")
    return value.reset_index(drop=True)


# ---- options and inputs, checked before anything runs
project_path = text_option("path")
if not project_path:
    omniscope_api.abort("Choose the folder of the Kedro project (the folder holding pyproject.toml).")
project_path = os.path.abspath(project_path)
pyproject = os.path.join(project_path, "pyproject.toml")
if not os.path.isfile(pyproject):
    omniscope_api.abort(f"No pyproject.toml in '{project_path}'. Choose the Kedro project's top folder.")
with open(pyproject, encoding="utf-8") as fh:
    if "[tool.kedro]" not in fh.read():
        omniscope_api.abort(f"'{pyproject}' has no [tool.kedro] section, so this is not a Kedro project "
                            "(Kedro 0.19 or later).")

inputs = []
for i in range(N_INPUTS):
    name = text_option(f"input{i}")
    data = omniscope_api.read_input_records(input_number=i)
    if name and data is None:
        omniscope_api.abort(f"Input dataset {i + 1} is named '{name}' but nothing is connected to input {i + 1}.")
    if data is not None and not name:
        omniscope_api.abort(f"Input {i + 1} is connected; give the Kedro dataset it feeds in "
                            f"'Input dataset {i + 1}'.")
    if name:
        inputs.append((name, data))

outputs = [text_option(f"output{i}") for i in range(N_OUTPUTS)]
if not outputs[0]:
    omniscope_api.abort("Give the Kedro dataset to output in 'Output dataset 1'.")
pipeline_name = text_option("pipeline") or None
env = text_option("env") or None

try:
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project
except ImportError as exc:
    omniscope_api.abort(f"Kedro is not installed in Omniscope's Python environment ({exc}). "
                        "Install kedro, and the packages the Kedro project needs, then run again.")

# ---- run
os.chdir(project_path)  # catalog file paths are relative to the project folder
if project_path not in sys.path:
    sys.path.append(project_path)

try:
    bootstrap_project(project_path)
except Exception as exc:  # noqa: BLE001 - report Kedro's reason to the user
    omniscope_api.abort(f"Kedro could not load the project in '{project_path}': {exc}")

omniscope_api.update_message("Running the Kedro pipeline" + (f" '{pipeline_name}'" if pipeline_name else ""))
results = {}
with KedroSession.create(project_path=project_path, env=env) as session:
    try:
        catalog = session.load_context().catalog
    except Exception as exc:  # noqa: BLE001
        omniscope_api.abort(f"Kedro could not read the project's configuration: {exc}")

    for name, data in inputs:
        if in_catalog(catalog, name):
            catalog.save(name, data)
        else:  # the convention of earlier versions of this block
            raw = os.path.join(project_path, "data", "01_raw")
            os.makedirs(raw, exist_ok=True)
            data.to_csv(os.path.join(raw, name + ".csv"), index=False)

    try:
        results = session.run(pipeline_name=pipeline_name) or {}
    except Exception as exc:  # noqa: BLE001
        omniscope_api.abort(f"The Kedro run failed: {type(exc).__name__}: {exc}")

    for i, name in enumerate(outputs):
        if not name:
            continue
        if name in results:
            frame = as_frame(results[name], name)
        elif in_catalog(catalog, name):
            frame = as_frame(catalog.load(name), name)
        else:
            reporting = os.path.join(project_path, "data", "08_reporting", name + ".csv")
            if not os.path.isfile(reporting):
                omniscope_api.abort(f"Output dataset '{name}' is not in the project's catalog, not a free output "
                                    f"of the run, and there is no data/08_reporting/{name}.csv.")
            frame = pd.read_csv(reporting)
        omniscope_api.write_output_records(frame, output_number=i)

omniscope_api.close(f"Kedro run finished; {sum(1 for o in outputs if o)} dataset(s) output.")
