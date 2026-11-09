# A/B Test

Tests whether variants differ from the control on conversion rate (z-test) or mean (Welch's t-test), with lift, confidence intervals, p-values, verdicts and required sample size.

Tells you whether a variant really beat the control, or whether the difference could be chance.

- **Conversion rates** (did the visitor buy, click, sign up?): two-proportion z-test
- **Means** (order value, time on page, basket size): Welch's t-test, which does not assume equal variances
- Each variant is compared with the **control**: difference, **relative lift**, **confidence interval**, **p-value**, *Significant* yes / no and a **plain-language verdict**
- **Sample size needed** per variant to confirm an effect of the observed size at the chosen power
- Optional **segments** (device, country, channel) with a **Bonferroni correction** for running many comparisons
- Data either **one row per visitor** (variant and outcome; outcomes such as Yes / No, 1 / 0, true / false are understood) or **one row per variant** (visitors and conversions)

The second output gives each variant's sample size, rate or mean and its confidence interval.

Compares two groups on rates or means in one step. Pure Python: no packages to install.

## Language
Python

## Inputs
- **Input 1**: experiment data, one row per visitor or one row per variant.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Data | Data layout | `layout` | Choice | Raw rows with one outcome each, or a summary with trials and successes per variant. Choices: One row per visitor / observation; One row per variant (trials and successes). Default: One row per visitor / observation. |
| Data | Variant field | `variant_field` | Field | Field naming the variant, such as A / B or Control / New checkout. From input 1. |
| Data | Outcome field (one row per visitor) | `metric_field` | Field | Converted (Yes / No, 1 / 0, true / false) for rates; a number for means. From input 1. |
| Data | Trials field (one row per variant) | `trials_field` | Field | For example Visitors. From input 1. |
| Data | Successes field (one row per variant) | `successes_field` | Field | For example Conversions. From input 1. |
| Test | Compare | `metric_type` | Choice | A rate (converted or not) is tested with a z-test; a mean with Welch's t-test. Choices: Conversion rate (proportion); Mean of a number. Default: Conversion rate (proportion). |
| Test | Control variant | `control` | Text | Value of the variant field for the control. Leave empty to use the first in alphabetical order. |
| Test | Confidence level | `confidence` | Decimal number | 0.95 means a 5% chance of calling a difference that is really chance. Default: 0.95. |
| Test | Power for sample size | `power` | Decimal number | Chance of detecting a real effect of the observed size; 0.8 is the usual choice. Default: 0.8. |
| Options | Test separately for each (optional) | `segment_fields` | Fields | For example Device or Country. From input 1. |
| Options | Bonferroni correction | `bonferroni` | Tick box | Divide the significance threshold by the number of comparisons, to protect against false positives when testing many variants or segments. Default: unticked. |

## Outputs
- **Test results** (`results`): One row per variant (and segment) compared with the control: difference, lift, confidence interval, p-value, significance, sample size needed, verdict.
- **Variant statistics** (`variants`): One row per variant (and segment): sample size, rate or mean, standard deviation, confidence interval.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
