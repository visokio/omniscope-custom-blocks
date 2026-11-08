# Anonymise

Replaces names, emails and other text with generated code words, and shifts numbers and dates by random noise, to make a safer copy of a dataset for demos and testing.

Customer lists, HR extracts and ticket logs often have to be shared with developers, testers or a demo audience who shouldn't see the real names and amounts. This block keeps the dataset's shape (its fields, record count, groupings and rough values) and replaces what identifies people.

- **Text** fields: each distinct value becomes a generated code word such as `mango3`. The same value gets the same word everywhere within a run, in every chosen field, so counts, groupings and joins between the chosen fields still work. Missing values stay missing.
- **Number** fields: random noise from a Laplace distribution is added to each value. Whole-number fields stay whole numbers; decimal fields get decimal noise.
- **Date** fields: each date is moved by a random number of seconds.
- Fields you don't choose, and fields of other types, pass through unchanged.

This is **pseudonymisation, not anonymisation**. The output keeps the original data's patterns, frequencies and approximate values, and someone who knows the data may recognise records by them (the one customer with 54 orders is still the one with about 54 orders). Treat the output as still sensitive; don't rely on it for external publication or as a regulatory compliance control.

## Language
Python

## Inputs
- **Input 1**: the records to anonymise.

## Options

| Option | Name in script | Type | Default | Description |
|---|---|---|---|---|
| Fields to anonymise | `selectedFields` | Fields (any type) | empty | Fields to replace or add noise to. Leave empty to anonymise every field. |
| Number privacy budget (epsilon) | `epsilon_numeric` | Number | 5 | Lower means more noise on number fields. |
| Number sensitivity | `sensitivity_numeric` | Number | 10 | In the fields' own units. Higher means more noise. |
| Date privacy budget (epsilon) | `epsilon_date` | Number | 5 | Lower means more noise on date fields. |
| Date sensitivity (seconds) | `sensitivity_date` | Number | 3,600 | In seconds (86,400 is one day). Higher means larger date shifts. |

The noise has a typical size (mean absolute change) of **sensitivity ÷ budget**: with the defaults, about 2 for numbers and about 12 minutes (720 seconds) for dates. One pair of options applies to every chosen number field, so a field of thousands and a field of single figures get noise of the same size; if they need different amounts, use two Anonymise blocks one after the other, each with its own fields. Budgets and sensitivities must be greater than zero.

## Outputs
- **Anonymised** (`Output Data`): the input with the chosen text fields replaced by code words and noise added to the chosen number and date fields. Same fields, same order, same number of records.

## Limits

- **Each run is different**: new code words and new noise every time the block runs. To keep one anonymised copy, write the output to a file or another destination and use that.
- Code words are drawn from a fixed list of about 150 English words, followed by a number (`apple1`, `apple2` ...); they say nothing about the original value.
- Noise can take a value past its natural limits: a count of 1 can become 0 or -1, a date can move across midnight (date-only values gain a time of day).
- Text fields that hold numbers or dates as text are treated as text and replaced with code words.
- The tests run 200,000 records with text, number, whole-number and date fields and check that they finish in under 60 seconds, including the test set-up.

## Dependencies
[OpenDP](https://opendp.org/) (`opendp`, MIT licence) for the noise, installed by Omniscope with pip on first run. pandas and numpy come with Omniscope's Python environment.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
