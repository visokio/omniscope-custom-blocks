"""Every command run here is the Python interpreter running the tests, printing or exiting: nothing touches files
or the network. Tests that need another operating system replace subprocess.run and only check what would run."""
import os
import shlex
import subprocess
import sys
import time

import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "nightly-steps.csv")
PY = shlex.quote(sys.executable)
RESULT_FIELDS = ["cmd", "code", "stdout", "stderr", "error"]


def py(code):
    return f"{PY} -c {shlex.quote(code)}"


def test_one_command_and_the_input_passes_through():
    df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
    res = run_block(HERE, df, {"command": py("print('hello')")}).raise_for_error()
    assert res.output(0)["id"].tolist() == [1, 2, 3]
    out = res.output(1)
    assert list(out.columns) == RESULT_FIELDS and len(out) == 1
    assert out.loc[0, "code"] == 0 and out.loc[0, "stdout"] == "hello" and pd.isna(out.loc[0, "error"])
    assert res.final_message == "Ran 1 command."


def test_no_input_is_fine_for_a_single_command():
    res = run_block(HERE, None, {"command": py("print(2 + 2)")}).raise_for_error()
    assert 0 not in res.outputs and res.output(1).loc[0, "stdout"].strip() == "4"


def test_sample_commands_from_a_field(monkeypatch):
    # The sample uses "python", which may not be on the PATH here (or may be another version): run this one
    monkeypatch.setattr(subprocess, "run", _python_alias(subprocess.run))
    # The original raised TypeError on the record with no command
    res = run_block(HERE, SAMPLE, {"commands_field": "Command"}).raise_for_error()
    assert len(res.output(0)) == 4
    out = res.output(1)
    assert out["cmd"].tolist() == ["python --version", "python -c \"print('Hello from the server')\"",
                                   "python -c \"print(2 + 2)\""]
    assert out["code"].tolist() == [0, 0, 0]
    assert out["stdout"].tolist()[0].startswith("Python 3")
    assert out["stdout"].str.strip().tolist()[1:] == ["Hello from the server", "4"]
    assert res.final_message == "Ran 3 commands. 1 records with no command were skipped."


def _python_alias(real_run):
    def run(args, **kw):
        if isinstance(args, list) and args and args[0] == "python":
            args = [sys.executable] + args[1:]
        return real_run(args, **kw)
    return run


def test_a_failed_command_stops_the_block_with_its_errors():
    # The original raised NameError ("ignoreErrors" is not defined) whenever a command failed
    cmd = py("import sys; print('working'); sys.stderr.write('disk full\\n'); sys.exit(3)")
    res = run_block(HERE, None, {"command": cmd})
    assert res.status == "aborted"
    assert "Exit code 3" in res.final_message and "disk full" in res.final_message


def test_carry_on_after_a_failed_command():
    df = pd.DataFrame({"c": [py("import sys; sys.exit(2)"), py("print('second')")]})
    res = run_block(HERE, df, {"commands_field": "c", "ignoreErrors": True}).raise_for_error()
    out = res.output(1)
    assert out["code"].tolist() == [2, 0] and out["error"].tolist()[0] == "Exit code 2" and pd.isna(out["error"][1])
    assert out.loc[1, "stdout"].strip() == "second"
    assert res.final_message == "Ran 2 commands, 1 failed (carried on, as set)."
    assert any("Exit code 2" in m for m in res.messages)


def test_a_program_that_does_not_exist():
    # The original raised FileNotFoundError
    res = run_block(HERE, None, {"command": "no-such-program-xyz --help"})
    assert res.status == "aborted" and "Program not found: no-such-program-xyz" in res.final_message
    res = run_block(HERE, None, {"command": "no-such-program-xyz", "ignoreErrors": True}).raise_for_error()
    assert pd.isna(res.output(1).loc[0, "code"]) and res.output(1).loc[0, "error"].startswith("Program not found")


def test_output_that_is_not_utf8():
    # The original raised UnicodeDecodeError (Windows programs often write in the local code page)
    res = run_block(HERE, None, {"command": py("import sys; sys.stdout.buffer.write(b'caf\\xe9\\n')")})
    assert res.raise_for_error().output(1).loc[0, "stdout"].startswith("caf")


def test_time_limit():
    t0 = time.time()
    res = run_block(HERE, None, {"command": py("import time; print('start', flush=True); time.sleep(30)"),
                                 "timeout": 1, "ignoreErrors": True}).raise_for_error()
    assert time.time() - t0 < 15
    out = res.output(1)
    assert out.loc[0, "error"] == "Stopped after the time limit of 1 seconds" and pd.isna(out.loc[0, "code"])


def test_quoted_arguments_and_no_shell():
    # Arguments are split like a shell would, but a ";" or "$HOME" is passed as text, not run or expanded
    res = run_block(HERE, None, {"command": f"{PY} -c \"import sys; print(sys.argv[1:])\" 'two words' '$HOME;ls'"})
    assert res.raise_for_error().output(1).loc[0, "stdout"].strip() == "['two words', '$HOME;ls']"


def test_what_runs_on_windows_and_with_cmd(monkeypatch):
    # On Windows the original split the command with shlex in non-POSIX mode, which kept the quotes inside the
    # arguments ("C:/My Files/a.txt" arrived with its quotes). The command line now goes to Windows as typed.
    calls = []

    def fake_run(args, **kw):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, b"ok", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(os, "name", "nt")
    run_block(HERE, None, {"command": 'copy "C:/My Files/a.txt" D:/', "auto_cmd": True}).raise_for_error()
    monkeypatch.setattr(os, "name", "posix")
    run_block(HERE, None, {"command": "dir /b", "auto_cmd": True}).raise_for_error()
    assert calls == ['cmd /c copy "C:/My Files/a.txt" D:/', ["cmd", "/c", "dir", "/b"]]


def test_bad_set_ups_abort_with_a_message():
    # The original crashed on each of these
    res = run_block(HERE, None, {})
    assert res.status == "aborted" and "Enter a Command" in res.final_message
    res = run_block(HERE, None, {"commands_field": "c"})
    assert res.status == "aborted" and "nothing is connected" in res.final_message
    res = run_block(HERE, pd.DataFrame({"x": [1]}), {"commands_field": "c"})
    assert res.status == "aborted" and "c is not in the input" in res.final_message
    res = run_block(HERE, None, {"command": f"{PY} -c \"print('unclosed)"})
    assert res.status == "aborted" and "Can't read the command" in res.final_message


def test_empty_input_with_a_field_runs_nothing():
    df = pd.DataFrame({"c": pd.Series([], dtype=object)})
    res = run_block(HERE, df, {"commands_field": "c"}).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0 and list(res.output(1).columns) == RESULT_FIELDS


def test_many_commands_and_a_large_input():
    df = pd.DataFrame({"c": [py(f"print({i} * 2)") for i in range(20)]})
    t0 = time.time()
    out = run_block(HERE, df, {"commands_field": "c"}).raise_for_error().output(1)
    assert time.time() - t0 < 60
    assert out["stdout"].str.strip().tolist() == [str(i * 2) for i in range(20)]
    big = pd.DataFrame({"id": range(200_000), "v": [1.5] * 200_000})
    res = run_block(HERE, big, {"command": py("print('done')")}).raise_for_error()
    assert len(res.output(0)) == 200_000
