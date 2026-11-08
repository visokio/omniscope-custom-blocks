# Product Recommendations

Item-to-item recommendations from purchase history: top new products per customer with the reason, and similar products per product.

**"Customers who bought X also bought Y"**, turned into a ranked list of products each customer has not bought yet.

- **Item-to-item collaborative filtering**: two products are similar when the same customers buy them (cosine similarity), with optional **shrinkage** so pairs seen with few customers count less
- A customer's score for a product is the sum of its similarity to everything they bought; already-bought products are left out
- Every recommendation says **"because you bought"** which product, for explainable offers and emails
- The **most similar products per product**, for "you may also like" on a product page

Products bought by fewer customers than the minimum are left out. Works from a plain list of purchases (customer, product); repeats are ignored. Handles up to 8,000 products.

## Language
Python

## Inputs
- **Input**: purchases with a customer field and a product field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | Customer field | `customer_field` | Field | From input 1. |
|  | Product field | `product_field` | Field | From input 1. |
|  | Recommendations per customer | `top_n` | Whole number | Default: 5. |
|  | Similar products per product | `similar_per_product` | Whole number | 0 = none. Default: 10. |
|  | Minimum customers per product | `min_customers` | Whole number | Default: 5. |
|  | Shrinkage | `shrinkage` | Decimal number | 0 = none; 10 down-weights pairs bought together by few customers. Default: 10.0. |
|  | Leave out products already bought | `exclude_bought` | Tick box | Default: ticked. |

## Outputs
- **Recommendations** (`recommendations`): Per customer: rank, recommended product, score, because you bought, similarity, products bought.
- **Similar products** (`similar`): Per product: similar products with similarity and customers who bought both.
- **Coverage** (`coverage`): one record: Customers, Customers With Recommendations, Products (every distinct product in the purchases), Products Scored and Products Left Out (too few customers), which add up to Products, Products Recommended At Least Once, and Purchases Used.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
