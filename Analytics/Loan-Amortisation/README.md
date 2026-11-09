# Loan Amortisation Schedule

Generates payment schedules for loans and leases (repayment, equal principal, interest only, with balloon), monthly, quarterly or annually, with a summary per loan.

Generates the full **payment schedule** for every loan, lease or finance agreement in a table: one row per payment with opening balance, payment, interest, principal repaid, closing balance and cumulative interest, plus a summary per loan.

- **Repayment** (annuity): level payments, the usual loan and mortgage structure
- **Equal principal**: the same capital each period, so payments decline
- **Interest only**: interest each period, capital repaid at the end
- Optional **balloon** (residual value, as in PCP car finance or asset finance): level payments leave that amount to be repaid with the final payment
- **Monthly, quarterly or annual** payments; term in months or years; rates as percentages (7.9) or fractions (0.079), detected automatically
- The repayment type can come from a field per loan (values such as *Repayment*, *Equal principal*, *Interest only*) or be set for all

Loans with missing or invalid values are listed in the summary with the reason instead of failing the block. Payment dates step on from the start date by whole months.

## Language
Python

## Inputs
- **Input 1**: one row per loan (principal, annual rate, term, and optionally start date, balloon, repayment type).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Loans | Loan ID (optional) | `loan_id_field` | Field | Names each loan in the schedule and summary. From input 1. |
| Loans | Principal | `principal_field` | Field | Amount borrowed. From input 1. |
| Loans | Annual interest rate | `rate_field` | Field | Percent (7.9) or fraction (0.079). From input 1. |
| Loans | Term | `term_field` | Field | Length of the loan, in the unit set by Term is in. From input 1. |
| Loans | Start date (optional) | `start_field` | Field | Payments fall one period after this date, then every period. From input 1. |
| Loans | Balloon / residual (optional) | `balloon_field` | Field | Amount left to pay at the end, as in a lease or balloon loan. From input 1. |
| Loans | Repayment type field (optional) | `type_field` | Field | Per-loan type; otherwise the default below is used. From input 1. |
| Terms | Default repayment type | `repayment_type` | Choice | Choices: Repayment (annuity); Equal principal; Interest only. Default: Repayment (annuity). |
| Terms | Payment frequency | `frequency` | Choice | How often payments fall due. Choices: Monthly; Quarterly; Annual. Default: Monthly. |
| Terms | Term is in | `term_unit` | Choice | Whether the term field counts months or years. Choices: Months; Years. Default: Months. |
| Terms | Rate format | `rate_format` | Choice | Choices: Automatic; Percent (7.9 = 7.9%); Fraction (0.079 = 7.9%). Default: Automatic. |

## Outputs
- **Payment schedule** (`schedule`): One row per loan and payment: date, opening balance, payment, interest, principal repaid, closing balance, cumulative interest.
- **Loan summary** (`summary`): One row per loan: type, status, payments, regular / first / final payment, total paid, total interest, final payment date.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
