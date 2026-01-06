"""Hardcoded supported modifiers for the Perspective Engine."""
from ..constants import INT_NULL

# Hardcoded modifiers - these define filtering and processing rules
SUPPORTED_MODIFIERS = {
    # ==========================================================================
    # PreProcessing - positions matching criteria are REMOVED
    # ==========================================================================
    'exclude_other_net_assets': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 2}
    },
    'exclude_class_positions': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'is_class_position', 'operator_type': '==', 'value': True}
    },
    'exclude_non_class_positions': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'is_class_position', 'operator_type': '==', 'value': False}
    },
    'exclude_future_in_kind_delivery': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'trade_type_id', 'operator_type': '==', 'value': 1}
    },
    'exclude_future_trades': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'and': [
            {'column': 'trade_type_id', 'operator_type': '==', 'value': 4},
            {'column': 'upcoming_trade_date', 'operator_type': '==', 'value': True}
        ]}
    },
    'exclude_future_flows': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'and': [
            {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 3},
            {'column': 'upcoming_trade_date', 'operator_type': '==', 'value': True}
        ]}
    },
    'exclude_pending_stop_trades': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'trade_type_id', 'operator_type': '==', 'value': 2}
    },
    'exclude_pending_limit_trades': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'trade_type_id', 'operator_type': '==', 'value': 3}
    },
    'exclude_potential_red_flags': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'red_flag_exclusion_type_id', 'operator_type': 'IsNotNull'}
    },
    'exclude_simulated_trades': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'or': [
            {'and': [
                {'column': 'position_source_type_id', 'operator_type': '==', 'value': 10},
                {'or': [
                    {'column': 'liquidity_type_id', 'operator_type': '==', 'value': INT_NULL},
                    {'column': 'liquidity_type_id', 'operator_type': '!=', 'value': 5}
                ]}
            ]},
            {'column': 'simulated_trade_id', 'operator_type': 'IsNotNull'}
        ]},
        'override_modifiers': ['include_all_trade_cash', 'include_trade_cash_within_perspective']
    },
    'exclude_simulated_cash': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'and': [
            {'column': 'position_source_type_id', 'operator_type': '==', 'value': 10},
            {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 5}
        ]},
        'override_modifiers': ['exclude_perspective_level_simulated_cash', 'include_simulated_cash']
    },
    'exclude_pending_trades': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'position_source_type_id', 'operator_type': '==', 'value': 9}
    },
    'exclude_current_flow': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'and': [
            {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 3},
            {'column': 'upcoming_trade_date', 'operator_type': '==', 'value': False}
        ]}
    },
    'exclude_manual_corrections': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'position_source_type_id', 'operator_type': '==', 'value': 8}
    },
    'exclude_initial_positions': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'position_source_type_id', 'operator_type': 'In', 'value': [1, 9, 11]}
    },
    'exclude_blocked_positions': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'column': 'position_blocking_type_id', 'operator_type': 'IsNotNull'}
    },
    'exclude_other_net_assets_excl_investment_grade_accrual': {
        'type': 'PreProcessing',
        'apply_to': 'both',
        'criteria': {'and': [
            {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 2},
            {'column': 'instrument_subtype_id', 'operator_type': 'NotIn', 'value': [93, 94]}
        ]}
    },

    # ==========================================================================
    # PostProcessing - positions matching criteria are KEPT (savior)
    # ==========================================================================
    'include_all_trade_cash': {
        'type': 'PostProcessing',
        'apply_to': 'both',
        'rule_result_operator': 'or',
        'criteria': {'and': [
            {'column': 'position_source_type_id', 'operator_type': '==', 'value': 10},
            {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 6}
        ]},
        'override_modifiers': ['exclude_perspective_level_simulated_cash']
    },
    'include_trade_cash_within_perspective': {
        'type': 'PostProcessing',
        'apply_to': 'both',
        'rule_result_operator': 'or',
        'criteria': {'and': [
            {'column': 'position_source_type_id', 'operator_type': '==', 'value': 10},
            {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 6}
        ]},
        'override_modifiers': ['exclude_perspective_level_simulated_cash']
    },
    'exclude_trade_cash': {
        'type': 'PostProcessing',
        'apply_to': 'both',
        'rule_result_operator': 'and',
        'criteria': {'not': {'and': [
            {'column': 'position_source_type_id', 'operator_type': '==', 'value': 10},
            {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 6}
        ]}},
        'override_modifiers': ['exclude_perspective_level_simulated_cash']
    },
    'exclude_perspective_level_simulated_cash': {
        'type': 'PostProcessing',
        'apply_to': 'both',
        'rule_result_operator': 'or',
        'criteria': {'and': [
            {'column': 'position_source_type_id', 'operator_type': '==', 'value': 10},
            {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 5},
            {'column': 'perspective_id', 'operator_type': 'In', 'value': f'({INT_NULL},perspective_id)'}
        ]}
    },
    'include_simulated_cash': {
        'type': 'PostProcessing',
        'apply_to': 'both',
        'rule_result_operator': 'or',
        'criteria': {'and': [
            {'column': 'position_source_type_id', 'operator_type': '==', 'value': 10},
            {'column': 'liquidity_type_id', 'operator_type': '==', 'value': 5}
        ]}
    },

    # ==========================================================================
    # Scaling - these are just flags, no filtering criteria
    # ==========================================================================
    'scale_holdings_to_100_percent': {
        'type': 'Scaling',
        'apply_to': 'both',
        'criteria': None
    },
    'scale_lookthroughs_to_100_percent': {
        'type': 'Scaling',
        'apply_to': 'both',
        'criteria': None
    },
}
