# Investment Appraisal

NPV, IRR / XIRR, MIRR, payback, discounted payback and profitability index per project from cash flows, with NPV profiles and multiple-IRR warnings.

Compares **projects, capital requests or business cases** from their cash flows.

- **NPV** at the discount rate (one rate for all, or a rate field per project)
- **IRR** (or **XIRR** on actual dates) and **MIRR** (finance and reinvestment at the discount rate)
- **Payback** and **discounted payback**, interpolated within the period
- **Profitability index** (PV of inflows / PV of outflows), totals, rank by NPV and an accept / reject flag
- Projects whose cash flows change sign more than once can have **several IRRs**: they are flagged and all IRRs found are listed

Timing is by **period number** (0 = now, 1 = end of year 1...) or by **date** (XNPV / XIRR: annual rate, actual days / 365, discounted to each project's first date). Several rows for the same project and time are added together.

Outputs: one row per project, the discounted cash flows with cumulative totals, and an **NPV profile** (NPV at rates from 0% to the maximum) for charts.

## Language
Python

## Inputs
- **Input**: cash flows with a project, a period number or date, and an amount.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | Project field | `project_field` | Field | Names the project each cash flow belongs to. From input 1. |
|  | Period or date field | `time_field` | Field | Period number (0 = today) or the date of each cash flow, to match Timing. From input 1. |
|  | Cash flow field | `amount_field` | Field | Outflows negative, inflows positive. From input 1. |
|  | Timing | `timing` | Choice | Period numbers for NPV and IRR; dates for XNPV and XIRR on actual days. Choices: Period numbers (0, 1, 2...); Dates (XNPV / XIRR). Default: Period numbers (0, 1, 2...). |
|  | Discount rate | `discount_rate` | Decimal number | Per period, or annual for dates. For example 0.08. Default: 0.08. |
|  | Rate per project (optional) | `rate_field` | Field | From input 1. |
|  | NPV profile up to rate | `profile_max_rate` | Decimal number | Default: 0.3. |

## Outputs
- **Projects** (`projects`): Per project: rate, flows, NPV, IRR, MIRR, profitability index, payback, discounted payback, notes, decision, rank.
- **Cash flows** (`cashflows`): Per project and time: cash flow, discount factor, present value, cumulative cash flow and present value.
- **NPV profile** (`npv_profile`): Per project: NPV at rates from 0% to the maximum in 1% steps.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
