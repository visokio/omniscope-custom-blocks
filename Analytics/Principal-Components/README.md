# Principal Component Analysis

PCA on numeric fields: explained variance, loadings and correlations, automatic or fixed number of components, and scores per row.

**Principal Component Analysis** summarises many correlated numeric fields with a few components: for building indices, segmentation, score plots of similar items, and reducing predictors before modelling.

- **Standardised** (correlation) PCA by default, so fields in different units count equally; or covariance PCA on centred values
- Components kept: a **fixed number**, or automatically (eigenvalue above 1 for standardised data, otherwise enough for a target share of variance)
- **Loadings** with each field's correlation with each component, ranked, and a short label of the main fields per component
- **Scores** for every row, plus an *unexplained distance* showing rows the kept components describe poorly (unusual profiles)
- Signs are fixed (largest loading positive) so results are repeatable

Rows with a missing value in a chosen field are left out of the fit and get no score.

## Language
Python

## Inputs
- **Input**: data with numeric fields.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | Numeric fields | `fields` | Fields | Leave empty to use every numeric field. From input 1. |
|  | Standardise fields (correlation PCA) | `standardise` | Tick box | Scales each field to unit variance first, so fields in large units do not dominate. Untick for covariance PCA. Default: ticked. |
|  | Components to keep | `components` | Whole number | 0 = automatic. Default: 0. |
|  | Variance to explain (covariance PCA, automatic) | `variance_target` | Decimal number | Default: 0.8. |

## Outputs
- **Components** (`components`): Per component: eigenvalue, share and cumulative share of variance, kept.
- **Loadings** (`loadings`): Per kept component and field: loading, correlation with the component, rank, main fields.
- **Scores** (`scores`): The input with a score per kept component and the unexplained distance.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the core Reduce Dimensions block

Use the core **Reduce Dimensions** block to compress numeric fields with PCA. Use this block when you need the explained variance and the loadings as tables, to report which fields drive each component.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
