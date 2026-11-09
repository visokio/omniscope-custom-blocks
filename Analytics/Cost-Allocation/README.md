# Cost Allocation

Apportions cost pools to departments, products or customers by drivers, with penny-exact largest-remainder rounding and a list of unallocated pools.

Apportions **cost pools** (IT, facilities, HR, finance) to **receivers** (departments, products, customers, sites) in proportion to a **driver** (headcount, floor area, users, tickets, revenue).

- Each pool names its own driver; a default driver can apply to pools without one
- Driver values in **long form** (receiver, driver, value) or **wide form** (one numeric column per driver)
- **Penny-exact rounding** (largest-remainder method): the allocations of every pool add up to the pool exactly, at the number of decimals you choose
- Pools that cannot be allocated (no driver values, or an amount that is not a number) are listed with the reason

Outputs: every allocation with share and driver value, a summary per receiver (total, from each pool, share of all costs), and the unallocated pools.

## Language
Python

## Inputs
- **Input 1**: cost pools (name, amount, driver).
- **Input 2**: driver values per receiver (long or wide form).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Cost pools (input 1) | Pool name | `pool_field` | Field | Names each cost pool, such as IT or Facilities. From input 1. |
| Cost pools (input 1) | Amount | `amount_field` | Field | The cost of each pool to be shared out. From input 1. |
| Cost pools (input 1) | Driver for the pool (optional) | `pool_driver_field` | Field | Which driver shares out this pool, such as Headcount or Floor Area. From input 1. |
| Drivers (input 2) | Receiver | `receiver_field` | Field | The department, product or customer receiving a share. From input 2. |
| Drivers (input 2) | Driver name (long form) | `driver_field` | Field | Leave empty for wide form (one column per driver). From input 2. |
| Drivers (input 2) | Driver value (long form) | `value_field` | Field | Size of the driver for each receiver, when drivers come one per row. From input 2. |
| Options | Default driver | `default_driver` | Text | For pools without one. |
| Options | Decimals | `decimals` | Whole number | 2 = to the penny. Default: 2. |

## Outputs
- **Allocations** (`allocations`): Per pool and receiver: driver, driver value, share, allocated amount.
- **Receivers** (`receivers`): Per receiver: total allocated, from each pool, share of all costs.
- **Unallocated** (`unallocated`): Pools that could not be allocated, with the reason.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
