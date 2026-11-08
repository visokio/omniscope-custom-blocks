# Multipart Form Upload

Posts files to an HTTP endpoint as multipart/form-data, one request per file, and records each response's status and body.

Many web services take files the way an HTML form with a file field sends them: a document store, an invoicing or e-signature service, a partner's data intake. This block sends files from the Omniscope server to such an endpoint and keeps a record of what each upload returned.

- Connect records with a **field of file paths** to upload one file per record, or, with nothing connected, choose **a single file**.
- The file goes in the multipart field named by **Form field name** (`file` by default), with its file name and a content type guessed from the extension.
- **Extra form fields**, **Headers** and an **Authorization** value (kept as a password) are options; no need to edit the script.
- Each upload is recorded: the input fields, plus the HTTP status, the response body (first 8,000 characters) and an error message. A failed upload does not stop the others.

## Language and libraries

Python, with requests (Apache License 2.0) for the HTTP calls and pandas (BSD 3-Clause). pandas is part of Omniscope's Python environment; Omniscope installs requests with pip on first run if it is missing (the manifest's `dependencies`).

## Inputs

- **Input 1** (optional): one record per file, with a field holding the file's path on the Omniscope server. Without an input, the single file chosen in the options is uploaded.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Upload URL | `upload_url` | Text | The endpoint to POST each file to, starting with `http://` or `https://`. |
| File to upload (no input) | `file_path_column` | File | The file to upload when no input is connected. |
| File path field | `file_path_field` | Field (text) | With an input connected: the field holding each record's file path. |
| Form field name | `form_field_name` | Text | The multipart field that carries the file; `file` by default. |
| Extra form fields | `extra_fields` | Text | Optional fields sent with every file, one per line as `name=value`. |
| Headers | `headers` | Text | Optional HTTP headers, one per line as `Name: value`. |
| Authorization | `authorization` | Password | Optional value of the Authorization header, such as `Bearer` and a token. |

Headers can also be written into the `CUSTOM_HEADERS` dictionary at the top of the script; the options take precedence.

## Outputs

- **Results** (`Output Data`): the input records (or a File path field for the single file), plus HTTP status (empty when no response came back), Response (the body, truncated to 8,000 characters) and Error (empty when the upload succeeded; otherwise the status, "File not found: ...", or the connection error).

## Limits

- One POST per file, one at a time, with a 30-second timeout for the connection and for each wait for data.
- Each request carries one file. Endpoints that want several files in one request need the script changed.
- Status codes of 400 and above count as failures, with the response kept for checking.
- **Secrets**: only the Authorization option is kept as a password. Headers and Extra form fields are saved as plain text in the project, so a key put there (or in `CUSTOM_HEADERS`) can be read by anyone who can open or edit the project. Use an `https://` URL: over `http://` the files and the Authorization value travel unencrypted.
- The block can read and send any file the Omniscope server can read, so give edit access to projects using it only to people trusted with those files.

## Source

[script.py](script.py)

The tests in `tests/` check the requests the block would send (no request leaves the machine) and use the invented answers in `tests/canned/`. The invoice files in `sample-data/files/` and the list `sample-data/upload-list.csv` are invented; `sample-data/placeholder.csv` is the block's output for them, for trying a workflow without an endpoint.
