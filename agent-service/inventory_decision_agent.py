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
    # Step 4: Build human-readable explanation
    # =========================================================================
    # Prepare full risk inputs for explanation
    explanation_inputs = {
        "risk_level": risk_level,
        "demand_risk": demand_risk,
        "supplier_risk": supplier_risk,
        "warehouse_stress": warehouse_stress,
        "cash_risk": cash_risk
    }
    
    explanation = build_decision_explanation(explanation_inputs, decision)
    
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
            "risk_level": risk_level
        },
        "explanation": explanation,
        "confidence": confidence
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
    
    print("\n" + "=" * 70)
    print("All tests completed successfully!")
    print("=" * 70)
