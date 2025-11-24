# Perspective Service - Complete System Logic Documentation

## Table of Contents
1. [System Overview & Architecture](#system-overview--architecture)
2. [Weight Calculation System](#weight-calculation-system)
3. [Modifier System](#modifier-system)
4. [Cascade Removal Logic](#cascade-removal-logic)
5. [Rule Application (apply_to)](#rule-application-apply_to)
6. [Lookthrough Grouping Behavior](#lookthrough-grouping-behavior)
7. [Execution Flow & Order of Operations](#execution-flow--order-of-operations)
8. [AND/OR/NOT Logic in Criteria](#andornot-logic-in-criteria)
9. [Edge Cases & Important Behaviors](#edge-cases--important-behaviors)
10. [Data Types & Null Handling](#data-types--null-handling)
11. [Examples & Common Patterns](#examples--common-patterns)

---

## System Overview & Architecture

### Split Dataframes Architecture
The system uses **two separate dataframes** to process portfolio data:
- **Positions DataFrame**: Contains direct position holdings
- **Lookthroughs DataFrame**: Contains indirect holdings (lookthrough positions)

Both dataframes flow through the pipeline independently until the cascade removal step.

### Lazy Evaluation Model
The system uses **Polars LazyFrames** for maximum performance:
- All operations build an execution graph without executing
- Actual computation happens only at `.collect()` calls
- This allows Polars to optimize the entire pipeline

### High-Level Data Flow
```
Input Data (Positions + Lookthroughs)
    ↓
Apply PreProcessing Modifiers (filters)
    ↓
Apply Perspective Rules (filters)
    ↓
Apply PostProcessing Modifiers (OR/AND logic)
    ↓
Cascade Removal (remove orphaned lookthroughs)
    ↓
Apply Scaling Modifiers (rescale weights)
    ↓
Output (collect and format)
```

---

## Weight Calculation System

### 1. scale_holdings_to_100_percent

**Purpose**: Rescales position weights to sum to 100% (1.0).

**Formula**:
```
new_weight = position_weight / (sum_of_all_positions + sum_of_essential_lookthroughs)
```

**Implementation** (gemini.py:529-538):
```python
for w in pos_weights:
    denom_expr = pl.col(f"{w}_pos_sum").fill_null(0.0) + pl.col(f"{w}_ess_sum").fill_null(0.0)

    final_positions = final_positions.with_columns(
        pl.when(pl.col("perspective_id").is_in(rescale_pos_pids))
          .then(pl.col(w) / denom_expr)
          .otherwise(pl.col(w))
          .alias(w)
    )
```

**Key Points**:
- Denominator = position sum + **essential_lookthroughs sum ONLY**
- Essential lookthroughs are included because they represent actual holdings
- Grouping: Per (perspective_id + container + sub_portfolio_id)
- Null handling: `.fill_null(0.0)` prevents division errors
- Only applies to perspectives that have this modifier in their active modifier list

**Example**:
```
Positions:     pos_1 (weight=10), pos_2 (weight=20)
Essential LT:  lt_1 (weight=5)
---
Denominator = 10 + 20 + 5 = 35
pos_1_new = 10 / 35 = 0.286
pos_2_new = 20 / 35 = 0.571
lt_1_new = 5 / 35 = 0.143  (essential lookthroughs also scaled by same denominator)
Total = 1.0
```

### 2. scale_lookthroughs_to_100_percent

**Purpose**: Rescales lookthroughs to 100% **per parent group**.

**Formula**:
```
new_weight = lookthrough_weight / sum_of_lookthroughs_for_same_parent_and_sub_portfolio
```

**Implementation** (gemini.py:545-553):
```python
for w in lt_weights:
    total = pl.col(w).sum().over([
        "perspective_id",
        "parent_instrument_id",
        "sub_portfolio_id",
        "record_type"
    ])
    final_lookthroughs = final_lookthroughs.with_columns(
        pl.when(pl.col("perspective_id").is_in(rescale_lt_pids))
          .then(pl.col(w) / total)
          .otherwise(pl.col(w))
          .alias(w)
    )
```

**Key Points**:
- Grouping: Per (perspective_id + parent_instrument_id + sub_portfolio_id + record_type)
- Each parent's lookthroughs are scaled independently
- If you have 2 parents with lookthroughs, total sum across all lookthroughs will be 2.0 (each parent = 1.0)
- Window function: `.sum().over(...)` computes per-group totals without losing row structure

**Example**:
```
Parent pos_1 (instrument_id=101, sub_portfolio=sub_A):
  lt_1 (weight=3.0)
  lt_2 (weight=6.0)

Parent pos_2 (instrument_id=102, sub_portfolio=sub_A):
  lt_3 (weight=4.0)
  lt_4 (weight=8.0)
---
Group 1 (parent=101, sub=sub_A): sum = 9.0
  lt_1_new = 3.0 / 9.0 = 0.333
  lt_2_new = 6.0 / 9.0 = 0.667

Group 2 (parent=102, sub=sub_A): sum = 12.0
  lt_3_new = 4.0 / 12.0 = 0.333
  lt_4_new = 8.0 / 12.0 = 0.667

Total sum = 0.333 + 0.667 + 0.333 + 0.667 = 2.0 (NOT 1.0!)
```

### When Rescaling Happens
- **After all filtering is complete** (PreProcessing + Rules + PostProcessing)
- **After cascade removal** (so orphaned lookthroughs don't affect denominator)
- **Before output** (last step before .collect())

---

## Modifier System

### Modifier Types

There are **3 types of modifiers**:

#### 1. PreProcessing Modifiers
- **Purpose**: Filter data BEFORE perspective rules are applied
- **Execution**: First in the pipeline
- **Logic**: Always uses AND logic (removes data)
- **Examples**:
  - `exclude_simulated_trades`: Removes positions where position_source_type_id = 10
  - `exclude_trade_cash`: Removes positions where liquidity_type_id = 6
  - `exclude_class_positions`: Removes positions where is_class_position = true

#### 2. PostProcessing Modifiers
- **Purpose**: Add data back OR apply additional filters AFTER perspective rules
- **Execution**: After perspective rules, before cascade removal
- **Logic**: Can use OR logic (adds data back) or AND logic (additional filter)
- **Controlled by**: `rule_result_operator` field ("or" or "and")
- **Examples**:
  - `include_all_trade_cash`: Adds back positions where liquidity_type_id = 6 (OR logic)
  - `include_simulated_cash`: Adds back positions where type=10 AND liq=5 (OR logic)

#### 3. Scaling Modifiers
- **Purpose**: Rescale weights to 100%
- **Execution**: Last step, after all filtering and cascade removal
- **No criteria**: These don't filter; they only rescale
- **Examples**:
  - `scale_holdings_to_100_percent`
  - `scale_lookthroughs_to_100_percent`

### Modifier Override System

**Purpose**: Certain modifiers can "override" (remove) other modifiers from execution.

**Implementation** (gemini.py:649-655):
```python
def _apply_overrides(self, mods):
    final = mods.copy()
    for m in mods:
        if m in self.modifier_overrides:
            for bad in self.modifier_overrides[m]:
                if bad in final:
                    final.remove(bad)
    return final
```

**Override Configuration** (gemini.py:310-316):
```python
self.modifier_overrides = {
    "exclude_simulated_trades": [
        "include_all_trade_cash",
        "include_trade_cash_within_perspective"
    ],
    "exclude_simulated_cash": [
        "exclude_perspective_level_simulated_cash",
        "include_simulated_cash"
    ],
    "include_all_trade_cash": [
        "exclude_perspective_level_simulated_cash"
    ],
    "include_trade_cash_within_perspective": [
        "exclude_perspective_level_simulated_cache"
    ],
    "exclude_trade_cash": [
        "exclude_perspective_level_simulated_cash"
    ]
}
```

**How It Works**:
1. Start with perspective's modifier list: `["exclude_simulated_trades", "include_all_trade_cash"]`
2. Check overrides: `exclude_simulated_trades` overrides `include_all_trade_cash`
3. Remove overridden modifiers: Final list = `["exclude_simulated_trades"]`
4. Only `exclude_simulated_trades` is applied

**Example**:
```
Perspective modifiers: ["exclude_simulated_trades", "include_all_trade_cash"]

Step 1: Process exclude_simulated_trades
  - Checks override dict
  - Finds: exclude_simulated_trades overrides ["include_all_trade_cash", ...]
  - Removes "include_all_trade_cash" from active list

Step 2: Final active modifiers = ["exclude_simulated_trades"]

Result: Only exclude_simulated_trades is applied; include_all_trade_cash is ignored
```

---

## Cascade Removal Logic

### What Is Cascade Removal?

When a **position is filtered out**, all of its **child lookthroughs** must also be removed, even if they would pass the filter criteria themselves.

### Why?
Lookthroughs represent holdings WITHIN a parent position. If the parent doesn't exist in the perspective, the lookthroughs are meaningless.

### Implementation (gemini.py:478-489)

```python
# 1. Get all parent positions that survived filtering
valid_parents = final_positions.select([
    "perspective_id",
    "instrument_id",  # This becomes the parent for lookthroughs
    "sub_portfolio_id"
]).unique()

# 2. Apply filtering to lookthroughs independently
processed_lt, rem_lt = self._apply_factor_masks(lt_lf, perspectives, lt_weights, "lookthrough")

# 3. Semi-join: Keep only lookthroughs with valid parents
final_lookthroughs = processed_lt.join(
    valid_parents,
    left_on=["perspective_id", "parent_instrument_id", "sub_portfolio_id"],
    right_on=["perspective_id", "instrument_id", "sub_portfolio_id"],
    how="semi"  # Semi-join: keeps left rows that have a match in right
)
```

### Join Keys

The cascade removal uses a **3-column join**:
- `perspective_id`: Lookthroughs only cascade within same perspective
- `parent_instrument_id` (LT) = `instrument_id` (Position): Links child to parent
- `sub_portfolio_id`: Ensures sub-portfolio consistency

### Example

```
Positions after filtering:
  pos_1: instrument_id=101, sub_portfolio=sub_A  ✓ KEPT
  pos_2: instrument_id=102, sub_portfolio=sub_A  ✗ REMOVED

Lookthroughs after their own filtering:
  lt_1: parent=101, sub_portfolio=sub_A  ✓ parent exists → KEPT
  lt_2: parent=101, sub_portfolio=sub_A  ✓ parent exists → KEPT
  lt_3: parent=102, sub_portfolio=sub_A  ✗ parent removed → CASCADE REMOVED
  lt_4: parent=102, sub_portfolio=sub_A  ✗ parent removed → CASCADE REMOVED

Final lookthroughs: lt_1, lt_2
```

### Edge Case: Lookthrough Passes Filter But Parent Doesn't

```
Position pos_4: liquidity_type_id=6  ✗ REMOVED by filter "liq != 6"
Lookthrough lt_6: parent=pos_4, liquidity_type_id=1  ✓ PASSES filter "liq != 6"

Result: lt_6 is CASCADE REMOVED because pos_4 was removed
```

This is **correct behavior** - lookthroughs cannot exist without their parent.

---

## Rule Application (apply_to)

### Purpose
The `apply_to` attribute controls **which data type** a rule or modifier applies to.

### Valid Values

| Value | Aliases | Applies To | Use Case |
|-------|---------|------------|----------|
| `"both"` | - | Positions AND Lookthroughs | Default; most common |
| `"holding"` | `"positions"` | Positions only | Position-specific filtering |
| `"reference"` | `"lookthroughs"` | Lookthroughs only | Lookthrough-specific filtering |

### Implementation (gemini.py:620-622, 627, 642)

```python
# PreProcessing modifier check
if (mod.apply_to == "holding" and mode != "position") or \
   (mod.apply_to == "reference" and mode == "position"):
    continue  # Skip this modifier

# Perspective rule check
if (rule.apply_to == "holding" and mode != "position") or \
   (rule.apply_to == "reference" and mode == "position"):
    continue  # Skip this rule
```

### How It Works

When processing positions (`mode="position"`):
- `apply_to="both"` → Applied ✓
- `apply_to="holding"` → Applied ✓
- `apply_to="reference"` → Skipped ✗

When processing lookthroughs (`mode="lookthrough"`):
- `apply_to="both"` → Applied ✓
- `apply_to="holding"` → Skipped ✗
- `apply_to="reference"` → Applied ✓

### Example

```json
{
  "rules": [
    {
      "criteria": {"column": "liquidity_type_id", "operator_type": "!=", "value": 6},
      "apply_to": "both"
    }
  ]
}
```

**Effect**:
- Positions: Filter out any position where `liquidity_type_id = 6`
- Lookthroughs: Filter out any lookthrough where `liquidity_type_id = 6`
- Each data type is filtered by its **own** `liquidity_type_id` value

**Important**: Rules apply to each data type's **own attributes**, NOT their parent's attributes.

---

## Lookthrough Grouping Behavior

### Purpose
When scaling lookthroughs to 100%, we need to know **which lookthroughs belong together**.

### Grouping Keys

Lookthroughs are grouped by **4 attributes**:
1. `perspective_id`: Perspectives are independent
2. `parent_instrument_id`: Each parent's lookthroughs scale independently
3. `sub_portfolio_id`: Sub-portfolios scale independently
4. `record_type`: Different lookthrough types scale independently

### Implementation (gemini.py:547)

```python
total = pl.col(w).sum().over([
    "perspective_id",
    "parent_instrument_id",
    "sub_portfolio_id",
    "record_type"
])
```

This is a **window function**: it computes the sum per group but keeps all rows (doesn't collapse).

### Why This Grouping?

**Example scenario**:
```
Position pos_1 has:
  - Essential lookthroughs in sub_A: lt_1, lt_2
  - Essential lookthroughs in sub_B: lt_3
  - Reference lookthroughs in sub_A: lt_4, lt_5
```

These are **4 separate groups**:
1. (parent=pos_1, sub=sub_A, type=essential) → lt_1, lt_2 scale to 100%
2. (parent=pos_1, sub=sub_B, type=essential) → lt_3 scales to 100% (alone)
3. (parent=pos_1, sub=sub_A, type=reference) → lt_4, lt_5 scale to 100%
4. Other parents are independent

### Example Calculation

```
Data:
  lt_1: parent=101, sub=sub_A, type=essential, weight=3.0
  lt_2: parent=101, sub=sub_A, type=essential, weight=6.0
  lt_3: parent=101, sub=sub_B, type=essential, weight=5.0
  lt_4: parent=102, sub=sub_A, type=essential, weight=4.0

Groups:
  Group A: (parent=101, sub=sub_A, type=essential) → sum=9.0
    lt_1_new = 3.0 / 9.0 = 0.333
    lt_2_new = 6.0 / 9.0 = 0.667

  Group B: (parent=101, sub=sub_B, type=essential) → sum=5.0
    lt_3_new = 5.0 / 5.0 = 1.0

  Group C: (parent=102, sub=sub_A, type=essential) → sum=4.0
    lt_4_new = 4.0 / 4.0 = 1.0

Total sum = 0.333 + 0.667 + 1.0 + 1.0 = 3.0
```

Note: Total is 3.0 (not 1.0) because there are 3 independent groups.

---

## Execution Flow & Order of Operations

### Complete Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ INPUT: Positions + Lookthroughs LazyFrames                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Apply PreProcessing Modifiers                      │
│   - exclude_simulated_trades                                │
│   - exclude_trade_cash                                      │
│   - exclude_class_positions                                 │
│   - etc.                                                    │
│   Logic: AND (all must pass)                                │
│   Apply to: Positions and Lookthroughs INDEPENDENTLY        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Apply Perspective Rules                            │
│   - Each perspective has 1+ rules                           │
│   - Rules combined with AND/OR based on condition_for_next  │
│   - Apply to: Positions and Lookthroughs INDEPENDENTLY      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Apply PostProcessing Modifiers                     │
│   - include_all_trade_cash (OR logic)                       │
│   - include_simulated_cash (OR logic)                       │
│   - Additional filters (AND logic)                          │
│   Logic: OR or AND based on rule_result_operator            │
│   Apply to: Positions and Lookthroughs INDEPENDENTLY        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Cascade Removal                                     │
│   - Semi-join lookthroughs with valid parent positions      │
│   - Remove orphaned lookthroughs                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Apply Scaling Modifiers                            │
│   - scale_holdings_to_100_percent                           │
│   - scale_lookthroughs_to_100_percent                       │
│   - Rescale weights per group                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Collect and Format Output                          │
│   - .collect() triggers Polars execution                    │
│   - Partition by perspective_id and container               │
│   - Format as nested dictionary                             │
└─────────────────────────────────────────────────────────────┘
```

### Filter Logic Building (gemini.py:613-647)

The `_build_filter_logic` method constructs a single filter expression per perspective:

```python
# Start with: "weight columns must not be null"
expr = pl.lit(True)
for w in weights:
    expr = expr & pl.col(w).is_not_null()

# Add PreProcessing modifiers (AND logic)
for m in mods:
    if m in compiled_modifiers and modifier_type == "PreProcessing":
        expr = expr & evaluate_criteria(m.criteria)

# Add Perspective Rules (AND/OR based on condition_for_next_rule)
rule_expr = None
for rule in perspective_rules:
    curr = evaluate_criteria(rule.criteria)
    if rule_expr is None:
        rule_expr = curr
    else:
        # Combine with previous rule using AND or OR
        rule_expr = rule_expr | curr if prev.condition_for_next_rule == "Or" else rule_expr & curr

# Add PostProcessing modifiers (OR or AND logic)
for m in mods:
    if m in compiled_modifiers and modifier_type == "PostProcessing":
        savior = evaluate_criteria(m.criteria)
        rule_expr = rule_expr | savior if m.rule_result_operator == "or" else rule_expr & savior

# Combine everything
final_expr = expr & rule_expr
```

### Key Points

1. **PreProcessing is AND**: All PreProcessing modifiers must pass
2. **Rules use condition_for_next_rule**: Can be AND or OR between rules
3. **PostProcessing can be OR**: Can add data back with `rule_result_operator="or"`
4. **Cascade happens AFTER all filtering**: Ensures correct parent-child relationships
5. **Scaling happens LAST**: Works on final filtered data

---

## AND/OR/NOT Logic in Criteria

### Nested Structure

Criteria can be deeply nested with `and`, `or`, and `not` operators.

### Implementation (gemini.py:68-84)

```python
def evaluate_criteria(cls, criteria: Dict[str, Any]) -> pl.Expr:
    # AND logic
    if "and" in criteria:
        sub = criteria["and"]
        if not sub: return pl.lit(True)  # Empty AND = True (short-circuit)
        expr = cls.evaluate_criteria(sub[0])
        for crit in sub[1:]:
            expr = expr & cls.evaluate_criteria(crit)
        return expr

    # OR logic
    if "or" in criteria:
        sub = criteria["or"]
        if not sub: return pl.lit(False)  # Empty OR = False (short-circuit)
        expr = cls.evaluate_criteria(sub[0])
        for crit in sub[1:]:
            expr = expr | cls.evaluate_criteria(crit)
        return expr

    # NOT logic
    if "not" in criteria:
        return ~cls.evaluate_criteria(criteria["not"])

    # Base case: single condition
    # ... operator evaluation ...
```

### Short-Circuit Behavior

- **Empty AND**: `{"and": []}` → Returns `True` (vacuous truth)
- **Empty OR**: `{"or": []}` → Returns `False` (no conditions satisfied)

### Examples

#### Example 1: Simple AND
```json
{
  "and": [
    {"column": "liquidity_type_id", "operator_type": "!=", "value": 6},
    {"column": "position_source_type_id", "operator_type": "!=", "value": 10}
  ]
}
```
**SQL equivalent**: `WHERE liquidity_type_id != 6 AND position_source_type_id != 10`

#### Example 2: OR Logic
```json
{
  "or": [
    {"column": "liquidity_type_id", "operator_type": "=", "value": 1},
    {"column": "liquidity_type_id", "operator_type": "=", "value": 2}
  ]
}
```
**SQL equivalent**: `WHERE liquidity_type_id = 1 OR liquidity_type_id = 2`

#### Example 3: NOT with AND (De Morgan's Law)
```json
{
  "not": {
    "and": [
      {"column": "position_source_type_id", "operator_type": "=", "value": 10},
      {"column": "liquidity_type_id", "operator_type": "=", "value": 5}
    ]
  }
}
```
**SQL equivalent**: `WHERE NOT (position_source_type_id = 10 AND liquidity_type_id = 5)`

**De Morgan equivalent**: `WHERE position_source_type_id != 10 OR liquidity_type_id != 5`

**Important**: The JSON uses `NOT (A AND B)` which is equivalent to `(NOT A) OR (NOT B)`, but the modifier definition should use:
```json
{
  "or": [
    {"column": "position_source_type_id", "operator_type": "!=", "value": 10},
    {"column": "liquidity_type_id", "operator_type": "!=", "value": 5}
  ]
}
```

#### Example 4: Nested AND/OR
```json
{
  "and": [
    {"column": "asset_class", "operator_type": "!=", "value": "Cash"},
    {
      "or": [
        {"column": "liquidity_type_id", "operator_type": "=", "value": 1},
        {"column": "liquidity_type_id", "operator_type": "=", "value": 3}
      ]
    }
  ]
}
```
**SQL equivalent**: `WHERE asset_class != 'Cash' AND (liquidity_type_id = 1 OR liquidity_type_id = 3)`

---

## Edge Cases & Important Behaviors

### 1. Empty Results After Filtering

**Scenario**: All positions or lookthroughs are filtered out.

**Behavior**:
- LazyFrames handle empty flows automatically
- No crashes or errors
- Output contains empty dictionaries for affected perspectives

**Example**:
```python
# If all positions filtered:
output = {
  "123": {
    "container_A": {
      "positions": {},  # Empty
      "essential_lookthroughs": {}  # Also empty (cascade removal)
    }
  }
}
```

### 2. Division by Zero in Scaling

**Scenario**: Attempting to scale when sum of weights is 0.

**Protection** (gemini.py:531):
```python
denom_expr = pl.col(f"{w}_pos_sum").fill_null(0.0) + pl.col(f"{w}_ess_sum").fill_null(0.0)
```

**Behavior**:
- `.fill_null(0.0)` replaces NULL with 0
- If denominator is 0, Polars produces `inf` or `null` (depends on numerator)
- Real-world: This shouldn't happen (positions always have weight > 0 if they exist)

### 3. Null Weight Handling

**Scenario**: A position has `weight = NULL`.

**Filtering** (gemini.py:615):
```python
expr = pl.lit(True)
for w in weights:
    expr = expr & pl.col(w).is_not_null()
```

**Behavior**:
- All NULL weights are filtered out at the start of filter building
- Rows with NULL weights never make it through the pipeline

### 4. Orphaned Lookthroughs

**Scenario**: A lookthrough's parent doesn't exist in input data.

**Behavior**:
- Cascade removal handles this via semi-join
- Lookthroughs without valid parents are removed
- No errors or warnings

### 5. Modifier Override Order

**Scenario**: Multiple modifiers could override each other.

**Behavior**:
- Overrides are processed in the order modifiers appear in the list
- First modifier's overrides are applied, then second, etc.
- **Example**:
  ```python
  mods = ["A", "B", "C"]
  A overrides B
  B overrides C

  Step 1: Process A → removes B
  Step 2: Process C (B is gone, so B's overrides don't apply)
  Final: ["A", "C"]
  ```

### 6. Nested In/NotIn Criteria

**Scenario**: `In` operator with nested criteria (dynamic value list).

**Implementation** (gemini.py:97-108):
```python
if operator_type in ["In", "NotIn"] and isinstance(parsed_value, NestedCriteria):
    # Execute nested criteria to get matching values
    matching_values = (
        lf.filter(evaluate_criteria(parsed_value.criteria))
        .select(column)
        .filter(pl.col(column).is_not_null())
        .collect().to_series().unique().to_list()
    )
    if operator_type == "In":
        return pl.col(column).is_in(matching_values) if matching_values else pl.lit(False)
    else:
        return ~pl.col(column).is_in(matching_values) if matching_values else pl.lit(True)
```

**Behavior**:
- Nested criteria is executed **at criteria evaluation time**
- Collects matching values dynamically
- If no matches found: `In` returns `False`, `NotIn` returns `True`

**Example**:
```json
{
  "column": "instrument_id",
  "operator_type": "In",
  "value": {
    "column": "liquidity_type_id",
    "operator_type": "=",
    "value": 1
  }
}
```
This finds all `instrument_id` values where `liquidity_type_id = 1`, then filters the current data to those IDs.

### 7. Scaling with Multiple Sub-Portfolios

**Scenario**: A position has lookthroughs in sub_A and sub_B.

**Behavior**:
- Each sub-portfolio scales independently
- Total sum across all sub-portfolios will be > 1.0

**Example**:
```
Position pos_1:
  Lookthroughs in sub_A: lt_1 (0.6), lt_2 (0.4) → sum = 1.0
  Lookthroughs in sub_B: lt_3 (0.7), lt_4 (0.3) → sum = 1.0

Total lookthrough weight for pos_1 = 2.0
```

### 8. apply_to with Mixed Types

**Scenario**: A rule with `apply_to="both"` but column only exists in one data type.

**Behavior**:
- Polars will error if column doesn't exist
- **Solution**: Use separate rules with `apply_to="holding"` and `apply_to="reference"`
- Or ensure all shared columns exist in both data types

---

## Data Types & Null Handling

### Sentinel Values (gemini.py:18-19)

```python
INT_NULL = -2147483648
FLOAT_NULL = -2147483648.49438
```

**Purpose**: Represent NULL values in systems that don't support native NULL.

**Usage**:
- These are legacy values; modern system uses Polars native NULL
- If input data contains these sentinel values, they should be converted to NULL:
  ```python
  df = df.with_columns([
      pl.when(pl.col("int_col") == INT_NULL).then(None).otherwise(pl.col("int_col")).alias("int_col")
  ])
  ```

### Polars NULL Handling

Polars has native NULL support:
- `.is_null()` → Check if value is NULL
- `.is_not_null()` → Check if value is NOT NULL
- `.fill_null(value)` → Replace NULL with a value

### Weight Column Types

All weight columns are **Float64** (doubles).

### Boolean Columns

Polars uses native booleans:
- `True` / `False` (not 1/0)
- Comparisons return boolean expressions

---

## Examples & Common Patterns

### Pattern 1: Exclude Specific Positions, Include Exceptions

**Requirement**: Exclude all simulated trades EXCEPT trade cash.

**Solution**: Use PreProcessing + PostProcessing with OR logic.

```json
{
  "modifiers": [
    "exclude_simulated_trades",  // PreProcessing: removes all type=10
    "include_all_trade_cash"     // PostProcessing: adds back type=10 AND liq=6
  ]
}
```

**Execution**:
1. PreProcessing removes: `position_source_type_id = 10` → All simulated trades gone
2. PostProcessing adds back: `position_source_type_id = 10 AND liquidity_type_id = 6` → Only trade cash returns

**Result**: Only trade cash (type=10, liq=6) is kept from simulated trades.

### Pattern 2: Multiple Rules with OR Logic

**Requirement**: Keep positions where `asset_class = "Equity"` OR `asset_class = "Fixed Income"`.

**Solution**: Use multiple rules with `condition_for_next_rule="Or"`.

```json
{
  "rules": [
    {
      "criteria": {"column": "asset_class", "operator_type": "=", "value": "Equity"},
      "apply_to": "both",
      "condition_for_next_rule": "Or"
    },
    {
      "criteria": {"column": "asset_class", "operator_type": "=", "value": "Fixed Income"},
      "apply_to": "both"
    }
  ]
}
```

### Pattern 3: Rescale Only Positions

**Requirement**: Scale positions to 100%, but leave lookthroughs at original weights.

**Solution**: Use only `scale_holdings_to_100_percent` modifier.

```json
{
  "modifiers": [
    "scale_holdings_to_100_percent"
  ]
}
```

**Result**: Positions sum to 1.0, lookthroughs retain original weights.

### Pattern 4: Filter Positions One Way, Lookthroughs Another

**Requirement**: Exclude class positions, but keep class lookthroughs.

**Solution**: Create separate modifiers with different `apply_to` values.

```json
{
  "exclude_class_positions_only": {
    "type": "PreProcessingFilteringModifier",
    "rule": {
      "criteria": {"column": "is_class_position", "operator_type": "!=", "value": true},
      "apply_to": "holding"  // Only applies to positions
    }
  }
}
```

### Pattern 5: Debugging Weight Calculations

**Step-by-step verification**:

1. **Check input weights**:
   ```python
   print(positions_df.select(["identifier", "weight"]).collect())
   ```

2. **Check after filtering**:
   ```python
   print(final_positions.select(["identifier", "weight"]).collect())
   ```

3. **Check scaling denominator** (add debug column):
   ```python
   final_positions = final_positions.with_columns(
       (pl.col("weight_pos_sum") + pl.col("weight_ess_sum")).alias("denominator")
   )
   ```

4. **Verify lookthrough grouping**:
   ```python
   final_lookthroughs.group_by([
       "parent_instrument_id",
       "sub_portfolio_id"
   ]).agg(pl.col("weight").sum())
   ```

### Pattern 6: Understanding Cascade Removal Impact

**Test**:
```python
# Before cascade
print(f"Positions: {len(final_positions.collect())}")
print(f"Lookthroughs before cascade: {len(processed_lt.collect())}")

# After cascade
print(f"Lookthroughs after cascade: {len(final_lookthroughs.collect())}")

# Difference = cascade-removed lookthroughs
```

---

## Quick Reference Tables

### Modifier Types at a Glance

| Type | When | Logic | Common Use |
|------|------|-------|------------|
| PreProcessing | Before rules | AND (filter) | Exclude unwanted data |
| PostProcessing | After rules | OR (add back) or AND | Include exceptions |
| Scaling | After cascade | N/A (rescale) | Normalize to 100% |

### apply_to Values

| Value | Positions | Lookthroughs |
|-------|-----------|--------------|
| `"both"` | ✓ | ✓ |
| `"holding"` | ✓ | ✗ |
| `"reference"` | ✗ | ✓ |

### Operator Reference

| Operator | SQL Equivalent | Example |
|----------|----------------|---------|
| `=` or `==` | `=` | `{"column": "id", "operator_type": "=", "value": 5}` |
| `!=` | `!=` | `{"column": "id", "operator_type": "!=", "value": 5}` |
| `>` | `>` | `{"column": "weight", "operator_type": ">", "value": 0.1}` |
| `<` | `<` | `{"column": "weight", "operator_type": "<", "value": 0.5}` |
| `>=` | `>=` | `{"column": "weight", "operator_type": ">=", "value": 0.1}` |
| `<=` | `<=` | `{"column": "weight", "operator_type": "<=", "value": 0.5}` |
| `In` | `IN (...)` | `{"column": "id", "operator_type": "In", "value": [1, 2, 3]}` |
| `NotIn` | `NOT IN (...)` | `{"column": "id", "operator_type": "NotIn", "value": [4, 5]}` |
| `Between` | `BETWEEN` | `{"column": "weight", "operator_type": "Between", "value": [0.1, 0.5]}` |
| `NotBetween` | `NOT BETWEEN` | `{"column": "weight", "operator_type": "NotBetween", "value": [0, 0.1]}` |
| `Like` | `LIKE` | `{"column": "name", "operator_type": "Like", "value": "%Corp%"}` |
| `NotLike` | `NOT LIKE` | `{"column": "name", "operator_type": "NotLike", "value": "%Cash%"}` |
| `IsNull` | `IS NULL` | `{"column": "optional_field", "operator_type": "IsNull"}` |
| `IsNotNull` | `IS NOT NULL` | `{"column": "required_field", "operator_type": "IsNotNull"}` |

---

## Summary

This document provides a complete reference for understanding the perspective service system logic. Key takeaways:

1. **Weight Scaling**:
   - Holdings scale by total (positions + essential LT)
   - Lookthroughs scale per parent group

2. **Modifiers**:
   - PreProcessing filters first (AND logic)
   - PostProcessing adds back or filters after rules (OR or AND)
   - Scaling rescales at the end

3. **Cascade Removal**:
   - Lookthroughs removed when parent positions filtered
   - Uses semi-join on (perspective_id, parent_id, sub_portfolio_id)

4. **Execution Order**:
   - PreProcessing → Rules → PostProcessing → Cascade → Scaling → Output

5. **apply_to**:
   - Controls which data type (positions/lookthroughs/both) a rule applies to
   - Each data type is filtered by its **own** attributes

6. **AND/OR Logic**:
   - Fully supports nested criteria
   - Empty AND = True, Empty OR = False
   - NOT uses De Morgan's laws

With this knowledge, you can confidently understand, debug, and extend the perspective service system.
