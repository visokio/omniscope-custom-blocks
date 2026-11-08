"""Trello connector: loads boards, lists, cards, checklists and checklist items, and searches cards, through
Trello's REST API (version 1)."""
import json

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

API = "https://api.trello.com/1"
TIMEOUT = 60
SEARCH_LIMIT = 1000  # the most cards Trello's search returns

# Fields asked of Trello for each kind of object, which are also the output fields (in this order)
BOARD_FIELDS = ["id", "name", "desc", "closed", "url", "shortUrl", "dateLastActivity", "idOrganization"]
LIST_FIELDS = ["id", "name", "closed", "pos", "idBoard"]
CARD_FIELDS = ["id", "name", "desc", "closed", "idList", "idBoard", "due", "dueComplete", "start",
               "dateLastActivity", "labels", "idMembers", "url", "shortUrl", "pos"]
CARD_COLUMNS = CARD_FIELDS[:5] + ["listName"] + CARD_FIELDS[5:] + ["checkItems", "checkItemsChecked", "comments"]
CHECKLIST_FIELDS = ["id", "name", "idCard", "idBoard", "pos"]
CHECKLIST_COLUMNS = CHECKLIST_FIELDS + ["checkItems", "checkItemsComplete"]
CHECKITEM_FIELDS = ["id", "name", "state", "idChecklist", "pos", "due", "idMember"]
DATE_FIELDS = ["dateLastActivity", "due", "start"]


def option_text(name):
    value = omniscope_api.get_option(name)
    return "" if value is None else str(value).strip()


class TrelloAPI:
    def __init__(self, api_key, api_token):
        self.session = requests.Session()
        # The key and token go in a header rather than the address, so they never appear in an error message
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f'OAuth oauth_consumer_key="{api_key}", oauth_token="{api_token}"',
        })

    def get(self, path, params=None):
        response = self.session.get(API + path, params=params, timeout=TIMEOUT)
        if response.status_code in (401, 403):
            omniscope_api.abort(f"Trello refused the request ({response.status_code}): check the API key and token, "
                                "and that the token's account can see the board.")
        if response.status_code == 404 or (response.status_code == 400 and "invalid id" in response.text.lower()):
            omniscope_api.abort(f"Trello found nothing at {path.split('?')[0]}: check the id.")
        if not response.ok:
            omniscope_api.abort(f"Trello returned {response.status_code} for {path}: {response.text.strip()[:300]}")
        return response.json()

    def boards(self, workspace_id):
        return self.get(f"/organizations/{workspace_id}/boards", {"fields": ",".join(BOARD_FIELDS)})

    def lists(self, board_id):
        return self.get(f"/boards/{board_id}/lists", {"fields": ",".join(LIST_FIELDS)})

    def cards_of_list(self, list_id):
        return self.get(f"/lists/{list_id}/cards", {"fields": ",".join(CARD_FIELDS + ["badges"])})

    def cards_of_board(self, board_id):
        return self.get(f"/boards/{board_id}/cards", {"fields": ",".join(CARD_FIELDS + ["badges"])})

    def checklists(self, card_id):
        return self.get(f"/cards/{card_id}/checklists", {"fields": ",".join(CHECKLIST_FIELDS)})

    def checkitems(self, checklist_id):
        return self.get(f"/checklists/{checklist_id}/checkItems")

    def search_cards(self, query):
        result = self.get("/search", {"query": query, "modelTypes": "cards", "cards_limit": SEARCH_LIMIT,
                                       "card_fields": ",".join(CARD_FIELDS + ["badges"])})
        return result.get("cards") or []


def cell(value):
    """One Trello value as an Omniscope value: labels by name, other lists joined, objects as JSON text."""
    if isinstance(value, list):
        return ", ".join(str(v.get("name") or v.get("color") or v.get("id")) if isinstance(v, dict) else str(v)
                         for v in value) or None
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return value


def frame(records, columns):
    rows = [{c: cell(r.get(c)) for c in columns} for r in records]
    df = pd.DataFrame(rows, columns=columns)
    for c in DATE_FIELDS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce", format="ISO8601")
    for c in df.columns:
        if df[c].isna().all() and not pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].astype(object)
    return df


def card_frame(cards, list_names):
    rows = []
    for card in cards:
        badges = card.get("badges") or {}
        rows.append(dict(card, listName=list_names.get(card.get("idList")), checkItems=badges.get("checkItems"),
                         checkItemsChecked=badges.get("checkItemsChecked"), comments=badges.get("comments")))
    return frame(rows, CARD_COLUMNS)


def checklist_frame(checklists):
    rows = []
    for cl in checklists:
        items = cl.get("checkItems") or []
        done = sum(i.get("state") == "complete" for i in items)
        rows.append(dict(cl, checkItems=len(items), checkItemsComplete=done))
    return frame(rows, CHECKLIST_COLUMNS)


api_key = option_text("apiKey")
api_token = option_text("apiToken")
workspace_id = option_text("workspaceID")
board_id = option_text("boardID")
list_id = option_text("listID")
card_id = option_text("cardID")
checklist_id = option_text("checklistID")
search = option_text("searchString")

if not api_key or not api_token:
    omniscope_api.abort("Enter the Trello API key and token.")
if not any([workspace_id, board_id, list_id, card_id, checklist_id, search]):
    omniscope_api.abort("Enter at least one of: workspace, board, list, card or checklist id, or a search.")

trello = TrelloAPI(api_key, api_token)
loaded = []

if workspace_id:
    boards = frame(trello.boards(workspace_id), BOARD_FIELDS)
    omniscope_api.write_output_records(boards, output_number=0)
    loaded.append(f"{len(boards)} boards")

list_names = {}
if board_id:
    lists = trello.lists(board_id)
    list_names = {lst.get("id"): lst.get("name") for lst in lists}
    omniscope_api.write_output_records(frame(lists, LIST_FIELDS), output_number=1)
    loaded.append(f"{len(lists)} lists")

if list_id or board_id:
    # The cards of the chosen list or, without one, of the whole board
    cards = trello.cards_of_list(list_id) if list_id else trello.cards_of_board(board_id)
    omniscope_api.write_output_records(card_frame(cards, list_names), output_number=2)
    loaded.append(f"{len(cards)} cards")

if card_id:
    checklists = trello.checklists(card_id)
    omniscope_api.write_output_records(checklist_frame(checklists), output_number=3)
    loaded.append(f"{len(checklists)} checklists")

if checklist_id:
    items = frame(trello.checkitems(checklist_id), CHECKITEM_FIELDS)
    omniscope_api.write_output_records(items, output_number=4)
    loaded.append(f"{len(items)} checklist items")

if search:
    found = trello.search_cards(search)
    omniscope_api.write_output_records(card_frame(found, list_names), output_number=5)
    loaded.append(f"{len(found)} cards found" + (" (Trello's search limit)" if len(found) >= SEARCH_LIMIT else ""))

omniscope_api.close("Loaded " + ", ".join(loaded) + ".")
