"""Fake ``omniscope.api`` for running custom block scripts outside Omniscope.

The real module is shipped with Omniscope and is not on PyPI. This stand-in
implements the documented Python API (``OmniscopeApi``) closely enough that a
block's ``script.py`` runs unchanged under pytest:

* inputs come from pandas DataFrames or CSV files,
* options come from a dict / JSON file (manifest defaults fill the gaps),
* outputs are captured as DataFrames (and optionally written to CSV),
* messages, commit / close / cancel / abort are recorded.

Configuration is passed through ``omniscope.api._configure(...)`` (done by
``harness.runner.run_block``), or through the ``OMNI_HARNESS_CONFIG``
environment variable pointing at a JSON file when a script is run directly::

    {"inputs": {"0": "in.csv"}, "options": {"x": 1}, "output_dir": "out"}

Behaviour mirrors the real API where it matters for testing:

* ``abort()`` terminates the script immediately (raises ``BlockAborted``),
* after commit/close/cancel/abort no further interaction is allowed,
* ``write_output_records`` must receive a DataFrame and the schema (field
  names and broad types) must be the same across calls to the same output,
* ``process_stream`` refuses ``None`` results and schema changes,
* streaming APIs and batch read/write APIs cannot be mixed.
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

__all__ = ["OmniscopeApi", "BlockAborted", "HarnessError"]


class BlockAborted(SystemExit):
    """Raised by ``abort()``: the real API terminates the script immediately."""

    def __init__(self, message=""):
        super().__init__(0)
        self.message = message


class HarnessError(RuntimeError):
    """The script used the API in a way the real Omniscope would reject."""


_CONFIG: dict | None = None
_LAST_INSTANCE = None


def _configure(config: dict | None):
    """Set the configuration for the next ``OmniscopeApi()`` (used by the runner)."""
    global _CONFIG, _LAST_INSTANCE
    _CONFIG = config
    _LAST_INSTANCE = None


def _last_instance():
    return _LAST_INSTANCE


def _load_config() -> dict:
    if _CONFIG is not None:
        return _CONFIG
    path = os.environ.get("OMNI_HARNESS_CONFIG")
    if path:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _broad_type(dtype) -> str:
    """Map a pandas dtype to the Omniscope field type it would become."""
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "DECIMAL"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "DATE"
    return "TEXT"


def _schema(df: pd.DataFrame):
    return [(str(c), _broad_type(t)) for c, t in df.dtypes.items()]


def _compatible(a, b) -> bool:
    if [n for n, _ in a] != [n for n, _ in b]:
        return False
    for (_, ta), (_, tb) in zip(a, b):
        # INTEGER and DECIMAL widen in Omniscope; an all-null chunk often
        # arrives as float or object, so be lenient there too.
        if ta == tb or {ta, tb} <= {"INTEGER", "DECIMAL"}:
            continue
        return False
    return True


ISO_DATE = r"\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?"


# Date fields reach scripts as datetime64[us, UTC] in host mode (pandas 3) and datetime64[ns, UTC] in
# Docker mode (pandas 2.3 image). Set OMNISCOPE_DT_UNIT=ns to mimic Docker.
DT_UNIT = os.environ.get("OMNISCOPE_DT_UNIT", "us")


def omniscope_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Give a frame the dtypes a real Omniscope server hands to a script
    (observed on Omniscope with pandas 3.1): Integer fields arrive as the
    nullable ``Int64`` dtype, Decimal as ``float64``, Text as ``object``
    holding ``str`` (missing = NaN), Date as ``datetime64``.
    A float column whose values are all whole numbers is treated as an
    Integer field with nulls, as Omniscope's type detection would.
    Date fields (and text that is entirely ISO dates, which Omniscope's
    type detection turns into Date fields) arrive as datetime64[us, UTC]."""
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_bool_dtype(s):
            continue
        if pd.api.types.is_datetime64_any_dtype(s):
            # Omniscope Date fields arrive time-zone aware, in UTC, microsecond precision
            d = s.dt.tz_localize("UTC") if s.dt.tz is None else s.dt.tz_convert("UTC")
            df[c] = d.astype(f"datetime64[{DT_UNIT}, UTC]")
            continue
        if (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)) and s.notna().any():
            nn = s.dropna().astype(str)
            if nn.str.fullmatch(ISO_DATE).all():
                d = pd.to_datetime(s, errors="coerce", format="mixed")
                if d.notna().sum() == s.notna().sum():
                    df[c] = d.dt.tz_localize("UTC").astype(f"datetime64[{DT_UNIT}, UTC]")
                    continue
        if pd.api.types.is_integer_dtype(s):
            df[c] = s.astype("Int64")
        elif pd.api.types.is_float_dtype(s):
            nn = s.dropna()
            if len(nn) and len(nn) < len(s) and (nn == nn.round()).all() and nn.abs().max() < 2**53:
                df[c] = s.astype("Int64")
        elif pd.api.types.is_string_dtype(s) and not pd.api.types.is_datetime64_any_dtype(s):
            df[c] = s.astype(object)
    return df


class OmniscopeApi:
    """Stand-in for ``omniscope.api.OmniscopeApi``."""

    def __init__(self):
        global _LAST_INSTANCE
        cfg = _load_config()
        self._options = dict(cfg.get("options") or {})
        self._docker = bool(cfg.get("is_docker", False))
        self._coerce = cfg.get("omniscope_dtypes", True)
        declared = cfg.get("declared_options")
        self._declared = None if declared is None else {str(d).lower() for d in declared}
        self._output_dir = cfg.get("output_dir")
        self._output_names = list(cfg.get("output_names") or [])
        self._inputs = {}
        for key, src in (cfg.get("inputs") or {}).items():
            self._inputs[int(key)] = src
        self._chunk_pos = {}
        self.outputs: dict[int, list[pd.DataFrame]] = {}
        self._schemas: dict[int, list] = {}
        self.messages: list[str] = []
        self.status: str | None = None  # committed / cancelled / aborted
        self.final_message: str | None = None
        self.options_read: list[str] = []
        self._mode: str | None = None  # "batch" or "stream"
        _LAST_INSTANCE = self

    # ------------------------------------------------------------------ utils
    def _check_open(self):
        if self.status is not None:
            raise HarnessError(f"API used after the execution was {self.status}")

    def _set_mode(self, mode):
        if self._mode is None:
            self._mode = mode
        elif self._mode != mode:
            raise HarnessError("streaming and batch read/write APIs cannot be mixed")

    def _input_frame(self, input_number) -> pd.DataFrame | None:
        if input_number not in self._inputs:
            return None
        src = self._inputs[input_number]
        if src is None:
            return None
        if isinstance(src, pd.DataFrame):
            return omniscope_dtypes(src.copy()) if self._coerce else src.copy()
        # Like Omniscope's File and Text Input blocks, pandas' CSV reader turns
        # empty cells and placeholders such as "N/A" and "NULL" into missing values.
        # Pass {"path": ..., "raw": True} to keep placeholders as text instead.
        if isinstance(src, dict) and "path" in src and src.get("text"):
            # Like a File block with field type detection "none" and placeholders kept, as probed on the server:
            # every field is text, the File block trims spaces, and the Python bridge still turns the pandas
            # NA tokens (N/A, NA, null, nan, #N/A...) into missing values.
            df = pd.read_csv(src["path"], dtype=str)
            df = df.apply(lambda c: c.str.strip())
            df = df.astype(object).where(df.notna() & (df != ""), None)
            return df
        if isinstance(src, dict) and "path" in src:
            kw = {"keep_default_na": False, "na_values": [""]} if src.get("raw") else {}
            df = pd.read_csv(src["path"], parse_dates=src.get("parse_dates") or False, **kw)
        else:
            df = pd.read_csv(src)
        return omniscope_dtypes(df) if self._coerce else df

    # -------------------------------------------------------------- options
    def get_option(self, option_name):
        """Real Omniscope looks options up case-insensitively and raises
        KeyError for a name the block does not declare (the docs say None)."""
        self._check_open()
        self.options_read.append(option_name)
        lowered = {str(k).lower(): v for k, v in self._options.items()}
        key = str(option_name).lower()
        if self._declared is not None and key not in self._declared:
            raise KeyError(key)
        return lowered.get(key)

    def is_docker(self):
        return self._docker

    # ---------------------------------------------------------------- input
    def read_input_records(self, input_number=0):
        self._check_open()
        self._set_mode("batch")
        return self._input_frame(input_number)

    def read_next_chunk(self, chunk_size=10000, input_number=0):
        self._check_open()
        df = self._input_frame(input_number)
        if df is None:
            return None
        pos = self._chunk_pos.get(input_number, 0)
        if pos >= len(df):
            return None
        self._chunk_pos[input_number] = pos + chunk_size
        return df.iloc[pos:pos + chunk_size].reset_index(drop=True)

    # --------------------------------------------------------------- output
    def _resolve_output(self, output):
        if isinstance(output, int):
            return output
        if isinstance(output, str):
            if output in self._output_names:
                return self._output_names.index(output)
            if output.isdigit():
                return int(output)
            raise HarnessError(f"unknown output name {output!r}; known: {self._output_names}")
        raise HarnessError(f"output must be int or str, got {type(output).__name__}")

    def _append(self, df, idx):
        if not isinstance(df, pd.DataFrame):
            raise HarnessError(f"output data must be a pandas DataFrame, got {type(df).__name__}")
        cols = [str(c) for c in df.columns]
        if len(set(cols)) != len(cols):
            raise HarnessError(f"duplicate output field names: {cols}")
        if any(c.strip() == "" for c in cols):
            raise HarnessError("empty output field name")
        sch = _schema(df)
        if idx in self._schemas and not _compatible(self._schemas[idx], sch):
            raise HarnessError(f"output {idx} schema changed between writes: {self._schemas[idx]} -> {sch}")
        self._schemas.setdefault(idx, sch)
        self.outputs.setdefault(idx, []).append(df.copy())

    def write_output_records(self, output_data, output_number=0):
        self._check_open()
        self._set_mode("batch")
        self._append(output_data, self._resolve_output(output_number))

    def write_output(self, output_data, output):
        self._check_open()
        self._set_mode("batch")
        self._append(output_data, self._resolve_output(output))

    # -------------------------------------------------------------- stream
    def process_stream(self, fn, chunk_size=10000):
        self._check_open()
        self._set_mode("stream")
        df = self._input_frame(0)
        if df is None:
            df = pd.DataFrame()
        starts = range(0, max(len(df), 1), chunk_size)
        for start in starts:
            chunk = df.iloc[start:start + chunk_size].reset_index(drop=True)
            out = fn(chunk)
            if out is None:
                raise HarnessError("process_stream function returned None")
            self._append(out, 0)

    # ------------------------------------------------------------ messages
    def update_message(self, message):
        self._check_open()
        self.messages.append(str(message))

    def _finish(self, status, message):
        self._check_open()
        self.status = status
        self.final_message = message or ""
        if self._output_dir and status == "committed":
            os.makedirs(self._output_dir, exist_ok=True)
            for idx, frames in self.output_frames().items():
                frames.to_csv(os.path.join(self._output_dir, f"output_{idx}.csv"), index=False)

    def commit(self, message=""):
        self._finish("committed", message)

    def close(self, message=""):
        self._finish("committed", message)

    def cancel(self, message=""):
        self._finish("cancelled", message)

    def abort(self, message=""):
        self._finish("aborted", message)
        raise BlockAborted(message)

    # ------------------------------------------------------- test helpers
    def output_frames(self) -> dict[int, pd.DataFrame]:
        res = {}
        for idx, frames in self.outputs.items():
            res[idx] = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        return res


if __name__ == "__main__":  # pragma: no cover
    print("This is the Omniscope API test double; see harness/README.md", file=sys.stderr)
