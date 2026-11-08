# Likert Survey Summary

Summarises Likert-scale survey questions: answer distributions, mean scores, top-2-box, net scores and neutral shares, per question and segment.

Summarises survey questions answered on an agreement or satisfaction scale (*Strongly disagree* to *Strongly agree*, *Very dissatisfied* to *Very satisfied*, or 1 to 5), straight from the export where each respondent is a row and each statement a column.

Per question (and per segment, such as department or region):

- **Distribution** of answers, with counts, shares and a signed *diverging share* ready for the classic diverging bar chart
- **Mean score**, **top-2-box** (% agree / satisfied), **bottom-2-box**, **neutral** share and **net score** (top minus bottom)
- Responses, no-answer and unrecognised counts, and a reliability flag for small groups
- A **tidy long table** (respondent, question, answer, score) for any further analysis

Answer text is matched ignoring case and punctuation; numbers 1 to N are accepted too; *N/A*, *Don't know* and *Prefer not to say* count as no answer. Built-in scales: agree (5 and 4 point), satisfaction, likelihood, frequency, numeric, or your own labels.

## Language
Python

## Inputs
- **Input 1**: survey responses, one row per respondent and one column per statement.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Questions | Question fields | `question_fields` | Fields | One field per survey statement. From input 1. |
| Questions | Break down by (optional) | `segment_fields` | Fields | For example Department or Region. From input 1. |
| Scale | Answer scale | `scale` | Choice | How the answers are worded, lowest to highest. Numbers and custom labels cover other scales. Choices: Agree, 5 point (Strongly disagree ... Strongly agree); Agree, 4 point (no neutral); Satisfaction, 5 point; Likelihood, 5 point; Frequency (Never ... Always); Numbers (1 to N); Custom labels. Default: Agree, 5 point (Strongly disagree ... Strongly agree). |
| Scale | Custom labels (lowest first) | `custom_labels` | Text | Comma-separated, for example Poor, Fair, Good, Very good, Excellent. |
| Scale | Top / bottom box size | `box_size` | Whole number | 2 = top-2-box (Agree + Strongly agree). Default: 2. |
| Scale | Minimum responses to report reliably | `min_responses` | Whole number | Default: 5. |

## Outputs
- **Question summary** (`summary`): Per question (and segment): responses, mean, top / bottom box, neutral, net score, rank, reliability.
- **Answer distribution** (`distribution`): Per question (and segment) and answer: count, share, diverging share.
- **Responses (long)** (`responses`): One row per respondent and question: answer label and score.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
