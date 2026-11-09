# JSON Expand fields

Turns a text field holding a JSON object into one new field per key, next to the input fields; nested objects and arrays become JSON text.

Web analytics events, API responses, form submissions and log lines often carry their details as a JSON object in one text field: `{"page": "/sale", "device": "tablet", "qty": 2}`. This block reads that object in every record and adds a field for each key, so the details can be filtered, grouped and charted like any other field.

- **One field per top-level key**, in the order the keys first appear across the records. A record without a key gets an empty value in that field.
- **Types**: a key whose values are all whole numbers becomes an Integer field, all numbers a Decimal field, all `true`/`false` a yes/no field; anything else, or a mix (`12` in one record, `"many"` in another), becomes text. JSON `null` is an empty value.
- **Nested values**: an object or array inside the JSON is written as JSON text (`{"method": "standard", "days": 3}`), ready for a second JSON Expand fields block or for **JSON Normalise**.
- **Records that can't be expanded are kept**: empty text, invalid JSON, or JSON that is not an object (an array or a single value) leave the new fields empty. The block's message says how many records had text that was not a JSON object.
- **Keep the input fields** (default) puts the new fields after the input fields; untick it to output only the new fields.

## Language and libraries

Python. It uses pandas (BSD 3-Clause licence), part of Omniscope's Python environment, and Python's own `json` module. Nothing else to install.

## Inputs
- **Input 1**: records with a text field holding a JSON object.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| JSON field | `jsonField` | Field (text) | The text field holding a JSON object in each record. From input 1. |
| Keep the input fields | `includeInput` | Yes/no | Output the input fields followed by the new ones. Unticked, only the new fields. Default: ticked. |
| Prefix for new fields | `fieldPrefix` | Text | Optional. Added to the start of each new field name, such as `json_`. |

## Outputs
- **Expanded** (`Output Data`): one record per input record, with one new field per JSON key.

## Limits
- Only the top level is expanded; run the block again on a nested field to go one level deeper.
- When a key has the same name as an input field, the block stops with a message; set a prefix to keep them apart.
- With **Keep the input fields** unticked and no JSON object in the data, there are no fields to output and the block stops with a message.
- Yes/no fields may show as text `True`/`False` in Omniscope.

## Size of input

In tests, 100,000 records with four keys each (one of them an array) took about 0.3 seconds.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
