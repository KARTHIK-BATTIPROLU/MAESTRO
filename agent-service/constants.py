"""
MAESTRO - Shared Constants & Defaults

Single source of truth for:
- Question key mappings (q1–q10)
- Default risk values
- Risk weight definitions
- Risk level thresholds
- Categorical enums
"""

from typing import Dict

# =============================================================================
# QUESTION KEY MAPPING — SINGLE SOURCE OF TRUTH
# =============================================================================

Q_KEY_MAP: Dict[str, str] = {
    "business_context": "q1",
    "inventory_decision_method": "q2",
    "stock_issues": "q3",
    "supplier_reliability": "q4",
    "demand_variability": "q5",
    "reorder_timing_issues": "q6",
    "warehouse_constraints": "q7",
    "cash_flow_impact": "q8",
    "system_limitations": "q9",
    "desired_outcome": "q10",
}

QUESTION_LABELS: Dict[str, str] = {
    "q1": "Business description (industry, products, scale)",
    "q2": "How inventory decisions are currently made",
    "q3": "History of stockouts or overstocking",
    "q4": "Supplier reliability and delivery delays",
    "q5": "Demand variability (seasonal, steady, volatile)",
    "q6": "Reorder timing challenges",
    "q7": "Warehouse or storage constraints",
    "q8": "Cash flow impact of inventory",
    "q9": "Current tools or system limitations",
    "q10": "Primary desired outcome from this system",
}

NUM_QUESTIONS = 10

# =============================================================================
# RISK DEFAULTS
# =============================================================================

DEFAULT_RISK: float = 0.5
DEFAULT_COMPOSITE_RISK: float = 0.5

# =============================================================================
# RISK WEIGHTS  (must sum to 1.0)
# =============================================================================

RISK_WEIGHTS = {
    "demand": 0.35,
    "supplier": 0.35,
    "warehouse": 0.30,
}

assert abs(sum(RISK_WEIGHTS.values()) - 1.0) < 1e-6, "Risk weights must sum to 1.0"

# =============================================================================
# RISK LEVEL THRESHOLDS
# =============================================================================

RISK_LEVEL_LOW_CEIL: float = 0.4
RISK_LEVEL_HIGH_FLOOR: float = 0.7

# =============================================================================
# EXTERNAL MODIFIER BOUNDS
# =============================================================================

EXT_MODIFIER_FLOOR: float = -0.2
EXT_MODIFIER_CEIL: float = 0.3

# =============================================================================
# WAREHOUSE UTILIZATION THRESHOLDS
# =============================================================================

WAREHOUSE_UTIL_LOW_CEIL: float = 0.50
WAREHOUSE_UTIL_HIGH_FLOOR: float = 0.75
