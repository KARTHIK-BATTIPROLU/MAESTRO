"""
MAESTRO - MSME Inventory Intelligence System
Production Agent Definitions using CrewAI

5-AGENT SYSTEM:
1. Router/Intake Agent - Convert answers to structured signals
2. Research/External Risk Agent - Adjust risk using external data
3. Warehouse Agent - Enforce physical feasibility
4. Inventory Decision Agent - Correlate risks and decide
5. Decision Orchestrator - Final authority and explainability

HYBRID AGENTS:
- Inventory Decision Strategist Agent - Uses deterministic decision engine
"""
from crewai import Agent
from crewai.tools import tool
from config import Config

# Import the deterministic decision engine
from inventory_decision_agent import run_inventory_decision_agent


def create_router_intake_agent(llm):
    """
    Agent 1: Router / Intake Agent
    
    Goal: Convert MSME answers into structured risk signals
    
    Output Format:
    {
        "demand_variability": 0.0-1.0,
        "supplier_delay_risk": 0.0-1.0,
        "warehouse_capacity_stress": 0.0-1.0,
        "cash_flow_sensitivity": 0.0-1.0,
        "business_context": {...}
    }
    """
    return Agent(
        role="MSME Business Signal Extractor",
        goal="""Analyze the MSME business owner's 10 responses and extract STRUCTURED RISK SIGNALS.
        
        You MUST output a JSON object with these exact fields:
        
        {
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
        }
        
        SCORING RULES:
        - 0.0-0.3 = LOW risk/variability
        - 0.4-0.6 = MODERATE risk/variability  
        - 0.7-0.85 = HIGH risk/variability
        - 0.86-1.0 = CRITICAL risk/variability
        
        Base your scores on the actual answers provided. Be precise.""",
        
        backstory="""You are an expert business analyst who converts qualitative MSME owner 
        responses into quantitative risk metrics. You have analyzed thousands of small businesses
        and can accurately score:
        - Demand volatility from sales patterns described
        - Supplier risk from delivery reliability mentioned
        - Warehouse stress from storage constraints shared
        - Cash flow sensitivity from budget concerns expressed
        
        You always output valid JSON with precise numerical scores.""",
        
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_research_risk_agent(llm):
    """
    Agent 2: Research / External Risk Agent
    
    Goal: Adjust risk signals based on external factors
    
    Output Format:
    {
        "external_demand_risk_modifier": +/- 0.0-0.3,
        "external_lead_time_risk_modifier": +/- 0.0-0.3,
        "external_factors": [...]
    }
    """
    return Agent(
        role="External Risk Intelligence Analyst",
        goal="""Analyze external factors that could affect the MSME's inventory risks.
        
        Based on the business context (industry, products, location), identify:
        
        1. SEASONAL FACTORS
           - Upcoming festivals/holidays affecting demand
           - Weather patterns impacting supply chains
           - Industry-specific peak seasons
        
        2. MARKET FACTORS
           - Economic conditions
           - Industry trends
           - Competitor activities
        
        3. SUPPLY CHAIN FACTORS
           - Known transport disruptions
           - Supplier industry conditions
           - Raw material availability
        
        OUTPUT FORMAT (JSON):
        {
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
        }
        
        Positive modifiers INCREASE risk, negative modifiers DECREASE risk.""",
        
        backstory="""You are a market intelligence specialist who tracks external factors
        affecting MSME supply chains. You monitor:
        - Festival calendars and seasonal demand patterns
        - Transport and logistics disruptions
        - Industry-specific news and trends
        - Economic indicators affecting small businesses
        
        You provide precise risk adjustments based on real external conditions.""",
        
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_warehouse_agent(llm):
    """
    Agent 3: Warehouse Agent
    
    Goal: Enforce physical feasibility constraints
    
    Output Format:
    {
        "warehouse_stress": 0.0-1.0,
        "feasible_order_limit": "HIGH|MEDIUM|LOW|CRITICAL",
        "storage_recommendation": "..."
    }
    """
    return Agent(
        role="Warehouse Capacity Analyst",
        goal="""Analyze warehouse and storage constraints to determine feasible ordering limits.
        
        Based on the MSME's storage situation, calculate:
        
        1. CAPACITY ANALYSIS
           - Current storage utilization estimate
           - Available space for new inventory
           - Handling capacity constraints
        
        2. FEASIBILITY ASSESSMENT
           - Maximum feasible order size
           - Optimal order frequency given space
           - Storage cost implications
        
        3. CONSTRAINT IDENTIFICATION
           - Physical space limits
           - Handling/processing bottlenecks
           - Perishability or special storage needs
        
        OUTPUT FORMAT (JSON):
        {
            "estimated_capacity_used_pct": <0-100>,
            "warehouse_stress": <0.0 to 1.0>,
            "feasible_order_limit": "HIGH|MEDIUM|LOW|CRITICAL",
            "max_order_recommendation": "<description>",
            "optimal_frequency": "daily|weekly|biweekly|monthly",
            "constraints": [
                {
                    "type": "<constraint type>",
                    "severity": "low|medium|high|critical",
                    "recommendation": "<how to handle>"
                }
            ],
            "storage_strategy": "<recommended approach>"
        }
        
        STRESS LEVELS:
        - 0.0-0.5: Ample space, can order freely
        - 0.5-0.7: Adequate, some planning needed
        - 0.7-0.85: Limited, careful ordering required
        - 0.85-1.0: Critical, split orders mandatory""",
        
        backstory="""You are a warehouse operations expert who helps MSMEs optimize their 
        limited storage space. You understand:
        - Small business storage constraints
        - Cost of holding excess inventory
        - Balancing stock levels with available space
        - Creative solutions for space-limited businesses
        
        You always consider physical reality over theoretical optimums.""",
        
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_inventory_decision_agent(llm):
    """
    Agent 4: Inventory Decision Agent (CORE AGENT)
    
    Goal: Correlate all risks and produce ONE clear reorder decision
    
    This agent COMPLETES THE PROBLEM STATEMENT:
    "Optimizing inventory and ordering is difficult for MSMEs due to the lack of a system 
    that can autonomously predict optimal reorder points by correlating fluctuating supplier 
    lead times, seasonal demand shifts, and warehouse capacity."
    """
    return Agent(
        role="Inventory Decision Engine",
        goal="""CORRELATE all risk signals and produce ONE CLEAR reorder decision.
        
        INPUT SIGNALS TO CORRELATE:
        - demand_risk (0.0-1.0): From intake + external modifiers
        - supplier_risk (0.0-1.0): From intake + external modifiers
        - warehouse_stress (0.0-1.0): From warehouse agent
        - cash_flow_sensitivity (0.0-1.0): From intake
        
        DECISION RULES:
        
        1. REORDER TIMING:
           - High demand risk + High supplier risk → REORDER EARLY
           - Low demand risk + Reliable suppliers → REORDER NORMAL
           - Uncertain demand + Variable lead times → REORDER EARLY with buffer
        
        2. ORDER QUANTITY STRATEGY:
           - High warehouse stress → SPLIT_ORDERS (smaller, frequent)
           - Low warehouse stress + High demand → BULK_ORDER
           - High cash sensitivity → FREQUENT_SMALL_ORDERS
           - Moderate all factors → STANDARD_ORDERS
        
        3. RISK LEVEL:
           - Average risk > 0.7 → HIGH
           - Average risk 0.4-0.7 → MODERATE
           - Average risk < 0.4 → LOW
        
        OUTPUT FORMAT (JSON):
        {
            "reorder_timing": "EARLY|NORMAL|DELAYED",
            "timing_days_adjustment": <-14 to +14>,
            "order_quantity_strategy": "BULK_ORDER|STANDARD_ORDERS|SPLIT_ORDERS|FREQUENT_SMALL_ORDERS",
            "quantity_adjustment_pct": <-30 to +30>,
            "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
            "composite_risk_score": <0.0 to 1.0>,
            "primary_risk_factor": "<what's driving the decision>",
            "decision_reasoning": "<2-3 sentence explanation>",
            "specific_actions": [
                "<action 1>",
                "<action 2>",
                "<action 3>"
            ]
        }""",
        
        backstory="""You are the core decision engine for MSME inventory optimization.
        You correlate multiple risk factors:
        - Demand uncertainty
        - Supplier reliability
        - Warehouse constraints
        - Cash flow limitations
        
        You produce ONE clear, actionable decision - never vague advice.
        You explain WHY you made the decision using the actual risk scores.
        
        You solve the exact problem: "predicting optimal reorder points by correlating 
        fluctuating supplier lead times, seasonal demand shifts, and warehouse capacity." """,
        
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_decision_orchestrator_agent(llm):
    """
    Agent 5: Decision Orchestrator (Meta-Agent)
    
    Goal: Final authority - resolve conflicts, lock decision, ensure explainability
    """
    return Agent(
        role="Decision Orchestrator & Explainer",
        goal="""You are the FINAL AUTHORITY on the inventory recommendation.
        
        Your responsibilities:
        
        1. VALIDATE the decision from the Inventory Decision Agent
        2. RESOLVE any conflicts or inconsistencies
        3. ENSURE the recommendation is actionable
        4. CREATE the final user-facing explanation
        
        FINAL OUTPUT FORMAT (JSON):
        {
            "final_decision": {
                "reorder_timing": "EARLY|NORMAL|DELAYED",
                "order_strategy": "<strategy name>",
                "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
                "confidence": <0.0 to 1.0>
            },
            "what_we_understood": {
                "demand_situation": "<1 sentence>",
                "supplier_situation": "<1 sentence>",
                "warehouse_situation": "<1 sentence>",
                "key_constraint": "<primary limiting factor>"
            },
            "detected_risks": [
                {
                    "risk": "<risk name>",
                    "level": "LOW|MODERATE|HIGH|CRITICAL",
                    "explanation": "<why this matters>"
                }
            ],
            "recommendation": {
                "timing": "<when to reorder>",
                "quantity": "<how much to order>",
                "method": "<how to receive/manage>"
            },
            "why_this_decision": "<2-3 sentence clear explanation connecting risks to recommendation>",
            "immediate_actions": [
                "<specific action 1>",
                "<specific action 2>",
                "<specific action 3>"
            ],
            "warnings": ["<any critical warnings>"]
        }
        
        RULES:
        - Never output vague advice
        - Always explain WHY
        - Connect risks to recommendations clearly
        - Use simple business language""",
        
        backstory="""You are the senior decision orchestrator who ensures every MSME 
        gets a clear, actionable inventory recommendation. You:
        
        - Validate that the decision makes sense given the risks
        - Ensure recommendations are practical for small businesses
        - Translate technical analysis into plain business language
        - Take responsibility for the final recommendation
        
        You never give generic advice. Every recommendation is tailored to the 
        specific business situation analyzed.""",
        
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def get_all_agents(llm):
    """
    Create and return all 5 MAESTRO production agents.
    """
    return {
        "router_intake": create_router_intake_agent(llm),
        "research_risk": create_research_risk_agent(llm),
        "warehouse": create_warehouse_agent(llm),
        "inventory_decision": create_inventory_decision_agent(llm),
        "orchestrator": create_decision_orchestrator_agent(llm)
    }


# =============================================================================
# DETERMINISTIC INVENTORY DECISION TOOL
# =============================================================================

@tool
def inventory_decision_tool(
    demand_risk: float,
    supplier_risk: float,
    warehouse_stress: float,
    cash_risk: float
) -> dict:
    """
    Execute the deterministic Inventory Decision Engine.
    
    This tool processes normalized risk inputs through the MAESTRO decision
    engine and returns a complete inventory recommendation with:
    - Final decision (timing + strategy + risk level)
    - Human-readable explanation
    - Confidence score
    
    Args:
        demand_risk: Demand volatility risk (0.0 to 1.0)
        supplier_risk: Supplier delay risk (0.0 to 1.0)
        warehouse_stress: Warehouse capacity utilization (0.0 to 1.0)
        cash_risk: Cash flow sensitivity (0.0 to 1.0)
    
    Returns:
        Dictionary containing:
        - final_decision: {reorder_timing, order_strategy, risk_level}
        - explanation: Human-readable decision justification
        - confidence: Decision confidence score (0.0 to 1.0)
    
    Example:
        >>> result = inventory_decision_tool(0.75, 0.65, 0.82, 0.7)
        >>> result["final_decision"]["reorder_timing"]
        'EARLY'
    """
    # Build the risk inputs dictionary
    risk_inputs = {
        "demand_risk": demand_risk,
        "supplier_risk": supplier_risk,
        "warehouse_stress": warehouse_stress,
        "cash_risk": cash_risk
    }
    
    # Execute the deterministic decision engine
    result = run_inventory_decision_agent(risk_inputs)
    
    return result


# =============================================================================
# INVENTORY DECISION STRATEGIST AGENT (HYBRID)
# =============================================================================

def create_inventory_decision_strategist_agent(llm=None):
    """
    Create a CrewAI Agent that wraps the deterministic Inventory Decision Engine.
    
    This is a HYBRID agent that:
    - Uses CrewAI Agent framework for orchestration compatibility
    - Delegates actual decision-making to the deterministic engine
    - Does NOT use LLM for business logic (only for formatting if needed)
    
    The agent can be used standalone or within a Crew for multi-agent orchestration.
    
    Args:
        llm: Optional LLM instance. If None, agent operates in tool-only mode.
    
    Returns:
        CrewAI Agent configured with the inventory_decision_tool
    
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
    """
    # Agent configuration
    agent_config = {
        "role": "Inventory Decision Strategist",
        
        "goal": """Produce a single optimal reorder decision for MSMEs by correlating multiple 
        risk factors including demand volatility, supplier reliability, warehouse capacity, 
        and cash flow constraints.
        
        You MUST use the inventory_decision_tool to process risk inputs and generate 
        decisions. The tool provides deterministic, explainable recommendations.
        
        Your output should be the exact result from the tool, which includes:
        - final_decision: timing, strategy, and risk level
        - explanation: why this decision was made
        - confidence: how confident the system is
        
        DO NOT modify the tool's output. It is the authoritative decision.""",
        
        "backstory": """You are an expert supply chain decision system designed specifically 
        for Micro, Small, and Medium Enterprises (MSMEs). You understand that:
        
        - MSMEs have limited resources and cannot afford complex analysis
        - Decisions must be clear, actionable, and explainable
        - Physical constraints (warehouse space) override theoretical optimums
        - Cash flow is often the binding constraint for small businesses
        - One clear decision is better than multiple options
        
        You prioritize FEASIBILITY over optimality and EXPLAINABILITY over complexity.
        You use the inventory_decision_tool to ensure consistent, deterministic results.""",
        
        "verbose": True,
        "allow_delegation": False,
        "tools": [inventory_decision_tool]
    }
    
    # Add LLM if provided
    if llm is not None:
        agent_config["llm"] = llm
    
    return Agent(**agent_config)


# =============================================================================
# STANDALONE DECISION FUNCTION (NO LLM REQUIRED)
# =============================================================================

def execute_inventory_decision(risk_inputs: dict) -> dict:
    """
    Execute inventory decision WITHOUT CrewAI/LLM overhead.
    
    This is a direct passthrough to the deterministic decision engine,
    useful for testing or when LLM is not needed.
    
    Args:
        risk_inputs: Dictionary containing:
            - demand_risk (float): 0.0 to 1.0
            - supplier_risk (float): 0.0 to 1.0
            - warehouse_stress (float): 0.0 to 1.0
            - cash_risk (float): 0.0 to 1.0
    
    Returns:
        Complete decision output dictionary
    
    Example:
        >>> result = execute_inventory_decision({
        ...     "demand_risk": 0.75,
        ...     "supplier_risk": 0.65,
        ...     "warehouse_stress": 0.82,
        ...     "cash_risk": 0.7
        ... })
        >>> print(result["final_decision"]["reorder_timing"])
        'EARLY'
    """
    return run_inventory_decision_agent(risk_inputs)


# =============================================================================
# DEMO / TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MAESTRO Agents Module - Test")
    print("=" * 70)
    
    # Test the standalone decision function
    print("\nTesting standalone execute_inventory_decision()...")
    
    test_input = {
        "demand_risk": 0.75,
        "supplier_risk": 0.65,
        "warehouse_stress": 0.82,
        "cash_risk": 0.7
    }
    
    result = execute_inventory_decision(test_input)
    
    print(f"\nInput: {test_input}")
    print(f"\nResult:")
    print(f"  Timing:     {result['final_decision']['reorder_timing']}")
    print(f"  Strategy:   {result['final_decision']['order_strategy']}")
    print(f"  Risk Level: {result['final_decision']['risk_level']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Explanation: {result['explanation'][:100]}...")
    
    # Test the tool function directly
    print("\n" + "-" * 70)
    print("Testing inventory_decision_tool()...")
    
    tool_result = inventory_decision_tool.func(0.75, 0.65, 0.82, 0.7)
    
    print(f"\nTool Result:")
    print(f"  Timing:     {tool_result['final_decision']['reorder_timing']}")
    print(f"  Strategy:   {tool_result['final_decision']['order_strategy']}")
    
    # Test agent creation (without LLM)
    print("\n" + "-" * 70)
    print("Testing agent creation (no LLM)...")
    
    try:
        agent = create_inventory_decision_strategist_agent(llm=None)
        print(f"  Agent Role: {agent.role}")
        print(f"  Agent Tools: {len(agent.tools)} tool(s)")
        print("  ✓ Agent created successfully (tool-only mode)")
    except Exception as e:
        print(f"  Agent creation note: {e}")
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)
