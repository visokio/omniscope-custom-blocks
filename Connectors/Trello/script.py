from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

import requests
import pandas as pd
import json

class TrelloAPI:
    def __init__(self, api_key, api_token):
        self.api_key = api_key
        self.api_token = api_token

    def get_boards(self, workspace_id):
        response = requests.get(f"https://api.trello.com/1/organizations/{workspace_id}/boards?key={self.api_key}&token={self.api_token}")
        response.raise_for_status()
        boards = response.json()
        return pd.DataFrame(boards)

    def get_lists(self, board_id):
        response = requests.get(f"https://api.trello.com/1/boards/{board_id}/lists?key={self.api_key}&token={self.api_token}")
        response.raise_for_status()
        lists = response.json()
        return pd.DataFrame(lists)

    def get_cards(self, list_id):
        response = requests.get(f"https://api.trello.com/1/lists/{list_id}/cards?key={self.api_key}&token={self.api_token}")
        response.raise_for_status()
        cards = response.json()
        return pd.DataFrame(cards)
        
    def get_checklists(self, card_id):
        response = requests.get(f"https://api.trello.com/1/cards/{card_id}/checklists?key={self.api_key}&token={self.api_token}")
        response.raise_for_status()
        checklists = response.json()
        return pd.DataFrame(checklists)

    def get_checkitems(self, checklist_id):
        response = requests.get(f"https://api.trello.com/1/checklists/{checklist_id}/checkitems?key={self.api_key}&token={self.api_token}")
        response.raise_for_status()
        checkitems = response.json()
        return pd.DataFrame(checkitems)
        
    def search_trello(self, query):
        url = f"https://api.trello.com/1/search?query={query}&key={self.api_key}&token={self.api_token}"
        response = requests.get(url)
        response.raise_for_status()
        return pd.json_normalize(response.json()['cards'])

apiKey = omniscope_api.get_option("apiKey")
apiToken = omniscope_api.get_option("apiToken")
workspaceID = omniscope_api.get_option("workspaceID")
boardID = omniscope_api.get_option("boardID")
listID = omniscope_api.get_option("listID")
cardID = omniscope_api.get_option("cardID")
checklistID = omniscope_api.get_option("checklistID")
searchString = omniscope_api.get_option("searchString")

trello = TrelloAPI(apiKey, apiToken)

   
if (workspaceID is not None):
    # Get all boards in a specific workspace
    boards_df = trello.get_boards(workspaceID)
    if boards_df is not None:
        omniscope_api.write_output_records(boards_df, output_number=0)

if (boardID is not None):
    # Get all lists in a specific board
    lists_df = trello.get_lists(boardID) 
    if (lists_df is not None):
         omniscope_api.write_output_records(lists_df, output_number=1)

if (listID is not None):
    # Get all cards in a specific list
    cards_df = trello.get_cards(listID)
    if (cards_df is not None):
         omniscope_api.write_output_records(cards_df, output_number=2)
         
if (cardID is not None):
    # Get all cards in a specific list
    checklists_df = trello.get_checklists(cardID)
    if (checklists_df is not None):
         omniscope_api.write_output_records(checklists_df, output_number=3)

if (checklistID is not None):
    # Get all cards in a specific list
    checkitems_df = trello.get_checkitems(checklistID)
    if (checkitems_df is not None):
         omniscope_api.write_output_records(checkitems_df, output_number=4)
         
if (searchString is not None):
    # Search in Trello
    results_df = trello.search_trello(searchString)
    #print(results_df)
    if (results_df is not None):
         omniscope_api.write_output_records(results_df, output_number=5)
    



omniscope_api.close()