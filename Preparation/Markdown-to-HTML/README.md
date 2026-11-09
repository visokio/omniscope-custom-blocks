# Markdown to HTML

Converts Markdown text in a field (bold, lists, links, headings, tables) to HTML in a new field, keeping the other fields.

Product descriptions, release notes, ticket comments and survey answers are often written in Markdown: `**bold**`, `- lists`, `[links](...)`, `## headings`. This block converts the text in each record to HTML, so it can be shown formatted in a view that displays HTML, sent in an email, or written to a web page or file.

- **One new field** (`HTML` by default) after the input fields. Name it after the Markdown field to replace that field instead, or untick **Keep the input fields** to output only the HTML.
- **Tables, fenced code and footnotes** (ticked by default) adds Python-Markdown's `extra` extension: tables, fenced code blocks, footnotes, abbreviations, definition lists and attribute lists. Unticked, only standard Markdown is converted.
- **Empty values stay empty.** Numbers are converted as their text.
- Footnote numbering starts again for each record.

## Language and libraries

Python. It uses pandas (BSD 3-Clause licence), part of Omniscope's Python environment, and Python-Markdown (the `markdown` package, BSD 3-Clause licence). `markdown` is listed in the block's dependencies, so Omniscope installs it with pip on first run if it is missing; the server needs access to the Python package index for that, or the package installed beforehand.

## Inputs
- **Input 1**: records with a text field holding Markdown.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Markdown field | `MarkdownText` | Field (text) | The text field holding Markdown. From input 1. |
| HTML field name | `outputField` | Text | Name of the new field holding the HTML. Use the Markdown field's name to replace it. Default `HTML`. |
| Keep the input fields | `includeInput` | Yes/no | Output the input fields with the HTML field after them. Unticked, only the HTML field. Default: ticked. |
| Tables, fenced code and footnotes | `extensions` | Yes/no | Also convert the `extra` Markdown extensions. Unticked: standard Markdown only. Default: ticked. |

## Outputs
- **HTML** (`Output Data`): one record per input record, with the HTML in the new field.

## Limits
- **HTML in the text is passed through unchanged**, including scripts. Only convert text from sources you trust if the HTML will be shown in a report or a web page.
- Links and images are written as given; relative links stay relative.
- The HTML has no surrounding page or styles: it is a fragment (`<p>`, `<ul>`, `<table>` and so on).

## Size of input

Each distinct text is converted once. In tests, 20,000 different short texts (a heading, a paragraph with a link, a two-item list) took about 7 seconds.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
