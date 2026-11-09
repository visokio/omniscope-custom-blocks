# For Each (Separate Workflows)

Runs another Omniscope project once per input record, setting that project's parameters from the record before each run, and lists the result of every run.

Some jobs have to be repeated with different settings in a separate project: the same branch report produced for each branch, the same load run for each source file, a shared template project run for each client. This block drives that other project from a list: one record per run, one field per project parameter.

- For each record, in order, the block **sets the other project's parameters** from the chosen fields (a field named like a parameter sets that parameter), **starts its workflow** (all of it, or the blocks you list) and **waits for the run to finish** before going on to the next record.
- The **Runs** output has one record per run: the run number, the parameter values and the result (COMPLETED, FAILED or CANCELLED).
- A failed or cancelled run stops the block, or, with **Carry on after a failed run**, is recorded and the next record goes ahead.
- If the other project is already running, the block waits for it, up to a time you set (10 minutes by default).

It uses the project's Workflow REST API: `w/updateparams` to set the parameters, `w/execute` to start the workflow and `w/job/<id>/state` to follow the run.

## When to use it rather than the core For Each block

The core **For Each** block repeats part of the workflow it sits in, appends each run's output and needs no server settings: use it whenever the blocks to repeat can live in the same project. Use this block when the work to repeat is a **separate project**: a template shared by several workflows, a project whose outputs (files, database tables, published reports) are what matters rather than data to append, or one that must keep its own parameter values after the loop.

## Before you start

- **The other project** needs project parameters (three-dots menu > Parameters) named like the input fields, linked to the block options they should change.
- **Two workflow jobs at once.** This block's own workflow keeps running while it waits, so the server must allow at least 2 concurrent workflow jobs (Admin app > Advanced > Concurrent Workflow Jobs; the default is 1). Otherwise each run stays queued; the block gives up after the busy-project wait with a message saying so.
- **Permissions.** The user making the requests needs the *Workflow Execution via APIs* and *Project parameters access via APIs* permissions (both off by default).
- **The address.** On the same server, use the internal address, such as `http://127.0.0.1:24679/Folder/Project.iox/`, which avoids the public address and its certificate. If the server asks for sign-in (a list of users), give a username and password: they are sent with basic authentication, which anyone watching the connection can read, so use an `https://` address unless the server is this machine (`127.0.0.1`). Use an account with only the permissions the block needs.
- A project cannot run itself with this block: it would wait for its own run to finish.

## Language and libraries

Python. It uses urllib3 (MIT licence) for the HTTP requests and pandas (BSD 3-Clause) for the records. pandas is part of Omniscope's Python environment; urllib3 is listed in the block's dependencies, so Omniscope installs it with pip on first run if it is missing.

## Inputs

- **Input 1**: one record per run, with one field per project parameter to set. Other fields are ignored.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Project address | `Iox_File_Url` | Text | The address of the project to run, ending in `.iox`. A report or workflow address of the project is cut back to the project. |
| Username | `username` | Text | Optional. For a server that asks for sign-in with a list of users. |
| Password | `password` | Password | Optional. The password for the username. |
| Parameter fields | `Parameters` | Fields | Input fields named like parameters of the other project. Each record sets these parameters, then the workflow runs once. |
| Blocks to run | `Block_Names` | Text | Optional. Names of the blocks to run, separated by commas. Empty: the whole workflow. Blocks they depend on run too when needed. |
| Refresh from source | `Refresh_From_Source` | Yes/no | Reload the data from the sources on every run, rather than reuse data the blocks already hold. |
| Carry on after a failed run | `ignore_errors` | Yes/no | Record a failed or cancelled run in the output and go on. Off: stop at the first failed run. |
| Wait for a busy project (minutes) | `busy_wait_minutes` | Integer | How long to wait for the project when it is already running, or when a run stays queued, before stopping with an error. Default 10. |

## Outputs

- **Runs** (`runs`): one record per input record: Run (1, 2, ...), the parameter fields, Result (COMPLETED, FAILED or CANCELLED) and Job ID. An output field whose name is already taken by a parameter field gets " (For Each)" added.

## Values sent

Text and numbers are sent as they are (whole numbers as whole numbers), yes/no values as true/false, dates as ISO 8601 text such as `2025-03-01T00:00:00+00:00`, and missing values as null. The server converts each value to its parameter's type, or refuses the update; the block then stops with the server's message (for example `Parameter 'Region' not found`).

## Limits

- Runs are one after another, never in parallel.
- Block names containing a comma cannot be listed.
- The block does not read the other project's data; to bring results back, have the other project write them somewhere this workflow reads (a file or a database table).
- Tested only against a stand-in for the server (see `tests/`): the requests are checked, not a real server's handling of them.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented.
