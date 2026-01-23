"""
MAESTRO Decision Engine - Risk Calculator, Decision Rules & Explanations

This module:
1. Calculates weighted composite risk score from individual risk signals
2. Classifies risk into LOW/MODERATE/HIGH levels
3. Determines reorder timing (EARLY/NORMAL/DELAYED)
4. Determines order strategy (SPLIT_ORDERS/FREQUENT_SMALL/BULK)
5. Generates human-readable explanations for decisions

Architecture:
    risk_signals.py → decision_engine.py → final output
    
Usage:
    from decision_engine import (
        build_composite_risk_profile,
        build_inventory_decision,
        build_decision_explanation
    )
    
    # Step 1: Calculate composite risk
    risks = {"demand_risk": 0.75, "supplier_risk": 0.65, "warehouse_stress": 0.82}
    risk_profile = build_composite_risk_profile(risks)
    # → {"composite_risk": 0.74, "risk_level": "HIGH"}
    
    # Step 2: Add cash risk and get decision
    risk_profile["cash_risk"] = 0.7
    decision = build_inventory_decision(risk_profile)
    # → {"reorder_timing": "EARLY", "order_strategy": "SPLIT_ORDERS"}
    
    # Step 3: Generate explanation
    explanation = build_decision_explanation(risk_profile, decision)
    # → "Your business faces elevated inventory risk..."
"""

# =============================================================================
# RISK WEIGHTS (must sum to 1.0)
# =============================================================================
# These weights reflect business priority:
# - Demand & Supplier are equally critical (35% each)
# - Warehouse is a physical constraint (30%)

DEMAND_WEIGHT = 0.35
SUPPLIER_WEIGHT = 0.35
WAREHOUSE_WEIGHT = 0.30

# Validation: weights must sum to 1.0
assert abs(DEMAND_WEIGHT + SUPPLIER_WEIGHT + WAREHOUSE_WEIGHT - 1.0) < 0.001, \
    "Risk weights must sum to 1.0"


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def calculate_composite_risk(
    demand_risk: float,
    supplier_risk: float,
    warehouse_stress: float
) -> float:
    """
    Calculate weighted composite risk score.
    
    Formula:
        composite = (demand × 0.35) + (supplier × 0.35) + (warehouse × 0.30)
    
    Args:
        demand_risk: Demand volatility risk (0.0 to 1.0)
        supplier_risk: Supplier delay risk (0.0 to 1.0)
        warehouse_stress: Warehouse capacity stress (0.0 to 1.0)
    
    Returns:
        Composite risk score capped between 0.0 and 1.0
    
    Example:
        >>> calculate_composite_risk(0.75, 0.65, 0.82)
        0.736
    """
    # Validate inputs - clamp to valid range
    demand_risk = max(0.0, min(1.0, float(demand_risk)))
    supplier_risk = max(0.0, min(1.0, float(supplier_risk)))
    warehouse_stress = max(0.0, min(1.0, float(warehouse_stress)))
    
    # Calculate weighted sum
    composite = (
        (demand_risk * DEMAND_WEIGHT) +
        (supplier_risk * SUPPLIER_WEIGHT) +
        (warehouse_stress * WAREHOUSE_WEIGHT)
    )
    
    # Cap result between 0.0 and 1.0 (should already be, but defensive)
    composite = max(0.0, min(1.0, composite))
    
    # Round to 2 decimal places for consistency
    return round(composite, 2)


def classify_risk_level(composite_risk: float) -> str:
    """
    Classify composite risk into categorical level.
    
    Thresholds:
        - LOW:      composite < 0.4
        - MODERATE: 0.4 ≤ composite < 0.7
        - HIGH:     composite ≥ 0.7
    
    Args:
        composite_risk: The composite risk score (0.0 to 1.0)
    
    Returns:
        Risk level string: "LOW", "MODERATE", or "HIGH"
    
    Example:
        >>> classify_risk_level(0.74)
        'HIGH'
    """
    # Validate input
    composite_risk = max(0.0, min(1.0, float(composite_risk)))
    
    # Apply classification rules
    if composite_risk < 0.4:
        return "LOW"
    elif composite_risk < 0.7:
        return "MODERATE"
    else:
        return "HIGH"


# =============================================================================
# WRAPPER FUNCTION
# =============================================================================

def build_composite_risk_profile(risks: dict) -> dict:
    """
    Build complete composite risk profile from individual risk signals.
    
    This is the main entry point for risk aggregation.
    
    Args:
        risks: Dictionary containing risk signals:
            - demand_risk (float): 0.0 to 1.0
            - supplier_risk (float): 0.0 to 1.0
            - warehouse_stress (float): 0.0 to 1.0
    
    Returns:
        Dictionary with:
            - composite_risk (float): Weighted aggregate score
            - risk_level (str): "LOW", "MODERATE", or "HIGH"
    
    Handles missing keys gracefully with default of 0.5 (neutral risk).
    
    Example:
        >>> build_composite_risk_profile({
        ...     "demand_risk": 0.75,
        ...     "supplier_risk": 0.65,
        ...     "warehouse_stress": 0.82
        ... })
        {'composite_risk': 0.74, 'risk_level': 'HIGH'}
    """
    # Default value for missing keys (neutral risk assumption)
    DEFAULT_RISK = 0.5
    
    # Extract values with defensive defaults
    demand_risk = risks.get("demand_risk", DEFAULT_RISK)
    supplier_risk = risks.get("supplier_risk", DEFAULT_RISK)
    warehouse_stress = risks.get("warehouse_stress", DEFAULT_RISK)
    
    # Handle None values
    if demand_risk is None:
        demand_risk = DEFAULT_RISK
    if supplier_risk is None:
        supplier_risk = DEFAULT_RISK
    if warehouse_stress is None:
        warehouse_stress = DEFAULT_RISK
    
    # Calculate composite risk
    composite = calculate_composite_risk(
        demand_risk=demand_risk,
        supplier_risk=supplier_risk,
        warehouse_stress=warehouse_stress
    )
    
    # Classify risk level
    level = classify_risk_level(composite)
    
    return {
        "composite_risk": composite,
        "risk_level": level
    }


# =============================================================================
# DECISION RULES
# =============================================================================

def determine_reorder_timing(risk_level: str) -> str:
    """
    Determine when to reorder based on overall risk level.
    
    Decision Logic:
        - HIGH risk     → EARLY (reorder sooner to build buffer)
        - MODERATE risk → NORMAL (standard reorder timing)
        - LOW risk      → DELAYED (can wait, optimize for efficiency)
    
    Args:
        risk_level: Risk classification ("HIGH", "MODERATE", "LOW")
    
    Returns:
        Reorder timing: "EARLY", "NORMAL", or "DELAYED"
    
    Example:
        >>> determine_reorder_timing("HIGH")
        'EARLY'
    """
    # Normalize input to uppercase for consistency
    risk_level = str(risk_level).upper().strip()
    
    # Apply timing rules based on risk level
    if risk_level == "HIGH":
        # High risk = reorder early to build safety buffer
        return "EARLY"
    elif risk_level == "MODERATE":
        # Moderate risk = standard timing is acceptable
        return "NORMAL"
    elif risk_level == "LOW":
        # Low risk = can delay for cost efficiency
        return "DELAYED"
    else:
        # Unknown risk level = default to NORMAL (safe middle ground)
        return "NORMAL"


def determine_order_strategy(
    warehouse_stress: float,
    cash_risk: float
) -> str:
    """
    Determine order quantity strategy based on constraints.
    
    Priority Order (first match wins):
        1. warehouse_stress >= 0.75 → SPLIT_ORDERS (can't store bulk)
        2. cash_risk >= 0.7         → FREQUENT_SMALL (preserve cash)
        3. Otherwise                → BULK (most efficient)
    
    Args:
        warehouse_stress: Warehouse capacity utilization (0.0 to 1.0)
        cash_risk: Cash flow sensitivity risk (0.0 to 1.0)
    
    Returns:
        Order strategy: "SPLIT_ORDERS", "FREQUENT_SMALL", or "BULK"
    
    Example:
        >>> determine_order_strategy(0.82, 0.5)
        'SPLIT_ORDERS'
    """
    # Validate and clamp inputs to valid range
    warehouse_stress = max(0.0, min(1.0, float(warehouse_stress)))
    cash_risk = max(0.0, min(1.0, float(cash_risk)))
    
    # Rule 1: High warehouse stress = must split orders (physical constraint)
    # This takes priority because you physically cannot store bulk orders
    if warehouse_stress >= 0.75:
        return "SPLIT_ORDERS"
    
    # Rule 2: High cash risk = frequent small orders (financial constraint)
    # Preserves cash flow by spreading payments over time
    if cash_risk >= 0.7:
        return "FREQUENT_SMALL"
    
    # Rule 3: No constraints = bulk ordering (most cost-efficient)
    return "BULK"


def build_inventory_decision(risk_profile: dict) -> dict:
    """
    Build complete inventory decision from risk profile.
    
    This combines risk assessment with decision rules to produce
    actionable reorder timing and quantity strategy.
    
    Args:
        risk_profile: Dictionary containing:
            - composite_risk (float): Overall risk score (0.0 to 1.0)
            - risk_level (str): "HIGH", "MODERATE", or "LOW"
            - warehouse_stress (float): Capacity utilization (0.0 to 1.0)
            - cash_risk (float): Cash flow sensitivity (0.0 to 1.0)
    
    Returns:
        Dictionary with:
            - reorder_timing (str): "EARLY", "NORMAL", or "DELAYED"
            - order_strategy (str): "SPLIT_ORDERS", "FREQUENT_SMALL", or "BULK"
    
    Handles missing keys gracefully with safe defaults.
    
    Example:
        >>> build_inventory_decision({
        ...     "composite_risk": 0.74,
        ...     "risk_level": "HIGH",
        ...     "warehouse_stress": 0.82,
        ...     "cash_risk": 0.7
        ... })
        {'reorder_timing': 'EARLY', 'order_strategy': 'SPLIT_ORDERS'}
    """
    # Default values for missing keys
    DEFAULT_RISK_LEVEL = "MODERATE"  # Safe middle ground
    DEFAULT_STRESS = 0.5             # Neutral assumption
    
    # Extract risk level with defensive default
    risk_level = risk_profile.get("risk_level", DEFAULT_RISK_LEVEL)
    if risk_level is None:
        risk_level = DEFAULT_RISK_LEVEL
    
    # Extract warehouse stress with defensive default
    warehouse_stress = risk_profile.get("warehouse_stress", DEFAULT_STRESS)
    if warehouse_stress is None:
        warehouse_stress = DEFAULT_STRESS
    
    # Extract cash risk with defensive default
    cash_risk = risk_profile.get("cash_risk", DEFAULT_STRESS)
    if cash_risk is None:
        cash_risk = DEFAULT_STRESS
    
    # Determine reorder timing based on overall risk
    timing = determine_reorder_timing(risk_level)
    
    # Determine order strategy based on constraints
    strategy = determine_order_strategy(warehouse_stress, cash_risk)
    
    return {
        "reorder_timing": timing,
        "order_strategy": strategy
    }


# =============================================================================
# EXPLANATION BUILDER
# =============================================================================

def build_decision_explanation(risk_inputs: dict, decision: dict) -> str:
    """
    Build a human-readable explanation for the inventory decision.
    
    This function generates deterministic, rule-based explanations
    without any LLM calls. The explanation connects detected risks
    to the recommended action.
    
    Args:
        risk_inputs: Dictionary containing:
            - risk_level (str): "HIGH", "MODERATE", or "LOW"
            - demand_risk (float): 0.0 to 1.0
            - supplier_risk (float): 0.0 to 1.0
            - warehouse_stress (float): 0.0 to 1.0
            - cash_risk (float): 0.0 to 1.0
        decision: Dictionary containing:
            - reorder_timing (str): "EARLY", "NORMAL", or "DELAYED"
            - order_strategy (str): "SPLIT_ORDERS", "FREQUENT_SMALL", or "BULK"
    
    Returns:
        A human-readable explanation string (2-4 sentences).
    
    Example:
        >>> risk_inputs = {
        ...     "risk_level": "HIGH",
        ...     "demand_risk": 0.75,
        ...     "supplier_risk": 0.65,
        ...     "warehouse_stress": 0.82,
        ...     "cash_risk": 0.7
        ... }
        >>> decision = {"reorder_timing": "EARLY", "order_strategy": "SPLIT_ORDERS"}
        >>> build_decision_explanation(risk_inputs, decision)
        'Demand is expected to rise due to seasonal factors...'
    """
    # Extract values with safe defaults
    DEFAULT_VALUE = 0.5
    
    risk_level = risk_inputs.get("risk_level", "MODERATE")
    demand_risk = risk_inputs.get("demand_risk", DEFAULT_VALUE) or DEFAULT_VALUE
    supplier_risk = risk_inputs.get("supplier_risk", DEFAULT_VALUE) or DEFAULT_VALUE
    warehouse_stress = risk_inputs.get("warehouse_stress", DEFAULT_VALUE) or DEFAULT_VALUE
    cash_risk = risk_inputs.get("cash_risk", DEFAULT_VALUE) or DEFAULT_VALUE
    
    reorder_timing = decision.get("reorder_timing", "NORMAL")
    order_strategy = decision.get("order_strategy", "BULK")
    
    # ==========================================================================
    # Part 1: Detect which risks are elevated
    # ==========================================================================
    detected_risks = []
    
    # Check demand risk (threshold: 0.6)
    if demand_risk >= 0.6:
        detected_risks.append("demand_high")
    
    # Check supplier risk (threshold: 0.6)
    if supplier_risk >= 0.6:
        detected_risks.append("supplier_high")
    
    # Check warehouse stress (threshold: 0.75)
    if warehouse_stress >= 0.75:
        detected_risks.append("warehouse_high")
    
    # Check cash risk (threshold: 0.7)
    if cash_risk >= 0.7:
        detected_risks.append("cash_high")
    
    # ==========================================================================
    # Part 2: Build situation summary based on risk level
    # ==========================================================================
    if risk_level == "HIGH":
        situation = "Your business faces elevated inventory risk."
    elif risk_level == "MODERATE":
        situation = "Your business has moderate inventory risk."
    else:
        situation = "Your business has low inventory risk."
    
    # ==========================================================================
    # Part 3: Build risk descriptions (1-3 sentences)
    # ==========================================================================
    risk_phrases = []
    
    if "demand_high" in detected_risks:
        risk_phrases.append("Demand is expected to fluctuate or increase due to seasonal or market factors")
    
    if "supplier_high" in detected_risks:
        risk_phrases.append("your suppliers show signs of delivery delays or uncertainty")
    
    if "warehouse_high" in detected_risks:
        risk_phrases.append("warehouse storage is currently constrained")
    
    if "cash_high" in detected_risks:
        risk_phrases.append("cash flow is sensitive and needs protection")
    
    # Combine risk phrases into a readable sentence
    if len(risk_phrases) == 0:
        risk_description = "No significant risk factors were detected."
    elif len(risk_phrases) == 1:
        risk_description = risk_phrases[0].capitalize() + "."
    elif len(risk_phrases) == 2:
        risk_description = risk_phrases[0].capitalize() + ", and " + risk_phrases[1] + "."
    else:
        # 3 or more risks
        risk_description = (
            risk_phrases[0].capitalize() + ", " +
            ", ".join(risk_phrases[1:-1]) + ", and " +
            risk_phrases[-1] + "."
        )
    
    # ==========================================================================
    # Part 4: Build constraint override explanation (if applicable)
    # ==========================================================================
    constraint_explanation = ""
    
    # Lead time override takes priority (can only pull earlier)
    lead_time_override_applied = risk_inputs.get("lead_time_override_applied", False)
    effective_lead_time_days = risk_inputs.get("effective_lead_time_days")
    
    if lead_time_override_applied and effective_lead_time_days is not None:
        constraint_explanation = f"Supplier lead times of ~{effective_lead_time_days:.0f} days influenced earlier ordering."
    # Warehouse constraint is secondary
    elif "warehouse_high" in detected_risks and order_strategy == "SPLIT_ORDERS":
        constraint_explanation = "Storage limitations prevent bulk ordering."
    # Cash constraint is tertiary
    elif "cash_high" in detected_risks and order_strategy == "FREQUENT_SMALL":
        constraint_explanation = "Cash flow constraints favor smaller, frequent orders."
    
    # ==========================================================================
    # Part 5: Build recommendation justification
    # ==========================================================================
    
    # Timing justification (enhanced with lead time context)
    if reorder_timing == "EARLY":
        if lead_time_override_applied and effective_lead_time_days is not None:
            timing_reason = f"reordering early accounts for the {effective_lead_time_days:.0f}-day effective lead time"
        else:
            timing_reason = "reordering early builds a safety buffer against disruptions"
    elif reorder_timing == "DELAYED":
        timing_reason = "delaying reorders optimizes costs given the low risk"
    else:
        timing_reason = "standard reorder timing is appropriate"
    
    # Strategy justification
    if order_strategy == "SPLIT_ORDERS":
        strategy_reason = "splitting orders into smaller deliveries avoids storage congestion"
    elif order_strategy == "FREQUENT_SMALL":
        strategy_reason = "frequent small orders preserve cash flow flexibility"
    else:
        strategy_reason = "bulk ordering provides the best cost efficiency"
    
    # Combine into recommendation sentence
    recommendation = f"Therefore, {timing_reason}, and {strategy_reason}."
    
    # ==========================================================================
    # Part 5b: Build quantity explanation (if available)
    # ==========================================================================
    quantity_explanation = ""
    quantity_context = risk_inputs.get("quantity_context")
    
    if quantity_context:
        avg_daily = quantity_context.get("avg_daily_sales", 0)
        lead_time = quantity_context.get("effective_lead_time_days", 0)
        qty_range = quantity_context.get("recommended_quantity_range", {})
        lower = qty_range.get("lower", 0)
        upper = qty_range.get("upper", 0)
        warehouse_constrained = quantity_context.get("warehouse_constrained", False)
        
        if avg_daily > 0 and lead_time > 0 and lower > 0:
            quantity_explanation = f"Based on average sales of {avg_daily:.0f}/day and supplier lead time of {lead_time:.0f} days, we recommend ordering {lower}-{upper} units."
            
            if warehouse_constrained:
                available = quantity_context.get("available_space", 0)
                quantity_explanation += f" (Note: Quantity limited by available warehouse space of {available:.0f} units.)"
    
    # ==========================================================================
    # Part 5c: Build reorder point explanation (if available)
    # ==========================================================================
    reorder_point_explanation = ""
    reorder_point_context = risk_inputs.get("reorder_point_context")
    
    if reorder_point_context:
        rop_units = reorder_point_context.get("reorder_point_units", 0)
        days_cover = reorder_point_context.get("days_of_cover_left", 0)
        rop_status = reorder_point_context.get("status", "")
        rop_action = reorder_point_context.get("action", "")
        current = reorder_point_context.get("current_stock", 0)
        
        if rop_units > 0:
            reorder_point_explanation = f"Your reorder point is {rop_units} units. At current sales, you have ~{days_cover:.0f} days of cover."
            
            # Add status-specific message
            if rop_status == "BELOW":
                reorder_point_explanation += f" ⚠️ Your stock ({current:.0f}) is BELOW the reorder point—reorder now."
            elif rop_status == "NEAR":
                reorder_point_explanation += f" Your stock ({current:.0f}) is approaching the reorder point—prepare to order soon."
    
    # ==========================================================================
    # Part 6: Assemble final explanation
    # ==========================================================================
    
    # Build the complete explanation
    parts = [situation, risk_description]
    
    if constraint_explanation:
        parts.append(constraint_explanation)
    
    parts.append(recommendation)
    
    # Add quantity explanation
    if quantity_explanation:
        parts.append(quantity_explanation)
    
    # Add reorder point explanation
    if reorder_point_explanation:
        parts.append(reorder_point_explanation)
    
    # Join with spaces, clean up any double spaces
    explanation = " ".join(parts)
    explanation = " ".join(explanation.split())  # Normalize whitespace
    
    return explanation


# =============================================================================
# DEMO / TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MAESTRO Decision Engine - Composite Risk Calculator Demo")
    print("=" * 60)
    
    # Test Case 1: High risk scenario
    test1 = {
        "demand_risk": 0.75,
        "supplier_risk": 0.65,
        "warehouse_stress": 0.82
    }
    result1 = build_composite_risk_profile(test1)
    print(f"\nTest 1: High risk business")
    print(f"  Input:  {test1}")
    print(f"  Output: {result1}")
    print(f"  Expected: composite ~0.74, level HIGH")
    
    # Test Case 2: Low risk scenario
    test2 = {
        "demand_risk": 0.2,
        "supplier_risk": 0.2,
        "warehouse_stress": 0.3
    }
    result2 = build_composite_risk_profile(test2)
    print(f"\nTest 2: Low risk business")
    print(f"  Input:  {test2}")
    print(f"  Output: {result2}")
    print(f"  Expected: composite ~0.23, level LOW")
    
    # Test Case 3: Moderate risk scenario
    test3 = {
        "demand_risk": 0.5,
        "supplier_risk": 0.5,
        "warehouse_stress": 0.5
    }
    result3 = build_composite_risk_profile(test3)
    print(f"\nTest 3: Moderate risk business")
    print(f"  Input:  {test3}")
    print(f"  Output: {result3}")
    print(f"  Expected: composite 0.50, level MODERATE")
    
    # Test Case 4: Missing keys (defensive)
    test4 = {
        "demand_risk": 0.8
        # supplier_risk and warehouse_stress missing
    }
    result4 = build_composite_risk_profile(test4)
    print(f"\nTest 4: Missing keys (defensive handling)")
    print(f"  Input:  {test4}")
    print(f"  Output: {result4}")
    print(f"  Note: Missing keys default to 0.5")
    
    # Test Case 5: Edge case - all zeros
    test5 = {
        "demand_risk": 0.0,
        "supplier_risk": 0.0,
        "warehouse_stress": 0.0
    }
    result5 = build_composite_risk_profile(test5)
    print(f"\nTest 5: All zeros (edge case)")
    print(f"  Input:  {test5}")
    print(f"  Output: {result5}")
    
    # Test Case 6: Edge case - all max
    test6 = {
        "demand_risk": 1.0,
        "supplier_risk": 1.0,
        "warehouse_stress": 1.0
    }
    result6 = build_composite_risk_profile(test6)
    print(f"\nTest 6: All maximum (edge case)")
    print(f"  Input:  {test6}")
    print(f"  Output: {result6}")
    
    # Verify weights
    print(f"\n" + "=" * 60)
    print("Weight Configuration:")
    print(f"  DEMAND_WEIGHT:    {DEMAND_WEIGHT} (35%)")
    print(f"  SUPPLIER_WEIGHT:  {SUPPLIER_WEIGHT} (35%)")
    print(f"  WAREHOUSE_WEIGHT: {WAREHOUSE_WEIGHT} (30%)")
    print(f"  Total:            {DEMAND_WEIGHT + SUPPLIER_WEIGHT + WAREHOUSE_WEIGHT}")
    print("=" * 60)
    
    # ==========================================================================
    # DECISION RULES TESTS
    # ==========================================================================
    print("\n" + "=" * 60)
    print("DECISION RULES - Reorder Timing Tests")
    print("=" * 60)
    
    # Test reorder timing
    print(f"\n  HIGH risk    → {determine_reorder_timing('HIGH')} (expected: EARLY)")
    print(f"  MODERATE risk → {determine_reorder_timing('MODERATE')} (expected: NORMAL)")
    print(f"  LOW risk      → {determine_reorder_timing('LOW')} (expected: DELAYED)")
    print(f"  Unknown risk  → {determine_reorder_timing('UNKNOWN')} (expected: NORMAL)")
    
    print("\n" + "=" * 60)
    print("DECISION RULES - Order Strategy Tests")
    print("=" * 60)
    
    # Test order strategy - warehouse stress takes priority
    print(f"\n  warehouse=0.82, cash=0.5 → {determine_order_strategy(0.82, 0.5)} (expected: SPLIT_ORDERS)")
    print(f"  warehouse=0.82, cash=0.8 → {determine_order_strategy(0.82, 0.8)} (expected: SPLIT_ORDERS)")
    print(f"  warehouse=0.5, cash=0.75 → {determine_order_strategy(0.5, 0.75)} (expected: FREQUENT_SMALL)")
    print(f"  warehouse=0.5, cash=0.5  → {determine_order_strategy(0.5, 0.5)} (expected: BULK)")
    
    print("\n" + "=" * 60)
    print("FULL INVENTORY DECISION - Integration Tests")
    print("=" * 60)
    
    # Full decision test 1: High risk + high warehouse stress
    decision_test1 = {
        "composite_risk": 0.74,
        "risk_level": "HIGH",
        "warehouse_stress": 0.82,
        "cash_risk": 0.7
    }
    decision1 = build_inventory_decision(decision_test1)
    print(f"\nTest D1: High risk + warehouse constraint")
    print(f"  Input:  {decision_test1}")
    print(f"  Output: {decision1}")
    print(f"  Expected: EARLY + SPLIT_ORDERS")
    
    # Full decision test 2: Low risk + cash constraint
    decision_test2 = {
        "composite_risk": 0.35,
        "risk_level": "LOW",
        "warehouse_stress": 0.5,
        "cash_risk": 0.75
    }
    decision2 = build_inventory_decision(decision_test2)
    print(f"\nTest D2: Low risk + cash constraint")
    print(f"  Input:  {decision_test2}")
    print(f"  Output: {decision2}")
    print(f"  Expected: DELAYED + FREQUENT_SMALL")
    
    # Full decision test 3: Moderate risk + no constraints
    decision_test3 = {
        "composite_risk": 0.55,
        "risk_level": "MODERATE",
        "warehouse_stress": 0.4,
        "cash_risk": 0.3
    }
    decision3 = build_inventory_decision(decision_test3)
    print(f"\nTest D3: Moderate risk + no constraints")
    print(f"  Input:  {decision_test3}")
    print(f"  Output: {decision3}")
    print(f"  Expected: NORMAL + BULK")
    
    # Full decision test 4: Missing keys (defensive)
    decision_test4 = {
        "risk_level": "HIGH"
        # warehouse_stress and cash_risk missing
    }
    decision4 = build_inventory_decision(decision_test4)
    print(f"\nTest D4: Missing keys (defensive)")
    print(f"  Input:  {decision_test4}")
    print(f"  Output: {decision4}")
    print(f"  Note: Missing constraints default to 0.5")
    
    # ==========================================================================
    # EXPLANATION BUILDER TESTS
    # ==========================================================================
    print("\n" + "=" * 60)
    print("EXPLANATION BUILDER - Human-Readable Output Tests")
    print("=" * 60)
    
    # Explanation test 1: High risk scenario (all risks elevated)
    exp_risk1 = {
        "risk_level": "HIGH",
        "demand_risk": 0.75,
        "supplier_risk": 0.65,
        "warehouse_stress": 0.82,
        "cash_risk": 0.7
    }
    exp_decision1 = {"reorder_timing": "EARLY", "order_strategy": "SPLIT_ORDERS"}
    explanation1 = build_decision_explanation(exp_risk1, exp_decision1)
    print(f"\nTest E1: High risk (all factors elevated)")
    print(f"  Risks: demand={exp_risk1['demand_risk']}, supplier={exp_risk1['supplier_risk']}, warehouse={exp_risk1['warehouse_stress']}, cash={exp_risk1['cash_risk']}")
    print(f"  Decision: {exp_decision1}")
    print(f"  Explanation:\n  \"{explanation1}\"")
    
    # Explanation test 2: Low risk scenario (no constraints)
    exp_risk2 = {
        "risk_level": "LOW",
        "demand_risk": 0.3,
        "supplier_risk": 0.2,
        "warehouse_stress": 0.4,
        "cash_risk": 0.3
    }
    exp_decision2 = {"reorder_timing": "DELAYED", "order_strategy": "BULK"}
    explanation2 = build_decision_explanation(exp_risk2, exp_decision2)
    print(f"\nTest E2: Low risk (no elevated factors)")
    print(f"  Risks: demand={exp_risk2['demand_risk']}, supplier={exp_risk2['supplier_risk']}, warehouse={exp_risk2['warehouse_stress']}, cash={exp_risk2['cash_risk']}")
    print(f"  Decision: {exp_decision2}")
    print(f"  Explanation:\n  \"{explanation2}\"")
    
    # Explanation test 3: Cash constraint only
    exp_risk3 = {
        "risk_level": "MODERATE",
        "demand_risk": 0.5,
        "supplier_risk": 0.4,
        "warehouse_stress": 0.5,
        "cash_risk": 0.8
    }
    exp_decision3 = {"reorder_timing": "NORMAL", "order_strategy": "FREQUENT_SMALL"}
    explanation3 = build_decision_explanation(exp_risk3, exp_decision3)
    print(f"\nTest E3: Cash constraint only")
    print(f"  Risks: demand={exp_risk3['demand_risk']}, supplier={exp_risk3['supplier_risk']}, warehouse={exp_risk3['warehouse_stress']}, cash={exp_risk3['cash_risk']}")
    print(f"  Decision: {exp_decision3}")
    print(f"  Explanation:\n  \"{explanation3}\"")
    
    # Explanation test 4: Demand + Supplier risk (no physical constraints)
    exp_risk4 = {
        "risk_level": "HIGH",
        "demand_risk": 0.7,
        "supplier_risk": 0.75,
        "warehouse_stress": 0.5,
        "cash_risk": 0.4
    }
    exp_decision4 = {"reorder_timing": "EARLY", "order_strategy": "BULK"}
    explanation4 = build_decision_explanation(exp_risk4, exp_decision4)
    print(f"\nTest E4: Demand + Supplier risk (no physical constraints)")
    print(f"  Risks: demand={exp_risk4['demand_risk']}, supplier={exp_risk4['supplier_risk']}, warehouse={exp_risk4['warehouse_stress']}, cash={exp_risk4['cash_risk']}")
    print(f"  Decision: {exp_decision4}")
    print(f"  Explanation:\n  \"{explanation4}\"")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
