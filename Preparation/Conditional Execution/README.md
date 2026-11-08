# Conditional Execution

When its yes/no option, usually linked to a project parameter, is on, starts a separate run of the listed blocks of a project; when it is off, does nothing.

Some parts of a project should only run when someone, or something outside the workflow, says so: a slow refresh from source, an export to a shared folder, an email. Link this block's **Run the blocks** option to a yes/no project parameter, and whatever sets the parameter (a report view, the scheduler, the REST API, or a **Set Project Parameters** block) decides whether those blocks run.

- **Off**: the block sends nothing and finishes with "nothing was started".
- **On**: the block asks the server to start the listed blocks (and whatever they depend on) as a **separate run**, and finishes straight away. It does not wait for that run or report how it went.
- The blocks can be in this project or another one, and need not be connected to this block.
- If the server refuses (unknown block name, no permission, no project at the address), the block stops with the server's message instead of reporting success.

It uses the project's Workflow REST API: `w/execute`, with `cancelExisting` true (a run of that project already in progress is cancelled so that the new one starts) and `waitForIdle` false (the request does not wait for the project to be idle).

## When to use it rather than the core control-flow blocks

The core **If Then Split** and **Output Router** blocks decide from the data, inside one run: they evaluate a formula on their input and halt the branches not taken. **Validate data** with a Halt action stops a branch when checks fail. Use those whenever the decision depends on the data flowing through this workflow. Use **Conditional Execution** when the decision is a **switch set from outside** the data (a parameter flipped in a report, by the scheduler or by another system), or when the blocks to start are **in another project** or not connected to anything that could carry the condition.

## Before you start

- **Permission.** The user making the request needs the *Workflow Execution via APIs* permission (off by default).
- **The address.** On the same server, use the internal address, such as `http://127.0.0.1:24679/Folder/Project.iox/`, which avoids the public address and its certificate. A report or workflow address of the project is cut back to the project. If the server asks for sign-in (a list of users), give a username and password: they are sent with basic authentication, which anyone watching the connection can read, so use an `https://` address unless the server is this machine (`127.0.0.1`). Use an account with only the permissions the block needs.
- **Pointing at this project.** Starting blocks of the project this block is in is the usual set-up. The request asks the server to cancel a run of that project already in progress (`cancelExisting`), and on this project that is the run this block belongs to, so make this block the last thing that run needs to do, and never list this block itself, or a block it depends on, among the blocks to run. How the server handles this case has not been tested here.

## Language and libraries

Python. It uses urllib3 (MIT licence) for the HTTP request. urllib3 is listed in the block's dependencies, so Omniscope installs it with pip on first run if it is missing.

## Inputs

None needed. An input, if connected, is ignored; connecting one is a way to make the block run after another block.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Project address | `Iox_File_Url` | Text | The address of the project whose blocks to run, ending in `.iox`. |
| Username | `username` | Text | Optional. For a server that asks for sign-in with a list of users. |
| Password | `password` | Password | Optional. The password for the username. |
| Run the blocks | `execute` | Yes/no | On: start the blocks. Off: do nothing. Link it to a yes/no project parameter (a parameter holding the text `true` also counts as on). |
| Blocks to run | `Block_Names` | Text | Names of the blocks to start, separated by commas. Blocks they depend on run too when needed. |
| Refresh from source | `Refresh_From_Source` | Yes/no | Reload the data from the sources, rather than reuse data the blocks already hold. |

## Outputs

None. The block's message says what was started, with the server's job ID.

## Limits

- Fire and forget: the started run's success or failure is not reported here; see the project's workflow or the Admin app's Workflow Job Queue.
- Block names containing a comma cannot be listed.
- Tested only against a stand-in for the server (see `tests/`): the request is checked, not a real server's handling of it, nor how `cancelExisting` and `waitForIdle` behave when the project is the one running this block.

## Source

[script.py](script.py)

`sample-data/stock-levels.csv` is invented data for the blocks it starts; the block itself reads no data. `sample-data/placeholder.csv` is the Reorder list those blocks rebuild from it (In stock below Reorder level), shown in the demo in place of a run (a demo can't carry its own project's address); a test checks it.
