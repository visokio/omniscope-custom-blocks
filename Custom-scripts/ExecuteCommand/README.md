# Execute Command

Runs a program on the machine that runs Omniscope, once or once per record, passes the input records through and outputs each command's exit code, output and errors.

Use it to make a command-line step part of a workflow: run a script that fetches or converts a file, copy or move files, or call a tool that has no Omniscope block. Blocks connected after it run once its commands have finished.

- Enter one **Command**, or choose a **Field with commands** to run one command per record (the field is used when both are set). Records with an empty command are skipped.
- Commands run in order, one at a time, **without a shell**. On Linux and macOS the command is split into the program and its arguments the way a shell would split it (quotes group words), but pipes (`|`), redirects (`>`), `;`, `&&` and variables such as `$HOME` are passed to the program as plain text. On Windows the command line goes to the program as typed.
- **Run through cmd /c** puts `cmd /c` in front of each command, so Windows shell commands such as `copy`, `dir` and `del` work: `cmd /c copy C:/Myfile.txt D:/Myfile.txt`. The command then runs through the Windows command shell, with its pipes, redirects and variables.
- By default the block **stops at the first command that fails** (a non-zero exit code, a program that can't be found, or the time limit) and shows the end of the command's error output in its message. Tick **Carry on after a failed command** to run the rest; each failure is recorded in the Commands output and shown as a message.
- The **time limit** stops a command that runs too long (10 minutes by default; 0 for no limit).

## Security: what this block can do, and who should use it

**This block runs any program, with any arguments, as the operating-system user that Omniscope runs as.** It can read, change and delete whatever that user can, start other programs, and reach whatever that machine can reach on the network. That is the purpose of the block, and the reason to think before allowing it.

- **Anyone who can edit a project can run commands on the server through it**: they can add the block, or change the command in one that is already there. The block adds no new power over Omniscope's other script blocks (a Python block can run programs too), but it makes running them a one-line job. On a shared server, only give project-editing rights in a folder to people you would trust with a login to the server itself.
- **With "Field with commands", whoever controls the data controls the commands.** Only feed it commands from a source you control (a file that only administrators can change, a table you maintain). Never build commands from form entries, uploaded files, web pages or other data that outsiders can influence: a value such as `cmd /c del ...` in the data would be run.
- **"Run through cmd /c" passes the command to the Windows shell**, where `&`, `|` and `>` take effect. Only tick it for commands that need it.
- **Run custom blocks in Docker** (Admin app, R/Python settings) to contain them: the command then runs inside the block's container, without access to the server's own files except the folders you share with it. Commands that need the server's own programs or files won't work there.
- The block writes each command and its output to the Commands output. Don't put passwords in commands, or the output, the project and any report built on it will hold them.

## Language
Python

## Inputs
- **Input 1** (optional): records to pass through, and the source of the commands when "Field with commands" is set.

## Options

| Option | Name in script | Type | Default | Description |
|---|---|---|---|---|
| Command | `command` | Text | | The program and its arguments, for example `python --version`. Leave empty to take commands from a field. |
| Field with commands | `commands_field` | Field | | A field with one command per record. Only use with data you trust. From input 1. |
| Carry on after a failed command | `ignoreErrors` | Yes/no | unticked | Untick to stop with an error at the first failed command; tick to run the rest and record the failure. |
| Run through cmd /c (Windows) | `auto_cmd` | Yes/no | unticked | Puts `cmd /c` in front of each command, for Windows shell commands such as `copy`. |
| Time limit (seconds) | `timeout` | Whole number | 600 | Stop a command that runs longer than this. 0 for no limit. |

## Outputs
- **Input Data** (`Output Data`): the input records, unchanged (nothing, if the input is not connected).
- **Commands** (`Output Data 2`): one record per command run: `cmd` (the command), `code` (its exit code; empty if it didn't run to the end), `stdout` (what it printed), `stderr` (its error output) and `error` (why it failed, empty when it worked). Output is read as UTF-8, with characters that aren't valid UTF-8 replaced; trailing line breaks are removed.

## Limits
- The command runs on the machine that runs the block: the Omniscope server, or, if the server runs custom blocks in Docker, the block's container. Paths and programs are that machine's, not yours.
- Each command's output is held in memory until it finishes; very large outputs (hundreds of megabytes) are better written to a file by the command itself.
- In tests, 20 short commands from a field ran in under a second.

## Dependencies
None beyond pandas, which Omniscope's Python environment provides, and Python's own `subprocess` and `shlex`.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo: `nightly-steps.csv` holds a few harmless commands, and `placeholder.csv` is the Commands output they give.
