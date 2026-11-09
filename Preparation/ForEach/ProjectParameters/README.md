# Project Parameters Batch Setting

Sets project parameters in one or more Omniscope projects: each input record gives a project's address and the values for the parameters named like its fields.

When several projects are copies of one design (a report per branch, per client or per country), their settings drift unless something keeps them in step. This block takes a table of settings, one record per project, and writes each record's values into that project's parameters, so the table becomes the one place to change them.

- For each record, in order, the block sends the values of the chosen **parameter fields** to the project at the record's **address** (a field named *Region* sets the parameter *Region*).
- Each record's values are **set together or not at all**: the server refuses the whole update if one parameter is missing or a value doesn't fit its type, and the block stops with the server's message, naming the record.
- Every address is checked before anything is sent, so a bad address does not leave half the projects updated.
- When two records name the same project, they are applied in order, so the later record's values stay.
- The input records are **passed on unchanged**, so blocks after this one run once the parameters are set.

The projects are not run. It uses each project's Workflow REST API: `w/updateparams`.

## When to use it

- **Set Project Parameters** sets several parameters of one project from name/value records (one record per parameter).
- This block sets parameters in **many projects**, one record per project and one field per parameter.
- **For Each (Separate Workflows)** sets a project's parameters and then runs it, once per record.

## Before you start

- Each project needs the parameters already: the API changes values, it cannot create, rename or retype a parameter.
- **Permission.** The user making the requests needs the *Project parameters access via APIs* permission (off by default).
- **Addresses.** On the same server, use internal addresses, such as `http://127.0.0.1:24679/Folder/Project.iox/`. A report or workflow address of a project is cut back to the project. If the server asks for sign-in (a list of users), give a username and password: they are sent to every project with basic authentication, which anyone watching the connection can read, so use an `https://` address unless the server is this machine (`127.0.0.1`). Use an account with only the permissions the block needs.

## Language and libraries

Python. It uses urllib3 (MIT licence) for the HTTP requests and pandas (BSD 3-Clause) for the records. pandas is part of Omniscope's Python environment; urllib3 is listed in the block's dependencies, so Omniscope installs it with pip on first run if it is missing.

## Inputs

- **Input 1**: one record per project update, with the project's address in one field and one field per parameter.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Project address field | `Iox_File_Url` | Field | The field holding each record's project address, ending in `.iox`. |
| Parameter fields | `Parameters` | Fields | Fields named like the projects' parameters. The address field is never sent as a parameter. |
| Username | `username` | Text | Optional. For a server that asks for sign-in with a list of users. |
| Password | `password` | Password | Optional. The password for the username. |

## Outputs

- **Records** (`output`): the input records, unchanged, once every project's parameters have been set.

## Values sent

Text and numbers are sent as they are (whole numbers as whole numbers), yes/no values as true/false, dates as ISO 8601 text such as `2025-03-01T00:00:00+00:00`, and missing values as null. The server converts each value to its parameter's type, or refuses the update.

## Limits

- One request per record, one after another.
- If a later record fails, the projects of the earlier records keep their new values.
- Tested only against a stand-in for the server (see `tests/`): the requests are checked, not a real server's handling of them.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented; `sample-data/placeholder.csv` is the block's output for it (the input, passed on).
