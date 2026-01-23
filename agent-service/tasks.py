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
    Task 1: Router / Context-Summarization Agent
    
    Purpose: Understand an MSME business from onboarding answers.
             Translate natural language into structured business context.
             Act ONLY as an interpreter, NOT a decision-maker.
    
    DOES NOT: Make decisions, recommend timing/quantity, invent data.
    """
    
    # Map user_responses keys to q1-q10 format for consistency
    # Handle both {key: value} and {q1: value} formats
    q_mapping = {
        'business_context': 'q1',
        'inventory_decision_method': 'q2', 
        'stock_issues': 'q3',
        'supplier_reliability': 'q4',
        'demand_variability': 'q5',
        'reorder_timing_issues': 'q6',
        'warehouse_constraints': 'q7',
        'cash_flow_impact': 'q8',
        'system_limitations': 'q9',
        'desired_outcome': 'q10'
    }
    
    # Build standardized q1-q10 format
    standardized = {}
    for key, value in user_responses.items():
        if key.startswith('q') and key[1:].isdigit():
            standardized[key] = value
        elif key in q_mapping:
            standardized[q_mapping[key]] = value
        else:
            # Try to assign to next available q slot
            idx = len(standardized) + 1
            if idx <= 10:
                standardized[f'q{idx}'] = value
    
    # Format as JSON-like input for clarity
    formatted_input = "\n".join([
        f'  "{k}": "{v}"' for k, v in sorted(standardized.items())
    ])
    
    return Task(
        description=f"""
        You are the Router / Context-Summarization Agent in MAESTRO.
        
        YOUR ROLE:
        - Understand an MSME business from onboarding answers
        - Translate natural language into structured business context
        - Act ONLY as an interpreter, NOT a decision-maker
        
        YOU MUST NOT:
        - Make inventory decisions
        - Suggest order quantities or timing
        - Predict numbers or forecasts
        - Invent facts not present in answers
        - Output explanations, markdown, or commentary
        
        =======================================
        MSME ONBOARDING ANSWERS
        =======================================
        {{
{formatted_input}
        }}
        =======================================
        
        QUESTION REFERENCE:
        - q1: Business description (industry, products, scale)
        - q2: How inventory decisions are currently made
        - q3: History of stockouts or overstocking
        - q4: Supplier reliability and delivery delays
        - q5: Demand variability (seasonal, steady, volatile)
        - q6: Reorder timing challenges
        - q7: Warehouse or storage constraints
        - q8: Cash flow impact of inventory
        - q9: Current tools or system limitations
        - q10: Primary desired outcome from this system
        
        INTERPRETATION RULES:
        - Use ONLY the information present in the answers
        - If something is unclear or missing, choose MEDIUM
        - Be conservative: avoid extreme values unless clearly stated
        - Prefer categorical reasoning over assumptions
        - Preserve MSME-specific details (do not generalize)
        
        CLASSIFICATION GUIDELINES:
        - "Festival demand", "weddings", "seasonal spikes" → seasonal + higher risk
        - "Fresh", "perishable", "daily procurement" → high perishability
        - "Manual tracking", "Excel", "WhatsApp" → manual or semi-digital
        - "Limited space", "no cold storage" → tight or critical warehouse
        - "Cash blocked", "tight cash", "credit dependence" → high sensitivity
        
        FINAL CHECK BEFORE OUTPUT:
        - JSON is valid
        - No numbers are invented
        - No decisions are suggested
        - No text outside JSON
        
        Output ONLY valid JSON. No markdown, no explanations.
        """,
        
        expected_output="""{
    "business_profile": {
        "industry": "",
        "products": "",
        "scale": "small | medium | large",
        "perishability": "low | medium | high"
    },
    "demand_summary": {
        "pattern": "stable | seasonal | volatile",
        "drivers": [],
        "risk_level": "low | medium | high"
    },
    "supplier_summary": {
        "reliability": "high | medium | low",
        "delay_frequency": "rare | occasional | frequent",
        "risk_level": "low | medium | high"
    },
    "warehouse_summary": {
        "capacity_status": "comfortable | tight | critical",
        "constraint_level": "low | medium | high"
    },
    "financial_summary": {
        "cash_flow_sensitivity": "low | medium | high"
    },
    "operational_summary": {
        "system_maturity": "manual | semi-digital | automated",
        "key_gaps": []
    },
    "primary_business_goal": "",
    "overall_context_narrative": ""
}""",
        
        agent=agent
    )


def create_external_risk_task(agent, business_context: dict):
    """
    Task 2: External Data / Risk Scout Agent
    
    Purpose: Observe the external environment affecting the business.
             Identify demand-side and supply-side risk signals.
             Convert real-world factors into bounded risk modifiers.
    
    DOES NOT: Make decisions, recommend timing/quantity, override internal context.
    """
    
    business_profile = business_context.get('business_profile', {})
    demand_summary = business_context.get('demand_summary', {})
    supplier_summary = business_context.get('supplier_summary', {})
    warehouse_summary = business_context.get('warehouse_summary', {})
    financial_summary = business_context.get('financial_summary', {})
    overall_context = business_context.get('overall_context_narrative', '')
    primary_goal = business_context.get('primary_business_goal', '')
    
    # Extract key fields with fallbacks
    industry = business_profile.get('industry', business_context.get('industry', 'retail'))
    products = business_profile.get('products', business_context.get('products', 'general goods'))
    scale = business_profile.get('scale', 'medium')
    perishability = business_profile.get('perishability', 'medium')
    demand_pattern = demand_summary.get('pattern', 'stable')
    demand_risk = demand_summary.get('risk_level', 'medium')
    supplier_reliability = supplier_summary.get('reliability', 'medium')
    
    return Task(
        description=f"""
        You are the External Data / Risk Scout Agent for MAESTRO.
        
        YOUR ROLE:
        - Observe the external environment affecting the business
        - Identify demand-side and supply-side risk signals
        - Convert real-world factors into bounded risk modifiers
        
        YOU MUST NOT:
        - Make inventory decisions
        - Suggest order quantities or reorder timing
        - Override internal business context
        - Invent risks without plausible real-world basis
        - Output explanations, markdown, or commentary
        
        =======================================
        INPUT: Business Context from Router Agent
        =======================================
        Business Profile:
        - Industry: {industry}
        - Products: {products}
        - Scale: {scale}
        - Perishability: {perishability}
        
        Demand Summary:
        - Pattern: {demand_pattern}
        - Risk Level: {demand_risk}
        
        Supplier Summary:
        - Reliability: {supplier_reliability}
        
        Overall Context: {overall_context}
        Primary Business Goal: {primary_goal}
        =======================================
        
        YOUR TASK:
        Identify **external factors** (outside the business) that could affect:
        - Demand volatility
        - Supplier lead-time reliability
        
        Then convert them into **bounded numerical risk modifiers**.
        
        CRITICAL BOUNDARIES:
        - external_demand_risk_modifier ∈ [-0.2, +0.3]
        - external_lead_time_risk_modifier ∈ [-0.2, +0.3]
        - If no strong external signals exist → return 0.0
        - Never exceed bounds under any condition
        
        INTERPRETATION GUIDELINES:
        - Festivals, holidays, weddings → increase demand risk
        - Weather events (monsoon, floods, heatwaves) → affect perishables & logistics
        - Transport strikes, fuel price spikes, border issues → affect lead time
        - Inflation or economic slowdown → reduce demand stability
        - Industry-specific cycles (agriculture, flowers, textiles) matter
        
        CONSERVATISM RULES:
        - Prefer small modifiers unless evidence is strong
        - If uncertain → choose 0.0
        - Never invent rare or global events unless industry-appropriate
        - Do NOT restate internal risks already captured by Router Agent
        
        FINAL CHECK BEFORE OUTPUT:
        - JSON is valid
        - Modifiers are within bounds [-0.2, +0.3]
        - No decisions or recommendations included
        - No duplication of internal context
        - No hallucinated disasters
        
        Output ONLY valid JSON. No markdown, no explanations.
        """,
        
        expected_output="""{
    "external_demand_risk_modifier": 0.0,
    "external_lead_time_risk_modifier": 0.0,
    "external_factors": [
        {
            "factor": "",
            "impact": "demand | supply",
            "severity": "low | medium | high",
            "timeframe": "immediate | short-term | upcoming"
        }
    ],
    "market_outlook": "favorable | neutral | challenging"
}""",
        
        agent=agent
    )


def create_warehouse_assessment_task(agent, intake_signals: dict):
    """
    Task 3: Warehouse Capacity Agent
    
    Purpose: Enforce PHYSICAL REALITY of inventory plans.
             Validate whether buffer policy is feasible.
             Adjust execution strategy if storage limits are violated.
    
    DOES NOT: Change risk level, buffer posture, or make timing decisions.
    """
    
    # Extract warehouse inputs
    warehouse_inputs = intake_signals.get('warehouse_inputs', {})
    current_stock = warehouse_inputs.get('current_stock', intake_signals.get('current_stock', 50))
    max_capacity = warehouse_inputs.get('max_capacity', intake_signals.get('max_capacity', 100))
    storage_type = warehouse_inputs.get('storage_type', intake_signals.get('storage_type', 'ambient'))
    perishability = warehouse_inputs.get('perishability', intake_signals.get('perishability', 'medium'))
    
    # Extract buffer policy
    buffer_policy = intake_signals.get('buffer_policy', {})
    risk_level = buffer_policy.get('risk_level', 'MODERATE')
    buffer_posture = buffer_policy.get('buffer_posture', 'MODERATE')
    inventory_philosophy = buffer_policy.get('inventory_philosophy', 'BALANCED')
    service_level_target = buffer_policy.get('service_level_target', '95%')
    cash_constraint_applied = buffer_policy.get('cash_constraint_applied', False)
    
    # Compute utilization for display
    utilization = current_stock / max_capacity if max_capacity > 0 else 0.5
    
    # Fallback extraction for backward compatibility
    if 'warehouse_stress' in intake_signals:
        utilization = intake_signals.get('warehouse_stress', utilization)
    
    return Task(
        description=f"""
        You are the Warehouse Capacity Agent for MAESTRO.
        
        YOUR ROLE:
        - Enforce PHYSICAL REALITY of inventory plans
        - Validate whether buffer policy is feasible
        - Adjust execution strategy if storage limits are violated
        
        YOU MUST:
        - Respect buffer policy intent
        - Respect risk level
        - Respect perishability and storage constraints
        - Prevent overstocking and spoilage
        
        YOU MUST NOT:
        - Change risk level
        - Change buffer posture
        - Change service level target
        - Make final reorder timing decisions
        - Modify financial or demand risks
        
        =======================================
        INPUT: Warehouse Inputs
        =======================================
        - current_stock: {current_stock}
        - max_capacity: {max_capacity}
        - storage_type: {storage_type}
        - perishability: {perishability}
        
        =======================================
        INPUT: Buffer Policy (DO NOT MODIFY)
        =======================================
        - risk_level: {risk_level}
        - buffer_posture: {buffer_posture}
        - inventory_philosophy: {inventory_philosophy}
        - service_level_target: {service_level_target}
        - cash_constraint_applied: {cash_constraint_applied}
        =======================================
        
        PROCESS RULES (NON-NEGOTIABLE):
        1. Compute warehouse_utilization = current_stock / max_capacity = {utilization:.2f}
        2. Classify capacity stress:
           - < 0.50 → LOW
           - 0.50 – 0.75 → MEDIUM
           - ≥ 0.75 → HIGH (HARD CONSTRAINT)
        3. HIGH capacity stress overrides buffer EXECUTION, not intent
        4. High perishability increases execution frequency
        5. Warehouse logic ALWAYS overrides quantity assumptions
        
        EXECUTION LOGIC:
        
        If warehouse_utilization ≥ 0.75:
        - execution_mode = "SPLIT_DELIVERIES"
        - max_fill_guideline = "Do not exceed 85% capacity at any time"
        - hard_constraint_triggered = true
        
        If perishability == "high":
        - preferred_frequency = "DAILY" or "2-3x weekly"
        
        If warehouse_utilization < 0.50 AND perishability != "high":
        - execution_mode = "BULK_ALLOWED"
        - preferred_frequency = "weekly" or "biweekly"
        
        FINAL CHECK BEFORE OUTPUT:
        - Warehouse constraints enforced
        - No changes to buffer policy
        - No risk recalculations
        - No timing decisions
        - JSON is valid and minimal
        
        Output ONLY valid JSON. No markdown, no explanations.
        """,
        
        expected_output="""{
    "warehouse_assessment": {
        "warehouse_utilization": 0.0,
        "capacity_stress": "LOW | MEDIUM | HIGH",
        "execution_mode": "BULK_ALLOWED | SPLIT_DELIVERIES",
        "preferred_frequency": "DAILY | 2-3x weekly | weekly | biweekly",
        "max_fill_guideline": "",
        "hard_constraint_triggered": false
    }
}""",
        
        agent=agent
    )


def create_risk_assessment_task(agent, all_signals: dict):
    """
    Task 4: Risk Assessment Agent
    
    Purpose: Evaluate how risky inventory management is RIGHT NOW for this business.
             Combine internal risk signals with external risk modifiers.
             Produce NORMALIZED, COMPARABLE risk scores.
    
    YOUR JOB IS MEASUREMENT, NOT DECISION.
    
    DOES NOT: Decide timing, quantity, strategy, or safety stock levels.
    """
    
    # Extract internal risks
    internal_risks = all_signals.get('internal_risks', {})
    demand_risk = internal_risks.get('demand_risk', all_signals.get('demand_risk', 0.5))
    supplier_risk = internal_risks.get('supplier_risk', all_signals.get('supplier_risk', 0.5))
    warehouse_stress = internal_risks.get('warehouse_stress', all_signals.get('warehouse_stress', 0.5))
    cash_flow_risk = internal_risks.get('cash_flow_risk', all_signals.get('cash_risk', 0.5))
    
    # Extract external modifiers
    external_modifiers = all_signals.get('external_modifiers', {})
    ext_demand_mod = external_modifiers.get('external_demand_risk_modifier', 
                                            all_signals.get('external_demand_risk_modifier', 0.0))
    ext_supply_mod = external_modifiers.get('external_lead_time_risk_modifier', 
                                            all_signals.get('external_lead_time_risk_modifier', 0.0))
    
    return Task(
        description=f"""
        You are the Risk Assessment Agent for MAESTRO.
        
        YOUR ROLE:
        - Evaluate how risky inventory management is RIGHT NOW for this business
        - Combine internal risk signals with external risk modifiers
        - Produce NORMALIZED, COMPARABLE risk scores
        
        YOU MUST NOT:
        - Decide reorder timing
        - Decide order quantity or strategy
        - Enforce warehouse constraints
        - Suggest safety stock levels
        - Use probabilistic or creative reasoning
        - Output explanations or recommendations
        
        YOUR JOB IS MEASUREMENT, NOT DECISION.
        
        =======================================
        INPUT: Internal Risks
        =======================================
        - demand_risk: {demand_risk}
        - supplier_risk: {supplier_risk}
        - warehouse_stress: {warehouse_stress}
        - cash_flow_risk: {cash_flow_risk}
        
        =======================================
        INPUT: External Modifiers
        =======================================
        - external_demand_risk_modifier: {ext_demand_mod}
        - external_lead_time_risk_modifier: {ext_supply_mod}
        =======================================
        
        PROCESS RULES (STRICT):
        1. Adjust ONLY demand and supplier risks using external modifiers
        2. Warehouse and cash risks are NEVER modified here
        3. Clamp all adjusted risks to the range [0.0, 1.0]
        4. Do NOT invent new risks
        5. Do NOT change weights
        6. Do NOT classify inventory strategy
        
        CALCULATION STEPS:
        - adjusted_demand_risk = clamp(demand_risk + external_demand_risk_modifier, 0.0, 1.0)
        - adjusted_supplier_risk = clamp(supplier_risk + external_lead_time_risk_modifier, 0.0, 1.0)
        - warehouse_stress = unchanged ({warehouse_stress})
        - cash_flow_risk = unchanged ({cash_flow_risk})
        
        Then compute COMPOSITE RISK SCORE:
        composite_risk = (adjusted_demand_risk × 0.35) + (adjusted_supplier_risk × 0.35) + (warehouse_stress × 0.30)
        
        RISK LEVEL CLASSIFICATION:
        - composite_risk < 0.4  → "LOW"
        - composite_risk < 0.7  → "MODERATE"
        - composite_risk >= 0.7 → "HIGH"
        
        FINAL CHECK BEFORE OUTPUT:
        - All values ∈ [0.0, 1.0]
        - Composite risk is mathematically correct
        - Risk level matches thresholds exactly
        - No strategy, timing, or quantity decisions included
        - Output is valid JSON only
        
        Output ONLY valid JSON. No markdown, no explanations.
        """,
        
        expected_output="""{
    "adjusted_risks": {
        "demand_risk": 0.0,
        "supplier_risk": 0.0,
        "warehouse_stress": 0.0,
        "cash_flow_risk": 0.0
    },
    "composite_risk_score": 0.0,
    "risk_level": "LOW | MODERATE | HIGH"
}""",
        
        agent=agent
    )


def create_policy_task(agent, policy_input: dict):
    """
    Task 5: Policy Agent
    
    Purpose: Decide inventory BUFFER POLICY (safety stock behavior).
             Translate risk level into stock protection strategy.
             Recommend how conservative the business should be.
    
    YOU ONLY DEFINE POLICY, NOT EXECUTION.
    
    DOES NOT: Decide timing, strategy, quantities, or override risks.
    """
    
    # Extract risk assessment output
    adjusted_risks = policy_input.get('adjusted_risks', {})
    demand_risk = adjusted_risks.get('demand_risk', policy_input.get('demand_risk', 0.5))
    supplier_risk = adjusted_risks.get('supplier_risk', policy_input.get('supplier_risk', 0.5))
    warehouse_stress = adjusted_risks.get('warehouse_stress', policy_input.get('warehouse_stress', 0.5))
    cash_flow_risk = adjusted_risks.get('cash_flow_risk', policy_input.get('cash_risk', 0.5))
    
    composite_risk_score = policy_input.get('composite_risk_score', 0.5)
    risk_level = policy_input.get('risk_level', policy_input.get('overall_risk_level', 'MODERATE'))
    
    return Task(
        description=f"""
        You are the Policy Agent for MAESTRO.
        
        YOUR ROLE:
        - Decide inventory BUFFER POLICY (safety stock behavior)
        - Translate risk level into stock protection strategy
        - Recommend how conservative the business should be
        
        YOU MUST NOT:
        - Decide reorder timing (early/normal/delayed)
        - Decide order strategy (bulk/split/frequent)
        - Enforce warehouse capacity constraints
        - Override risk scores
        - Modify or recalculate risks
        - Use probabilistic or creative reasoning
        - Output final decisions
        
        YOU ONLY DEFINE POLICY, NOT EXECUTION.
        
        =======================================
        INPUT: Risk Assessment Output
        =======================================
        Adjusted Risks:
        - demand_risk: {demand_risk}
        - supplier_risk: {supplier_risk}
        - warehouse_stress: {warehouse_stress}
        - cash_flow_risk: {cash_flow_risk}
        
        Composite Risk Score: {composite_risk_score}
        Risk Level: {risk_level}
        =======================================
        
        POLICY LOGIC:
        
        If risk_level == "LOW":
        - Buffer philosophy: Lean
        - Safety stock posture: Minimal
        - Inventory attitude: Cost-optimized
        - Service level target: ~90%
        
        If risk_level == "MODERATE":
        - Buffer philosophy: Balanced
        - Safety stock posture: Moderate
        - Inventory attitude: Stability-focused
        - Service level target: ~95%
        
        If risk_level == "HIGH":
        - Buffer philosophy: Protective
        - Safety stock posture: Aggressive
        - Inventory attitude: Risk-averse
        - Service level target: ~98-99%
        
        CASH FLOW ADJUSTMENT (SECONDARY):
        - If cash_flow_risk >= 0.7: Reduce buffer aggressiveness by ONE level
          (Aggressive → Moderate, Moderate → Minimal)
        - If cash_flow_risk <= 0.3: Keep policy unchanged
        - Cash risk MUST NEVER increase buffer beyond risk_level intent
        
        FINAL CHECK BEFORE OUTPUT:
        - Policy aligns with risk level
        - Cash constraint only reduces aggressiveness
        - No quantities mentioned
        - No timing or strategy decisions included
        - Output is valid JSON only
        
        Output ONLY valid JSON. No markdown, no explanations.
        """,
        
        expected_output="""{
    "buffer_policy": {
        "risk_level": "LOW | MODERATE | HIGH",
        "buffer_posture": "MINIMAL | MODERATE | AGGRESSIVE",
        "inventory_philosophy": "LEAN | BALANCED | PROTECTIVE",
        "service_level_target": "90% | 95% | 98-99%",
        "cash_constraint_applied": false
    }
}""",
        
        agent=agent
    )


def create_inventory_decision_task(agent, all_signals: dict):
    """
    Task 7: Inventory Decision Engine (CORE)
    Compute weighted composite risk and produce ONE clear reorder decision.
    
    Input:
    All normalized risks + warehouse constraints
    
    Output:
    {
        "reorder_timing": "EARLY | NORMAL | DELAYED",
        "order_strategy": "BULK | SPLIT_ORDERS | FREQUENT_SMALL",
        "risk_level": "",
        "confidence": float
    }
    """
    
    # Extract all signals
    adjusted_demand_risk = all_signals.get('adjusted_demand_risk', all_signals.get('demand_risk', 0.5))
    adjusted_supplier_risk = all_signals.get('adjusted_supplier_risk', all_signals.get('supplier_risk', 0.5))
    warehouse_stress = all_signals.get('warehouse_stress', 0.5)
    cash_risk = all_signals.get('cash_risk', 0.5)
    
    # Extract upstream agent outputs
    feasible_strategy = all_signals.get('feasible_strategy', 'SPLIT_ORDERS')
    buffer_policy = all_signals.get('buffer_policy', 'MEDIUM')
    overall_risk_level = all_signals.get('overall_risk_level', 'MEDIUM')
    
    return Task(
        description=f"""
        You are the Inventory Decision Engine. Compute weighted composite risk and produce ONE decision.
        
        INPUT SIGNALS:
        - adjusted_demand_risk: {adjusted_demand_risk}
        - adjusted_supplier_risk: {adjusted_supplier_risk}
        - warehouse_stress: {warehouse_stress}
        - cash_risk: {cash_risk}
        
        UPSTREAM AGENT OUTPUTS:
        - feasible_strategy: {feasible_strategy} (from Warehouse Agent - NON-NEGOTIABLE)
        - buffer_policy: {buffer_policy} (from Policy Agent)
        - overall_risk_level: {overall_risk_level} (from Risk Assessment Agent)
        
        PROCESS:
        
        STEP 1: Compute Weighted Composite Risk
        composite = (0.3 * adjusted_demand_risk) + (0.3 * adjusted_supplier_risk) + (0.25 * warehouse_stress) + (0.15 * cash_risk)
        
        STEP 2: Decide Reorder Timing (based on composite)
        - composite >= 0.7 → EARLY
        - composite >= 0.4 and < 0.7 → NORMAL
        - composite < 0.4 → DELAYED
        
        STEP 3: Apply Hard Constraint Overrides
        - order_strategy MUST equal feasible_strategy (warehouse constraint is absolute)
        - You CANNOT override the Warehouse Agent's decision
        
        STEP 4: Compute Confidence
        - variance = average of (|risk - mean_risk|) for all 4 risks
        - confidence = 1.0 - variance
        
        STRICT RULES:
        1. Produce ONLY ONE decision
        2. Deterministic logic only - NO randomness
        3. Same inputs → same outputs ALWAYS
        4. Warehouse feasible_strategy is NON-NEGOTIABLE
        
        OUTPUT ONLY VALID JSON. No markdown, no explanations.
        """,
        
        expected_output="""{
            "reorder_timing": "EARLY | NORMAL | DELAYED",
            "order_strategy": "BULK | SPLIT_ORDERS | FREQUENT_SMALL",
            "risk_level": "LOW | MEDIUM | HIGH",
            "confidence": <float 0.0-1.0>
        }""",
        
        agent=agent
    )


def create_orchestrator_task(agent, all_analysis: dict):
    """
    Task 8: Decision Orchestrator Agent
    
    Purpose: Combine outputs from all previous agents.
             Validate consistency across decisions.
             Produce ONE final, explainable inventory recommendation.
             Translate technical logic into MSME-friendly language.
    
    DOES NOT: Recalculate risks, modify policy, override warehouse constraints.
    """
    
    # Extract outputs from all previous agents
    context_summary = all_analysis.get('context_summary', all_analysis.get('business_context', {}))
    external_risks = all_analysis.get('external_risks', all_analysis.get('external', {}))
    risk_assessment = all_analysis.get('risk_assessment', {})
    buffer_policy = all_analysis.get('buffer_policy', {})
    warehouse_assessment = all_analysis.get('warehouse_assessment', all_analysis.get('warehouse', {}))
    
    # Extract key values for display
    risk_level = risk_assessment.get('risk_level', 'MODERATE')
    composite_risk = risk_assessment.get('composite_risk_score', 0.5)
    adjusted_risks = risk_assessment.get('adjusted_risks', {})
    
    execution_mode = warehouse_assessment.get('execution_mode', 'SPLIT_DELIVERIES')
    hard_constraint = warehouse_assessment.get('hard_constraint_triggered', False)
    warehouse_utilization = warehouse_assessment.get('warehouse_utilization', 0.5)
    
    buffer_posture = buffer_policy.get('buffer_posture', 'MODERATE')
    inventory_philosophy = buffer_policy.get('inventory_philosophy', 'BALANCED')
    
    # Extract lead time context (if available)
    lead_time_context = all_analysis.get('lead_time_context', {})
    effective_lead_time_days = lead_time_context.get('effective_lead_time_days')
    lead_time_override_applied = lead_time_context.get('lead_time_override_applied', False)
    
    return Task(
        description=f"""
        You are the Decision Orchestrator Agent for MAESTRO.
        
        YOUR ROLE:
        - Combine outputs from all previous agents
        - Validate consistency across decisions
        - Produce ONE final, explainable inventory recommendation
        - Translate technical logic into MSME-friendly language
        
        YOU MUST:
        - Respect all upstream agent outputs
        - Preserve hard constraints (warehouse limits)
        - Preserve policy intent (buffer posture)
        - Produce ONE final decision (no alternatives)
        - Clearly explain WHY the decision was made
        - If supplier lead times are long (>=7 days), explicitly mention this influenced earlier ordering
        
        YOU MUST NOT:
        - Recalculate risk scores
        - Modify buffer policy
        - Override warehouse constraints
        - Introduce new data
        - Provide multiple options
        
        =======================================
        INPUT: Context Summary (from Router Agent)
        =======================================
        {context_summary}
        
        =======================================
        INPUT: External Risks (from Risk Scout)
        =======================================
        {external_risks}
        
        =======================================
        INPUT: Supplier Lead Time Context
        =======================================
        - Effective Lead Time: {effective_lead_time_days} days
        - Lead Time Override Applied: {lead_time_override_applied}
        - NOTE: If effective lead time >= 7 days, explicitly mention:
          "Supplier lead times of ~{effective_lead_time_days} days influenced earlier ordering"
        =======================================
        INPUT: Risk Assessment
        =======================================
        - Risk Level: {risk_level}
        - Composite Risk Score: {composite_risk}
        - Adjusted Risks: {adjusted_risks}
        
        =======================================
        INPUT: Buffer Policy
        =======================================
        - Buffer Posture: {buffer_posture}
        - Inventory Philosophy: {inventory_philosophy}
        - Full Policy: {buffer_policy}
        
        =======================================
        INPUT: Warehouse Assessment
        =======================================
        - Execution Mode: {execution_mode}
        - Hard Constraint Triggered: {hard_constraint}
        - Warehouse Utilization: {warehouse_utilization}
        - Full Assessment: {warehouse_assessment}
        =======================================
        
        FINAL DECISION RULES:
        1. Reorder timing comes ONLY from risk_level:
           - HIGH → EARLY
           - MODERATE → NORMAL
           - LOW → DELAYED
        
        2. Order strategy comes ONLY from warehouse_assessment.execution_mode: {execution_mode}
        
        3. If hard_constraint_triggered = {hard_constraint}:
           - If true: Mention it explicitly in explanation
           - Explain why execution differs from buffer intent
        
        4. Confidence score rules:
           - HIGH risk → 0.75–0.85
           - MODERATE → 0.60–0.75
           - LOW → 0.50–0.65
        
        FINAL CHECK BEFORE OUTPUT:
        - Exactly ONE decision
        - Warehouse constraints respected
        - Explanation matches logic
        - No hallucinations
        - Valid JSON
        
        Output ONLY valid JSON. No markdown, no explanations.
        """,
        
        expected_output="""{
    "final_decision": {
        "reorder_timing": "EARLY | NORMAL | DELAYED",
        "order_strategy": "",
        "risk_level": "",
        "confidence": 0.0
    },
    "what_we_understood": {
        "demand_situation": "",
        "supplier_situation": "",
        "warehouse_situation": "",
        "key_constraint": ""
    },
    "detected_risks": [
        { "risk": "", "level": "", "explanation": "" }
    ],
    "why_this_decision": "",
    "immediate_actions": [
        "",
        "",
        "",
        "",
        ""
    ],
    "warnings": []
}""",
        
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
