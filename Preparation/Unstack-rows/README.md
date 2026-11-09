# Unstack Records

Splits text fields that hold several values in one cell, such as one item per line, into one record per value, repeating the other fields.

Exports from forms, CRM and order systems often put several values in one cell: the products on an order, one per line, with their quantities in the next cell, also one per line. This block turns each such record into one record per value, so the values can be counted, joined and charted.

- Choose one or more **text fields to unstack** and the **separator** between their values.
- Values in the chosen fields are **paired by position**: the first product with the first quantity, the second with the second, and so on.
- A record becomes as many records as its **longest list**. Shorter lists are filled with **empty values**.
- The **other fields are repeated** on each new record and keep their types.
- A record with nothing to split (a single value, or empty chosen fields) stays as one record.

The unstacked values are text; convert them afterwards if they are numbers (Field Organiser).

## Language and libraries

Python. It uses pandas and numpy (both BSD 3-Clause), part of Omniscope's Python environment. Nothing else to install.

## Inputs
- **Input 1**: records with one or more text fields holding several values each.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Fields to unstack | `textFields` | Fields (text) | Text fields holding several values each. Values in the chosen fields are paired by position. From input 1. |
| Separator | `separator` | Text | The text between values. `\n` is a line break (the default), `\t` a tab, `\r` a carriage return; anything else is matched exactly as typed, so `, ` (comma and space) and `,` differ. |

## Outputs
- **Unstacked** (`Output`): one record per value in the chosen fields, with the other fields repeated.

## Size of input

In tests, 200,000 records unstacked into about 600,000 in under a second.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
