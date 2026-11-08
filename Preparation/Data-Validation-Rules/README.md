# Data Validation Rules

Validates data against a rules table or typed rules (not empty, unique, ranges, lists, patterns, emails, postcodes, field comparisons) with violations per row and per rule.

Checks data against a list of **validation rules** and reports every violation, a summary per rule and a pass / fail flag per row.

Rules come from a **rules table on input 2** (Field, Check, Value, Severity, optional Rule Name), so business users can maintain them, or are typed in the options one per line: `Field | CHECK | value | severity`.

**Checks**: NOT_EMPTY, UNIQUE, MIN, MAX, BETWEEN (`low..high`), ALLOWED and NOT_ALLOWED (`a|b|c`), PATTERN (regular expression), MIN_LENGTH, MAX_LENGTH, IS_NUMBER, IS_DATE, NOT_FUTURE, EMAIL, UK_POSTCODE, COMPARE with another field (`<= Credit Limit`), REQUIRED_IF another field has a value (`Country = UK`).

**Severity** is Error or Warning; a row is *Valid* when it has no errors. Empty values pass every check except NOT_EMPTY and REQUIRED_IF, so each problem is reported once.

Outputs: one row per violation (with your key fields), one row per rule with failures, rate, status and examples, and the input with error and warning counts.

## Language
Python

## Inputs
- **Input 1**: the data to check.
- **Input 2 (optional)**: a rules table (field, check, value, severity, rule name).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Rules | Rules (one per line) | `rules` | Text | Field / CHECK / value / severity, for example: Email / EMAIL / / Error |
| Rules | Key fields for the violations list | `key_fields` | Fields | For example Customer ID. From input 1. |
| Rules | Example values per rule | `examples` | Whole number | Default: 3. |
| Rules table (input 2, optional) | Field column | `rule_field_field` | Field | Column of the rules table naming the field to check. From input 2. |
| Rules table (input 2, optional) | Check column | `rule_check_field` | Field | Column naming the check, such as NOT_EMPTY or BETWEEN. From input 2. |
| Rules table (input 2, optional) | Value column | `rule_value_field` | Field | Column with the check's value, such as a range or list. From input 2. |
| Rules table (input 2, optional) | Severity column | `rule_severity_field` | Field | Column with Error or Warning. From input 2. |
| Rules table (input 2, optional) | Rule name column | `rule_name_field` | Field | Column with a readable name for each rule. From input 2. |

## Outputs
- **Violations** (`violations`): One row per failed check: row number, key fields, rule, field, check, severity, value found.
- **Rule summary** (`rules`): Per rule: rows checked, rows failing, failure rate, status, example values, first failing row.
- **Rows** (`rows`): The input with Errors, Warnings, Failed Rules and Valid.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the core Validate data block

Use the core **Validate data** block to stop a workflow on schema problems, rule matches or record-count limits. Use this block when the rules live in a table that business users maintain, and you want a results table per record and per rule rather than a pass or fail.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
