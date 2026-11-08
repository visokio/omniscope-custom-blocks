# Text Word Frequency

Word and phrase counts in a text field, overall and per group, with stop words, n-grams and the terms most distinctive of each group.

Counts the words and short phrases in a text field (survey comments, complaints, reviews, ticket descriptions, call notes), overall and per group, and finds the words most **distinctive** of each group.

- Words are lower-cased; English **stop words** (the, and, was...) are removed, plus any you add; numbers are dropped unless you keep them
- **Phrases** of up to 4 consecutive remaining words (for example *call back*, *wait on hold*)
- For each term: occurrences, the **number of rows using it** and the share of rows, and its rank
- With **groups** (channel, product, NPS category): the share of rows in the other groups and a **distinctiveness z-score** (weighted log-odds with an informative prior, Monroe et al. 2008); z above 1.96 is flagged

A second output returns the rows with their word count, the number of terms kept and which of the top terms they use, so comments can be filtered by term in a Report.

## Language
Python

## Inputs
- **Input**: data with a text field, and optionally fields to compare groups by.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Text | Text field | `text_field` | Field | The free text to count words in, such as comments. From input 1. |
| Text | Compare groups (optional) | `group_fields` | Fields | For example Channel, Product or NPS Category. From input 1. |
| Terms | Longest phrase (words) | `max_ngram` | Whole number | 1 = single words only. Default: 2. |
| Terms | Shortest word (letters) | `min_word_length` | Whole number | Default: 2. |
| Terms | Minimum rows using a term | `min_documents` | Whole number | Rarer terms are left out. Default: 2. |
| Terms | Top terms per group | `top_n` | Whole number | 0 = all. Default: 0. |
| Terms | Remove English stop words | `remove_stop_words` | Tick box | Default: ticked. |
| Terms | Extra stop words | `extra_stop_words` | Text | Comma-separated, for example your brand name. |
| Terms | Keep numbers | `keep_numbers` | Tick box | Default: unticked. |

## Outputs
- **Terms** (`terms`): Per group and term: occurrences, rows using it, share of rows, rank, share in other groups, distinctiveness z.
- **Rows** (`rows`): The input with Word Count, Terms Kept and Top Terms Used.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
