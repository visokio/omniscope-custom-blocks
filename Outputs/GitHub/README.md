# GitHub

Reads a CSV or other delimited file from a GitHub repository into records, or writes the input records to a file in a repository as a new commit.

Small reference tables (price lists, region mappings, targets) and published datasets often live in GitHub repositories, where every change is versioned and reviewed. This block reads such a file straight into a workflow, or writes a workflow's result back as a commit, so the repository keeps a history of every published version.

- **Read**: the file's records come out of the block. A public repository needs no token. A file that isn't delimited text comes out as one record, in a field `content`, holding its text.
- **Write**: the input records are written as CSV to the file path, in **one commit** on the chosen branch, or the repository's **default branch** when none is given. The rest of the repository is untouched; an existing file is replaced, a new one is added (with any new folders).
- After writing, the output is **one record describing the commit**: repository, branch, file path, records written, bytes, commit id and its address on GitHub.
- Optionally the file is **zlib-compressed**, and the **separator** can be any character (tab included).

## Language and libraries

Python. It uses requests (Apache License 2.0) for GitHub's REST API and pandas (BSD 3-Clause) to read and write the CSV text. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

- **Input 1** (Write only): the records to write. Not used when reading.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Access token | `githubToken` | Password | A GitHub personal access token. Optional to read a public repository; needed to read a private one (Contents: read) and to write (Contents: read and write). |
| Mode | `mode` | Choice | Read a file from GitHub (`READ`, the default), or write the input to GitHub (`WRITE`). |
| zlib-compressed file | `compressed` | Yes/no | Tick if the file is, or should be written, compressed with zlib. |
| Separator | `separator` | Text | The character between fields: `,` (the default), `;`, `\|`; `\t` or `tab` for a tab. |
| Repository path | `repositoryPath` | Text | `owner/repository`, such as `octo-org/sales-data`; a pasted `https://github.com/...` address also works. |
| File path | `filePath` | Text | The file within the repository, such as `data/sales.csv`. |
| Branch | `branch` | Text | Optional. The branch to read from or commit to; empty uses the repository's default branch. |
| Commit message | `commitMessage` | Text | Optional, for writing. Empty gives "Update <file path> from Omniscope". |

To create a token: GitHub > Settings > Developer settings > Personal access tokens > Fine-grained tokens, choose the repository and give **Contents** read-only (to read) or read and write (to write).

## Outputs

- **Data** (`Output Data 2`): when reading, the file's records (field types as pandas reads them: whole numbers, decimals, text); when writing, one record: Repository, Branch, File path, Records written, Bytes, Commit, Commit URL.

## Limits

- Files up to 100 MB (GitHub's limit for the contents API and for files in a repository).
- Writing replaces the whole file; it does not merge with what is there. If someone else commits to the branch between the block's read of the branch and its update, GitHub refuses the update and the block stops with GitHub's message (nothing is overwritten).
- Dates are written as pandas writes them (`2025-01-31 00:00:00+00:00` for an Omniscope date); reading does not turn text into dates.
- Each run that writes makes a commit, even if the data has not changed.
- In tests, writing 200,000 records (three fields) took under a second before the network; against GitHub the time is the upload.

## Source

[script.py](script.py)

The tests in `tests/` run the script against a stand-in GitHub API that serves `tests/canned/monthly-sales.csv` (invented, written by `tests/make_canned.py`) and records the requests a write would send. `sample-data/placeholder.csv` is the same invented file: what the block outputs when it reads it.
