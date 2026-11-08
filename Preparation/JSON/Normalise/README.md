# JSON Normalise

Turns JSON text into a flat table: each object becomes a record and each array item a record of its own, nested objects become fields such as customer.name, and the input fields are repeated on every record.

Orders exported with their lines as a JSON array, API responses saved as text, and documents from document databases all hold several levels of data in one field. This block flattens them: one record per object or array item, one field per key, with the input record's fields repeated so each line still carries its order number, customer and date.

- **Objects and arrays**: a JSON object gives one record; an array of objects gives one record per item. An array item that is not an object (`"red"`), or JSON that is a single value, goes in a field ending `_value`.
- **Field names**: the JSON field's name, an underscore and the key (`Lines_sku`). Keys of nested objects are joined with a dot (`Lines_options.colour`). Fields appear in the order their keys are first met.
- **Arrays inside an item** (`"tags": ["bulk", "pallet"]`) are written as JSON text; run the block again on that field to turn them into records too.
- **Types**: a key whose values are all whole numbers becomes an Integer field, all numbers a Decimal field, all `true`/`false` a yes/no field; anything else, or a mix, becomes text. JSON `null` is an empty value.
- **Records without JSON**: with **Keep the input fields** ticked, a record whose JSON field is empty, an empty array or invalid JSON is kept once, with the JSON fields empty; the block's message says how many records had invalid JSON. Unticked, such records give nothing.

## Language and libraries

Python. It uses pandas and numpy (both BSD 3-Clause licence), part of Omniscope's Python environment, and Python's own `json` module. Nothing else to install.

## Inputs
- **Input 1**: records with a text field holding a JSON object or an array of objects.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| JSON field | `jsonField` | Field (text) | The text field holding JSON: an object, or an array of objects, in each record. From input 1. |
| Keep the input fields | `includeInput` | Yes/no | Repeat the input fields on every record made from them, before the JSON fields. Unticked, only the JSON fields. Default: ticked. |

## Outputs
- **Flattened** (`Output Data`): one record per JSON object or array item (plus one per input record without JSON, when the input fields are kept).

## Limits
- Only the top-level array is turned into records; arrays inside an item stay as JSON text.
- A new field whose name (the JSON field's name, an underscore and the key) matches an input field name stops the block with a message.
- With **Keep the input fields** unticked and no JSON in the data, there are no fields to output and the block stops with a message.
- Yes/no fields may show as text `True`/`False` in Omniscope.

## Size of input

In tests, 20,000 orders with one to five lines each (about 60,000 records out) took about a quarter of a second.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
