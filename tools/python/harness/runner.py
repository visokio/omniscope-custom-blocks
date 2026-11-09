"""Run an Omniscope custom block's script.py against the fake API.

    from harness.runner import run_block
    res = run_block("Preparation/Partition", inputs=[df], options={"partition_size": 2})
    res.output(0)      # DataFrame written to the first output
    res.status         # "committed" / "cancelled" / "aborted" / None
    res.messages       # update_message() calls
    res.error          # exception raised by the script, if any

Options not supplied are filled from the manifest's ``defaultValue`` (that is
what a user who leaves an option untouched gets in Omniscope). Supplying an
option the manifest does not declare raises, to catch typos.

Command line::

    python -m harness.runner <block_dir> --input a.csv [--input b.csv] \
        [--options opts.json] [--out outdir]
"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import sys
import traceback
from dataclasses import dataclass, field

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from omniscope import api as fake_api  # noqa: E402


@dataclass
class BlockResult:
    status: str | None
    outputs: dict
    messages: list
    final_message: str | None
    error: BaseException | None = None
    traceback: str | None = None
    options_read: list = field(default_factory=list)

    def output(self, idx=0) -> pd.DataFrame | None:
        return self.outputs.get(idx)

    @property
    def ok(self) -> bool:
        return self.error is None and self.status == "committed"

    def raise_for_error(self):
        if self.error is not None:
            raise AssertionError(f"block raised {self.error!r}\n{self.traceback}")
        if self.status != "committed":
            raise AssertionError(f"block finished with status {self.status!r}: {self.final_message}")
        return self


def load_manifest(block_dir):
    path = os.path.join(block_dir, "manifest.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _iter_options(options):
    for opt in options or []:
        yield opt


def manifest_defaults(manifest) -> dict:
    res = {}
    for opt in _iter_options((manifest or {}).get("options")):
        value = opt.get("defaultValue")
        if value is None and opt.get("@visokiotype", "").endswith("BooleanCustomBlockPublicOption"):
            value = False  # an untouched checkbox reads as False
        res[opt["name"]] = value
    return res


def output_names(manifest) -> list:
    return [o.get("id") for o in (manifest or {}).get("blockOutputs") or []]


def run_block(block_dir, inputs=None, options=None, *, use_defaults=True, strict_options=True,
              output_dir=None, is_docker=False, script=None) -> BlockResult:
    """Execute ``script.py`` of ``block_dir`` in-process with the fake API."""
    manifest = load_manifest(block_dir)
    opts = manifest_defaults(manifest) if use_defaults else {}
    declared = {o["name"] for o in _iter_options((manifest or {}).get("options"))}
    for k, v in (options or {}).items():
        if strict_options and manifest is not None and k not in declared:
            raise KeyError(f"option {k!r} is not declared in manifest.json (declared: {sorted(declared)})")
        opts[k] = v
    if isinstance(inputs, (pd.DataFrame, str, dict)):
        inputs = [inputs]
    inp = {}
    for i, src in enumerate(inputs or []):
        inp[i] = src
    fake_api._configure({
        "inputs": inp,
        "options": opts,
        "output_dir": output_dir,
        "output_names": output_names(manifest),
        "is_docker": is_docker,
        "declared_options": sorted(declared) if manifest is not None else None,
    })
    script_path = script or os.path.join(block_dir, (manifest or {}).get("scriptFilename", "script.py"))
    error = tb = None
    old_cwd = os.getcwd()
    try:
        runpy.run_path(script_path, run_name="__main__")
    except fake_api.BlockAborted:
        pass
    except SystemExit as exc:  # sys.exit() / raise SystemExit() after commit is normal
        if exc.code not in (None, 0):
            error, tb = exc, traceback.format_exc()
    except BaseException as exc:  # noqa: BLE001 - report everything to the test
        error, tb = exc, traceback.format_exc()
    finally:
        os.chdir(old_cwd)
    inst = fake_api._last_instance()
    fake_api._configure(None)
    if inst is None:
        return BlockResult(None, {}, [], None, error, tb)
    return BlockResult(inst.status, inst.output_frames(), inst.messages, inst.final_message,
                       error, tb, inst.options_read)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("block_dir")
    ap.add_argument("--input", action="append", default=[])
    ap.add_argument("--options", help="JSON file of option values")
    ap.add_argument("--out", help="directory for output_<n>.csv")
    a = ap.parse_args(argv)
    options = {}
    if a.options:
        with open(a.options, encoding="utf-8") as fh:
            options = json.load(fh)
    res = run_block(a.block_dir, inputs=a.input, options=options, output_dir=a.out)
    for m in res.messages:
        print("message:", m)
    print("status:", res.status, "-", res.final_message)
    for idx, df in res.outputs.items():
        print(f"--- output {idx}: {len(df)} rows x {len(df.columns)} fields")
        print(df.head(10).to_string())
    if res.error:
        print(res.traceback, file=sys.stderr)
        return 1
    return 0 if res.status == "committed" else 2


if __name__ == "__main__":
    sys.exit(main())
