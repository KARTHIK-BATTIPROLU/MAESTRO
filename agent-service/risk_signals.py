"""
MAESTRO Risk Signal Calculator
==============================

Pure functions for calculating normalized risk signals from MSME business inputs.
All functions are deterministic, rule-based, and return values between 0.0 and 1.0.

Risk Scale:
- 0.0 - 0.3: LOW risk
- 0.3 - 0.6: MODERATE risk  
- 0.6 - 0.8: HIGH risk
- 0.8 - 1.0: CRITICAL risk
"""


def calculate_demand_risk(demand_type: str, seasonal_event: bool = False) -> float:
    """
    Calculate demand risk based on demand pattern and seasonal factors.
    
    Args:
        demand_type: One of "steady", "seasonal", "volatile"
        seasonal_event: Whether a seasonal event (festival, holiday) is approaching
        
    Returns:
        Risk score between 0.0 and 1.0
        
    Examples:
        >>> calculate_demand_risk("steady", False)
        0.2
        >>> calculate_demand_risk("seasonal", True)
        0.7
        >>> calculate_demand_risk("volatile", True)
        0.9
    """
    # Base risk by demand type
    demand_risk_map = {
        "steady": 0.2,
        "seasonal": 0.6,
        "volatile": 0.8
    }
    
    # Get base risk (default to moderate if unknown type)
    base_risk = demand_risk_map.get(demand_type.lower(), 0.5)
    
    # Add seasonal event modifier
    if seasonal_event:
        base_risk += 0.1
    
    # Cap at 1.0
    return min(base_risk, 1.0)


def calculate_supplier_risk(delay_frequency: str, external_disruption: bool = False) -> float:
    """
    Calculate supplier risk based on delivery reliability and external factors.
    
    Args:
        delay_frequency: One of "reliable", "sometimes_delayed", "frequently_delayed"
        external_disruption: Whether external disruption (strike, weather) is expected
        
    Returns:
        Risk score between 0.0 and 1.0
        
    Examples:
        >>> calculate_supplier_risk("reliable", False)
        0.2
        >>> calculate_supplier_risk("sometimes_delayed", True)
        0.65
        >>> calculate_supplier_risk("frequently_delayed", True)
        0.95
    """
    # Base risk by delay frequency
    supplier_risk_map = {
        "reliable": 0.2,
        "sometimes_delayed": 0.5,
        "frequently_delayed": 0.8
    }
    
    # Get base risk (default to moderate if unknown type)
    base_risk = supplier_risk_map.get(delay_frequency.lower(), 0.5)
    
    # Add external disruption modifier
    if external_disruption:
        base_risk += 0.15
    
    # Cap at 1.0
    return min(base_risk, 1.0)


def calculate_warehouse_stress(current_stock: int, max_capacity: int) -> float:
    """
    Calculate warehouse stress as a ratio of current stock to max capacity.
    
    Args:
        current_stock: Current inventory level (units)
        max_capacity: Maximum warehouse capacity (units)
        
    Returns:
        Stress score between 0.0 and 1.0
        
    Examples:
        >>> calculate_warehouse_stress(500, 1000)
        0.5
        >>> calculate_warehouse_stress(820, 1000)
        0.82
        >>> calculate_warehouse_stress(1200, 1000)
        1.0
        >>> calculate_warehouse_stress(100, 0)
        1.0
    """
    # Handle edge case: zero or negative capacity
    if max_capacity <= 0:
        return 1.0
    
    # Calculate stress ratio
    stress = current_stock / max_capacity
    
    # Cap between 0.0 and 1.0
    return max(0.0, min(stress, 1.0))


def calculate_cash_risk(cash_flow_level: str) -> float:
    """
    Calculate cash flow risk based on business financial situation.
    
    Args:
        cash_flow_level: One of "stable", "tight", "blocked"
        
    Returns:
        Risk score between 0.0 and 1.0
        
    Examples:
        >>> calculate_cash_risk("stable")
        0.2
        >>> calculate_cash_risk("tight")
        0.5
        >>> calculate_cash_risk("blocked")
        0.8
    """
    # Cash risk mapping
    cash_risk_map = {
        "stable": 0.2,
        "tight": 0.5,
        "blocked": 0.8
    }
    
    # Get risk (default to moderate if unknown level)
    return cash_risk_map.get(cash_flow_level.lower(), 0.5)


def build_risk_profile(input_data: dict) -> dict:
    """
    Build complete risk profile from business input data.
    
    This is the main entry point for risk calculation. It takes raw business
    inputs and returns normalized risk scores for all four dimensions.
    
    Args:
        input_data: Dictionary containing:
            - demand_type: str ("steady", "seasonal", "volatile")
            - seasonal_event: bool
            - supplier_delay: str ("reliable", "sometimes_delayed", "frequently_delayed")
            - external_disruption: bool
            - current_stock: int
            - max_capacity: int
            - cash_flow: str ("stable", "tight", "blocked")
            
    Returns:
        Dictionary with normalized risk scores:
            - demand_risk: float (0.0-1.0)
            - supplier_risk: float (0.0-1.0)
            - warehouse_stress: float (0.0-1.0)
            - cash_risk: float (0.0-1.0)
            
    Example:
        >>> input_data = {
        ...     "demand_type": "seasonal",
        ...     "seasonal_event": True,
        ...     "supplier_delay": "sometimes_delayed",
        ...     "external_disruption": False,
        ...     "current_stock": 820,
        ...     "max_capacity": 1000,
        ...     "cash_flow": "tight"
        ... }
        >>> build_risk_profile(input_data)
        {'demand_risk': 0.7, 'supplier_risk': 0.5, 'warehouse_stress': 0.82, 'cash_risk': 0.5}
    """
    # Extract inputs with defaults
    demand_type = input_data.get("demand_type", "steady")
    seasonal_event = input_data.get("seasonal_event", False)
    supplier_delay = input_data.get("supplier_delay", "reliable")
    external_disruption = input_data.get("external_disruption", False)
    current_stock = input_data.get("current_stock", 0)
    max_capacity = input_data.get("max_capacity", 1000)
    cash_flow = input_data.get("cash_flow", "stable")
    
    # Calculate all risk dimensions
    return {
        "demand_risk": calculate_demand_risk(demand_type, seasonal_event),
        "supplier_risk": calculate_supplier_risk(supplier_delay, external_disruption),
        "warehouse_stress": calculate_warehouse_stress(current_stock, max_capacity),
        "cash_risk": calculate_cash_risk(cash_flow)
    }


def get_composite_risk(risk_profile: dict) -> float:
    """
    Calculate composite risk score from all risk dimensions.
    
    Args:
        risk_profile: Dictionary with demand_risk, supplier_risk, warehouse_stress, cash_risk
        
    Returns:
        Average risk score (0.0-1.0)
        
    Example:
        >>> profile = {"demand_risk": 0.7, "supplier_risk": 0.5, "warehouse_stress": 0.82, "cash_risk": 0.5}
        >>> get_composite_risk(profile)
        0.63
    """
    risks = [
        risk_profile.get("demand_risk", 0.5),
        risk_profile.get("supplier_risk", 0.5),
        risk_profile.get("warehouse_stress", 0.5),
        risk_profile.get("cash_risk", 0.5)
    ]
    return round(sum(risks) / len(risks), 2)


def get_risk_level(score: float) -> str:
    """
    Convert numeric risk score to categorical level.
    
    Args:
        score: Risk score between 0.0 and 1.0
        
    Returns:
        Risk level: "LOW", "MODERATE", "HIGH", or "CRITICAL"
        
    Example:
        >>> get_risk_level(0.25)
        'LOW'
        >>> get_risk_level(0.55)
        'MODERATE'
        >>> get_risk_level(0.75)
        'HIGH'
        >>> get_risk_level(0.9)
        'CRITICAL'
    """
    if score < 0.3:
        return "LOW"
    elif score < 0.6:
        return "MODERATE"
    elif score < 0.8:
        return "HIGH"
    else:
        return "CRITICAL"


# ============================================
# TESTING / DEMO
# ============================================

if __name__ == "__main__":
    # Example usage
    print("=" * 50)
    print("MAESTRO Risk Signal Calculator - Demo")
    print("=" * 50)
    
    # Test case 1: Moderate risk business
    test_input_1 = {
        "demand_type": "seasonal",
        "seasonal_event": True,
        "supplier_delay": "sometimes_delayed",
        "external_disruption": False,
        "current_stock": 820,
        "max_capacity": 1000,
        "cash_flow": "tight"
    }
    
    print("\nTest Case 1: Seasonal business with tight cash flow")
    print(f"Input: {test_input_1}")
    
    profile_1 = build_risk_profile(test_input_1)
    print(f"Risk Profile: {profile_1}")
    print(f"Composite Risk: {get_composite_risk(profile_1)}")
    print(f"Risk Level: {get_risk_level(get_composite_risk(profile_1))}")
    
    # Test case 2: High risk business
    test_input_2 = {
        "demand_type": "volatile",
        "seasonal_event": True,
        "supplier_delay": "frequently_delayed",
        "external_disruption": True,
        "current_stock": 950,
        "max_capacity": 1000,
        "cash_flow": "blocked"
    }
    
    print("\n" + "-" * 50)
    print("\nTest Case 2: High-risk volatile business")
    print(f"Input: {test_input_2}")
    
    profile_2 = build_risk_profile(test_input_2)
    print(f"Risk Profile: {profile_2}")
    print(f"Composite Risk: {get_composite_risk(profile_2)}")
    print(f"Risk Level: {get_risk_level(get_composite_risk(profile_2))}")
    
    # Test case 3: Low risk business
    test_input_3 = {
        "demand_type": "steady",
        "seasonal_event": False,
        "supplier_delay": "reliable",
        "external_disruption": False,
        "current_stock": 300,
        "max_capacity": 1000,
        "cash_flow": "stable"
    }
    
    print("\n" + "-" * 50)
    print("\nTest Case 3: Low-risk stable business")
    print(f"Input: {test_input_3}")
    
    profile_3 = build_risk_profile(test_input_3)
    print(f"Risk Profile: {profile_3}")
    print(f"Composite Risk: {get_composite_risk(profile_3)}")
    print(f"Risk Level: {get_risk_level(get_composite_risk(profile_3))}")
    
    print("\n" + "=" * 50)
    print("All tests completed successfully!")
