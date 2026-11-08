# Trello

Loads Trello boards, lists, cards, checklists and checklist items, and searches cards, with labels, members and due dates as fields.

Trello boards hold a team's work in progress: content plans, recruitment pipelines, small projects. To count cards per list, see what is overdue or combine several boards, the cards need to be records. This block reads them from Trello's REST API each time the workflow runs.

Each output is loaded only when its option is set:

| Set this | To get |
|---|---|
| Workspace id | **Boards**: the workspace's boards |
| Board id | **Lists**: the board's lists; and **Cards**: every open card on the board, with the name of its list |
| List id | **Cards**: only that list's open cards |
| Card id | **Checklists**: the card's checklists, with how many items each has and how many are complete |
| Checklist id | **Items**: the checklist's items and their state |
| Search cards | **Search results**: up to 1,000 cards matching the search |

- Labels come out **by name** (by colour when a label has no name), member ids and other lists **joined with commas**.
- **Due**, **start** and **last activity** are dates (UTC).
- Cards carry their checklist progress (items, items checked) and comment count.

## Language and libraries

Python. It uses requests (Apache License 2.0) for the HTTP calls and pandas (BSD 3-Clause) for the output. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

None. The block is a source: it reads from Trello.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| API Key | `apiKey` | Password | The API key of a Trello Power-Up: create one at https://trello.com/power-ups/admin, then open its API key page. |
| API Token | `apiToken` | Password | A token generated from the API key's page. The block sees what this token's account can see. |
| Workspace id (boards) | `workspaceID` | Text | The id or short name from the workspace address, https://trello.com/w/your-workspace. |
| Board id (lists and cards) | `boardID` | Text | The board's id, or the short code from its address (https://trello.com/b/AbCd1234). |
| List id (cards of one list) | `listID` | Text | Only this list's cards. A list's id is in the board's `.json` address. |
| Card id (checklists) | `cardID` | Text | The card's id, or the short code from its address. |
| Checklist id (items) | `checklistID` | Text | The checklist whose items to load. |
| Search cards | `searchString` | Text | Text to search for across the boards the token can see, in Trello's search syntax (such as `label:Blog` or `due:week`). |

Empty options are ignored. At least one id or a search is needed.

## Outputs

- **Boards** (`Boards`): id, name, desc, closed, url, shortUrl, dateLastActivity, idOrganization.
- **Lists** (`Lists`): id, name, closed, pos, idBoard.
- **Cards** (`Cards`): id, name, desc, closed, idList, listName, idBoard, due, dueComplete, start, dateLastActivity, labels, idMembers, url, shortUrl, pos, checkItems, checkItemsChecked, comments. `listName` is filled when the board id is set.
- **Checklists** (`Checklists`): id, name, idCard, idBoard, pos, checkItems, checkItemsComplete.
- **Items** (`Items`): id, name, state, idChecklist, pos, due, idMember.
- **Search results** (`Search results`): the same fields as Cards.

## Limits

- Archived cards and lists are not loaded (Trello's default for these requests); archived boards are, with closed = true.
- Trello's search returns at most 1,000 cards; the final message says when that limit was reached.
- Member names are not looked up: cards carry member ids.
- The block only reads. A Trello token can also allow changes to boards and may never expire, depending on how it was made: keep it private, and revoke it from your Trello account settings when it is no longer needed.
- In tests, a board of 20,000 canned cards was turned into records in under a second; against Trello, the time is mostly Trello's response time (one request per output).

## Source

[script.py](script.py)

The tests in `tests/` run the script against invented Trello responses (`tests/canned/`, written by `tests/make_canned.py`); `sample-data/placeholder.csv` is the Cards output for the sample board, for trying a workflow without a Trello account.
