# Running Balance

Running balances per account from opening balances and dated transactions, with lowest balance, days below zero or a limit, and average daily balance.

**Running balance per account** from an opening balance and dated transactions: bank and customer accounts, loyalty points, budgets, stock in units.

- Per transaction: the **balance after it**, and whether the account is **below zero** (or below a limit, such as an overdraft limit)
- Per account: opening and closing balance, total in and out, **lowest balance and when**, **days below zero** (or the limit) and the **average daily balance** (time-weighted, to the as-of date)
- **Opening balances** from an optional second input (account, balance); otherwise accounts start at zero
- Transactions on the same date keep their input order

## Language
Python

## Inputs
- **Input 1**: transactions (account, date, amount).
- **Input 2 (optional)**: opening balances (account, balance).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Transactions (input 1) | Account | `account_field` | Field | Identifies the account each transaction belongs to. From input 1. |
| Transactions (input 1) | Date | `date_field` | Field | Date of each transaction. From input 1. |
| Transactions (input 1) | Amount (in positive, out negative) | `amount_field` | Field | Money in as positive, money out as negative. From input 1. |
| Transactions (input 1) | Limit (optional) | `limit` | Decimal number | For example 500 for an overdraft limit of 500; 0 = none. Default: 0.0. |
| Transactions (input 1) | As of date | `as_of` | Text | Default: the latest transaction date. |
| Opening balances (input 2, optional) | Account | `opening_account_field` | Field | Account in the opening balances table, matched to input 1. From input 2. |
| Opening balances (input 2, optional) | Opening balance | `opening_balance_field` | Field | Balance before the first transaction. From input 2. |

## Outputs
- **Transactions** (`transactions`): The input with Balance After, Below Zero (and Below Limit).
- **Accounts** (`accounts`): Per account: opening, in, out, closing, lowest balance and date, days below zero / limit, average daily balance.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
