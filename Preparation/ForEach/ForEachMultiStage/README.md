# For Each Multi Stage

Runs another Omniscope project once per input record in up to three stages, each a separate run of its own blocks, with an optional stage run once before the loop. Before each record's stages it sets the project's parameters from the record.

Within one workflow run, Omniscope runs blocks in the order their connections require; blocks that are not connected have no set order. When one part of a project must finish before another starts (build a file, then publish it; load a table, then report on it), each part has to be a separate run. This block runs those parts as stages, in order, once per record.

- **Before the loop** (optional): the listed blocks run once, before any parameter is set, for example to refresh a shared lookup.
- **For each record**, in order: the block **sets the project's parameters** from the chosen fields, then runs **stage 1**, **stage 2** and **stage 3**, each a separate workflow run started when the previous one has finished. Stage 1 always runs (no blocks listed: the whole workflow); stages 2 and 3 run only when they list blocks.
- The **Passes** output has one record per input record: the pass number, the parameter values, the result, the stage that failed (if any) and the job IDs of the stages.
- A failed or cancelled stage stops the block, or, with **Carry on after a failed pass**, skips the rest of that pass and goes on with the next record. A failed stage before the loop always stops the block.

It uses the project's Workflow REST API: `w/updateparams`, `w/execute` and `w/job/<id>/state`.

## When to use it

- Use the core **For Each** block when the blocks to repeat can sit in the same project as the loop: it is simpler and faster.
- Use **For Each (Separate Workflows)** to repeat a separate project once per record in a single run.
- Use this block when each record needs **several runs in a set order** in the other project, or one run **before the loop**.

## Before you start

- **The other project** needs project parameters named like the input fields, linked to the block options they should change.
- **Two workflow jobs at once.** This block's own workflow keeps running while it waits, so the server must allow at least 2 concurrent workflow jobs (Admin app > Advanced > Concurrent Workflow Jobs; the default is 1).
- **Permissions.** The user making the requests needs the *Workflow Execution via APIs* and *Project parameters access via APIs* permissions.
- **The address.** On the same server, use the internal address, such as `http://127.0.0.1:24679/Folder/Project.iox/`. If the server asks for sign-in (a list of users), give a username and password: they are sent with basic authentication, which anyone watching the connection can read, so use an `https://` address unless the server is this machine (`127.0.0.1`). Use an account with only the permissions the block needs.
- A project cannot run itself with this block.

## Language and libraries

Python. It uses urllib3 (MIT licence) for the HTTP requests and pandas (BSD 3-Clause) for the records. pandas is part of Omniscope's Python environment; urllib3 is listed in the block's dependencies, so Omniscope installs it with pip on first run if it is missing.

## Inputs

- **Input 1**: one record per pass, with one field per project parameter to set. Other fields are ignored.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Project address | `Iox_File_Url` | Text | The address of the project to run, ending in `.iox`. A report or workflow address of the project is cut back to the project. |
| Username | `username` | Text | Optional. For a server that asks for sign-in with a list of users. |
| Password | `password` | Password | Optional. The password for the username. |
| Blocks before the loop | `Block_Names_Before` | Text | Optional. Blocks to run once, before any parameter is set, separated by commas. Empty: no stage before the loop. |
| Refresh from source (before the loop) | `Refresh_From_Source_Before` | Yes/no | Reload the sources when running the blocks before the loop. |
| Parameter fields | `Parameters` | Fields | Input fields named like parameters of the other project. |
| Stage 1 blocks | `Block_Names` | Text | Optional. Blocks to run first on each pass, separated by commas. Empty: the whole workflow. |
| Refresh from source (stage 1) | `Refresh_From_Source` | Yes/no | Reload the sources in stage 1. |
| Stage 2 blocks | `Block_Names2` | Text | Optional. Blocks to run once stage 1 has finished. Empty: no stage 2. |
| Refresh from source (stage 2) | `Refresh_From_Source2` | Yes/no | Reload the sources in stage 2. |
| Stage 3 blocks | `Block_Names3` | Text | Optional. Blocks to run once stage 2 has finished. Empty: no stage 3. |
| Refresh from source (stage 3) | `Refresh_From_Source3` | Yes/no | Reload the sources in stage 3. |
| Carry on after a failed pass | `ignore_errors` | Yes/no | Record a failed pass and go on with the next record. Off: stop at the first failure. |
| Wait for a busy project (minutes) | `busy_wait_minutes` | Integer | How long to wait for the project when it is already running, or when a run stays queued, before stopping with an error. Default 10. |

## Outputs

- **Passes** (`passes`): one record per input record: Pass (1, 2, ...), the parameter fields, Result (COMPLETED, FAILED or CANCELLED), Failed at stage (empty when the pass completed) and Job IDs (the stages' job IDs, comma-separated). An output field whose name is already taken by a parameter field gets " (For Each)" added.

## Values sent

Text and numbers are sent as they are (whole numbers as whole numbers), yes/no values as true/false, dates as ISO 8601 text such as `2025-03-01T00:00:00+00:00`, and missing values as null. The server converts each value to its parameter's type, or refuses the update; the block then stops with the server's message.

## Limits

- Stages and passes run one after another, never in parallel. Each stage is a full workflow run, with its start-up time.
- Block names containing a comma cannot be listed.
- Tested only against a stand-in for the server (see `tests/`): the requests are checked, not a real server's handling of them.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented.
