"""Execute Command: runs one command, or one command per record, on the machine that runs the block, and passes the
input records through."""
import os
import shlex
import subprocess

import pandas as pd
from omniscope.api import OmniscopeApi

api = OmniscopeApi()

command = api.get_option("command")
commands_field = api.get_option("commands_field")
ignore_errors = bool(api.get_option("ignoreErrors"))
auto_cmd = bool(api.get_option("auto_cmd"))
timeout = api.get_option("timeout")

input_data = api.read_input_records(input_number=0)

timeout = None if timeout in (None, "", 0) else float(timeout)
if timeout is not None and timeout < 0:
    api.abort("Time limit must be 0 (no limit) or a number of seconds.")

if commands_field:
    if input_data is None:
        api.abort("\"Field with commands\" is set, but nothing is connected to the block's input.")
    if commands_field not in input_data.columns:
        api.abort(f"{commands_field} is not in the input.")
    values = input_data[commands_field]
    commands = [None if pd.isna(v) or str(v).strip() == "" else str(v).strip() for v in values]
else:
    if command is None or str(command).strip() == "":
        api.abort("Enter a Command, or choose a Field with commands.")
    commands = [str(command).strip()]

windows = os.name == "nt"


def run(cmd):
    """Runs one command; returns (exit code, output, errors, problem)."""
    full = "cmd /c " + cmd if auto_cmd else cmd
    # No shell: on Windows the command line goes to the program as typed (Windows splits it); elsewhere it is
    # split into the program and its arguments like a shell would, but without pipes, redirects or variables.
    try:
        args = full if windows else shlex.split(full)
    except ValueError as exc:  # an unclosed quote
        return None, "", "", f"Can't read the command: {exc}"
    program = full.split()[0] if windows else args[0]
    try:
        result = subprocess.run(args, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        return None, "", "", f"Program not found: {program}"
    except PermissionError:
        return None, "", "", "Permission denied: the program can't be run"
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"").decode("utf-8", errors="replace")
        err = (exc.stderr or b"").decode("utf-8", errors="replace")
        return None, out, err, f"Stopped after the time limit of {timeout:g} seconds"
    out = result.stdout.decode("utf-8", errors="replace")
    err = result.stderr.decode("utf-8", errors="replace")
    problem = None if result.returncode == 0 else f"Exit code {result.returncode}"
    return result.returncode, out, err, problem


def last_lines(text, n=5, width=600):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return " | ".join(lines[-n:])[-width:]


rows = []
skipped = 0
for cmd in commands:
    if cmd is None:
        skipped += 1
        continue
    code, out, err, problem = run(cmd)
    # trailing line breaks dropped, so "4\n" compares equal to "4" in later blocks
    rows.append({"cmd": cmd, "code": code, "stdout": out.rstrip("\r\n"), "stderr": err.rstrip("\r\n"),
                 "error": problem})
    if problem is not None:
        detail = last_lines(err) or last_lines(out)
        text = f"Command failed ({problem}): {cmd}" + (f" -- {detail}" if detail else "")
        if not ignore_errors:
            api.abort(text)
        api.update_message(text)

results = pd.DataFrame(rows, columns=["cmd", "code", "stdout", "stderr", "error"])
results["code"] = pd.array(results["code"].tolist(), dtype="Int64")
for c in ("cmd", "stdout", "stderr", "error"):
    results[c] = results[c].astype(object)

if input_data is not None:
    api.write_output(input_data, "Output Data")
api.write_output(results, "Output Data 2")

failed = int(results["error"].notna().sum())
message = f"Ran {len(results)} command{'s' if len(results) != 1 else ''}"
message += f", {failed} failed (carried on, as set)." if failed else "."
if skipped:
    message += f" {skipped} records with no command were skipped."
api.commit(message)
