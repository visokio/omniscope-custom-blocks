# Linear Optimisation

Solves linear and integer programmes given as data (variables with objective and bounds, constraints in long format) with the HiGHS solver: optimal plan, slack, binding constraints and shadow prices.

Finds the **best plan** under constraints: the product mix that maximises profit within machine, labour and material capacity; the cheapest blend that meets a specification; the staffing that covers demand at least cost. The model is given as **data**, so planners can maintain it in a spreadsheet or database:

**Input 1, decision variables**: one row per variable (product, route, shift) with its objective coefficient (profit or cost per unit), and optionally a lower bound (minimum, contract commitments), an upper bound (maximum demand) and a whole-number flag.

**Input 2, constraints** in long format: one row per constraint and variable with the coefficient (for example hours per unit), plus the constraint's sense (`<=`, `>=` or `=`) and limit (capacity), repeated on each row.

Outputs:
- **Solution**: the optimal value of every variable, its contribution to the objective, whether it sits at a bound, and its reduced cost
- **Constraints**: amount used, limit, slack, **binding** yes / no and the **shadow price** (how much the objective would improve per extra unit of that resource; continuous models only)
- **Summary**: status (optimal, infeasible, unbounded), objective value, counts and the solver message

Uses the HiGHS solver in scipy (installed automatically through the block's dependencies).

## Language
Python

## Inputs
- **Input 1**: decision variables (name, objective coefficient, optional bounds and integer flag).
- **Input 2**: constraints in long format (constraint, variable, coefficient, sense, limit).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Objective | Goal | `objective_sense` | Choice | Whether the best plan has the highest or the lowest objective. Choices: Maximise (profit, output); Minimise (cost, time). Default: Maximise (profit, output). |
| Variables (input 1) | Variable name | `var_name_field` | Field | Names each decision variable, such as a product to make. From input 1. |
| Variables (input 1) | Objective coefficient | `objective_field` | Field | Profit or cost per unit. From input 1. |
| Variables (input 1) | Lower bound (optional) | `lower_field` | Field | Minimum value; empty means 0. From input 1. |
| Variables (input 1) | Upper bound (optional) | `upper_field` | Field | Maximum value; empty means no limit. From input 1. |
| Variables (input 1) | Whole-number flag (optional) | `integer_field` | Field | Yes / true / 1 for variables that must be whole numbers. From input 1. |
| Variables (input 1) | All variables are whole numbers | `all_integer` | Tick box | Default: unticked. |
| Constraints (input 2) | Constraint name | `constraint_field` | Field | Names each constraint, such as a resource; one row per variable that uses it. From input 2. |
| Constraints (input 2) | Variable | `constraint_var_field` | Field | Must match the variable names in input 1. From input 2. |
| Constraints (input 2) | Coefficient | `coefficient_field` | Field | Amount of the constraint used by one unit of the variable. From input 2. |
| Constraints (input 2) | Sense | `sense_field` | Field | <=, >= or = (also: at most, at least, exactly). From input 2. |
| Constraints (input 2) | Limit | `limit_field` | Field | Right-hand side, such as capacity. From input 2. |
| Constraints (input 2) | Time limit (seconds) | `time_limit` | Decimal number | Default: 60.0. |

## Outputs
- **Solution** (`solution`): Input 1 with Optimal Value, Objective Contribution, At Bound, Reduced Cost.
- **Constraints** (`constraints`): Per constraint: sense, limit, used, slack, binding, shadow price.
- **Summary** (`summary`): Status, objective value, variable and constraint counts, solver message.

## Dependencies
scipy

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
