# Customer Lifetime Value

Historical and predictive customer lifetime value from orders (BG/NBD and Gamma-Gamma), with probability active, discounting and a holdout check.

**Customer lifetime value** from order history: what each customer has spent, how likely they are to still be active, and what they are expected to spend in the coming months.

The prediction uses the standard *buy till you die* models used in retail and subscription-free businesses:

- **BG/NBD** for how often each customer buys and the probability they are still active (a customer who used to buy weekly and has not bought for three months is probably gone; one who buys twice a year probably is not)
- **Gamma-Gamma** for the expected value per order, shrinking each customer's average towards the overall average when they have few orders

Predicted CLV = expected purchases in each future month x expected order value x margin, discounted at the annual rate you choose.

Optional **holdout check**: the model is fitted again on data up to N months before the end and its predicted purchases are compared with what customers actually did, so you can see how far to trust it.

Purchases are counted per customer per day; days with zero or negative net value (refunds) are dropped. Needs the *scipy* package, which is installed with the block.

## Language
Python

## Inputs
- **Input**: order lines with a customer ID, order date and value.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Orders | Customer field | `customer_field` | Field | Identifies a customer. From input 1. |
| Orders | Order date field | `date_field` | Field | Date of each order. From input 1. |
| Orders | Order value field | `value_field` | Field | Revenue or profit per order line. From input 1. |
| Orders | Summarise by (optional) | `group_fields` | Fields | For example acquisition channel or region (taken from each customer's first order). From input 1. |
| Prediction | As of date (optional) | `as_of` | Text | Default: the latest order date. |
| Prediction | Horizon (months) | `horizon_months` | Whole number | How far ahead the predicted value runs. Default: 12. |
| Prediction | Annual discount rate | `discount_rate` | Decimal number | For example 0.1 for 10%. Default: 0.1. |
| Prediction | Margin | `margin` | Decimal number | Share of order value that is profit; 1 = predict revenue. Default: 1.0. |
| Prediction | Holdout check (months) | `holdout_months` | Whole number | 0 = no check. Default: 0. |

## Outputs
- **Customers** (`customers`): Per customer: history, probability active, status, expected purchases and order value, predicted CLV, CLV tier.
- **Summary** (`summary`): Overall and per group: customers, active share, revenue to date, predicted CLV total, average and concentration.
- **Model** (`model`): Fitted BG/NBD and Gamma-Gamma parameters, checks and holdout accuracy.
- **Holdout check** (`validation`): Actual vs predicted purchases in the holdout period by number of earlier repeat purchases.

## Dependencies
scipy

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
