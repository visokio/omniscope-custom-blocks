# Survival Analysis

Estimates survival (or retention) curves from time-to-event data with censoring, by the Kaplan-Meier or Fleming-Harrington method, overall or per group, with 95% confidence limits and the median time per group.

Each input record is one subject (a customer, a machine, a patient) with:

- **Time**: how long it was followed, in any unit (days, months...): until the event, or until it was last seen without one;
- **Event**: whether the event (cancelling, failing, dying) happened at the end of that time. A subject still going is **censored**: it counts as at risk up to its time, and is not counted as an event.

The survival curve is the estimated share of subjects still without the event at each time. Because censored subjects only count while they are followed, the curve is not biased by subjects who joined recently, as a simple "share who cancelled" would be.

How the block runs it (R's survival package, `survfit()`):

- **Kaplan-Meier** (default): at each time with events, survival is multiplied by (at risk - events) / at risk.
- **Fleming-Harrington**: survival is exp(-H), where H is the Nelson-Aalen cumulative hazard (the sum of events / at risk). Slightly higher than Kaplan-Meier, mostly where few subjects remain.
- The 95% confidence limits are survfit's default ("log" intervals). Where survival reaches 0 they are empty.
- **Event** may be 0 / 1 (1 = event), 1 / 2 (2 = event, as in R's `Surv()`) or true / false.
- **Group** (optional): one curve per value. Records with a missing time, event or group are left out.
- The curve starts with a row at time 0 (survival 1, everyone at risk) for each group, so a step line starts at the top.

## Inputs
- **Input 1**: one record per subject, with a numeric Time field, an Event field and optionally a Group field.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Time | `time` | Field | How long each subject was followed (a number, not a date). Required. |
| Event | `event` | Field | 1 = event, 0 = censored (or 2 / 1, or true / false). Required. |
| Group | `strata` | Field | Optional: one curve per value of this field. |
| Method | `type` | Choice | Kaplan-Meier (`kaplan-meier`, default) or Fleming-Harrington (`fleming-harrington`). |

## Outputs
- **Curve** (`Output Data`): one record per group and time at which an event or censoring happened, plus time 0. Fields: the Group field (when chosen, under its own name), **Time**, **At risk**, **Events**, **Censored**, **Survival**, **Lower 95%**, **Upper 95%**, **Std error (log survival)** (survfit's standard error, which is on the log scale).
- **Summary** (`Summary`): one record per group: the Group field, **Records**, **Events**, **Censored**, **Median time** (the first time survival is 0.5 or below), **Median lower 95%**, **Median upper 95%**. The median and its limits are empty where the curve does not get that low.

## Limits

- Time must be a number of units, not a date: work out the duration first (for example with `DATEDIFF` in a Field Organiser), or use the Churn Survival Curves block, which takes start and end dates.
- In tests, 100,000 subjects in 50 groups took about 1 second.

## Language and libraries
R, with the **survival** package (licence: LGPL 2 or later), one of R's recommended packages that come with most R installations; install it with `install.packages("survival")` if it is missing. Earlier versions also needed ggfortify (and with it ggplot2); it is no longer used.

## Source
[script.R](script.R)

The sample data in `sample-data/` is invented for the demo; `sample-data/make-sample.R` generates it.
