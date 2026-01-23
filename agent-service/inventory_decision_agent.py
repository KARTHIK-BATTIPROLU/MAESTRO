"""
MAESTRO Inventory Decision Agent - Core Decision Interface

This module provides the main entry point for inventory decision-making.
It orchestrates the decision engine functions to produce a single,
structured output with decision, explanation, and confidence.

Architecture:
    risk_signals.py → decision_engine.py → inventory_decision_agent.py
    
Usage:
    from inventory_decision_agent import run_inventory_decision_agent
    
    risk_inputs = {
        "demand_risk": 0.75,
        "supplier_risk": 0.65,
        "warehouse_stress": 0.82,
        "cash_risk": 0.7
    }
    
    result = run_inventory_decision_agent(risk_inputs)
    # → {
    #     "final_decision": {"reorder_timing": "EARLY", "order_strategy": "SPLIT_ORDERS", "risk_level": "HIGH"},
    #     "explanation": "Your business faces elevated inventory risk...",
    #     "confidence": 0.85
    # }
"""

# =============================================================================
# IMPORTS
# =============================================================================

from decision_engine import (
    build_composite_risk_profile,
    build_inventory_decision,
    build_decision_explanation
)


# =============================================================================
# BUFFER MULTIPLIERS FOR QUANTITY CALCULATION (EOQ-LITE)
# =============================================================================

BUFFER_MULTIPLIERS = {
    "MINIMAL": 1.1,      # 10% safety buffer
    "MODERATE": 1.25,    # 25% safety buffer
    "AGGRESSIVE": 1.4,   # 40% safety buffer
}

# Safety multipliers for Reorder Point (ROP) calculation
ROP_SAFETY_MULTIPLIERS = {
    "MINIMAL": 1.0,      # No safety buffer (just-in-time)
    "MODERATE": 1.15,    # 15% safety buffer
    "AGGRESSIVE": 1.30,  # 30% safety buffer
}

# Default values for quantity calculation
DEFAULT_AVG_DAILY_SALES = 50.0  # Conservative default if no live data
DEFAULT_LEAD_TIME_DAYS = 3.0    # Conservative default lead time
DEFAULT_MAX_CAPACITY = 1000     # Reasonable default capacity
DEFAULT_CURRENT_STOCK = 500     # Conservative default stock level


# =============================================================================
# QUANTITY RECOMMENDATION (EOQ-LITE, MSME-SAFE)
# =============================================================================

def calculate_recommended_quantity(
    avg_daily_sales: float,
    effective_lead_time_days: float,
    buffer_policy: str,
    current_stock: float,
    max_capacity: float
) -> dict:
    """
    Calculate recommended order quantity using EOQ-lite formula.
    
    This provides MSME-safe quantity recommendations that:
    - Account for demand during lead time
    - Add safety buffer based on risk posture
    - Never exceed available warehouse space
    
    Formula:
        base_demand = avg_daily_sales × effective_lead_time_days
        raw_quantity = base_demand × buffer_multiplier
        final_quantity = min(raw_quantity, available_space)
    
    Buffer Multipliers:
        - MINIMAL    → 1.1× (10% buffer)
        - MODERATE   → 1.25× (25% buffer)
        - AGGRESSIVE → 1.4× (40% buffer)
    
    Args:
        avg_daily_sales: Average daily sales units
        effective_lead_time_days: Lead time with variability buffer
        buffer_policy: Risk posture ("MINIMAL", "MODERATE", "AGGRESSIVE")
        current_stock: Current inventory level
        max_capacity: Maximum warehouse capacity
    
    Returns:
        Dictionary with:
            - base_demand: Raw demand during lead time
            - buffer_multiplier: Applied multiplier
            - raw_quantity: Quantity before warehouse constraint
            - available_space: Warehouse capacity remaining
            - warehouse_constrained: Whether capacity limit was hit
            - final_quantity: Constrained quantity
            - recommended_quantity_range: {lower, upper} bounds (±10%)
    
    Example:
        >>> calculate_recommended_quantity(100, 5.0, "MODERATE", 300, 1000)
        {'base_demand': 500.0, 'buffer_multiplier': 1.25, 'raw_quantity': 625.0,
         'available_space': 700.0, 'warehouse_constrained': False, 'final_quantity': 625.0,
         'recommended_quantity_range': {'lower': 563, 'upper': 688}}
    """
    # Validate inputs
    avg_daily_sales = max(0.0, float(avg_daily_sales or DEFAULT_AVG_DAILY_SALES))
    effective_lead_time_days = max(1.0, float(effective_lead_time_days or DEFAULT_LEAD_TIME_DAYS))
    max_capacity = max(1.0, float(max_capacity or DEFAULT_MAX_CAPACITY))
    current_stock = max(0.0, float(current_stock or DEFAULT_CURRENT_STOCK))
    
    # Normalize buffer policy
    buffer_policy = str(buffer_policy).upper().strip()
    buffer_multiplier = BUFFER_MULTIPLIERS.get(buffer_policy, BUFFER_MULTIPLIERS["MODERATE"])
    
    # Calculate base demand (EOQ-lite)
    base_demand = avg_daily_sales * effective_lead_time_days
    
    # Apply buffer multiplier
    raw_quantity = base_demand * buffer_multiplier
    
    # Calculate available warehouse space
    available_space = max(0.0, max_capacity - current_stock)
    
    # Apply warehouse constraint (quantity must NEVER exceed capacity)
    warehouse_constrained = raw_quantity > available_space
    final_quantity = min(raw_quantity, available_space)
    
    # Calculate recommended range (±10%)
    lower_bound = round(final_quantity * 0.9)
    upper_bound = round(final_quantity * 1.1)
    
    # Ensure upper bound doesn't exceed available space
    upper_bound = min(upper_bound, round(available_space))
    
    # Ensure lower bound is not negative
    lower_bound = max(0, lower_bound)
    
    print(f"  📦 Quantity calculation: {avg_daily_sales:.1f}/day × {effective_lead_time_days:.1f}d × {buffer_multiplier}x = {raw_quantity:.0f} units")
    if warehouse_constrained:
        print(f"  ⚠️  Warehouse constrained: {raw_quantity:.0f} → {final_quantity:.0f} (available: {available_space:.0f})")
    print(f"  📦 Recommended range: {lower_bound} - {upper_bound} units")
    
    return {
        "avg_daily_sales": avg_daily_sales,
        "effective_lead_time_days": effective_lead_time_days,
        "base_demand": round(base_demand, 1),
        "buffer_policy": buffer_policy,
        "buffer_multiplier": buffer_multiplier,
        "raw_quantity": round(raw_quantity, 1),
        "current_stock": current_stock,
        "max_capacity": max_capacity,
        "available_space": round(available_space, 1),
        "warehouse_constrained": warehouse_constrained,
        "final_quantity": round(final_quantity, 1),
        "recommended_quantity_range": {
            "lower": lower_bound,
            "upper": upper_bound
        }
    }


# =============================================================================
# REORDER POINT (ROP) CALCULATION
# =============================================================================

def calculate_reorder_point(
    avg_daily_sales: float,
    effective_lead_time_days: float,
    buffer_policy: str,
    current_stock: float,
    max_capacity: float
) -> dict:
    """
    Calculate Reorder Point (ROP) and stock status.
    
    ROP is the inventory level at which a new order should be placed
    to avoid stockouts during the lead time period.
    
    Formula:
        lead_time_demand = avg_daily_sales × effective_lead_time_days
        reorder_point = lead_time_demand × safety_multiplier
        reorder_point = min(reorder_point, max_capacity × 0.9)  # Cap at 90% capacity
    
    Safety Multipliers:
        - MINIMAL    → 1.0× (no buffer, just-in-time)
        - MODERATE   → 1.15× (15% safety stock)
        - AGGRESSIVE → 1.30× (30% safety stock)
    
    Status & Action:
        - BELOW ROP           → REORDER_NOW
        - Within 15% of ROP   → PREPARE
        - Above ROP           → SAFE
    
    Args:
        avg_daily_sales: Average daily sales units
        effective_lead_time_days: Lead time with variability buffer
        buffer_policy: Risk posture ("MINIMAL", "MODERATE", "AGGRESSIVE")
        current_stock: Current inventory level
        max_capacity: Maximum warehouse capacity
    
    Returns:
        Dictionary with:
            - lead_time_demand: Demand during lead time
            - safety_multiplier: Applied safety multiplier
            - reorder_point_units: The ROP threshold
            - reorder_point_capped: Whether 90% capacity cap was applied
            - current_stock: Current inventory level
            - status: "BELOW" | "NEAR" | "ABOVE"
            - action: "REORDER_NOW" | "PREPARE" | "SAFE"
            - days_of_cover_left: Days until stockout at current sales
            - units_above_rop: How many units above/below ROP
    
    Example:
        >>> calculate_reorder_point(100, 5.0, "MODERATE", 400, 1000)
        {'lead_time_demand': 500.0, 'safety_multiplier': 1.15, 'reorder_point_units': 575,
         'status': 'BELOW', 'action': 'REORDER_NOW', 'days_of_cover_left': 4.0}
    """
    # Validate inputs with defaults
    avg_daily_sales = max(0.1, float(avg_daily_sales or DEFAULT_AVG_DAILY_SALES))  # Min 0.1 to avoid div/0
    effective_lead_time_days = max(1.0, float(effective_lead_time_days or DEFAULT_LEAD_TIME_DAYS))
    max_capacity = max(1.0, float(max_capacity or DEFAULT_MAX_CAPACITY))
    current_stock = max(0.0, float(current_stock or DEFAULT_CURRENT_STOCK))
    
    # Normalize buffer policy
    buffer_policy = str(buffer_policy).upper().strip()
    safety_multiplier = ROP_SAFETY_MULTIPLIERS.get(buffer_policy, ROP_SAFETY_MULTIPLIERS["MODERATE"])
    
    # Calculate lead time demand
    lead_time_demand = avg_daily_sales * effective_lead_time_days
    
    # Calculate raw reorder point
    raw_reorder_point = lead_time_demand * safety_multiplier
    
    # Cap at 90% of max capacity (to leave room for safety)
    capacity_cap = max_capacity * 0.9
    reorder_point_capped = raw_reorder_point > capacity_cap
    reorder_point_units = min(raw_reorder_point, capacity_cap)
    reorder_point_units = round(reorder_point_units)
    
    # Calculate days of cover left
    days_of_cover_left = round(current_stock / avg_daily_sales, 1)
    
    # Determine status and action
    units_above_rop = current_stock - reorder_point_units
    near_threshold = reorder_point_units * 1.15  # Within 15% of ROP
    
    if current_stock <= reorder_point_units:
        status = "BELOW"
        action = "REORDER_NOW"
    elif current_stock <= near_threshold:
        status = "NEAR"
        action = "PREPARE"
    else:
        status = "ABOVE"
        action = "SAFE"
    
    # Print status
    status_emoji = {
        "BELOW": "🚨",
        "NEAR": "⚠️",
        "ABOVE": "✅"
    }
    print(f"  {status_emoji.get(status, '📦')} Reorder Point: {reorder_point_units} units (current: {current_stock:.0f}, status: {status})")
    print(f"  📅 Days of cover: {days_of_cover_left} days at {avg_daily_sales:.1f}/day")
    
    return {
        "avg_daily_sales": avg_daily_sales,
        "effective_lead_time_days": effective_lead_time_days,
        "lead_time_demand": round(lead_time_demand, 1),
        "buffer_policy": buffer_policy,
        "safety_multiplier": safety_multiplier,
        "raw_reorder_point": round(raw_reorder_point, 1),
        "reorder_point_units": reorder_point_units,
        "reorder_point_capped": reorder_point_capped,
        "max_capacity": max_capacity,
        "current_stock": current_stock,
        "status": status,
        "action": action,
        "days_of_cover_left": days_of_cover_left,
        "units_above_rop": round(units_above_rop, 1),
    }


# =============================================================================
# CONFIDENCE CALCULATION
# =============================================================================

def calculate_confidence(risk_level: str) -> float:
    """
    Calculate decision confidence based on risk level.
    
    Higher risk = higher confidence (we're more certain about the recommendation)
    Lower risk = lower confidence (standard advice, less urgent)
    
    Confidence Ranges:
        - HIGH risk     → 0.85 (midpoint of 0.8–0.9)
        - MODERATE risk → 0.65 (midpoint of 0.6–0.7)
        - LOW risk      → 0.45 (midpoint of 0.4–0.5)
    
    Args:
        risk_level: Risk classification ("HIGH", "MODERATE", "LOW")
    
    Returns:
        Confidence score between 0.0 and 1.0
    
    Example:
        >>> calculate_confidence("HIGH")
        0.85
    """
    # Normalize input
    risk_level = str(risk_level).upper().strip()
    
    # Deterministic midpoint values for each risk level
    confidence_map = {
        "HIGH": 0.85,      # Midpoint of 0.8–0.9
        "MODERATE": 0.65,  # Midpoint of 0.6–0.7
        "LOW": 0.45        # Midpoint of 0.4–0.5
    }
    
    # Return mapped value or default to MODERATE confidence
    return confidence_map.get(risk_level, 0.65)


# =============================================================================
# MAIN AGENT FUNCTION
# =============================================================================

def run_inventory_decision_agent(risk_inputs: dict) -> dict:
    """
    Run the Inventory Decision Agent to produce a complete recommendation.
    
    This is the main entry point for the decision-making pipeline.
    It takes raw risk inputs and produces a structured output with:
    - Final decision (timing + strategy + risk level)
    - Human-readable explanation
    - Confidence score
    
    Args:
        risk_inputs: Dictionary containing:
            - demand_risk (float): Demand volatility (0.0 to 1.0)
            - supplier_risk (float): Supplier delay risk (0.0 to 1.0)
            - warehouse_stress (float): Warehouse capacity (0.0 to 1.0)
            - cash_risk (float): Cash flow sensitivity (0.0 to 1.0)
    
    Returns:
        Dictionary with:
            - final_decision (dict): reorder_timing, order_strategy, risk_level
            - explanation (str): Human-readable decision explanation
            - confidence (float): Confidence score (0.0 to 1.0)
    
    Example:
        >>> risk_inputs = {
        ...     "demand_risk": 0.75,
        ...     "supplier_risk": 0.65,
        ...     "warehouse_stress": 0.82,
        ...     "cash_risk": 0.7
        ... }
        >>> result = run_inventory_decision_agent(risk_inputs)
        >>> result["final_decision"]["reorder_timing"]
        'EARLY'
    """
    # =========================================================================
    # Step 1: Validate and extract inputs with defensive defaults
    # =========================================================================
    DEFAULT_RISK = 0.5  # Neutral assumption for missing values
    
    demand_risk = risk_inputs.get("demand_risk", DEFAULT_RISK)
    supplier_risk = risk_inputs.get("supplier_risk", DEFAULT_RISK)
    warehouse_stress = risk_inputs.get("warehouse_stress", DEFAULT_RISK)
    cash_risk = risk_inputs.get("cash_risk", DEFAULT_RISK)
    
    # Handle None values
    if demand_risk is None:
        demand_risk = DEFAULT_RISK
    if supplier_risk is None:
        supplier_risk = DEFAULT_RISK
    if warehouse_stress is None:
        warehouse_stress = DEFAULT_RISK
    if cash_risk is None:
        cash_risk = DEFAULT_RISK
    
    # Extract quantity-related inputs (for EOQ-lite calculation)
    avg_daily_sales = risk_inputs.get("avg_daily_sales")
    current_stock = risk_inputs.get("current_stock")
    max_capacity = risk_inputs.get("max_capacity")
    buffer_policy = risk_inputs.get("buffer_policy", "MODERATE")
    
    # =========================================================================
    # Step 2: Build composite risk profile
    # =========================================================================
    # This calculates the weighted composite risk and classifies it
    risk_profile = build_composite_risk_profile({
        "demand_risk": demand_risk,
        "supplier_risk": supplier_risk,
        "warehouse_stress": warehouse_stress
    })
    
    # Extract composite values
    composite_risk = risk_profile.get("composite_risk", 0.5)
    risk_level = risk_profile.get("risk_level", "MODERATE")
    
    # Extract effective lead time (if available from risk_inputs)
    effective_lead_time_days = risk_inputs.get("effective_lead_time_days")
    lead_time_info = risk_inputs.get("lead_time_info", {})
    
    # =========================================================================
    # Step 3: Build inventory decision (timing + strategy)
    # =========================================================================
    # Combine risk profile with cash risk for decision
    decision_input = {
        "composite_risk": composite_risk,
        "risk_level": risk_level,
        "warehouse_stress": warehouse_stress,
        "cash_risk": cash_risk
    }
    
    decision = build_inventory_decision(decision_input)
    
    # Extract decision values
    reorder_timing = decision.get("reorder_timing", "NORMAL")
    order_strategy = decision.get("order_strategy", "BULK")
    
    # =========================================================================
    # Step 3b: Lead Time Override (can ONLY pull timing EARLIER, never delay)
    # =========================================================================
    lead_time_override_applied = False
    original_timing = reorder_timing
    
    if effective_lead_time_days is not None and effective_lead_time_days >= 7:
        # Long lead times require earlier ordering regardless of risk level
        if reorder_timing != "EARLY":
            reorder_timing = "EARLY"
            lead_time_override_applied = True
            print(f"  ⚡ Lead time override: {original_timing} → EARLY (effective_lead_time={effective_lead_time_days}d ≥ 7d)")
    
    # =========================================================================
    # Step 3c: Calculate Recommended Quantity (EOQ-lite, MSME-safe)
    # =========================================================================
    quantity_context = None
    
    # Only calculate if we have enough data
    if effective_lead_time_days is not None or avg_daily_sales is not None:
        # Derive buffer policy from risk level if not provided
        if buffer_policy is None:
            buffer_policy_map = {
                "HIGH": "AGGRESSIVE",
                "MODERATE": "MODERATE",
                "LOW": "MINIMAL"
            }
            buffer_policy = buffer_policy_map.get(risk_level, "MODERATE")
        
        quantity_context = calculate_recommended_quantity(
            avg_daily_sales=avg_daily_sales or DEFAULT_AVG_DAILY_SALES,
            effective_lead_time_days=effective_lead_time_days or DEFAULT_LEAD_TIME_DAYS,
            buffer_policy=buffer_policy,
            current_stock=current_stock or DEFAULT_CURRENT_STOCK,
            max_capacity=max_capacity or DEFAULT_MAX_CAPACITY
        )
    
    # =========================================================================
    # Step 3d: Calculate Reorder Point (ROP)
    # =========================================================================
    reorder_point_context = None
    
    # Calculate ROP if we have enough data
    if effective_lead_time_days is not None or avg_daily_sales is not None:
        reorder_point_context = calculate_reorder_point(
            avg_daily_sales=avg_daily_sales or DEFAULT_AVG_DAILY_SALES,
            effective_lead_time_days=effective_lead_time_days or DEFAULT_LEAD_TIME_DAYS,
            buffer_policy=buffer_policy,
            current_stock=current_stock or DEFAULT_CURRENT_STOCK,
            max_capacity=max_capacity or DEFAULT_MAX_CAPACITY
        )
    
    # =========================================================================
    # Step 4: Build human-readable explanation
    # =========================================================================
    # Prepare full risk inputs for explanation (including lead time info)
    explanation_inputs = {
        "risk_level": risk_level,
        "demand_risk": demand_risk,
        "supplier_risk": supplier_risk,
        "warehouse_stress": warehouse_stress,
        "cash_risk": cash_risk,
        "effective_lead_time_days": effective_lead_time_days,
        "lead_time_info": lead_time_info,
        "lead_time_override_applied": lead_time_override_applied,
        "quantity_context": quantity_context,
        "reorder_point_context": reorder_point_context,
    }
    
    # Update decision with potentially overridden timing
    final_decision = {
        "reorder_timing": reorder_timing,
        "order_strategy": order_strategy
    }
    
    explanation = build_decision_explanation(explanation_inputs, final_decision)
    
    # =========================================================================
    # Step 5: Calculate confidence score
    # =========================================================================
    confidence = calculate_confidence(risk_level)
    
    # =========================================================================
    # Step 6: Assemble final output
    # =========================================================================
    result = {
        "final_decision": {
            "reorder_timing": reorder_timing,
            "order_strategy": order_strategy,
            "risk_level": risk_level,
            "recommended_quantity_range": quantity_context["recommended_quantity_range"] if quantity_context else None,
            "reorder_point": {
                "units": reorder_point_context["reorder_point_units"] if reorder_point_context else None,
                "status": reorder_point_context["status"] if reorder_point_context else None,
                "action": reorder_point_context["action"] if reorder_point_context else None,
                "days_of_cover_left": reorder_point_context["days_of_cover_left"] if reorder_point_context else None,
                "alert_level": {"REORDER_NOW": "CRITICAL", "PREPARE": "WARNING", "SAFE": "OK"}.get(
                    reorder_point_context["action"], "OK"
                ) if reorder_point_context else None,
            } if reorder_point_context else None,
        },
        "explanation": explanation,
        "confidence": confidence,
        "lead_time_context": {
            "effective_lead_time_days": effective_lead_time_days,
            "lead_time_override_applied": lead_time_override_applied,
            "original_timing": original_timing if lead_time_override_applied else None,
        },
        "quantity_context": quantity_context,
        "reorder_point_context": reorder_point_context,
    }
    
    return result


# =============================================================================
# DEMO / TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MAESTRO Inventory Decision Agent - Integration Test")
    print("=" * 70)
    
    # Test Case 1: High risk scenario
    print("\n" + "-" * 70)
    print("Test 1: High Risk Scenario (all factors elevated)")
    print("-" * 70)
    
    test1_input = {
        "demand_risk": 0.75,
        "supplier_risk": 0.65,
        "warehouse_stress": 0.82,
        "cash_risk": 0.7
    }
    
    result1 = run_inventory_decision_agent(test1_input)
    
    print(f"\nInput: {test1_input}")
    print(f"\nOutput:")
    print(f"  Final Decision:")
    print(f"    - Reorder Timing: {result1['final_decision']['reorder_timing']}")
    print(f"    - Order Strategy: {result1['final_decision']['order_strategy']}")
    print(f"    - Risk Level:     {result1['final_decision']['risk_level']}")
    print(f"  Confidence: {result1['confidence']}")
    print(f"  Explanation: \"{result1['explanation']}\"")
    
    # Test Case 2: Low risk scenario
    print("\n" + "-" * 70)
    print("Test 2: Low Risk Scenario (healthy business)")
    print("-" * 70)
    
    test2_input = {
        "demand_risk": 0.25,
        "supplier_risk": 0.2,
        "warehouse_stress": 0.35,
        "cash_risk": 0.3
    }
    
    result2 = run_inventory_decision_agent(test2_input)
    
    print(f"\nInput: {test2_input}")
    print(f"\nOutput:")
    print(f"  Final Decision:")
    print(f"    - Reorder Timing: {result2['final_decision']['reorder_timing']}")
    print(f"    - Order Strategy: {result2['final_decision']['order_strategy']}")
    print(f"    - Risk Level:     {result2['final_decision']['risk_level']}")
    print(f"  Confidence: {result2['confidence']}")
    print(f"  Explanation: \"{result2['explanation']}\"")
    
    # Test Case 3: Moderate risk with cash constraint
    print("\n" + "-" * 70)
    print("Test 3: Moderate Risk with Cash Constraint")
    print("-" * 70)
    
    test3_input = {
        "demand_risk": 0.5,
        "supplier_risk": 0.45,
        "warehouse_stress": 0.5,
        "cash_risk": 0.8
    }
    
    result3 = run_inventory_decision_agent(test3_input)
    
    print(f"\nInput: {test3_input}")
    print(f"\nOutput:")
    print(f"  Final Decision:")
    print(f"    - Reorder Timing: {result3['final_decision']['reorder_timing']}")
    print(f"    - Order Strategy: {result3['final_decision']['order_strategy']}")
    print(f"    - Risk Level:     {result3['final_decision']['risk_level']}")
    print(f"  Confidence: {result3['confidence']}")
    print(f"  Explanation: \"{result3['explanation']}\"")
    
    # Test Case 4: Missing keys (defensive handling)
    print("\n" + "-" * 70)
    print("Test 4: Partial Input (missing keys)")
    print("-" * 70)
    
    test4_input = {
        "demand_risk": 0.8
        # Other keys missing
    }
    
    result4 = run_inventory_decision_agent(test4_input)
    
    print(f"\nInput: {test4_input}")
    print(f"\nOutput:")
    print(f"  Final Decision:")
    print(f"    - Reorder Timing: {result4['final_decision']['reorder_timing']}")
    print(f"    - Order Strategy: {result4['final_decision']['order_strategy']}")
    print(f"    - Risk Level:     {result4['final_decision']['risk_level']}")
    print(f"  Confidence: {result4['confidence']}")
    print(f"  Note: Missing keys defaulted to 0.5")
    
    # Test Case 5: Empty input (full defaults)
    print("\n" + "-" * 70)
    print("Test 5: Empty Input (all defaults)")
    print("-" * 70)
    
    test5_input = {}
    
    result5 = run_inventory_decision_agent(test5_input)
    
    print(f"\nInput: {test5_input}")
    print(f"\nOutput:")
    print(f"  Final Decision:")
    print(f"    - Reorder Timing: {result5['final_decision']['reorder_timing']}")
    print(f"    - Order Strategy: {result5['final_decision']['order_strategy']}")
    print(f"    - Risk Level:     {result5['final_decision']['risk_level']}")
    print(f"  Confidence: {result5['confidence']}")
    print(f"  Note: All keys defaulted to 0.5 (neutral)")
    
    # Test Case 6: Lead Time Override (LOW risk but long lead time → EARLY)
    print("\n" + "-" * 70)
    print("Test 6: Lead Time Override (LOW risk but effective_lead_time >= 7 days)")
    print("-" * 70)
    
    test6_input = {
        "demand_risk": 0.25,       # LOW
        "supplier_risk": 0.3,      # LOW
        "warehouse_stress": 0.30,  # LOW
        "cash_risk": 0.2,          # LOW
        "effective_lead_time_days": 8.0,  # >= 7 → Should trigger EARLY override
        "lead_time_info": {
            "avg_lead_time_days": 5.0,
            "variability_level": "HIGH",
            "variability_multiplier": 1.6,
            "effective_lead_time_days": 8.0,
            "source": "live"
        }
    }
    
    result6 = run_inventory_decision_agent(test6_input)
    
    print(f"\nInput: demand_risk=0.25, supplier=0.3, warehouse=0.30, cash=0.2")
    print(f"       effective_lead_time_days=8.0 (>= 7 threshold)")
    print(f"\nOutput:")
    print(f"  Final Decision:")
    print(f"    - Reorder Timing: {result6['final_decision']['reorder_timing']}")
    print(f"    - Order Strategy: {result6['final_decision']['order_strategy']}")
    print(f"    - Risk Level:     {result6['final_decision']['risk_level']}")
    print(f"  Confidence: {result6['confidence']}")
    print(f"  Lead Time Context: {result6.get('lead_time_context', {})}")
    print(f"  Explanation: \"{result6['explanation']}\"")
    
    # Verify override worked
    assert result6['final_decision']['reorder_timing'] == 'EARLY', \
        f"Expected EARLY but got {result6['final_decision']['reorder_timing']}"
    assert result6.get('lead_time_context', {}).get('lead_time_override_applied') == True, \
        "Expected lead_time_override_applied=True"
    print(f"\n  ✅ Lead time override verified: LOW risk overridden to EARLY timing")
    
    # Test Case 7: Quantity Recommendation (EOQ-lite with live data)
    print("\n" + "-" * 70)
    print("Test 7: Quantity Recommendation (EOQ-lite with full inputs)")
    print("-" * 70)
    
    test7_input = {
        "demand_risk": 0.6,
        "supplier_risk": 0.5,
        "warehouse_stress": 0.45,
        "cash_risk": 0.4,
        "effective_lead_time_days": 5.0,
        "avg_daily_sales": 100.0,      # 100 units/day
        "current_stock": 300,           # 300 units in warehouse
        "max_capacity": 1000,           # 1000 unit capacity
        "buffer_policy": "MODERATE",    # 1.25x multiplier
    }
    
    result7 = run_inventory_decision_agent(test7_input)
    
    print(f"\nInput: avg_daily_sales=100, lead_time=5d, buffer=MODERATE (1.25x)")
    print(f"       current_stock=300, max_capacity=1000")
    print(f"       Expected: base=500, raw=625, available=700, final=625")
    print(f"\nOutput:")
    print(f"  Final Decision:")
    print(f"    - Reorder Timing: {result7['final_decision']['reorder_timing']}")
    print(f"    - Order Strategy: {result7['final_decision']['order_strategy']}")
    print(f"    - Risk Level:     {result7['final_decision']['risk_level']}")
    print(f"    - Recommended Qty: {result7['final_decision'].get('recommended_quantity_range')}")
    print(f"  Confidence: {result7['confidence']}")
    print(f"  Quantity Context: {result7.get('quantity_context', {})}")
    print(f"  Explanation: \"{result7['explanation']}\"")
    
    # Verify quantity calculation
    qty_ctx = result7.get('quantity_context', {})
    assert qty_ctx.get('base_demand') == 500.0, f"Expected base_demand=500, got {qty_ctx.get('base_demand')}"
    assert qty_ctx.get('raw_quantity') == 625.0, f"Expected raw_quantity=625, got {qty_ctx.get('raw_quantity')}"
    assert qty_ctx.get('warehouse_constrained') == False, "Should not be warehouse constrained"
    print(f"\n  ✅ Quantity calculation verified: 100/day × 5d × 1.25 = 625 units")
    
    # Test Case 8: Quantity with Warehouse Constraint
    print("\n" + "-" * 70)
    print("Test 8: Quantity with Warehouse Constraint")
    print("-" * 70)
    
    test8_input = {
        "demand_risk": 0.7,
        "supplier_risk": 0.6,
        "warehouse_stress": 0.85,
        "cash_risk": 0.5,
        "effective_lead_time_days": 6.0,
        "avg_daily_sales": 150.0,       # 150 units/day
        "current_stock": 850,            # 850 units (warehouse almost full)
        "max_capacity": 1000,            # Only 150 units available
        "buffer_policy": "AGGRESSIVE",   # 1.4x multiplier
    }
    
    result8 = run_inventory_decision_agent(test8_input)
    
    print(f"\nInput: avg_daily_sales=150, lead_time=6d, buffer=AGGRESSIVE (1.4x)")
    print(f"       current_stock=850, max_capacity=1000 (only 150 available)")
    print(f"       Expected: base=900, raw=1260, available=150, final=150 (CONSTRAINED)")
    print(f"\nOutput:")
    print(f"  Final Decision:")
    print(f"    - Reorder Timing: {result8['final_decision']['reorder_timing']}")
    print(f"    - Order Strategy: {result8['final_decision']['order_strategy']}")
    print(f"    - Risk Level:     {result8['final_decision']['risk_level']}")
    print(f"    - Recommended Qty: {result8['final_decision'].get('recommended_quantity_range')}")
    print(f"  Quantity Context: {result8.get('quantity_context', {})}")
    print(f"  Explanation: \"{result8['explanation']}\"")
    
    # Verify warehouse constraint
    qty_ctx = result8.get('quantity_context', {})
    assert qty_ctx.get('warehouse_constrained') == True, "Should be warehouse constrained"
    assert qty_ctx.get('final_quantity') == 150.0, f"Expected final=150, got {qty_ctx.get('final_quantity')}"
    print(f"\n  ✅ Warehouse constraint verified: 1260 → 150 (limited by available space)")
    
    # Test Case 9: Reorder Point - BELOW (needs immediate action)
    print("\n" + "-" * 70)
    print("Test 9: Reorder Point - Stock BELOW ROP (REORDER_NOW)")
    print("-" * 70)
    
    test9_input = {
        "demand_risk": 0.5,
        "supplier_risk": 0.5,
        "warehouse_stress": 0.3,
        "cash_risk": 0.4,
        "effective_lead_time_days": 5.0,
        "avg_daily_sales": 100.0,       # 100 units/day
        "current_stock": 400,            # 400 units (BELOW ROP of 575)
        "max_capacity": 1000,
        "buffer_policy": "MODERATE",     # 1.15x safety for ROP
    }
    # Expected ROP: 100 × 5 × 1.15 = 575 units
    # Current: 400 < 575 → BELOW → REORDER_NOW
    
    result9 = run_inventory_decision_agent(test9_input)
    
    print(f"\nInput: avg_daily_sales=100, lead_time=5d, current_stock=400")
    print(f"       Expected ROP: 100 × 5 × 1.15 = 575 units")
    print(f"       Current (400) < ROP (575) → BELOW → REORDER_NOW")
    print(f"\nOutput:")
    print(f"  Reorder Point: {result9['final_decision'].get('reorder_point')}")
    print(f"  ROP Context: {result9.get('reorder_point_context', {})}")
    print(f"  Explanation: \"{result9['explanation']}\"")
    
    # Verify ROP calculation
    rop_ctx = result9.get('reorder_point_context', {})
    assert rop_ctx.get('reorder_point_units') == 575, f"Expected ROP=575, got {rop_ctx.get('reorder_point_units')}"
    assert rop_ctx.get('status') == "BELOW", f"Expected BELOW, got {rop_ctx.get('status')}"
    assert rop_ctx.get('action') == "REORDER_NOW", f"Expected REORDER_NOW, got {rop_ctx.get('action')}"
    print(f"\n  ✅ ROP BELOW verified: 400 < 575 → REORDER_NOW")
    
    # Test Case 10: Reorder Point - NEAR (prepare to order)
    print("\n" + "-" * 70)
    print("Test 10: Reorder Point - Stock NEAR ROP (PREPARE)")
    print("-" * 70)
    
    test10_input = {
        "demand_risk": 0.5,
        "supplier_risk": 0.5,
        "warehouse_stress": 0.4,
        "cash_risk": 0.4,
        "effective_lead_time_days": 5.0,
        "avg_daily_sales": 100.0,        # 100 units/day
        "current_stock": 620,             # 620 units (NEAR ROP, within 15%)
        "max_capacity": 1000,
        "buffer_policy": "MODERATE",      # 1.15x safety for ROP
    }
    # Expected ROP: 575 units
    # Near threshold: 575 × 1.15 = 661
    # Current: 575 < 620 < 661 → NEAR → PREPARE
    
    result10 = run_inventory_decision_agent(test10_input)
    
    print(f"\nInput: avg_daily_sales=100, lead_time=5d, current_stock=620")
    print(f"       ROP=575, near_threshold=661")
    print(f"       575 < 620 < 661 → NEAR → PREPARE")
    print(f"\nOutput:")
    print(f"  Reorder Point: {result10['final_decision'].get('reorder_point')}")
    print(f"  Days of Cover: {result10.get('reorder_point_context', {}).get('days_of_cover_left')} days")
    
    # Verify NEAR status
    rop_ctx = result10.get('reorder_point_context', {})
    assert rop_ctx.get('status') == "NEAR", f"Expected NEAR, got {rop_ctx.get('status')}"
    assert rop_ctx.get('action') == "PREPARE", f"Expected PREPARE, got {rop_ctx.get('action')}"
    print(f"\n  ✅ ROP NEAR verified: 620 within 15% of 575 → PREPARE")
    
    # Test Case 11: Reorder Point - ABOVE (safe)
    print("\n" + "-" * 70)
    print("Test 11: Reorder Point - Stock ABOVE ROP (SAFE)")
    print("-" * 70)
    
    test11_input = {
        "demand_risk": 0.3,
        "supplier_risk": 0.3,
        "warehouse_stress": 0.5,
        "cash_risk": 0.3,
        "effective_lead_time_days": 5.0,
        "avg_daily_sales": 100.0,        # 100 units/day
        "current_stock": 800,             # 800 units (well ABOVE ROP)
        "max_capacity": 1000,
        "buffer_policy": "MODERATE",
    }
    # Expected ROP: 575 units
    # Current: 800 > 661 (near threshold) → ABOVE → SAFE
    
    result11 = run_inventory_decision_agent(test11_input)
    
    print(f"\nInput: avg_daily_sales=100, lead_time=5d, current_stock=800")
    print(f"       ROP=575, 800 > 661 → ABOVE → SAFE")
    print(f"\nOutput:")
    print(f"  Reorder Point: {result11['final_decision'].get('reorder_point')}")
    print(f"  Days of Cover: {result11.get('reorder_point_context', {}).get('days_of_cover_left')} days")
    
    # Verify ABOVE status
    rop_ctx = result11.get('reorder_point_context', {})
    assert rop_ctx.get('status') == "ABOVE", f"Expected ABOVE, got {rop_ctx.get('status')}"
    assert rop_ctx.get('action') == "SAFE", f"Expected SAFE, got {rop_ctx.get('action')}"
    assert rop_ctx.get('days_of_cover_left') == 8.0, f"Expected 8 days cover, got {rop_ctx.get('days_of_cover_left')}"
    print(f"\n  ✅ ROP ABOVE verified: 800 > 661 → SAFE (8 days cover)")
    
    print("\n" + "=" * 70)
    print("All tests completed successfully!")
    print("=" * 70)
