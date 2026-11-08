# Data Profiler

Profiles a dataset: one record per field with its type, missing and distinct counts, most common value and statistics, and the records with z-scores and anomaly flags for every numeric field.

Point it at a new data source before building on it, or after a change upstream, to see what each field holds: how much is missing, whether an ID is really unique, what the usual values are, and which numbers sit far from the rest.

- **Fields output**: one record per field (all fields, or the ones you choose) with its Omniscope type, the number of records, missing values (count and %), distinct values, and the most common value with its count (left empty when every value occurs once).
- Numeric fields also get the **mean, standard deviation, minimum, lower quartile, median, upper quartile, maximum, skewness** and the number of **anomalies**. Date fields get the **first and last date**.
- **Records output**: the input records, unchanged, with three fields added for each numeric field:
  - `<field>_z_score`: how many standard deviations the value is from the field's mean (the same mean and standard deviation as in the Fields output);
  - `<field>_anomaly`: 1 when that distance is at least the **anomaly threshold** (3 by default), otherwise 0;
  - `<field>_p_value`: the chance of a value at least this far from the mean, either side, if the field were normally distributed (1 at the mean, 0.0027 at 3 standard deviations).
- **Anomaly count** on each record says how many of its values were flagged.

Missing values are left out of the statistics; their z-score, flag and p-value are empty. Boolean fields are counted (missing, distinct, most common) but not scored.

## Language
Python

## Inputs
- **Input 1**: any records.

## Options

| Option | Name in script | Type | Default | Description |
|---|---|---|---|---|
| Fields to profile | `fields` | Fields (any type) | empty | Leave empty to profile every field. From input 1. |
| Anomaly threshold (standard deviations) | `threshold` | Number | 3 | A numeric value is flagged when it is at least this many standard deviations from its field's mean. Must be greater than 0. |

## Outputs
- **Fields** (`Output Data`): one record per profiled field, in input order: Field, Type (Text, Integer, Decimal, Date or Boolean), Records, Missing, Missing %, Distinct, Most common, Most common count, Mean, Std dev, Min, Lower quartile, Median, Upper quartile, Max, Skewness, First date, Last date, Anomalies. The fields are the same whatever the input, so blocks after it keep working when the data changes; statistics that don't apply to a field's type are empty.
- **Records** (`Output Data 2`): the input records with `<field>_z_score`, `<field>_anomaly` and `<field>_p_value` for each numeric field (all z-scores first, then all flags, then all p-values) and **Anomaly count** at the end. An input field with one of these names is replaced.

## Limits
- The standard deviation is the sample standard deviation (divided by n − 1), as in the Fields output.
- A z-score is measured against a mean and standard deviation that include the unusual values themselves, so one very large value widens the spread and can hide smaller ones. With 10 values or fewer no value can be 3 standard deviations from the mean, so small inputs have no anomalies at the default threshold. For skewed fields (amounts, durations) many ordinary values can look unusual; the community **Outlier Flagger** block offers IQR and median-based (MAD) rules instead.
- A field with only one value, or with every value the same, has no z-scores.
- Text that holds numbers is profiled as text; convert it first (Field Organiser) to get statistics.
- The most common value is written as text. When several values are equally common, the lowest is shown (numbers and dates in order, text alphabetically).
- In tests, 200,000 records with five fields took under a second.

## Dependencies
SciPy (BSD licence) for the normal distribution behind the p-values, listed in the block's dependencies so Omniscope installs it with pip on first run if it is missing. pandas and numpy (BSD licence) come with Omniscope's Python environment.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo; `generate.py` there recreates it.
