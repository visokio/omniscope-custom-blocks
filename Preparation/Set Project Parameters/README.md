# Set Project Parameters

Sets project parameters, often of the project the block is in, from records holding a parameter name and a value. All the values are set in one request, so either all of them change or none does.

Project parameters drive filters, file paths, titles and thresholds across a workflow. This block lets the workflow itself set them: from a settings file, a lookup, a calculation or a user's choice in an Editable Table, one record per parameter.

- Each record names a **parameter** and its new **value**, in two fields you choose.
- All the values go to the project in **one request**: if one parameter does not exist, or a value doesn't fit its type, the server refuses the whole update and the block stops with the server's message.
- When a name appears twice, the **later record's value** is set.
- A record with no parameter name stops the block before anything is sent.
- The **Set** output holds the records whose values were set, so blocks after this one run once the parameters are in place.

Blocks that read a parameter use its new value the next time they run. It uses the project's Workflow REST API: `w/updateparams`, asking the server not to wait for the project to be idle (`waitForIdle` false), since the project may be the one running this block.

## When to use it

- This block: several parameters of **one** project, from name/value records.
- **Project Parameters Batch Setting**: the same parameters in **many** projects, one record per project.
- The core **For Each** block: parameters changed only for the duration of its loop, in its own project, with no server settings needed.

## Before you start

- The project needs the parameters already: the API changes values, it cannot create, rename or retype a parameter.
- **Permission.** The user making the request needs the *Project parameters access via APIs* permission (off by default).
- **The address.** For this project, give its own address; on the same server, the internal address such as `http://127.0.0.1:24679/Folder/Project.iox/` avoids the public address and its certificate. A report or workflow address of the project is cut back to the project. If the server asks for sign-in (a list of users), give a username and password: they are sent with basic authentication, which is readable by anyone on the network path unless the address starts with `https://` (the internal `127.0.0.1` address never leaves the machine).

## Language and libraries

Python. It uses urllib3 (MIT licence) for the HTTP request and pandas (BSD 3-Clause) for the records. pandas is part of Omniscope's Python environment; urllib3 is listed in the block's dependencies, so Omniscope installs it with pip on first run if it is missing.

## Inputs

- **Input 1**: one record per parameter, with the parameter's name in one field and its new value in another. Other fields are passed on.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Project address | `Iox_File_Url` | Text | The address of the project whose parameters to set, ending in `.iox`. |
| Username | `username` | Text | Optional. For a server that asks for sign-in with a list of users. |
| Password | `password` | Password | Optional. The password for the username. |
| Name field | `Params_Name` | Field | The field holding the names of the parameters to set. |
| Value field | `Params_Value` | Field | The field holding the values to give them. |

## Outputs

- **Set** (`set`): the records whose values were set, one per parameter (for a name given twice, the later record), with all their fields.

## Values sent

The value field's values are sent as they are: text as text, numbers as numbers (whole numbers as whole numbers), yes/no values as true/false, dates as ISO 8601 text such as `2025-03-01T00:00:00+00:00`, and missing values as null. A value field holding several kinds of parameter (text and numbers) is a text field in Omniscope, so numbers arrive as text such as `"150"`; whether the server accepts text for a Number parameter has not been tested.

## Limits

- One project per block.
- Tested only against a stand-in for the server (see `tests/`): the request is checked, not a real server's handling of it.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented. `sample-data/placeholder.csv` is the block's Set output for `parameter-values.csv`, shown in the demo in place of the block (a demo can't carry its own project's address); a test checks they match.
