# Canonical Schema Mapper

Maps the many names a field goes by (aliases) to one canonical name, combines fields that hold the same thing, and converts each to a set type with an optional default, following rules kept as data (typed into the block or in a CSV file), working through the data in chunks so large inputs never have to fit in memory.

Exports from different systems, or from one system over time, call the same thing by different names: `OrderID`, `Order No`, `order id`. This block reads rules that list, for each field you want (the canonical field), the names it may arrive under, its type and a default, and applies them to every record. For a mapping you set up once and rarely change, the core **Define schema** block is simpler (see [How it relates to other blocks](#how-it-relates-to-other-blocks)); this block is for when the rules themselves are data.

- **Matching names.** An input field becomes a canonical field when its name matches the canonical name or one of its aliases. With **Match names loosely** (the default), case is ignored and spaces, hyphens and underscores are treated alike, so `Order Date`, `order_date` and `ORDER-DATE` match.
- **Combining fields.** When several input fields match one canonical field (a file with both `Qty` and `Quantity`), each record takes the first value present: a field named like the canonical field first, then the aliases in the order the rule lists them.
- **Types.** Each value is converted to the rule's type. Values that can't be converted (`two` in a number field) become empty, and the block's message says how many there were per field.
- **Defaults.** Empty and unreadable values get the rule's default, if it has one. A rule without a default leaves them empty.
- **Field order.** By default each canonical field takes the place of the first input field it came from, and canonical fields that match no input field are left out. Tick **Output every canonical field** for a fixed schema: every canonical field, in the rules' order (missing ones filled with their default or left empty), then any unmapped fields.

The rules come from the **Schema rules** option when it is filled in: the rules CSV typed (or pasted) into the block, one rule per line or rules separated by semicolons, with or without a heading row. With it empty, the block reads them from the **Schema rules file** option, a CSV file on the server. The columns are the same either way. The block streams (Omniscope passes the data through in chunks), and a streaming block has exactly one input, so the rules are an option rather than a second input.

## The rules

One CSV row per canonical field, with these columns (capitals and spaces around the headings are ignored). Typed into the block without a heading row, the columns are taken in this order, and trailing empty cells can be left out (`quantity, Qty|Units, integer`).

| Column | Needed | What it holds |
|---|---|---|
| `canonical` | Yes | The field name to output. |
| `aliases` | Yes (may be empty) | Other names for the field, separated by a vertical bar (`\|`), or by commas in a quoted cell (`"Area, Zone"`). |
| `type` | No | `string` (the default; `text` also works), `number` (`decimal`), `integer`, `date`, `datetime` or `boolean`. |
| `default` | No | The value for empty and unreadable values, in the field's type. Write dates as `2025-01-31`. |
| `format` | No | For dates written as text: the format, such as `%d/%m/%Y` for 31/01/2025 ([Python date codes](https://docs.python.org/3/library/datetime.html#format-codes)). ISO dates (2025-01-31) are read as well. |

```csv
canonical,aliases,type,default,format
order_id,OrderID|Order No,string,,
order_date,Order Date|OrderDate|Date Ordered,date,,%d/%m/%Y
quantity,Qty|Quantity|Units,integer,,
paid,Paid|Is Paid,boolean,false,
currency,Currency,string,GBP,
```

How values are converted:

- **number** and **integer**: numbers, and text that is a plain number (`12`, `4.50`). Text with currency signs or thousands separators (`£3`, `1,200`) can't be read. **integer** also rejects fractions (`2.5`).
- **date** and **datetime**: Date fields keep their value; text is read with the rule's format, or else as an ISO date or month first (`03/04/2025` is 4 March). **date** drops the time of day. Both come out as dates in UTC.
- **boolean**: `true`, `t`, `yes`, `y`, `1` are true and `false`, `f`, `no`, `n`, `0` are false, in any case; anything else is unreadable.
- **string**: values are kept as text. With **Treat blank text as missing** (the default), text that is empty or only spaces counts as missing.

Typed into the block, the sample rules read:

```
order_id, OrderID|Order No; order_date, Order Date|OrderDate|Date Ordered, date, , %d/%m/%Y; quantity, Qty|Quantity|Units, integer; paid, Paid|Is Paid, boolean, false; currency, Currency, string, GBP
```

A cell containing a comma or a semicolon goes in double quotes (`"Area, Zone"`).

The block stops with a message if there are no rules (Schema rules empty and no file) or the file is missing, if the rules have no `canonical` or `aliases` column, a typed rule has more than five cells, the rules list a canonical field twice, name an unknown type, or have a default that is not valid for its type.

## Language
Python

## Inputs
- **Input 1**: records whose fields may arrive under different names.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Rules | Schema rules | `rulesText` | Text | The rules CSV written in the block, one rule per line or rules separated by semicolons: canonical, aliases, type, default, format (heading row optional). Takes precedence over the file. |
| Rules | Schema rules file | `rules` | File | CSV file with the columns canonical, aliases and, optionally, type, default and format. Used when Schema rules is empty. |
| Options | Keep unmapped fields | `passthrough_unmapped` | Yes/no | Pass input fields that match no rule through unchanged. Untick to output the canonical fields only. Default: yes. |
| Options | Treat blank text as missing | `prefer_non_empty_strings` | Yes/no | When combining aliases, skip text that is empty or only spaces and take the next alias's value; blank text also gets the default. Default: yes. |
| Options | Match names loosely | `auto_normalise_aliases` | Yes/no | Ignore case, and treat spaces, hyphens and underscores alike, when matching field names to aliases. Untick to match names exactly. Default: yes. |
| Options | Output every canonical field | `add_missing_canonical` | Yes/no | Output all canonical fields in the rules' order, even those no input field matches, followed by the unmapped fields. Default: no. |

## Outputs
- **Canonical** (`Output Data`): the input with its fields renamed, combined and converted as the rules say.

## Size of input

The block streams: Omniscope passes the records through in chunks (10,000 at a time) and each chunk is mapped with the same rules, so the input never has to fit in Python's memory. Every canonical field has the same type in every chunk, and the count of unreadable values in the block's message covers all chunks. On an Omniscope server, 300,000 records with six fields (two of them combined into one) took about 40 seconds.

## How it relates to other blocks

- **For fixed renames and types, use the core Define schema block.** It maps input fields and their aliases to schema fields with set types (Integer, Decimal, Text, Date, with a date pattern), can merge several matching fields taking the first non-empty value, can match similar names, and says what to do with missing and unexpected fields. Set up once in the block's settings, it needs no Python.
- **Format field names** (core) changes how names are written (Title Case, snake case) without mapping one name to another; **Bulk field organiser** (core) renames or retypes many fields by pattern (find and replace in names, prefix, suffix).
- **This block's value is data-driven rules**, an advanced capability: the aliases, types, defaults and date formats are kept as a table (a CSV file on the server, or the rules text), so the list can be shared between workflows and projects and changed without editing each workflow. It also covers what Define schema doesn't: a default per field, yes/no fields, and a count of values that couldn't be converted.
- Among community blocks, **Smart Schema Normaliser** tidies names and types with no rules at all; **Field Renamer** and **Streaming Field Renamer** rename one name to one name, without combining fields or converting types.

## Dependencies
None beyond pandas, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

The sample data in `sample-data/` (two order exports and a rules file) is invented for the demo.
