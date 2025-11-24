# Original Perspective Service Formulas
## Reference from core_perspective_functions/

This document contains the exact formulas and logic from the original perspective service implementation in `core_perspective_service/core_perspective_functions/`. These formulas serve as the **ground truth** for calculating expected values in tests.

---

## Table of Contents
1. [Exposure Factor (Per-Row Scaling)](#exposure-factor-per-row-scaling)
2. [scale_holdings_to_100_percent](#scale_holdings_to_100_percent)
3. [rescale_lookthroughs_to_100_percent](#rescale_lookthroughs_to_100_percent)
4. [Calculation Order](#calculation-order)
5. [Manual Calculation Examples](#manual-calculation-examples)

---

## Exposure Factor (Per-Row Scaling)

**Source**: `position_and_lookthrough_data.py:725-743`

### Purpose
Applies a per-row multiplier (exposure_factor) to positions or lookthroughs that match specific criteria.

### Formula
```
For each position/lookthrough where criteria matches:
    new_weight = original_weight * exposure_factor

If multiple exposure factors applied (chained):
    cumulative_exposure_factor = exposure_factor_1 * exposure_factor_2 * ...
    new_weight = original_weight * cumulative_exposure_factor
```

### Implementation Details (Lines 725-743)
```python
def _apply_exposure_factor_to_positions(self, results, positions, scaling_result_label, exposure_factor, weight_labels):
    # Merge results with positions to identify which rows matched criteria
    result_df = positions.merge(results, left_on='identifier', right_on='identifier')

    # Initialize exposure_factor column if not exists
    if not 'exposure_factor' in result_df.columns:
        result_df['exposure_factor'] = np.nan

    # Apply exposure factor CUMULATIVELY (multiplies existing factor if present)
    result_df.loc[result_df[scaling_result_label] == True, 'exposure_factor'] = \
        result_df['exposure_factor'].apply(lambda x: 1 if pd.isnull(x) else x) * exposure_factor

    # Multiply each weight label by the exposure factor
    for label in weight_labels:
        result_df.loc[result_df[scaling_result_label] == True, label] = \
            result_df[label].astype(float) * exposure_factor

    return result_df
```

### Key Points
1. **Cumulative**: If exposure_factor already exists, multiply by it (don't replace)
2. **Conditional**: Only applies to rows where criteria evaluates to True
3. **Multi-weight**: Applies to ALL weight labels (weight, gross_weight, etc.)
4. **Tracking**: Stores cumulative exposure_factor in a column for reference

### Manual Calculation Example
```
Input:
  pos_1: weight=10.0, exposure_factor=NULL
  pos_2: weight=20.0, exposure_factor=NULL

Scaling rule 1: exposure_factor=0.5, applies to all

Step 1: Apply exposure_factor=0.5
  pos_1: exposure_factor = 1 * 0.5 = 0.5, weight = 10.0 * 0.5 = 5.0
  pos_2: exposure_factor = 1 * 0.5 = 0.5, weight = 20.0 * 0.5 = 10.0

Output:
  pos_1: weight=5.0, exposure_factor=0.5
  pos_2: weight=10.0, exposure_factor=0.5
```

### Chained Exposure Factors Example
```
Input:
  pos_1: weight=10.0

Scaling rule 1: exposure_factor=0.8 (applies to all)
Scaling rule 2: exposure_factor=1.25 (applies to all)

Step 1: Apply first scaling rule
  pos_1: exposure_factor = 1 * 0.8 = 0.8, weight = 10.0 * 0.8 = 8.0

Step 2: Apply second scaling rule
  pos_1: exposure_factor = 0.8 * 1.25 = 1.0, weight = 8.0 * 1.25 = 10.0

Output:
  pos_1: weight=10.0, exposure_factor=1.0
```

---

## scale_holdings_to_100_percent

**Source**: `position_and_lookthrough_data.py:885-900`

### Purpose
Rescales position weights so the total (positions + essential lookthroughs) sums to 100% (1.0).

### Formula
```
positions_to_rescale = concat(positions, essential_lookthroughs)
denominator = sum(positions_to_rescale[weight_labels])

For each position:
    new_weight = position_weight / denominator
```

### Implementation Details (Lines 885-900)
```python
def _rescale_positions_to_100_percent(self):
    # Determine which weight labels to rescale
    rescale_labels = [k for k in self._associated_position_scaling_weight_labels.keys()]

    # CRITICAL: Include essential_lookthroughs in denominator calculation
    positions_to_rescale = self._position_data
    if self._lookthroughs and 'essential_lookthroughs' in self._lookthroughs:
        positions_to_rescale = pd.concat([positions_to_rescale, self._lookthroughs['essential_lookthroughs']])

    # Rescale positions (divide by sum, with zero protection)
    self._position_data.loc[:, rescale_labels] = \
        self._position_data[rescale_labels] / \
        positions_to_rescale[rescale_labels].sum().transform(lambda x: x if x != 0 else 1)

    return
```

### Key Points
1. **Denominator includes essential_lookthroughs**: This is CRITICAL
2. **Zero protection**: If sum is 0, use 1 to avoid division by zero
3. **Only positions are rescaled**: Lookthroughs are NOT rescaled by this modifier
4. **Multi-weight**: Applies to all weight labels

### Grouping
- **No explicit grouping** in original code (operates on entire dataframe)
- **In gemini.py**: Grouping is ALWAYS by `(perspective_id, container, sub_portfolio_id)`
- **IMPORTANT**: sub_portfolio_id is REQUIRED in gemini.py (not optional like in old code)

### Manual Calculation Example
```
Input:
  pos_1: weight=20.0
  pos_2: weight=30.0
  lt_1: weight=10.0 (essential_lookthroughs, parent=pos_1)

Step 1: Calculate denominator
  denominator = sum(positions) + sum(essential_lookthroughs)
  denominator = (20.0 + 30.0) + (10.0) = 60.0

Step 2: Rescale positions
  pos_1_new = 20.0 / 60.0 = 0.333333
  pos_2_new = 30.0 / 60.0 = 0.500000

Step 3: Lookthroughs NOT rescaled
  lt_1_new = 10.0 (unchanged)

Output:
  pos_1: weight=0.333333
  pos_2: weight=0.500000
  lt_1: weight=10.0

Verification:
  position_sum = 0.333333 + 0.500000 = 0.833333
  total_sum = 0.833333 + 10.0 = 10.833333

NOTE: Positions do NOT sum to 1.0 by themselves!
      Positions + essential_lookthroughs were divided by their combined sum.
```

---

## rescale_lookthroughs_to_100_percent

**Source**: `position_and_lookthrough_data.py:839-865`

### Purpose
Rescales lookthroughs to 100% **per parent group**.

### Formula

**Original implementation**:
```
If sub_portfolio_id exists:
    Group by (parent_instrument_id, sub_portfolio_id)
Else:
    Group by (parent_instrument_id)
```

**gemini.py implementation (NEW REQUIREMENT)**:
```
ALWAYS Group by (perspective_id, parent_instrument_id, sub_portfolio_id, record_type)
```

**Note**: sub_portfolio_id is REQUIRED in gemini.py (all test data must include it)

**Calculation**:
```
For each group:
    denominator = sum(lookthroughs_in_group[weight_labels])

    For each lookthrough in group:
        new_weight = lookthrough_weight / denominator
```

### Implementation Details (Lines 839-865)
```python
def rescale_lookthroughs_to_100_percent(self, lookthrough_name, datasets_for_rescaling, modifier_rule_criteria, perspective_id):
    # Evaluate criteria against positions to find matching parents
    rule_result = self._evaluate_rule_results(modifier_rule_criteria, datasets_for_rescaling, ...)

    # Get parent instrument_ids that matched the rule
    parents_which_match_the_rule = rule_result['instrument_id'][rule_result['result'] == True].values.tolist()

    if not parents_which_match_the_rule:
        return

    # CRITICAL: Group by parent_instrument_id AND sub_portfolio_id if it exists
    if 'sub_portfolio_id' in self._lookthroughs[lookthrough_name].columns:
        # Group by BOTH parent_instrument_id and sub_portfolio_id
        rescale_weights = self._lookthroughs[lookthrough_name][
            self._lookthroughs[lookthrough_name]['parent_instrument_id'].isin(parents_which_match_the_rule)
        ].groupby(['parent_instrument_id', 'sub_portfolio_id'], dropna=False)[self._lookthrough_weight_labels].transform(sum)
    else:
        # Group only by parent_instrument_id
        rescale_weights = self._lookthroughs[lookthrough_name][
            self._lookthroughs[lookthrough_name]['parent_instrument_id'].isin(parents_which_match_the_rule)
        ].groupby(['parent_instrument_id'])[self._lookthrough_weight_labels].transform(sum)

    # Rescale the weights by dividing by group sum
    self._lookthroughs[lookthrough_name].loc[
        self._lookthroughs[lookthrough_name]['parent_instrument_id'].isin(parents_which_match_the_rule),
        self._lookthrough_weight_labels
    ] = self._lookthroughs[lookthrough_name][self._lookthrough_weight_labels] / rescale_weights[self._lookthrough_weight_labels]
```

### Key Points
1. **Per-parent grouping**: Each parent's lookthroughs sum to 100% independently
2. **Sub-portfolio awareness**: If sub_portfolio_id exists, each (parent, sub_portfolio) group sums to 100%
3. **Conditional application**: Only rescales lookthroughs whose parents match the modifier criteria
4. **Multi-weight**: Applies to all lookthrough weight labels

### Manual Calculation Example (With sub_portfolio_id - gemini.py ALWAYS requires this)
```
Input:
  pos_1: instrument_id=101, sub_portfolio_id=sub_A
  pos_2: instrument_id=102, sub_portfolio_id=sub_A
  lt_1: parent=101, sub_portfolio_id=sub_A, weight=3.0
  lt_2: parent=101, sub_portfolio_id=sub_A, weight=6.0
  lt_3: parent=102, sub_portfolio_id=sub_A, weight=4.0
  lt_4: parent=102, sub_portfolio_id=sub_A, weight=8.0

Modifier: Rescale all lookthroughs

Step 1: Group by (parent_instrument_id, sub_portfolio_id)
  Group 1 (parent=101, sub=sub_A): lt_1, lt_2
  Group 2 (parent=102, sub=sub_A): lt_3, lt_4

Step 2: Calculate denominators per group
  Group 1 sum: 3.0 + 6.0 = 9.0
  Group 2 sum: 4.0 + 8.0 = 12.0

Step 3: Rescale per group
  lt_1_new = 3.0 / 9.0 = 0.333333
  lt_2_new = 6.0 / 9.0 = 0.666667
  lt_3_new = 4.0 / 12.0 = 0.333333
  lt_4_new = 8.0 / 12.0 = 0.666667

Output:
  lt_1: weight=0.333333
  lt_2: weight=0.666667
  lt_3: weight=0.333333
  lt_4: weight=0.666667

Verification:
  Group 1 sum: 0.333333 + 0.666667 = 1.0
  Group 2 sum: 0.333333 + 0.666667 = 1.0
  Total sum: 2.0 (NOT 1.0!)
```

### Manual Calculation Example (With sub_portfolio_id)
```
Input:
  pos_1: instrument_id=101
  lt_1: parent=101, sub_portfolio=sub_A, weight=3.0
  lt_2: parent=101, sub_portfolio=sub_A, weight=6.0
  lt_3: parent=101, sub_portfolio=sub_B, weight=5.0

Step 1: Group by (parent_instrument_id, sub_portfolio_id)
  Group 1 (parent=101, sub=sub_A): lt_1, lt_2
  Group 2 (parent=101, sub=sub_B): lt_3

Step 2: Calculate denominators per group
  Group 1 sum: 3.0 + 6.0 = 9.0
  Group 2 sum: 5.0

Step 3: Rescale per group
  lt_1_new = 3.0 / 9.0 = 0.333333
  lt_2_new = 6.0 / 9.0 = 0.666667
  lt_3_new = 5.0 / 5.0 = 1.0

Output:
  lt_1: weight=0.333333
  lt_2: weight=0.666667
  lt_3: weight=1.0

Verification:
  Group 1 sum: 0.333333 + 0.666667 = 1.0
  Group 2 sum: 1.0
  Total sum: 2.0
```

---

## Calculation Order

Based on the original implementation, the order of operations is:

```
1. Apply PreProcessing Modifiers (filtering)
2. Apply Perspective Rules (filtering with AND/OR logic)
3. Apply PostProcessing Modifiers (OR/AND add-back logic)
4. Apply Exposure Factors (per-row scaling)
5. Cascade Removal (remove orphaned lookthroughs)
6. Apply scale_holdings_to_100_percent (if modifier present)
7. Apply rescale_lookthroughs_to_100_percent (if modifier present)
8. Output formatting
```

**CRITICAL**: Exposure factors are applied BEFORE rescaling modifiers!

---

## Manual Calculation Examples

### Example 1: Exposure Factor + scale_holdings_to_100_percent

```
Input:
  pos_1: weight=10.0
  pos_2: weight=20.0
  lt_1: weight=5.0 (essential_lookthroughs, parent=pos_1)

Modifiers:
  1. Exposure factor = 0.75 (applies to all positions)
  2. scale_holdings_to_100_percent

Step 1: Apply exposure factor to positions
  pos_1: weight = 10.0 * 0.75 = 7.5
  pos_2: weight = 20.0 * 0.75 = 15.0
  lt_1: weight = 5.0 (unchanged - exposure factor only on positions)

Step 2: Apply scale_holdings_to_100_percent
  Denominator = sum(positions) + sum(essential_lookthroughs)
  Denominator = (7.5 + 15.0) + 5.0 = 27.5

  pos_1_new = 7.5 / 27.5 = 0.272727
  pos_2_new = 15.0 / 27.5 = 0.545455

Output:
  pos_1: weight=0.272727, exposure_factor=0.75
  pos_2: weight=0.545455, exposure_factor=0.75
  lt_1: weight=5.0

Verification:
  position_sum = 0.272727 + 0.545455 = 0.818182
  total_with_lt = 0.818182 + 5.0 = 5.818182
```

### Example 2: Exposure Factor + rescale_lookthroughs_to_100_percent

```
Input:
  pos_1: instrument_id=101
  lt_1: parent=101, weight=4.0
  lt_2: parent=101, weight=8.0

Modifiers:
  1. Exposure factor = 1.5 (applies to lookthroughs where weight > 5)
  2. rescale_lookthroughs_to_100_percent

Step 1: Apply exposure factor
  lt_1: weight < 5, no exposure factor applied, weight=4.0
  lt_2: weight > 5, exposure factor applied, weight = 8.0 * 1.5 = 12.0

Step 2: Apply rescale_lookthroughs_to_100_percent
  Group by parent=101
  Denominator = 4.0 + 12.0 = 16.0

  lt_1_new = 4.0 / 16.0 = 0.25
  lt_2_new = 12.0 / 16.0 = 0.75

Output:
  lt_1: weight=0.25
  lt_2: weight=0.75, exposure_factor=1.5

Verification:
  sum = 0.25 + 0.75 = 1.0
```

### Example 3: Multiple Lookthrough Types

```
Input:
  pos_1: instrument_id=101
  essential_lt_1: parent=101, weight=5.0
  reference_lt_1: parent=101, weight=3.0
  complete_lt_1: parent=101, weight=2.0

Modifier: scale_holdings_to_100_percent

Step 1: Determine which lookthroughs to include in denominator
  ONLY essential_lookthroughs are included (lines 895-896)

Step 2: Calculate denominator
  Denominator = sum(positions) + sum(essential_lookthroughs)
  Denominator = 0 (no positions) + 5.0 = 5.0

  NOTE: reference_lookthroughs and complete_lookthroughs are NOT included!

Step 3: No positions to rescale (only lookthroughs in this example)

Output:
  essential_lt_1: weight=5.0 (unchanged)
  reference_lt_1: weight=3.0 (unchanged)
  complete_lt_1: weight=2.0 (unchanged)
```

---

## Summary of Key Differences from gemini.py

When calculating expected values for tests, be aware:

1. **Grouping**: Original code doesn't explicitly group by perspective_id/container (assumes single perspective per call). gemini.py processes multiple perspectives in one call, so it groups by (perspective_id, container, sub_portfolio_id).

2. **Lookthrough types**: Original code specifically checks for 'essential_lookthroughs' by name. gemini.py uses record_type='essential_lookthroughs'.

3. **Zero protection**: Original uses `.transform(lambda x: x if x != 0 else 1)`. gemini.py uses `.fill_null(0.0)` and relies on Polars' inf/nan handling.

4. **Exposure factor tracking**: Original stores cumulative exposure_factor in a column. gemini.py multiplies weights directly without storing the factor.

5. **Data structure**: Original uses Pandas wide format. gemini.py uses Polars long format with unpivot/melt.

Despite these implementation differences, the **mathematical results should be identical** when calculated by hand using these formulas.
