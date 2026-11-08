# Unescape HTML

Turns HTML character references such as `&amp;`, `&eacute;` and `&#163;` in a text field back into the characters they stand for, in a new field.

Text taken from web pages, RSS feeds, CMS and e-commerce exports or web APIs often arrives with its special characters written as HTML references: `Caf&eacute; mugs &amp; saucers` instead of `Café mugs & saucers`, `&pound;45` instead of `£45`. Those values don't match the same text elsewhere, sort oddly and look wrong in a report. This block converts them back.

- **Named references** (`&amp;`, `&lt;`, `&quot;`, `&eacute;`, `&ndash;`, `&rarr;` and the rest of the HTML5 list), **decimal** (`&#8211;`) and **hexadecimal** (`&#x2615;`) references are all converted.
- **Non-breaking spaces as plain spaces** (ticked by default): `&nbsp;` becomes an ordinary space. A non-breaking space looks like a space but is a different character, so `15 m` with one does not equal `15 m` with the other in a join or a filter.
- **Repeat for double-escaped text**: text escaped twice (`&amp;lt;`) becomes `&lt;` after one pass. Tick this to keep going until nothing changes, so it becomes `<`.
- **Text that is not a reference is left as it is**: `R&D`, `Q&A`, `AT&T`, `&bogus;`.
- **One new field** (`Unicode text` by default) after the input fields. Give it the name of the field being unescaped to replace that field instead. A name already used by another input field stops the block with a message.
- **Missing values stay missing.** Values that are not text are converted as their text.

## Language and libraries

Python. It uses pandas (BSD 3-Clause licence), part of Omniscope's Python environment, and `html.unescape` from the Python standard library. It needs nothing else installed.

## Inputs
- **Input 1**: records with a text field holding escaped text.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Text to unescape | `fieldName` | Field (text) | The text field holding the escaped text. From input 1. |
| Unescaped field name | `outputField` | Text | Name of the new field. Use the name of the field being unescaped to replace it. Default `Unicode text`. |
| Repeat for double-escaped text | `repeat` | Yes/no | Unescape again until nothing changes. Default: unticked (one pass). |
| Non-breaking spaces as plain spaces | `plainSpaces` | Yes/no | Turn non-breaking spaces into ordinary spaces. Default: ticked. |

## Outputs
- **Unescaped** (`Output Data`): the input records with the unescaped text in a new field.

## Limits
- **HTML tags are not removed**: `&lt;b&gt;` becomes `<b>`, and `<b>` already in the text stays.
- **Some old reference names work without a semicolon**, as they do in web browsers: `&pound10` becomes `£10`. Text that happens to contain such a name after an `&` (`&copy`, `&not`, `&pound` and about a hundred others) is changed too.
- **Repeat for double-escaped text** also unescapes text that was meant to show a reference: a page explaining that `&amp;lt;` is written for `<` loses that. Leave it unticked unless the source is known to be escaped twice.

## Size of input

The records are processed in chunks as they stream through. In tests, 200,000 records took under half a second.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
