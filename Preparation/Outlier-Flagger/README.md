# Outlier Flagger

Flags low and high outliers in many numeric fields at once, within groups, by IQR, z-score or robust MAD, with bounds and optional capping.

Flags **unusually low or high values** in many numeric fields at once, optionally **within groups** (per product, category, region, machine), by a standard rule:

- **IQR** (Tukey's fences): outside Q1 - k x IQR to Q3 + k x IQR, k = 1.5 by default
- **Z-score**: more than k standard deviations from the mean, k = 3
- **MAD** (robust z, Iglewicz and Hoaglin): 0.6745 x (value - median) / MAD above k = 3.5; not distorted by the outliers themselves

Groups with fewer values than the minimum are not tested. Optionally adds **capped** (winsorised) copies of the fields, clipped to the bounds.

Outputs: the rows with a Low / High / No flag per field, a count and a list; one row per outlying value with its bound, score and distance beyond the bound; and the bounds used per field and group.

## Language
Python

## Inputs
- **Input**: data with numeric fields (and optional group and key fields).

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Numeric fields | `fields` | Fields | Leave empty to check every numeric field. From input 1. |
| Within groups (optional) | `group_fields` | Fields | For example Category. From input 1. |
| Key fields for the outlier list | `key_fields` | Fields | For example Claim ID. From input 1. |
| Method | `method` | Choice | IQR and MAD resist the outliers they look for; z-score suits roughly normal data. Choices: IQR (Tukey's fences); Z-score; MAD (robust z). Default: IQR (Tukey's fences). |
| Multiplier | `k` | Decimal number | 0 = the method's default (1.5, 3 or 3.5). Default: 0.0. |
| Smallest group to test | `min_group_size` | Whole number | Groups with fewer values are not tested. Default: 10. |
| Add capped (winsorised) fields | `add_capped` | Tick box | Default: unticked. |

## Outputs
- **Rows** (`rows`): The input with an outlier flag per field, Outlier Count and Outlier Fields (and capped fields if chosen).
- **Outliers** (`outliers`): One row per outlying value: row number, keys, group, field, value, direction, bound, score.
- **Bounds** (`bounds`): Per field and group: values, bounds, low and high counts, share, minimum, median, maximum.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the core Anomaly Detection block

Use the core **Anomaly Detection** block for an anomaly score per record across several fields. Use this block when you need explicit, explainable bounds per field (IQR, z-score or MAD), within groups, and the option to cap values rather than only flag them. The community Data Quality Analyser flags IQR outliers as one check among many.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
