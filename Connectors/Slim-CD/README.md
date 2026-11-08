# Slim CD Transaction

Loads the transactions of a Slim CD payment gateway account (the SearchTransactions2 report), filtered by date range, customer, amount, card or transaction details, one record per transaction.

Slim CD is a payment gateway for card and cheque payments. Its reporting interface answers transaction searches with the same filters as the gateway's own search screen. This block sends one search and writes the result as records:

- **Credentials and scope**: username, password and Site ID are required; a Client ID narrows the search to one client.
- **Date range**: start and end dates keep the search small (recommended).
- **Filters**: name, city, state, ZIP code, e-mail, amount, client transaction reference, transaction type, card details, clerk name and gateway ID. Empty filters are not sent.
- **Result controls**: Max records limits the number of transactions; Reverse order asks for the newest first.
- **Record count only** returns one record with the number of transactions the search would return, to check the size of a search before loading it.

The transaction fields come out in a fixed order (gateid, transactiondate, transtype, processor, siteid, batchno, approved, cardtype, cardpresent, ... cashback), with any further fields Slim CD returns after them, so the fields are the same whether a search finds transactions or not. By default the transaction date is a date, amounts (amount, salestax, tip, giftbalance, cashback) are decimals, IDs and batch numbers whole numbers, and cardpresent true/false; ZIP codes stay text, so leading zeros and ZIP+4 forms survive. Tick **Treat all output fields as text** to keep every value as Slim CD sent it.

When Slim CD refuses the search (for example wrong credentials), the block stops with Slim CD's own response code and description.

**Security.** Slim CD's reporting service takes the username and password as parameters in the request address (sent over HTTPS), so they can appear in the logs of any proxy that records full addresses; the block keeps the address out of its own messages. Use a login with reporting access only, not an administrator's. The filters, Card number included, are plain text options saved in the project, and the output holds customers' names, addresses and e-mail addresses with the card numbers as Slim CD returns them (masked): treat the project and its data as payment data.

## Language and libraries

Python. It uses requests (Apache License 2.0) for the HTTP call and pandas (BSD 3-Clause) for the output. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

None. The block is a source: it reads from Slim CD.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Username | `username` | Text | The Slim CD username. |
| Password | `password` | Password | The Slim CD password (may be empty for API access credentials). |
| Site ID | `siteid` | Text | Your Slim CD Site ID. |
| Client ID | `clientid` | Text | Optional: one client ID. |
| Start date | `startdate` | Text | Optional: the first day to search (YYYY-MM-DD). |
| End date | `enddate` | Text | Optional: the last day to search (YYYY-MM-DD). |
| Treat all output fields as text | `treat_all_output_as_text` | Yes/no | Every field as text, exactly as sent. Default: unticked (typed). |
| Record count only | `recordcountonly` | Yes/no | One record with the count instead of the transactions. |
| Max records | `maxrecords` | Text | Optional: the most transactions to return (a whole number). |
| Reverse order | `reverseorder` | Yes/no | Newest transactions first. |
| First name, Last name, City, State, ZIP code, E-mail | `firstname`, `lastname`, `city`, `state`, `zip`, `email` | Text | Optional customer filters. |
| Amount | `amount` | Text | Optional: the transaction amount. |
| Client transaction reference | `clienttransref` | Text | Optional: your own reference sent with the transaction. |
| Transaction type | `transtype` | Text | Optional: the type as Slim CD names it. |
| Card number, Card ID, Card part | `cardnumber`, `cardid`, `cardpart` | Text | Optional card filters, passed to Slim CD unchanged. |
| Clerk name | `clerkname` | Text | Optional. |
| Gateway ID | `gateid` | Text | Optional: one transaction's gateway ID. |

## Outputs

- **Transactions** (`Transactions`): one record per transaction, with the fields listed above. With Record count only: one record with recordcount, siteid, clientid, startdate and enddate.

## Limits

- One search per run; Slim CD may cap the number of transactions a search returns: narrow the date range or set Max records.
- Transaction dates are written as Slim CD sends them, without a time zone; Omniscope shows them as they are.
- Start date and End date are passed to Slim CD unchanged: enter them as YYYY-MM-DD.
- Slim CD's developer documentation is now behind a sign-in; the request and reply shapes used here are those of the SearchTransactions2 JSON service.

## Source

[script.py](script.py)

The tests in `tests/` run the script against an invented SearchTransactions2 reply (`tests/canned/search-reply.json`, written by `tests/make_canned.py`): 36 transactions of a fictional shop, with masked, invented card numbers. `sample-data/placeholder.csv` is the block's output for that reply, for trying a workflow without a Slim CD account.
