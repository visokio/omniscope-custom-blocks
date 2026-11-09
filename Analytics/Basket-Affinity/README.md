# Basket Affinity Matrix

Measures how often every pair of items is bought together (support, confidence, lift, Jaccard) from basket data, with each item's strongest partners.

Which products are bought together, and how much more often than chance? From transaction lines (one row per basket and item), the block measures **every pair** of the most common items:

- **Baskets with both**, **support** (share of all baskets containing both)
- **Confidence** in both directions: of baskets with A, the share that also have B (and the reverse)
- **Lift**: how many times more often the pair occurs than if the items were independent (above 1 = bought together, below 1 = bought apart)
- **Jaccard** similarity, and an association label

The item summary lists each item's baskets, support and its **strongest partners by lift**. Items are limited to the most frequent ones (50 by default) so the matrix stays readable; pairs below a minimum number of shared baskets are left out to avoid noisy lifts.

A compact, all-pairs view for range, layout and cross-sell decisions; Omniscope's native Basket Analysis block produces association rules for larger item sets.

## Language
Python

## Inputs
- **Input 1**: transaction lines, one row per basket (order) and item.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Data | Basket / order ID | `basket_field` | Field | Identifies a basket: rows with the same value were bought together. From input 1. |
| Data | Item / product | `item_field` | Field | The item in each row, such as a product name or SKU. From input 1. |
| Filters | Most frequent items to include | `max_items` | Whole number | Only this many of the most often bought items are paired, which keeps the output readable. Default: 50. |
| Filters | Minimum baskets per item | `min_item_baskets` | Whole number | Default: 5. |
| Filters | Minimum baskets per pair | `min_pair_baskets` | Whole number | Pairs seen together fewer times are left out. Default: 3. |
| Filters | Partners listed per item | `top_partners` | Whole number | Default: 3. |

## Outputs
- **Item pairs** (`pairs`): One row per item pair: baskets with both, support, confidence both ways, lift, Jaccard, association.
- **Item summary** (`items`): Per item: baskets, support and strongest partners by lift.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the core Basket Analysis block

Use the core **Basket Analysis** block for association rules: which items predict which. Use this block when you want the full item-by-item matrix (support, confidence, lift, Jaccard) to draw as a heat map or filter in a report.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
