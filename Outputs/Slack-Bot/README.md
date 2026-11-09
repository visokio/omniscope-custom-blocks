# Slack Bot

Posts one message to a Slack channel for each input record, as your Slack app's bot, optionally with a file attached.

Alerts and summaries computed in a workflow are most useful where the team already talks. This block posts each record's message to a Slack channel: a stock alert per warehouse, a daily figure, a link to the Report.

- The **message field** holds each record's text. Web addresses in it become links; Slack markup already in the text (`<https://...|label>`, `<@U0123>` mentions, `<!here>`) is kept. `&`, `<` and `>` are escaped so they show as typed.
- A link ends at the first space: write spaces in an address as `%20`. A full stop or bracket just after an address stays outside the link.
- Links to a Report should use an address the channel's readers can open (the server's name, not `127.0.0.1` as in the invented sample), and they still need permission to view the Report.
- Records with an empty message (and no file) are skipped.
- **File to attach**: optional; every message is posted with that file, under the **attachment title**. The file must be on the machine running Omniscope; the block checks it exists before posting anything.
- If Slack refuses a message (wrong token, channel not found, app not in the channel, missing permission), the block stops and says which record, Slack's error code with a hint, and how many messages were posted before it.

## Language and libraries

Python. It uses requests (Apache License 2.0) for Slack's Web API and pandas (BSD 3-Clause). pandas is part of Omniscope's Python environment; Omniscope installs requests with pip on first run if it is missing (the manifest's `dependencies`).

## Setting up Slack

1. Create an app at [api.slack.com/apps](https://api.slack.com/apps) (From scratch), in your workspace.
2. Under **OAuth & Permissions**, add the bot token scope `chat:write`, and `files:write` to attach files.
3. Install the app in the workspace and copy the **Bot User OAuth Token** (`xoxb-...`).
4. In the channel, `/invite @your-app`. The **channel ID** is at the bottom of the channel's details (About tab), such as `C0123ABCD`.

## Inputs

- **Input 1**: one record per message.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Bot User OAuth token | `authToken` | Password | From the app's OAuth & Permissions page; starts with `xoxb-`. |
| Channel ID | `channelID` | Text | Such as `C0123ABCD`. The app must be in the channel. |
| Message field | `message` | Field | The field holding each record's message. |
| File to attach | `attachmentPath` | File | Optional. Attached to every message. |
| Attachment title | `attachmentName` | Text | The title Slack shows for the file. Default "My Report". |

## Outputs

- **Messages** (`Output Data`): one record per input record: `Row` (the record's number, from 0), `Message` (as sent, in Slack's format), `AttachmentPath`.
- **Sent** (`Output Data 2`): one record per input record: `Row`, `Action` (`postMessage`, `upload_with_comment` or `skip`), `Channel`, `Timestamp` (Slack's `ts` for the message, which identifies it in Slack's API), `File ID` (for an attachment).

## How the messages are sent

- Text only: `chat.postMessage` with the channel and text.
- With a file: Slack's external upload (`files.getUploadURLExternal`, then the file's bytes, then `files.completeUploadExternal` with the message as its comment), which posts the message and the file together.

## Limits

- Messages are sent one by one; Slack allows about one message per second per channel for a sustained run, so large inputs take a while, and Slack may refuse with `ratelimited`.
- Slack cuts a message longer than 40,000 characters.
- The tests use a stand-in for Slack's API (canned replies in `tests/canned/`) and check every request; nothing is sent to Slack.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented.
