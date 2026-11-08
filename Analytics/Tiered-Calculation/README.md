# Tiered Calculation

Applies tier tables (commission plans, tax bands, volume discounts) marginally or to the whole amount, per plan, with a breakdown by tier.

Applies a **tier table** to an amount: commission plans, tax bands, volume discounts, rebates and stepped tariffs.

- **Marginal**: each slice of the amount is charged at its own tier's rate (income tax bands, commission accelerators)
- **Whole amount**: the whole amount is charged at the rate of the tier it falls in, plus that tier's fixed amount (volume discount tables)
- Tiers from a **table on input 2** (from, to, rate, optional fixed amount, optional **plan** key so different rows use different plans), or typed in the options: `0-10000: 0.02, 10000-50000: 0.05, 50000-: 0.08`
- Rates as decimals (0.05) or percentages (5%); an empty *to* means up to the next tier, or no limit for the top tier

Outputs: each row with the result, the effective rate and the tier reached, and a breakdown of the result by tier (for statements and checks).

## Language
Python

## Inputs
- **Input 1**: the amounts (and optionally a plan field).
- **Input 2 (optional)**: the tier table (from, to, rate, fixed amount, plan).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Amounts (input 1) | Amount field | `amount_field` | Field | The amount to apply the tiers to, such as sales. From input 1. |
| Amounts (input 1) | Plan field (optional) | `plan_field` | Field | Matches the plan key of the tier table. From input 1. |
| Amounts (input 1) | Method | `mode` | Choice | Marginal applies each tier's rate to its own slice, as income tax does; whole applies the reached rate to everything. Choices: Marginal (each slice at its tier's rate); Whole amount at the reached tier's rate. Default: Marginal (each slice at its tier's rate). |
| Amounts (input 1) | Result field name | `result_name` | Text | Name of the new field holding the result. Default: Tiered Result. |
| Tiers | Tiers (if no input 2) | `tiers` | Text | from-to: rate, for example 0-10000: 0.02, 10000-: 0.05 (add + fixed for a fixed amount) |
| Tiers | Plan key (input 2) | `tier_plan_field` | Field | Plan name in the tier table, matched to the plan field of input 1. From input 2. |
| Tiers | From (input 2) | `tier_from_field` | Field | Lower bound of each tier. From input 2. |
| Tiers | To (input 2) | `tier_to_field` | Field | Upper bound of each tier; when empty, the next tier's lower bound. From input 2. |
| Tiers | Rate (input 2) | `tier_rate_field` | Field | Rate for each tier, such as 0.05 for 5%. From input 2. |
| Tiers | Fixed amount (input 2) | `tier_fixed_field` | Field | From input 2. |

## Outputs
- **Rows** (`rows`): The input with the result, effective rate and tier reached.
- **Breakdown** (`breakdown`): Per row and tier: band, rate, amount in the tier, result in the tier.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
