# RFM Segmentation

Scores customers on recency, frequency and monetary value from transactions and assigns named segments such as Champions, At Risk and Lost, with a segment summary.

Turns a transactions table into a **customer segmentation** marketers can act on, using the classic RFM method:

- **Recency**: days since the customer last bought (relative to an analysis date, by default the day after the latest transaction)
- **Frequency**: number of orders (distinct order IDs, or rows if no order field is chosen)
- **Monetary**: total spend

Each is scored 1 to 5 (or 1 to N) by percentile, where 5 is best (most recent, most frequent, highest spend), giving an RFM score such as *543*. Customers are then placed in one of ten named segments:

*Champions, Loyal Customers, Potential Loyalists, New Customers, Need Attention, About to Sleep, At Risk, Can't Lose Them, Hibernating, Lost*

based on their recency score and the average of their frequency and monetary scores. The second output summarises each segment (customers, revenue, shares, averages) with a description and a suggested action.

The segment rules are a widely used starting point, not a standard: the scores are in the output, so you can define your own segments with a formula.

## Language
Python

## Inputs
- **Input 1**: transactions, one row per order (or order line with an order ID).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Transactions | Customer field | `customer_field` | Field | Identifies a customer. From input 1. |
| Transactions | Order date field | `date_field` | Field | Date of each order, for recency. From input 1. |
| Transactions | Order value field | `amount_field` | Field | Value of each order, summed for the monetary score. From input 1. |
| Transactions | Order ID field (optional) | `order_field` | Field | Frequency counts distinct order IDs. Leave empty to count rows (one row per order). From input 1. |
| Scoring | Analysis date | `analysis_date` | Text | Recency is measured to this date, such as 2025-12-31. Leave empty for the day after the latest transaction. |
| Scoring | Score bands | `bins` | Whole number | 5 gives scores 1 to 5 (quintiles). Default: 5. |
| Scoring | Text dates are day first | `day_first` | Tick box | Read 03/04/2025 as 3 April. Default: ticked. |

## Outputs
- **Customer scores** (`customers`): One row per customer: recency, frequency, monetary, average order value, R / F / M scores, RFM score, segment.
- **Segment summary** (`segments`): One row per segment: customers, revenue, shares, averages, description, suggested action.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
