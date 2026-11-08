# SFTP Downloader

Downloads the files in a folder on an SFTP server to the Omniscope server and lists them, ready for an Append files block to load.

Suppliers, banks, payroll bureaux and older systems often deliver data as files dropped on an SFTP server each night. This block fetches the files from one folder and outputs one record per file with its path on the Omniscope server; an **Append files** block then loads their contents.

- Signs in with a **password**, a **private key file**, or both (a key with a passphrase).
- Takes every file in the folder, or only those matching **extensions or patterns** such as `csv, xlsx` or `sales_*.csv` (not case-sensitive). Sub-folders are skipped.
- Checks the server's identity against a **host key** fingerprint when you give one, and stops if the server offers a different key. Without one, any key is accepted and the final message shows the key it saw, ready to paste into the option.
- Outputs the local **File path**, the **File name**, the **Size** and the **Modified** time on the server.

## Language and libraries

Python, with paramiko (LGPL 2.1) for SSH and SFTP, and pandas (BSD 3-Clause). pandas is part of Omniscope's Python environment; Omniscope installs paramiko with pip on first run if it is missing (the manifest's `dependencies`).

## Inputs

None. The block reads from the SFTP server.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| User name | `username` | Text | The account to sign in with. |
| Password | `password` | Password | The account's password, or the private key's passphrase. Can be empty with a key that has none. |
| Private key file | `privateKeyFile` | File | Optional: a private key file (OpenSSH format) on the Omniscope server. |
| Host name | `hostname` | Text | The SFTP server, such as `sftp.example.com`. |
| Port | `port` | Integer | Usually 22. |
| Host key | `hostKey` | Text | The server's key fingerprint (`SHA256:...`) or its known_hosts line. Empty: any key is accepted. |
| Folder on the SFTP server | `folder` | Text | The folder whose files to download, such as `/outgoing/daily`. |
| Files to download | `extension` | Text | Extensions or patterns, comma-separated: `csv`, `.csv`, `sales_*.csv`. Empty: every file. |
| Download to folder | `localFolder` | Text | A folder on the Omniscope server for the files (created if missing). Empty: the block's own working folder. |

To find the fingerprint, ask the server's administrator, or run `ssh-keyscan sftp.example.com | ssh-keygen -lf -` on a machine you trust and take the `SHA256:` part for the key type the server uses.

## Outputs

- **Files** (`Output Data`): File path (on the Omniscope server), File name, Size (bytes), Modified (the time on the SFTP server, UTC). Sorted by file name.

## Loading the files

Connect the output to an **Append files** block and set it to take the file names from the upstream block, using the **File path** field. All the files should have the same layout.

## Limits

- One folder; sub-folders are not entered.
- Every matching file is downloaded on every run; files of the same name in the download folder are replaced. Use a Filter on Modified downstream to keep only recent ones.
- Without a Host key the connection is encrypted but the server's identity is not checked.

## Source

[script.py](script.py)

The tests in `tests/` use a stand-in for the SFTP connection (no server is contacted) that serves the invented files in `tests/canned/server/`. `sample-data/placeholder.csv` is the block's output for them, for trying a workflow without an SFTP server.
