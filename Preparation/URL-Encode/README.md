# URL Encode

Percent-encodes the text in a field (UTF-8) into a new field, so it can go into a link, a query string or a web request.

Search terms, product names, place names and free text often hold characters that break a link: spaces, `&` and `=` (which split a query string), `#` (which starts a fragment), `+` (which some servers read as a space), `%`, and letters outside English such as é or ø. This block replaces each of them with its `%` code, for example `fish & chips` becomes `fish%20%26%20chips` and `café` becomes `caf%C3%A9`. Put the result after `?q=` in a link, or into the URL of a web request.

- **Letters, digits and `_ . - ~` are kept**; every other character is encoded as the `%` codes of its UTF-8 bytes.
- **Slashes are kept** unless **Encode slashes** is ticked, so a whole path such as `reports/2025/q1` stays readable. Tick it when the text goes into one part of a path, where a `/` would start a new part.
- **Spaces as +** gives the form style used by HTML forms (`tea+for+two`); `+` in the text is then encoded as `%2B`.
- **One new field** (`Quoted text` by default) after the input fields. Give it the name of the field being encoded to replace that field instead. A name already used by another input field stops the block with a message.
- **Missing values stay missing.** Values that are not text are encoded as their text.

## Language and libraries

Python. It uses pandas (BSD 3-Clause licence), part of Omniscope's Python environment, and `urllib.parse` from the Python standard library. It needs nothing else installed.

## Inputs
- **Input 1**: records with a text field to encode.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Text to encode | `fieldName` | Field (text) | The text field to encode. From input 1. |
| Encoded field name | `outputField` | Text | Name of the new field holding the encoded text. Use the name of the field being encoded to replace it. Default `Quoted text`. |
| Encode slashes | `encodeSlashes` | Yes/no | Encode `/` as `%2F` too. Default: unticked (`/` is kept). |
| Spaces as + | `spacesAsPlus` | Yes/no | Encode spaces as `+` instead of `%20`. Default: unticked. |

## Outputs
- **Encoded** (`Output Data`): the input records with the encoded text in a new field.

## Limits
- **Encode the values, not a whole link.** Encoding `https://example.com/?q=tea` turns `:`, `?` and `=` into codes too, which is not a working link. Encode the search term or parameter value, then join it to the rest of the link with a formula.
- Text that is already encoded is encoded again (`%20` becomes `%2520`).
- There is no decoding: the block only encodes.

## Size of input

The records are processed in chunks as they stream through. In tests, 200,000 records took about half a second.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
