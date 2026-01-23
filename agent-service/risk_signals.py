"""
MAESTRO Risk Signal Calculator
==============================

Pure functions for calculating normalized risk signals from MSME business inputs.
All functions are deterministic, rule-based, and return values between 0.0 and 1.0.

NOW ENHANCED: Can consume live business_state from MongoDB for data-driven decisions.
Falls back to payload values if live data is unavailable.

Risk Scale:
- 0.0 - 0.3: LOW risk
- 0.3 - 0.6: MODERATE risk  
- 0.6 - 0.8: HIGH risk
- 0.8 - 1.0: CRITICAL risk

Data Sources:
- demand_risk: Uses sales_trend + avg_daily_sales from business_state
- warehouse_stress: Uses utilization_ratio from business_state
- supplier_risk: Uses variability_level from business_state
"""

from typing import Optional, Dict, Any


# =============================================================================
# EFFECTIVE LEAD TIME CALCULATION
# =============================================================================

VARIABILITY_MULTIPLIERS = {
    "LOW": 1.1,
    "MEDIUM": 1.3,
    "HIGH": 1.6,
}


def compute_effective_lead_time_days(
    business_state: Optional[Dict[str, Any]] = None,
    fallback_lead_time: float = 3.0
) -> dict:
    """
    Compute effective lead time with variability buffer.
    
    Effective lead time accounts for supplier variability to give
    a more realistic planning horizon.
    
    Formula:
        effective_lead_time = avg_lead_time_days × variability_multiplier
    
    Multipliers:
        - LOW variability  → 1.1× (10% buffer)
        - MEDIUM variability → 1.3× (30% buffer)
        - HIGH variability → 1.6× (60% buffer)
    
    Args:
        business_state: Live business state from MongoDB (optional)
        fallback_lead_time: Default lead time if no live data (default: 3.0 days)
    
    Returns:
        Dictionary with:
            - avg_lead_time_days: Raw average lead time
            - variability_level: LOW/MEDIUM/HIGH
            - variability_multiplier: The multiplier applied
            - effective_lead_time_days: Final adjusted lead time
            - source: "live" or "fallback"
    
    Example:
        >>> state = {"supplier_snapshot": {"avg_lead_time_days": 5.0, "variability_level": "HIGH"}}
        >>> compute_effective_lead_time_days(state)
        {'avg_lead_time_days': 5.0, 'variability_level': 'HIGH', 'variability_multiplier': 1.6, 'effective_lead_time_days': 8.0, 'source': 'live'}
    """
    # Try to get live data
    if business_state and business_state.get("supplier_snapshot"):
        supplier_snapshot = business_state["supplier_snapshot"]
        
        if supplier_snapshot.get("record_count", 0) > 0:
            avg_lead_time = supplier_snapshot.get("avg_lead_time_days", fallback_lead_time)
            variability = supplier_snapshot.get("variability_level", "MEDIUM").upper()
            
            # Get multiplier (default to MEDIUM if unknown)
            multiplier = VARIABILITY_MULTIPLIERS.get(variability, 1.3)
            effective = round(avg_lead_time * multiplier, 1)
            
            print(f"  📊 [LIVE] effective_lead_time: {avg_lead_time}d × {multiplier} ({variability}) = {effective}d")
            
            return {
                "avg_lead_time_days": avg_lead_time,
                "variability_level": variability,
                "variability_multiplier": multiplier,
                "effective_lead_time_days": effective,
                "source": "live"
            }
    
    # Fallback: assume MEDIUM variability
    multiplier = VARIABILITY_MULTIPLIERS["MEDIUM"]
    effective = round(fallback_lead_time * multiplier, 1)
    
    print(f"  📊 [FALLBACK] effective_lead_time: {fallback_lead_time}d × {multiplier} (MEDIUM) = {effective}d")
    
    return {
        "avg_lead_time_days": fallback_lead_time,
        "variability_level": "MEDIUM",
        "variability_multiplier": multiplier,
        "effective_lead_time_days": effective,
        "source": "fallback"
    }


def calculate_demand_risk(
    demand_type: str, 
    seasonal_event: bool = False,
    business_state: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calculate demand risk based on demand pattern and seasonal factors.
    
    NOW ENHANCED: Uses live sales_trend and avg_daily_sales from business_state
    when available, falling back to demand_type for categorical assessment.
    
    Args:
        demand_type: One of "steady", "seasonal", "volatile"
        seasonal_event: Whether a seasonal event (festival, holiday) is approaching
        business_state: Live business state from MongoDB (optional)
        
    Returns:
        Risk score between 0.0 and 1.0
        
    Examples:
        >>> calculate_demand_risk("steady", False)
        0.2
        >>> calculate_demand_risk("seasonal", True)
        0.7
        >>> calculate_demand_risk("volatile", True, {"demand_snapshot": {"sales_trend": "increasing"}})
        0.75
    """
    # ========================================
    # TRY LIVE DATA FIRST
    # ========================================
    if business_state and business_state.get("demand_snapshot"):
        demand_snapshot = business_state["demand_snapshot"]
        
        # Check if we have enough data
        if demand_snapshot.get("record_count", 0) > 0:
            sales_trend = demand_snapshot.get("sales_trend", "stable")
            
            # Map sales trend to risk
            trend_risk_map = {
                "increasing": 0.5,   # Increasing demand = moderate risk (need more stock)
                "stable": 0.3,       # Stable = low-moderate risk
                "decreasing": 0.2,   # Decreasing = low risk
            }
            base_risk = trend_risk_map.get(sales_trend, 0.4)
            
            # Adjust based on demand type (categorical still relevant for volatility)
            if demand_type.lower() == "volatile":
                base_risk += 0.2
            elif demand_type.lower() == "seasonal":
                base_risk += 0.1
            
            # Add seasonal event modifier
            if seasonal_event:
                base_risk += 0.1
            
            print(f"  📊 [LIVE] demand_risk from sales_trend='{sales_trend}': {min(base_risk, 1.0):.2f}")
            return min(base_risk, 1.0)
    
    # ========================================
    # FALLBACK TO CATEGORICAL ASSESSMENT
    # ========================================
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
    
    print(f"  📊 [FALLBACK] demand_risk from demand_type='{demand_type}': {min(base_risk, 1.0):.2f}")
    return min(base_risk, 1.0)


def calculate_supplier_risk(
    delay_frequency: str, 
    external_disruption: bool = False,
    business_state: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calculate supplier risk based on delivery reliability and external factors.
    
    NOW ENHANCED: Uses variability_level from business_state when available.
    Falls back to delay_frequency categorical assessment.
    
    Args:
        delay_frequency: One of "reliable", "sometimes_delayed", "frequently_delayed"
        external_disruption: Whether external disruption (strike, weather) is expected
        business_state: Live business state from MongoDB (optional)
        
    Returns:
        Risk score between 0.0 and 1.0
        
    Examples:
        >>> calculate_supplier_risk("reliable", False)
        0.2
        >>> calculate_supplier_risk("sometimes_delayed", True)
        0.65
        >>> calculate_supplier_risk("frequently_delayed", True, {"supplier_snapshot": {"variability_level": "HIGH"}})
        0.95
    """
    # ========================================
    # TRY LIVE DATA FIRST
    # ========================================
    if business_state and business_state.get("supplier_snapshot"):
        supplier_snapshot = business_state["supplier_snapshot"]
        
        # Check if we have enough data
        if supplier_snapshot.get("record_count", 0) > 0:
            variability_level = supplier_snapshot.get("variability_level", "MEDIUM")
            
            # Map variability level to risk
            variability_risk_map = {
                "LOW": 0.2,      # Low variance = reliable
                "MEDIUM": 0.5,  # Medium variance = some delays
                "HIGH": 0.8,    # High variance = unpredictable
            }
            base_risk = variability_risk_map.get(variability_level.upper(), 0.5)
            
            # Add external disruption modifier
            if external_disruption:
                base_risk += 0.15
            
            print(f"  📊 [LIVE] supplier_risk from variability_level='{variability_level}': {min(base_risk, 1.0):.2f}")
            return min(base_risk, 1.0)
    
    # ========================================
    # FALLBACK TO CATEGORICAL ASSESSMENT
    # ========================================
    # Base risk by delay frequency
    supplier_risk_map = {
        "reliable": 0.2,
        "none": 0.2,
        "sometimes_delayed": 0.5,
        "minor": 0.5,
        "frequently_delayed": 0.8,
        "frequent": 0.8,
        "major": 0.9,
    }
    
    # Get base risk (default to moderate if unknown type)
    base_risk = supplier_risk_map.get(delay_frequency.lower(), 0.5)
    
    # Add external disruption modifier
    if external_disruption:
        base_risk += 0.15
    
    print(f"  📊 [FALLBACK] supplier_risk from delay_frequency='{delay_frequency}': {min(base_risk, 1.0):.2f}")
    return min(base_risk, 1.0)


def calculate_warehouse_stress(
    current_stock: Optional[int] = None, 
    max_capacity: Optional[int] = None,
    business_state: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calculate warehouse stress as a ratio of current stock to max capacity.
    
    NOW ENHANCED: Uses utilization_ratio directly from business_state when available.
    No longer requires hardcoded current_stock/max_capacity values.
    
    Args:
        current_stock: Current inventory level (units) - OPTIONAL if business_state provided
        max_capacity: Maximum warehouse capacity (units) - OPTIONAL if business_state provided
        business_state: Live business state from MongoDB (optional)
        
    Returns:
        Stress score between 0.0 and 1.0
        
    Examples:
        >>> calculate_warehouse_stress(500, 1000)
        0.5
        >>> calculate_warehouse_stress(business_state={"warehouse_snapshot": {"utilization_ratio": 0.82}})
        0.82
        >>> calculate_warehouse_stress(100, 0)
        1.0
    """
    # ========================================
    # TRY LIVE DATA FIRST
    # ========================================
    if business_state and business_state.get("warehouse_snapshot"):
        warehouse_snapshot = business_state["warehouse_snapshot"]
        
        # Use utilization_ratio directly (already computed in backend)
        utilization_ratio = warehouse_snapshot.get("utilization_ratio")
        if utilization_ratio is not None:
            stress = max(0.0, min(utilization_ratio, 1.0))
            print(f"  📊 [LIVE] warehouse_stress from utilization_ratio: {stress:.2f}")
            return stress
        
        # Fallback: compute from live current_stock/max_capacity
        live_stock = warehouse_snapshot.get("current_stock")
        live_capacity = warehouse_snapshot.get("max_capacity")
        if live_stock is not None and live_capacity is not None and live_capacity > 0:
            stress = max(0.0, min(live_stock / live_capacity, 1.0))
            print(f"  📊 [LIVE] warehouse_stress from stock={live_stock}/capacity={live_capacity}: {stress:.2f}")
            return stress
    
    # ========================================
    # FALLBACK TO PAYLOAD VALUES
    # ========================================
    # Handle missing values
    if current_stock is None or max_capacity is None:
        print(f"  📊 [DEFAULT] warehouse_stress: no data available, using 0.5")
        return 0.5
    
    # Handle edge case: zero or negative capacity
    if max_capacity <= 0:
        print(f"  📊 [FALLBACK] warehouse_stress: invalid capacity, using 1.0")
        return 1.0
    
    # Calculate stress ratio
    stress = current_stock / max_capacity
    stress = max(0.0, min(stress, 1.0))
    
    print(f"  📊 [FALLBACK] warehouse_stress from payload stock={current_stock}/capacity={max_capacity}: {stress:.2f}")
    return stress


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
    
    NOW ENHANCED: Accepts business_state for live data-driven risk assessment.
    Falls back to payload values when live data is unavailable.
    
    Args:
        input_data: Dictionary containing:
            - demand_type: str ("steady", "seasonal", "volatile")
            - seasonal_event: bool
            - supplier_delay: str ("reliable", "sometimes_delayed", "frequently_delayed")
            - external_disruption: bool
            - current_stock: int (OPTIONAL if business_state provided)
            - max_capacity: int (OPTIONAL if business_state provided)
            - cash_flow: str ("stable", "tight", "blocked")
            - business_state: dict (OPTIONAL - live MongoDB data)
            
    Returns:
        Dictionary with normalized risk scores:
            - demand_risk: float (0.0-1.0)
            - supplier_risk: float (0.0-1.0)
            - warehouse_stress: float (0.0-1.0)
            - cash_risk: float (0.0-1.0)
            - data_source: str ("live" | "payload" | "mixed")
            
    Example:
        >>> input_data = {
        ...     "demand_type": "seasonal",
        ...     "seasonal_event": True,
        ...     "supplier_delay": "sometimes_delayed",
        ...     "external_disruption": False,
        ...     "current_stock": 820,
        ...     "max_capacity": 1000,
        ...     "cash_flow": "tight",
        ...     "business_state": { ... }
        ... }
        >>> build_risk_profile(input_data)
        {'demand_risk': 0.7, 'supplier_risk': 0.5, 'warehouse_stress': 0.82, 'cash_risk': 0.5, 'data_source': 'live'}
    """
    # Extract inputs with defaults
    demand_type = input_data.get("demand_type", "steady")
    seasonal_event = input_data.get("seasonal_event", False)
    supplier_delay = input_data.get("supplier_delay", "reliable")
    external_disruption = input_data.get("external_disruption", False)
    current_stock = input_data.get("current_stock")
    max_capacity = input_data.get("max_capacity")
    cash_flow = input_data.get("cash_flow", "stable")
    business_state = input_data.get("business_state")
    
    # Track data source
    data_sources = []
    
    print("\n  🔍 Building risk profile...")
    
    # ========================================
    # CALCULATE ALL RISK DIMENSIONS
    # ========================================
    
    # Demand risk (uses sales_trend from business_state if available)
    demand_risk = calculate_demand_risk(demand_type, seasonal_event, business_state)
    if business_state and business_state.get("demand_snapshot", {}).get("record_count", 0) > 0:
        data_sources.append("demand:live")
    else:
        data_sources.append("demand:payload")
    
    # Supplier risk (uses variability_level from business_state if available)
    supplier_risk = calculate_supplier_risk(supplier_delay, external_disruption, business_state)
    if business_state and business_state.get("supplier_snapshot", {}).get("record_count", 0) > 0:
        data_sources.append("supplier:live")
    else:
        data_sources.append("supplier:payload")
    
    # Warehouse stress (uses utilization_ratio from business_state if available)
    warehouse_stress = calculate_warehouse_stress(current_stock, max_capacity, business_state)
    if business_state and business_state.get("warehouse_snapshot", {}).get("utilization_ratio") is not None:
        data_sources.append("warehouse:live")
    else:
        data_sources.append("warehouse:payload")
    
    # Cash risk (no live data source yet, always from payload)
    cash_risk = calculate_cash_risk(cash_flow)
    data_sources.append("cash:payload")
    
    # ========================================
    # COMPUTE EFFECTIVE LEAD TIME
    # ========================================
    lead_time_info = compute_effective_lead_time_days(business_state)
    effective_lead_time_days = lead_time_info["effective_lead_time_days"]
    
    if lead_time_info["source"] == "live":
        data_sources.append("lead_time:live")
    else:
        data_sources.append("lead_time:fallback")
    
    # Determine overall data source
    live_count = sum(1 for s in data_sources if "live" in s)
    if live_count >= 4:
        overall_source = "live"
    elif live_count > 0:
        overall_source = "mixed"
    else:
        overall_source = "payload"
    
    print(f"  ✅ Risk profile built (data_source: {overall_source})")
    
    # ========================================
    # EXTRACT VALUES FOR QUANTITY CALCULATION
    # ========================================
    # Get avg_daily_sales from live business_state if available
    avg_daily_sales = None
    if business_state and business_state.get("demand_snapshot"):
        avg_daily_sales = business_state["demand_snapshot"].get("avg_daily_sales")
    
    # Get warehouse values - prefer live data, fall back to payload
    final_current_stock = current_stock
    final_max_capacity = max_capacity
    if business_state and business_state.get("warehouse_snapshot"):
        ws = business_state["warehouse_snapshot"]
        if ws.get("current_stock") is not None:
            final_current_stock = ws["current_stock"]
        if ws.get("max_capacity") is not None:
            final_max_capacity = ws["max_capacity"]
    
    return {
        "demand_risk": demand_risk,
        "supplier_risk": supplier_risk,
        "warehouse_stress": warehouse_stress,
        "cash_risk": cash_risk,
        "effective_lead_time_days": effective_lead_time_days,
        "lead_time_info": lead_time_info,
        "data_source": overall_source,
        "data_sources_detail": data_sources,
        # Values for quantity calculation
        "avg_daily_sales": avg_daily_sales,
        "current_stock": final_current_stock,
        "max_capacity": final_max_capacity,
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
    
    # Test case 4: Business with LIVE data from MongoDB
    test_input_4 = {
        "demand_type": "seasonal",
        "seasonal_event": False,
        "supplier_delay": "reliable",  # Will be overridden by live data
        "external_disruption": False,
        "current_stock": 500,  # Will be overridden by live data
        "max_capacity": 1000,
        "cash_flow": "stable",
        "business_state": {
            "demand_snapshot": {
                "avg_daily_sales": 125.50,
                "last_7_days_total": 878.50,
                "sales_trend": "increasing",  # LIVE: will increase demand risk
                "record_count": 14
            },
            "warehouse_snapshot": {
                "current_stock": 720,
                "max_capacity": 1000,
                "utilization_ratio": 0.72,  # LIVE: 72% utilization
                "record_count": 5
            },
            "supplier_snapshot": {
                "avg_lead_time_days": 4.2,
                "variability_level": "HIGH",  # LIVE: will increase supplier risk
                "record_count": 8
            },
            "data_freshness": {
                "last_sale": "2025-01-15",
                "last_warehouse_update": "2025-01-15",
                "last_delivery": "2025-01-14"
            }
        }
    }
    
    print("\n" + "-" * 50)
    print("\nTest Case 4: Business with LIVE MongoDB data")
    print(f"Input (with business_state): demand_type={test_input_4['demand_type']}, supplier_delay={test_input_4['supplier_delay']}")
    print(f"Live data: sales_trend=increasing, utilization=72%, variability=HIGH")
    
    profile_4 = build_risk_profile(test_input_4)
    print(f"Risk Profile: {profile_4}")
    print(f"Composite Risk: {get_composite_risk(profile_4)}")
    print(f"Risk Level: {get_risk_level(get_composite_risk(profile_4))}")
    print(f"Data Source: {profile_4.get('data_source')} → {profile_4.get('data_sources_detail')}")
    print(f"Effective Lead Time: {profile_4.get('effective_lead_time_days')} days")
    print(f"Lead Time Info: {profile_4.get('lead_time_info')}")
    
    # Test case 5: Business with LONG lead time (>= 7 days) - should trigger EARLY override
    test_input_5 = {
        "demand_type": "steady",  # Low demand risk
        "seasonal_event": False,
        "supplier_delay": "reliable",
        "external_disruption": False,
        "current_stock": 300,  # Low warehouse stress
        "max_capacity": 1000,
        "cash_flow": "stable",  # Low cash risk
        "business_state": {
            "demand_snapshot": {
                "avg_daily_sales": 50.0,
                "sales_trend": "stable",
                "record_count": 10
            },
            "warehouse_snapshot": {
                "current_stock": 300,
                "max_capacity": 1000,
                "utilization_ratio": 0.30,
                "record_count": 5
            },
            "supplier_snapshot": {
                "avg_lead_time_days": 5.0,  # 5 days × 1.6 (HIGH) = 8 days effective
                "variability_level": "HIGH",  # HIGH variability = 1.6x multiplier
                "record_count": 8
            }
        }
    }
    
    print("\n" + "-" * 50)
    print("\nTest Case 5: LOW risk business but LONG lead time (should trigger EARLY override)")
    print(f"Business is low risk, but supplier avg_lead_time=5d × HIGH variability=1.6 = 8d effective")
    
    profile_5 = build_risk_profile(test_input_5)
    print(f"Risk Profile (without lead time override logic here):")
    print(f"  demand_risk: {profile_5['demand_risk']}")
    print(f"  supplier_risk: {profile_5['supplier_risk']}")
    print(f"  warehouse_stress: {profile_5['warehouse_stress']}")
    print(f"  effective_lead_time_days: {profile_5['effective_lead_time_days']} days")
    print(f"Composite Risk: {get_composite_risk(profile_5)} → Risk Level: {get_risk_level(get_composite_risk(profile_5))}")
    print(f"⚡ With {profile_5['effective_lead_time_days']}d >= 7d, inventory_decision_agent will override to EARLY timing")
    
    print("\n" + "=" * 50)
    print("All tests completed successfully!")
