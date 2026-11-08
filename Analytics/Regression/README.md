# Regression

Linear or logistic regression with coefficients, standard errors, p-values, confidence intervals, odds ratios, VIF, fit statistics and scored rows.

**Linear** (least squares) or **logistic** (yes / no outcome) regression with the full statistical output.

- **Coefficients** with standard errors, t or z statistics, **p-values** and confidence intervals; **odds ratios** for logistic regression
- **VIF** (variance inflation factor) per term, to spot collinear predictors (above 10 is a warning sign)
- **Fit**: R-squared, adjusted R-squared, RMSE, F test and AIC; or log-likelihood, McFadden pseudo R-squared, likelihood-ratio test, **AUC** and accuracy
- **Scored rows**: prediction, residual and a prediction interval (linear), or probability and predicted class (logistic)

Text predictors are dummy-coded against their most common value (for example *Contract = One year* compared with *Monthly*). Rows with missing values are left out of the fit but still scored when their predictors are complete. *Automatic* chooses logistic when the target has exactly two values.

Python with numpy only; the tests check the results against reference values from statsmodels.

## Language
Python

## Inputs
- **Input**: data with the target and predictor fields.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Model | Target field | `target_field` | Field | The value to explain: a number (linear) or a yes / no outcome (logistic). From input 1. |
| Model | Predictor fields | `predictor_fields` | Fields | Numbers or text (text is dummy-coded). From input 1. |
| Model | Model | `model` | Choice | Automatic chooses logistic for a two-value target and linear otherwise. Choices: Automatic; Linear; Logistic. Default: Automatic. |
| Model | Positive class (logistic) | `positive_class` | Text | Default: Yes / 1 / True if present. |
| Options | Confidence level | `confidence` | Decimal number | For the coefficient confidence intervals. Default: 0.95. |
| Options | Classification threshold (logistic) | `threshold` | Decimal number | Default: 0.5. |
| Options | Most values for a text predictor | `max_levels` | Whole number | Default: 30. |

## Outputs
- **Coefficients** (`coefficients`): Per term: coefficient, standard error, t or z, p-value, confidence interval, VIF, odds ratio (logistic), significant.
- **Fit** (`fit`): Model statistics: rows, R-squared, F test, AIC; or log-likelihood, pseudo R-squared, LR test, AUC, accuracy.
- **Scored rows** (`scored`): The input with prediction, residual and interval, or probability and predicted class.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the core Regression block

Use the core **Regression** block to fit a model and generate predictions. Use this block when you need the statistics report: coefficients with standard errors, p-values and confidence intervals, and logistic regression for yes/no outcomes.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
