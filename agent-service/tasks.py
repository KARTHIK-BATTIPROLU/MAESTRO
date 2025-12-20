"""
MAESTRO - MSME Inventory Intelligence System
Production Task Definitions for CrewAI Agents

5-STAGE PIPELINE:
1. Intake Analysis → Structured Signals
2. External Risk Research → Risk Modifiers
3. Warehouse Assessment → Feasibility Constraints
4. Inventory Decision → Correlated Recommendation
5. Final Orchestration → User-Ready Output

DETERMINISTIC TASKS:
- inventory_decision_task_deterministic → Uses rule-based decision engine
"""
from crewai import Task

# Import the deterministic decision function from agents
from agents import execute_inventory_decision


def create_intake_analysis_task(agent, user_responses: dict):
    """
    Task 1: Router/Intake Agent
    Convert MSME answers into structured risk signals
    """
    
    # Format the user responses for the agent
    formatted_responses = "\n".join([
        f"Q{i+1}: {key}\nA: {value}\n"
        for i, (key, value) in enumerate(user_responses.items())
    ])
    
    return Task(
        description=f"""
        Analyze the following MSME business owner's 10 responses and extract STRUCTURED RISK SIGNALS.
        
        === BUSINESS OWNER'S RESPONSES ===
        {formatted_responses}
        === END OF RESPONSES ===
        
        Your task is to:
        1. Read each response carefully
        2. Extract risk indicators from qualitative descriptions
        3. Convert them into numerical scores (0.0 to 1.0)
        4. Build a structured business profile
        
        SCORING GUIDE:
        - Demand Variability: Score based on how unpredictable their sales are
          * "Steady sales" → 0.2-0.3
          * "Some seasonal variation" → 0.4-0.5
          * "Highly seasonal/volatile" → 0.7-0.8
          * "Completely unpredictable" → 0.85-0.95
        
        - Supplier Delay Risk: Score based on delivery reliability mentioned
          * "Always on time" → 0.1-0.2
          * "Usually reliable, occasional delays" → 0.4-0.5
          * "Frequent delays" → 0.7-0.8
          * "Unreliable, constant issues" → 0.85-0.95
        
        - Warehouse Capacity Stress: Score based on storage constraints
          * "Plenty of space" → 0.1-0.3
          * "Adequate but need to manage" → 0.4-0.6
          * "Limited space, careful planning needed" → 0.7-0.8
          * "Critical, always full" → 0.85-0.95
        
        - Cash Flow Sensitivity: Score based on financial flexibility
          * "No budget constraints" → 0.1-0.2
          * "Some budget awareness needed" → 0.4-0.5
          * "Tight cash flow, careful spending" → 0.7-0.8
          * "Very tight, every rupee counts" → 0.85-0.95
        
        OUTPUT YOUR ANALYSIS AS VALID JSON ONLY.
        """,
        
        expected_output="""{
            "demand_variability": <0.0 to 1.0>,
            "supplier_delay_risk": <0.0 to 1.0>,
            "warehouse_capacity_stress": <0.0 to 1.0>,
            "cash_flow_sensitivity": <0.0 to 1.0>,
            "business_context": {
                "industry": "<industry type>",
                "products": "<main products>",
                "scale": "<small/medium/large>",
                "current_method": "<how they currently reorder>",
                "main_problems": ["problem1", "problem2"],
                "desired_outcome": "<what they want>"
            },
            "signals": {
                "demand_pattern": "steady|seasonal|volatile|unpredictable",
                "supplier_reliability": "reliable|moderate|unreliable|critical",
                "storage_situation": "ample|adequate|limited|critical",
                "stockout_history": "rare|occasional|frequent|constant",
                "overstock_history": "rare|occasional|frequent|constant"
            }
        }""",
        
        agent=agent
    )


def create_external_risk_task(agent, business_context: dict):
    """
    Task 2: Research/External Risk Agent
    Analyze external factors and provide risk modifiers
    """
    
    industry = business_context.get('industry', 'retail')
    products = business_context.get('products', 'general goods')
    
    return Task(
        description=f"""
        Analyze EXTERNAL FACTORS that could affect inventory risks for this business:
        
        BUSINESS CONTEXT:
        - Industry: {industry}
        - Products: {products}
        - Current Date Context: Consider current season, upcoming events, economic conditions
        
        Your task is to:
        1. Identify relevant seasonal factors (festivals, holidays, weather)
        2. Consider market conditions for this industry
        3. Assess supply chain factors (transport, supplier industries)
        4. Calculate risk modifiers
        
        RISK MODIFIER RULES:
        - Positive values (+0.05 to +0.30) INCREASE risk
        - Negative values (-0.05 to -0.20) DECREASE risk
        - Zero (0.0) means no external impact
        
        EXAMPLES:
        - Diwali approaching for retail business → demand_modifier: +0.20
        - Off-season for seasonal products → demand_modifier: -0.15
        - Transport strike risk → lead_time_modifier: +0.25
        - Stable economic conditions → demand_modifier: +0.00
        
        OUTPUT YOUR ANALYSIS AS VALID JSON ONLY.
        """,
        
        expected_output="""{
            "external_demand_risk_modifier": <-0.2 to +0.3>,
            "external_lead_time_risk_modifier": <-0.2 to +0.3>,
            "external_factors": [
                {
                    "factor": "<description>",
                    "impact": "demand|supply|both",
                    "severity": "low|medium|high",
                    "timeframe": "<when relevant>"
                }
            ],
            "market_outlook": "favorable|neutral|challenging",
            "recommendations": ["<specific external-based advice>"]
        }""",
        
        agent=agent
    )


def create_warehouse_assessment_task(agent, intake_signals: dict):
    """
    Task 3: Warehouse Agent
    Assess storage constraints and feasibility limits
    """
    
    storage_situation = intake_signals.get('signals', {}).get('storage_situation', 'adequate')
    warehouse_stress = intake_signals.get('warehouse_capacity_stress', 0.5)
    
    return Task(
        description=f"""
        Analyze WAREHOUSE AND STORAGE CONSTRAINTS for ordering feasibility.
        
        CURRENT SIGNALS:
        - Storage Situation: {storage_situation}
        - Initial Warehouse Stress Score: {warehouse_stress}
        
        Your task is to:
        1. Assess realistic storage capacity constraints
        2. Determine feasible order sizes
        3. Recommend optimal ordering frequency
        4. Identify critical storage constraints
        
        FEASIBILITY CATEGORIES:
        - HIGH: Can handle bulk orders, plenty of space
        - MEDIUM: Standard orders OK, some planning needed
        - LOW: Must use smaller, frequent orders
        - CRITICAL: Severe constraints, split orders mandatory
        
        FREQUENCY RECOMMENDATIONS:
        - High stress + Limited space → daily or 2-3x weekly
        - Medium stress → weekly orders
        - Low stress → biweekly or monthly bulk orders
        
        OUTPUT YOUR ANALYSIS AS VALID JSON ONLY.
        """,
        
        expected_output="""{
            "estimated_capacity_used_pct": <0-100>,
            "warehouse_stress": <0.0 to 1.0>,
            "feasible_order_limit": "HIGH|MEDIUM|LOW|CRITICAL",
            "max_order_recommendation": "<description>",
            "optimal_frequency": "daily|2-3x weekly|weekly|biweekly|monthly",
            "constraints": [
                {
                    "type": "<constraint type>",
                    "severity": "low|medium|high|critical",
                    "recommendation": "<how to handle>"
                }
            ],
            "storage_strategy": "<recommended approach>"
        }""",
        
        agent=agent
    )


def create_inventory_decision_task(agent, all_signals: dict):
    """
    Task 4: Inventory Decision Agent (CORE)
    Correlate all risks and produce ONE clear reorder decision
    """
    
    # Extract all signals
    demand_risk = all_signals.get('demand_variability', 0.5)
    supplier_risk = all_signals.get('supplier_delay_risk', 0.5)
    warehouse_stress = all_signals.get('warehouse_stress', 0.5)
    cash_sensitivity = all_signals.get('cash_flow_sensitivity', 0.5)
    
    # Apply external modifiers if available
    ext_demand_mod = all_signals.get('external_demand_risk_modifier', 0)
    ext_supply_mod = all_signals.get('external_lead_time_risk_modifier', 0)
    
    adjusted_demand = min(1.0, max(0.0, demand_risk + ext_demand_mod))
    adjusted_supplier = min(1.0, max(0.0, supplier_risk + ext_supply_mod))
    
    return Task(
        description=f"""
        CORRELATE ALL RISK SIGNALS and produce ONE CLEAR REORDER DECISION.
        
        === RISK SIGNALS TO CORRELATE ===
        
        BASE SIGNALS (from intake):
        - Demand Variability: {demand_risk}
        - Supplier Delay Risk: {supplier_risk}
        - Warehouse Stress: {warehouse_stress}
        - Cash Flow Sensitivity: {cash_sensitivity}
        
        EXTERNAL MODIFIERS:
        - External Demand Modifier: {ext_demand_mod:+.2f}
        - External Lead Time Modifier: {ext_supply_mod:+.2f}
        
        ADJUSTED SIGNALS:
        - Adjusted Demand Risk: {adjusted_demand:.2f}
        - Adjusted Supplier Risk: {adjusted_supplier:.2f}
        
        === DECISION RULES ===
        
        TIMING DECISION:
        - If demand_risk > 0.6 AND supplier_risk > 0.6 → EARLY (reorder 5-14 days earlier)
        - If demand_risk < 0.4 AND supplier_risk < 0.4 → NORMAL (standard timing)
        - If supplier_risk > 0.7 regardless of demand → EARLY (buffer for delays)
        - Otherwise → EARLY with small buffer
        
        QUANTITY STRATEGY:
        - If warehouse_stress > 0.7 → SPLIT_ORDERS (smaller, more frequent)
        - If warehouse_stress < 0.4 AND demand_risk > 0.6 → BULK_ORDER (stock up)
        - If cash_sensitivity > 0.7 → FREQUENT_SMALL_ORDERS (preserve cash)
        - Otherwise → STANDARD_ORDERS
        
        RISK LEVEL:
        - Calculate composite: (demand + supplier + warehouse + cash) / 4
        - If composite > 0.7 → HIGH
        - If composite > 0.5 → MODERATE
        - If composite > 0.3 → LOW
        - Otherwise → MINIMAL
        
        OUTPUT YOUR DECISION AS VALID JSON ONLY.
        """,
        
        expected_output="""{
            "reorder_timing": "EARLY|NORMAL|DELAYED",
            "timing_days_adjustment": <-14 to +7>,
            "order_quantity_strategy": "BULK_ORDER|STANDARD_ORDERS|SPLIT_ORDERS|FREQUENT_SMALL_ORDERS",
            "quantity_adjustment_pct": <-30 to +30>,
            "risk_level": "MINIMAL|LOW|MODERATE|HIGH|CRITICAL",
            "composite_risk_score": <0.0 to 1.0>,
            "primary_risk_factor": "<what's driving the decision>",
            "decision_reasoning": "<2-3 sentence explanation>",
            "specific_actions": [
                "<action 1>",
                "<action 2>",
                "<action 3>"
            ]
        }""",
        
        agent=agent
    )


def create_orchestrator_task(agent, all_analysis: dict):
    """
    Task 5: Decision Orchestrator
    Final authority - create user-ready output
    """
    
    # Extract key pieces from all analysis
    business_context = all_analysis.get('business_context', {})
    signals = all_analysis.get('signals', {})
    decision = all_analysis.get('decision', {})
    warehouse = all_analysis.get('warehouse', {})
    external = all_analysis.get('external', {})
    
    return Task(
        description=f"""
        You are the FINAL AUTHORITY. Create the user-facing recommendation.
        
        === ALL ANALYSIS DATA ===
        
        BUSINESS CONTEXT:
        {business_context}
        
        RISK SIGNALS:
        {signals}
        
        WAREHOUSE ASSESSMENT:
        {warehouse}
        
        EXTERNAL FACTORS:
        {external}
        
        DECISION ENGINE OUTPUT:
        {decision}
        
        === YOUR TASK ===
        
        1. VALIDATE the decision makes sense given all the data
        2. CREATE a clear, user-friendly recommendation
        3. EXPLAIN why in simple business language
        4. LIST immediate actions
        
        THE OUTPUT MUST MATCH THIS EXACT FORMAT for the frontend to display:
        
        {{
            "final_decision": {{
                "reorder_timing": "EARLY|NORMAL|DELAYED",
                "order_strategy": "<strategy in plain English>",
                "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
                "confidence": <0.7 to 1.0>
            }},
            "what_we_understood": {{
                "demand_situation": "<1 clear sentence about their demand>",
                "supplier_situation": "<1 clear sentence about their suppliers>",
                "warehouse_situation": "<1 clear sentence about their storage>",
                "key_constraint": "<the main limiting factor>"
            }},
            "detected_risks": [
                {{
                    "risk": "<risk name>",
                    "level": "LOW|MODERATE|HIGH|CRITICAL",
                    "explanation": "<why this matters to them>"
                }}
            ],
            "recommendation": {{
                "timing": "<when to reorder in plain English>",
                "quantity": "<how much to order in plain English>",
                "method": "<how to manage orders in plain English>"
            }},
            "why_this_decision": "<2-3 sentence explanation a business owner can understand>",
            "immediate_actions": [
                "<specific action 1>",
                "<specific action 2>",
                "<specific action 3>"
            ],
            "warnings": ["<any critical warnings, or empty array>"]
        }}
        
        RULES:
        - Use simple business language, no jargon
        - Be specific, not vague
        - Connect the risks to the recommendation clearly
        - Make actions immediately actionable
        
        OUTPUT VALID JSON ONLY.
        """,
        
        expected_output="""Valid JSON matching the exact format specified above.""",
        
        agent=agent
    )


# =============================================================================
# DETERMINISTIC INVENTORY DECISION TASK
# =============================================================================

def create_inventory_decision_task_deterministic(
    agent,
    risk_inputs: dict
) -> Task:
    """
    Create a deterministic Inventory Decision Task.
    
    This task uses the rule-based decision engine (no LLM) to produce
    consistent, explainable inventory recommendations. It wraps the
    deterministic `execute_inventory_decision` function.
    
    Args:
        agent: The CrewAI agent to assign this task to
        risk_inputs: Dictionary containing normalized risk values:
            - demand_risk (float): 0.0 to 1.0
            - supplier_risk (float): 0.0 to 1.0
            - warehouse_stress (float): 0.0 to 1.0
            - cash_risk (float): 0.0 to 1.0
    
    Returns:
        CrewAI Task configured for inventory decision-making
    
    Output Format:
        {
            "final_decision": {
                "reorder_timing": "EARLY | NORMAL | DELAYED",
                "order_strategy": "SPLIT_ORDERS | FREQUENT_SMALL | BULK",
                "risk_level": "HIGH | MODERATE | LOW"
            },
            "explanation": "Human-readable explanation...",
            "confidence": 0.85
        }
    
    Usage:
        from tasks import create_inventory_decision_task_deterministic
        from agents import create_inventory_decision_strategist_agent
        
        agent = create_inventory_decision_strategist_agent(llm)
        risk_inputs = {
            "demand_risk": 0.75,
            "supplier_risk": 0.65,
            "warehouse_stress": 0.82,
            "cash_risk": 0.7
        }
        task = create_inventory_decision_task_deterministic(agent, risk_inputs)
    """
    # Validate and extract inputs with safe defaults
    DEFAULT_RISK = 0.5
    
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
    
    # Format risk values for task description
    risk_summary = f"""
    - Demand Risk:      {demand_risk:.2f}
    - Supplier Risk:    {supplier_risk:.2f}
    - Warehouse Stress: {warehouse_stress:.2f}
    - Cash Risk:        {cash_risk:.2f}
    """
    
    return Task(
        description=f"""
        Analyze correlated demand, supplier, warehouse, and cash risks to produce 
        a SINGLE OPTIMAL inventory reorder decision for an MSME business.
        
        === NORMALIZED RISK INPUTS ===
        {risk_summary}
        
        === YOUR TASK ===
        
        Use the inventory_decision_tool to process these risk inputs and generate
        the final recommendation. The tool will:
        
        1. Calculate the composite risk score (weighted average)
        2. Classify the overall risk level (HIGH/MODERATE/LOW)
        3. Determine reorder timing (EARLY/NORMAL/DELAYED)
        4. Determine order strategy (SPLIT_ORDERS/FREQUENT_SMALL/BULK)
        5. Generate a human-readable explanation
        6. Calculate confidence score
        
        IMPORTANT:
        - Do NOT modify the tool's output
        - Do NOT add your own analysis
        - Return the tool's result exactly as-is
        - The tool provides deterministic, rule-based decisions
        
        Call the inventory_decision_tool with:
        - demand_risk: {demand_risk}
        - supplier_risk: {supplier_risk}
        - warehouse_stress: {warehouse_stress}
        - cash_risk: {cash_risk}
        """,
        
        expected_output="""{
            "final_decision": {
                "reorder_timing": "EARLY | NORMAL | DELAYED",
                "order_strategy": "SPLIT_ORDERS | FREQUENT_SMALL | BULK",
                "risk_level": "HIGH | MODERATE | LOW"
            },
            "explanation": "<Human-readable explanation of the decision>",
            "confidence": <0.45 to 0.85>
        }""",
        
        agent=agent
    )


def run_inventory_decision_task_standalone(risk_inputs: dict) -> dict:
    """
    Run the inventory decision task WITHOUT CrewAI overhead.
    
    This is a direct passthrough to the deterministic decision engine,
    useful for testing, API endpoints, or when the full CrewAI pipeline
    is not needed.
    
    Args:
        risk_inputs: Dictionary containing:
            - demand_risk (float): 0.0 to 1.0
            - supplier_risk (float): 0.0 to 1.0
            - warehouse_stress (float): 0.0 to 1.0
            - cash_risk (float): 0.0 to 1.0
    
    Returns:
        Complete decision output dictionary with:
            - final_decision: {reorder_timing, order_strategy, risk_level}
            - explanation: Human-readable string
            - confidence: Float 0.0 to 1.0
    
    Example:
        >>> result = run_inventory_decision_task_standalone({
        ...     "demand_risk": 0.75,
        ...     "supplier_risk": 0.65,
        ...     "warehouse_stress": 0.82,
        ...     "cash_risk": 0.7
        ... })
        >>> print(result["final_decision"]["reorder_timing"])
        'EARLY'
    """
    return execute_inventory_decision(risk_inputs)


# =============================================================================
# DEMO / TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MAESTRO Tasks Module - Test")
    print("=" * 70)
    
    # Test the standalone task function
    print("\nTesting run_inventory_decision_task_standalone()...")
    
    test_inputs = [
        {
            "name": "High Risk Business",
            "demand_risk": 0.75,
            "supplier_risk": 0.65,
            "warehouse_stress": 0.82,
            "cash_risk": 0.7
        },
        {
            "name": "Low Risk Business",
            "demand_risk": 0.25,
            "supplier_risk": 0.2,
            "warehouse_stress": 0.35,
            "cash_risk": 0.3
        },
        {
            "name": "Cash Constrained Business",
            "demand_risk": 0.5,
            "supplier_risk": 0.4,
            "warehouse_stress": 0.5,
            "cash_risk": 0.8
        }
    ]
    
    for test in test_inputs:
        name = test.pop("name")
        print(f"\n{'─' * 70}")
        print(f"Test: {name}")
        print(f"{'─' * 70}")
        
        result = run_inventory_decision_task_standalone(test)
        
        print(f"\nInput Risks:")
        print(f"  Demand:    {test.get('demand_risk', 0.5)}")
        print(f"  Supplier:  {test.get('supplier_risk', 0.5)}")
        print(f"  Warehouse: {test.get('warehouse_stress', 0.5)}")
        print(f"  Cash:      {test.get('cash_risk', 0.5)}")
        
        print(f"\nDecision:")
        print(f"  Timing:     {result['final_decision']['reorder_timing']}")
        print(f"  Strategy:   {result['final_decision']['order_strategy']}")
        print(f"  Risk Level: {result['final_decision']['risk_level']}")
        print(f"  Confidence: {result['confidence']}")
        
        # Restore name for potential reuse
        test["name"] = name
    
    print(f"\n{'=' * 70}")
    print("All tests completed!")
    print("=" * 70)
