# Slack API WebClient

Calls any Slack Web API method, such as conversations.list or chat.postMessage, and turns the answer into records, following every page.

Slack's Web API has a method for nearly everything in a workspace: channels, members, messages, files, reactions, user groups. Each answers with JSON, and long lists come in pages. This block makes the call, follows the pages and writes the list in the answer as records, so channel sizes, membership or message activity can be reported on like any other data. It can also call methods that change something, such as posting a message.

- Enter the **method name** and its **arguments** as JSON; GET for reading methods, POST for methods that change something.
- **Records**: one record per item of the list in the answer (channels, members, messages...); nested objects become dotted field names (`topic.value`), lists left inside an item become JSON text.
- An answer with no list (such as `users.profile.get` or `chat.postMessage`) becomes **one record**.
- **Pages** are followed with Slack's cursor until the last one (up to 1,000 pages), unless you untick **Follow pages**.
- When Slack says the rate limit was hit, the block waits as long as Slack asks and tries again.
- A refused call (`ok: false`) stops the block with Slack's error, and the scope the token is missing when Slack names it.

## Language and libraries

Python. It uses requests (Apache License 2.0) for the HTTP calls and pandas (BSD 3-Clause) for the output. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

None. The block is a source (or, for methods such as chat.postMessage, a sender): it calls Slack.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Slack token | `authToken` | Password | The bot or user token (`xoxb-...` or `xoxp-...`) from your Slack app's OAuth & Permissions page, with the scopes the method needs. |
| API method | `methodName` | Text | The Web API method, such as `conversations.list` (the default), `users.list`, `conversations.history` or `chat.postMessage`. See https://api.slack.com/methods. |
| HTTP method | `methodType` | Choice | GET (arguments from Query Params, the default) or POST (arguments from JSON Payload). |
| JSON Payload (POST) | `jsonPayload` | Text | Arguments for a POST, as a JSON object: `{"channel": "C0123456789", "text": "Report is ready"}`. |
| Query Params (GET) | `params` | Text | Arguments for a GET, as a JSON object: `{"types": "public_channel,private_channel", "limit": 200}`. Empty means none. |
| Records from | `recordsFrom` | Text | The list in the answer to turn into records, such as `channels`, `members` or `messages`. Empty: the first list of objects in the answer. |
| Follow pages | `followPages` | Yes/no | Repeat the call with Slack's next cursor until the last page (ticked by default). |

## Outputs

- **Records** (`Output Data`): one record per item of the list, all pages combined; or one record for an answer without a list. A list of plain values (such as the member ids from `conversations.members`) gives one field, `value`.
- **Raw response** (`Output Data 2`): one record per page, with the page's JSON text in the field `Text Response`.

## Limits

- Slack sends times as Unix seconds (`created`) or message timestamps (`ts`); convert them with a Formula if you need dates.
- Some methods only accept arguments as a form, not JSON; for those use GET.
- POST calls run every time the workflow runs: a chat.postMessage block posts a message on every run.
- The block calls whatever method it is given, with everything the token's scopes allow, including methods that delete, archive or invite. Give the Slack app only the scopes the method needs, and keep a token with write scopes out of shared projects.
- In tests, 100 canned pages of 200 channels (20,000 records) were combined in under a second; against Slack, the time is set by Slack's rate limits, which differ by method.

## Source

[script.py](script.py)

The tests in `tests/` run the script against invented Slack answers (`tests/canned/`, written by `tests/make_canned.py`); `sample-data/placeholder.csv` is the Records output for the invented `conversations.list` answer, for trying a workflow without a Slack token.
