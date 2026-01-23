"""
MAESTRO - MSME Inventory Intelligence System
Production Orchestrator - Multi-Agent Pipeline

UNIFIED PIPELINE FLOW (run_full_pipeline):
0. Raw Data Preservation → Single Source of Truth
1. Router Agent [LLM] → structured business context
2. Signal Conversion [DETERMINISTIC] → numeric internal risk signals
3. External Risk Scout [LLM] → bounded modifiers [-0.2, +0.3]
4. Risk Assessment [DETERMINISTIC] → composite risk score + level
5. Policy Agent [DETERMINISTIC] → buffer policy
6. Warehouse Agent [DETERMINISTIC] → feasibility & execution mode
7. Decision Orchestrator [LLM] → final JSON output

DETERMINISTIC PIPELINE (run_maestro_pipeline):
- Pure rule-based decision engine
- No LLM calls required
- Predictable, explainable outputs

HARD CONSTRAINT PRIORITY:
- Warehouse capacity ALWAYS overrides buffer intent
- Cash risk can REDUCE buffer, never increase it
- External modifiers are bounded [-0.2, +0.3]
"""
import json
import re
from crewai import Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI

from agents import get_all_agents
from tasks import (
    create_intake_analysis_task,
    create_external_risk_task,
    create_risk_assessment_task,
    create_policy_task,
    create_warehouse_assessment_task,
    create_inventory_decision_task,
    create_orchestrator_task
)
from config import Config

# Import deterministic decision engine components
from risk_signals import build_risk_profile
from inventory_decision_agent import run_inventory_decision_agent


# =============================================================================
# RAW DATA PRESERVATION - SINGLE SOURCE OF TRUTH
# =============================================================================

def preserve_raw_answers(user_responses: dict) -> dict:
    """
    Preserve raw onboarding answers as the SINGLE SOURCE OF TRUTH.
    
    This function treats the 10 onboarding answers as immutable data.
    It does NOT:
    - Modify any answers
    - Infer missing information
    - Optimize or clean data
    - Add assumptions
    - Make decisions
    
    It ONLY:
    - Structures the data in q1-q10 format
    - Preserves the business owner's exact wording
    - Makes this data available to all downstream agents
    
    Args:
        user_responses: Raw answers from onboarding (various key formats)
        
    Returns:
        Dictionary with keys q1-q10 containing exact original answers
        
    Example:
        >>> raw = {"business_context": "Flower trading"}
        >>> preserve_raw_answers(raw)
        {"q1": "Flower trading", "q2": "", ...}
    """
    # Key mapping from named keys to q1-q10 format
    KEY_MAP = {
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
    
    # Initialize with empty strings (no assumptions)
    preserved = {
        'q1': '',
        'q2': '',
        'q3': '',
        'q4': '',
        'q5': '',
        'q6': '',
        'q7': '',
        'q8': '',
        'q9': '',
        'q10': ''
    }
    
    # Preserve exact answers without modification
    for key, value in user_responses.items():
        # Handle q1-q10 format directly
        if key.lower().startswith('q') and key[1:].isdigit():
            q_key = f"q{key[1:]}"
            if q_key in preserved:
                preserved[q_key] = str(value) if value is not None else ''
        # Handle named key format
        elif key in KEY_MAP:
            preserved[KEY_MAP[key]] = str(value) if value is not None else ''
        # Handle question_1 through question_10 format
        elif key.startswith('question_') and key[9:].isdigit():
            q_num = int(key[9:])
            if 1 <= q_num <= 10:
                preserved[f'q{q_num}'] = str(value) if value is not None else ''
    
    return preserved


def get_raw_answer(preserved_data: dict, question_number: int) -> str:
    """
    Retrieve a specific raw answer by question number.
    
    Args:
        preserved_data: Output from preserve_raw_answers()
        question_number: 1-10
        
    Returns:
        The exact raw answer string (empty string if not found)
    """
    if not 1 <= question_number <= 10:
        return ''
    return preserved_data.get(f'q{question_number}', '')


# =============================================================================
# DETERMINISTIC SIGNAL CONVERSION LAYER
# =============================================================================

def convert_context_to_signals(context_summary: dict) -> dict:
    """
    Deterministic signal conversion from categorical to numeric.
    
    Converts Router Agent categorical outputs to numeric risk signals
    for the Decision Engine.
    
    RULES:
    - NO LLM
    - NO randomness
    - Same input → same output
    - Use fixed mappings only
    
    MAPPING:
        LOW    → 0.3
        MEDIUM → 0.6
        HIGH   → 0.9
    
    INPUT (from Router Agent):
        - demand_summary.risk_level
        - supplier_summary.risk_level
        - warehouse_summary.constraint_level
        - financial_summary.cash_flow_sensitivity
    
    OUTPUT:
        {
            "demand_risk": float,
            "supplier_risk": float,
            "warehouse_stress": float,
            "cash_risk": float
        }
    
    Args:
        context_summary: Output from Router/Context-Summarization Agent
        
    Returns:
        Dictionary with numeric risk signals (0.0-1.0)
    """
    # FIXED MAPPING - Deterministic, no randomness
    RISK_MAP = {
        "low": 0.3,
        "medium": 0.6,
        "high": 0.9
    }
    
    # Default value for missing/invalid inputs
    DEFAULT = 0.6  # Medium risk assumption
    
    # Extract categorical values from context summary
    demand_summary = context_summary.get('demand_summary', {})
    supplier_summary = context_summary.get('supplier_summary', {})
    warehouse_summary = context_summary.get('warehouse_summary', {})
    financial_summary = context_summary.get('financial_summary', {})
    
    # Convert demand_summary.risk_level → demand_risk
    demand_level = str(demand_summary.get('risk_level', 'medium')).lower().strip()
    demand_risk = RISK_MAP.get(demand_level, DEFAULT)
    
    # Convert supplier_summary.risk_level → supplier_risk
    supplier_level = str(supplier_summary.get('risk_level', 'medium')).lower().strip()
    supplier_risk = RISK_MAP.get(supplier_level, DEFAULT)
    
    # Convert warehouse_summary.constraint_level → warehouse_stress
    warehouse_level = str(warehouse_summary.get('constraint_level', 'medium')).lower().strip()
    warehouse_stress = RISK_MAP.get(warehouse_level, DEFAULT)
    
    # Convert financial_summary.cash_flow_sensitivity → cash_risk
    cash_level = str(financial_summary.get('cash_flow_sensitivity', 'medium')).lower().strip()
    cash_risk = RISK_MAP.get(cash_level, DEFAULT)
    
    return {
        "demand_risk": demand_risk,
        "supplier_risk": supplier_risk,
        "warehouse_stress": warehouse_stress,
        "cash_risk": cash_risk
    }


# =============================================================================
# DETERMINISTIC MAESTRO PIPELINE
# =============================================================================

def run_maestro_pipeline(input_context: dict) -> dict:
    """
    Execute the deterministic MAESTRO pipeline for inventory decisions.
    
    This pipeline uses pure rule-based logic without LLM calls.
    It converts raw business inputs into structured risk signals,
    then produces a deterministic inventory decision.
    
    NOW ENHANCED: Accepts business_state from MongoDB for live data-driven decisions.
    Falls back to payload values when live data is unavailable.
    
    Args:
        input_context: Dictionary containing:
            - demand_type (str): "steady", "seasonal", "volatile"
            - seasonal_event (bool): Whether seasonal event is expected
            - supplier_delay (str): "none", "minor", "frequent", "major"
            - external_disruption (bool): Whether external disruption exists
            - current_stock (int): Current inventory level (OPTIONAL if business_state)
            - max_capacity (int): Maximum warehouse capacity (OPTIONAL if business_state)
            - cash_flow (str): "healthy", "tight", "critical"
            - business_state (dict): Live business state from MongoDB (OPTIONAL)
    
    Returns:
        Dictionary containing:
            - success (bool): Whether pipeline executed successfully
            - final_decision: {reorder_timing, order_strategy, risk_level}
            - explanation (str): Human-readable decision explanation
            - confidence (float): Decision confidence score (0.0-1.0)
            - risk_profile: Detailed risk breakdown
            - data_source (str): "live" | "payload" | "mixed"
    
    Example:
        >>> context = {
        ...     "demand_type": "seasonal",
        ...     "seasonal_event": True,
        ...     "supplier_delay": "frequent",
        ...     "external_disruption": False,
        ...     "current_stock": 60,
        ...     "max_capacity": 100,
        ...     "cash_flow": "tight",
        ...     "business_state": { ... }
        ... }
        >>> result = run_maestro_pipeline(context)
        >>> result["final_decision"]["reorder_timing"]
        'EARLY'
    """
    print("\n" + "="*60)
    print("🚀 MAESTRO DETERMINISTIC PIPELINE - Starting")
    print("="*60 + "\n")
    
    # Check if we have live business state
    has_business_state = input_context.get("business_state") is not None
    print(f"📡 Live business_state available: {has_business_state}")
    
    try:
        # ========================================
        # STAGE 1: BUILD RISK PROFILE
        # ========================================
        print("\n📊 Stage 1: Building Risk Profile from inputs...")
        
        risk_profile = build_risk_profile(input_context)
        
        data_source = risk_profile.get("data_source", "payload")
        print(f"✅ Risk Profile (data_source={data_source}): "
              f"demand={risk_profile['demand_risk']:.2f}, "
              f"supplier={risk_profile['supplier_risk']:.2f}, "
              f"warehouse={risk_profile['warehouse_stress']:.2f}, "
              f"cash={risk_profile['cash_risk']:.2f}")
        
        # ========================================
        # STAGE 2: RUN DECISION AGENT
        # ========================================
        print("\n🎯 Stage 2: Running Inventory Decision Agent...")
        
        decision_result = run_inventory_decision_agent(risk_profile)
        
        # Extract lead time context
        lead_time_context = decision_result.get("lead_time_context", {})
        effective_lead_time = lead_time_context.get("effective_lead_time_days")
        lead_time_override = lead_time_context.get("lead_time_override_applied", False)
        
        # Extract quantity context
        quantity_context = decision_result.get("quantity_context")
        
        # Extract reorder point context
        reorder_point_context = decision_result.get("reorder_point_context")
        
        print(f"✅ Decision: {decision_result['final_decision']['reorder_timing']} + "
              f"{decision_result['final_decision']['order_strategy']} "
              f"(Risk: {decision_result['final_decision']['risk_level']}, "
              f"Confidence: {decision_result['confidence']:.2f})")
        
        if lead_time_override:
            print(f"   ⚡ Lead time override applied: effective_lead_time={effective_lead_time}d >= 7d")
        
        if quantity_context:
            qty_range = quantity_context.get("recommended_quantity_range", {})
            print(f"   📦 Recommended quantity: {qty_range.get('lower', 0)}-{qty_range.get('upper', 0)} units")
        
        if reorder_point_context:
            rop = reorder_point_context.get("reorder_point_units", 0)
            rop_status = reorder_point_context.get("status", "")
            days_cover = reorder_point_context.get("days_of_cover_left", 0)
            print(f"   🎯 Reorder Point: {rop} units (status: {rop_status}, {days_cover} days cover)")
        
        print("\n" + "="*60)
        print("✅ MAESTRO DETERMINISTIC PIPELINE COMPLETE")
        print("="*60 + "\n")
        
        # ========================================
        # BUILD FINAL RESPONSE
        # ========================================
        return {
            "success": True,
            "pipeline": "deterministic",
            "data_source": data_source,
            "final_decision": decision_result["final_decision"],
            "explanation": decision_result["explanation"],
            "confidence": decision_result["confidence"],
            "risk_profile": {
                "demand_risk": risk_profile["demand_risk"],
                "supplier_risk": risk_profile["supplier_risk"],
                "warehouse_stress": risk_profile["warehouse_stress"],
                "cash_risk": risk_profile["cash_risk"],
                "effective_lead_time_days": risk_profile.get("effective_lead_time_days"),
            },
            "lead_time_context": lead_time_context,
            "quantity_context": quantity_context,
            "reorder_point_context": reorder_point_context,
            "input_context": {
                k: v for k, v in input_context.items() 
                if k != "business_state"  # Don't echo back full business_state
            }
        }
        
    except Exception as e:
        print(f"\n❌ Pipeline error: {str(e)}")
        return {
            "success": False,
            "pipeline": "deterministic",
            "data_source": "error",
            "error": str(e),
            "final_decision": {
                "reorder_timing": "NORMAL",
                "order_strategy": "BULK",
                "risk_level": "MODERATE"
            },
            "explanation": "Unable to process inputs. Defaulting to standard recommendation.",
            "confidence": 0.5,
            "risk_profile": {},
            "input_context": {
                k: v for k, v in input_context.items() 
                if k != "business_state"
            }
        }


def extract_json_from_response(response_text: str) -> dict:
    """
    Extract JSON from agent response, handling markdown code blocks.
    """
    text = str(response_text)
    
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        text = json_match.group(1)
    
    # Try to find JSON object pattern
    json_obj_match = re.search(r'\{[\s\S]*\}', text)
    if json_obj_match:
        try:
            return json.loads(json_obj_match.group())
        except json.JSONDecodeError:
            pass
    
    # Return empty dict if parsing fails
    return {}


def run_full_pipeline(user_responses: dict, use_deterministic_core: bool = True) -> dict:
    """
    Execute the complete 6-agent MAESTRO unified pipeline.
    
    PIPELINE STAGES:
    0. Raw Data Preservation → Single Source of Truth (q1-q10)
    1. Router Agent [LLM] → structured business context
    2. Signal Conversion [DETERMINISTIC] → numeric internal risk signals
    3. External Risk Scout [LLM] → bounded modifiers [-0.2, +0.3]
    4. Risk Assessment [DETERMINISTIC] → composite risk score + level
    5. Policy Agent [DETERMINISTIC] → buffer policy
    6. Warehouse Agent [DETERMINISTIC] → feasibility & execution mode
    7. Decision Orchestrator [LLM] → final JSON output
    
    HARD CONSTRAINT PRIORITY:
    - Warehouse capacity ALWAYS overrides buffer intent
    - Cash risk can REDUCE buffer, never increase it
    - External modifiers are bounded [-0.2, +0.3]
    
    Args:
        user_responses: Dict of user answers from onboarding (q1-q10 or named keys)
        use_deterministic_core: If True, use rule-based logic for stages 4-6.
                               If False, use LLM for all stages.
        
    Returns:
        {
            "success": bool,
            "pipeline": "full",
            "raw_answers": {...},
            "stages": {...},  # Output from each stage
            "result": {...}   # Final orchestrator output
        }
    """
    print("\n" + "="*70)
    print("🚀 MAESTRO UNIFIED PIPELINE - Starting Full Analysis")
    print("="*70)
    print(f"   Mode: {'Hybrid (LLM + Deterministic)' if use_deterministic_core else 'Full LLM'}")
    print("="*70 + "\n")
    
    # Initialize LLM
    llm = None
    if Config.GOOGLE_API_KEY:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.2  # Lower temperature for more consistent outputs
        )
    
    if not llm:
        print("⚠️ No LLM configured - returning mock response")
        return {
            "success": False,
            "pipeline": "full",
            "error": "No LLM configured",
            "result": generate_mock_response(user_responses)["result"]
        }
    
    # Get all agents
    agents = get_all_agents(llm)
    
    # Accumulated stage outputs
    stages = {}
    
    try:
        # ════════════════════════════════════════════════════════════════════
        # STAGE 0: RAW DATA PRESERVATION - Single Source of Truth
        # ════════════════════════════════════════════════════════════════════
        print("\n📦 STAGE 0: Preserving Raw Answers as Single Source of Truth...")
        
        raw_answers = preserve_raw_answers(user_responses)
        stages['raw_answers'] = raw_answers
        
        non_empty = {k: v for k, v in raw_answers.items() if v}
        print(f"   ✅ Preserved {len(non_empty)} raw answers: {list(non_empty.keys())}")
        
        # ════════════════════════════════════════════════════════════════════
        # STAGE 1: ROUTER AGENT [LLM] - Context Summarization
        # ════════════════════════════════════════════════════════════════════
        print("\n📋 STAGE 1: Router Agent - Understanding Business Context [LLM]...")
        
        intake_task = create_intake_analysis_task(
            agents["router_intake"],
            raw_answers
        )
        
        intake_crew = Crew(
            agents=[agents["router_intake"]],
            tasks=[intake_task],
            process=Process.sequential,
            verbose=True
        )
        
        intake_result = intake_crew.kickoff()
        context_summary = extract_json_from_response(intake_result.raw)
        
        # Validate context_summary has required fields
        if not context_summary:
            context_summary = _generate_default_context_summary(raw_answers)
        
        stages['context_summary'] = context_summary
        print(f"   ✅ Context summary extracted: {list(context_summary.keys())}")
        
        # ════════════════════════════════════════════════════════════════════
        # STAGE 2: SIGNAL CONVERSION [DETERMINISTIC]
        # ════════════════════════════════════════════════════════════════════
        print("\n🔢 STAGE 2: Signal Conversion - Categorical to Numeric [DETERMINISTIC]...")
        
        internal_risks = convert_context_to_signals(context_summary)
        stages['internal_risks'] = internal_risks
        
        print(f"   ✅ Internal risks: demand={internal_risks['demand_risk']:.2f}, "
              f"supplier={internal_risks['supplier_risk']:.2f}, "
              f"warehouse={internal_risks['warehouse_stress']:.2f}, "
              f"cash={internal_risks['cash_risk']:.2f}")
        
        # ════════════════════════════════════════════════════════════════════
        # STAGE 3: EXTERNAL RISK SCOUT [LLM] - Bounded Modifiers
        # ════════════════════════════════════════════════════════════════════
        print("\n🌐 STAGE 3: External Risk Scout - Analyzing External Factors [LLM]...")
        
        external_task = create_external_risk_task(
            agents["research_risk"],
            context_summary
        )
        
        external_crew = Crew(
            agents=[agents["research_risk"]],
            tasks=[external_task],
            process=Process.sequential,
            verbose=True
        )
        
        external_result = external_crew.kickoff()
        external_risks = extract_json_from_response(external_result.raw)
        
        # Clamp external modifiers to bounds [-0.2, +0.3]
        external_risks = _clamp_external_modifiers(external_risks)
        stages['external_risks'] = external_risks
        
        print(f"   ✅ External modifiers: demand={external_risks.get('external_demand_risk_modifier', 0):.2f}, "
              f"lead_time={external_risks.get('external_lead_time_risk_modifier', 0):.2f}")
        
        # ════════════════════════════════════════════════════════════════════
        # STAGE 4: RISK ASSESSMENT [DETERMINISTIC]
        # ════════════════════════════════════════════════════════════════════
        print("\n📊 STAGE 4: Risk Assessment - Computing Composite Risk [DETERMINISTIC]...")
        
        if use_deterministic_core:
            # Use deterministic calculation
            risk_assessment = _compute_risk_assessment(internal_risks, external_risks)
        else:
            # Use LLM (for formatting only)
            risk_input = {
                'internal_risks': internal_risks,
                'external_modifiers': {
                    'external_demand_risk_modifier': external_risks.get('external_demand_risk_modifier', 0),
                    'external_lead_time_risk_modifier': external_risks.get('external_lead_time_risk_modifier', 0)
                }
            }
            risk_task = create_risk_assessment_task(agents["risk_assessment"], risk_input)
            risk_crew = Crew(
                agents=[agents["risk_assessment"]],
                tasks=[risk_task],
                process=Process.sequential,
                verbose=True
            )
            risk_result = risk_crew.kickoff()
            risk_assessment = extract_json_from_response(risk_result.raw)
            if not risk_assessment:
                risk_assessment = _compute_risk_assessment(internal_risks, external_risks)
        
        stages['risk_assessment'] = risk_assessment
        print(f"   ✅ Risk Level: {risk_assessment.get('risk_level', 'UNKNOWN')}, "
              f"Composite: {risk_assessment.get('composite_risk_score', 0):.2f}")
        
        # ════════════════════════════════════════════════════════════════════
        # STAGE 5: POLICY AGENT [DETERMINISTIC]
        # ════════════════════════════════════════════════════════════════════
        print("\n📜 STAGE 5: Policy Agent - Determining Buffer Strategy [DETERMINISTIC]...")
        
        if use_deterministic_core:
            # Use deterministic calculation
            buffer_policy = _compute_buffer_policy(risk_assessment)
        else:
            # Use LLM (for formatting only)
            policy_task = create_policy_task(agents["policy"], risk_assessment)
            policy_crew = Crew(
                agents=[agents["policy"]],
                tasks=[policy_task],
                process=Process.sequential,
                verbose=True
            )
            policy_result = policy_crew.kickoff()
            buffer_policy = extract_json_from_response(policy_result.raw)
            if not buffer_policy or 'buffer_policy' not in buffer_policy:
                buffer_policy = _compute_buffer_policy(risk_assessment)
        
        stages['buffer_policy'] = buffer_policy
        bp = buffer_policy.get('buffer_policy', buffer_policy)
        print(f"   ✅ Buffer Posture: {bp.get('buffer_posture', 'UNKNOWN')}, "
              f"Philosophy: {bp.get('inventory_philosophy', 'UNKNOWN')}")
        
        # ════════════════════════════════════════════════════════════════════
        # STAGE 6: WAREHOUSE AGENT [DETERMINISTIC] - Hard Constraints
        # ════════════════════════════════════════════════════════════════════
        print("\n🏭 STAGE 6: Warehouse Agent - Enforcing Physical Constraints [DETERMINISTIC]...")
        
        # Extract warehouse inputs from context
        warehouse_inputs = _extract_warehouse_inputs(context_summary, raw_answers)
        
        if use_deterministic_core:
            # Use deterministic calculation
            warehouse_assessment = _compute_warehouse_assessment(warehouse_inputs, buffer_policy)
        else:
            # Use LLM (for formatting only)
            warehouse_input = {
                'warehouse_inputs': warehouse_inputs,
                'buffer_policy': buffer_policy.get('buffer_policy', buffer_policy)
            }
            warehouse_task = create_warehouse_assessment_task(agents["warehouse"], warehouse_input)
            warehouse_crew = Crew(
                agents=[agents["warehouse"]],
                tasks=[warehouse_task],
                process=Process.sequential,
                verbose=True
            )
            warehouse_result = warehouse_crew.kickoff()
            warehouse_assessment = extract_json_from_response(warehouse_result.raw)
            if not warehouse_assessment or 'warehouse_assessment' not in warehouse_assessment:
                warehouse_assessment = _compute_warehouse_assessment(warehouse_inputs, buffer_policy)
        
        stages['warehouse_assessment'] = warehouse_assessment
        wa = warehouse_assessment.get('warehouse_assessment', warehouse_assessment)
        print(f"   ✅ Execution Mode: {wa.get('execution_mode', 'UNKNOWN')}, "
              f"Hard Constraint: {wa.get('hard_constraint_triggered', False)}")
        
        # ════════════════════════════════════════════════════════════════════
        # STAGE 7: DECISION ORCHESTRATOR [LLM] - Final Output
        # ════════════════════════════════════════════════════════════════════
        print("\n🎭 STAGE 7: Decision Orchestrator - Creating Final Recommendation [LLM]...")
        
        # Build complete analysis for orchestrator
        orchestrator_input = {
            'context_summary': context_summary,
            'external_risks': external_risks,
            'risk_assessment': risk_assessment,
            'buffer_policy': buffer_policy.get('buffer_policy', buffer_policy),
            'warehouse_assessment': warehouse_assessment.get('warehouse_assessment', warehouse_assessment)
        }
        
        orchestrator_task = create_orchestrator_task(
            agents["orchestrator"],
            orchestrator_input
        )
        
        orchestrator_crew = Crew(
            agents=[agents["orchestrator"]],
            tasks=[orchestrator_task],
            process=Process.sequential,
            verbose=True
        )
        
        final_result = orchestrator_crew.kickoff()
        final_output = extract_json_from_response(final_result.raw)
        
        # Validate final output has required structure
        if not final_output or 'final_decision' not in final_output:
            final_output = _generate_fallback_decision(stages)
        
        stages['final_output'] = final_output
        
        print("\n" + "="*70)
        print("✅ MAESTRO UNIFIED PIPELINE COMPLETE")
        print("="*70)
        fd = final_output.get('final_decision', {})
        print(f"   Reorder Timing: {fd.get('reorder_timing', 'N/A')}")
        print(f"   Order Strategy: {fd.get('order_strategy', 'N/A')}")
        print(f"   Risk Level: {fd.get('risk_level', 'N/A')}")
        print(f"   Confidence: {fd.get('confidence', 0):.2f}")
        print("="*70 + "\n")
        
        return {
            "success": True,
            "pipeline": "full",
            "raw_answers": raw_answers,
            "stages": stages,
            "result": final_output
        }
        
    except Exception as e:
        print(f"\n❌ Pipeline error at stage: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "pipeline": "full",
            "error": str(e),
            "raw_answers": preserve_raw_answers(user_responses),
            "stages": stages,
            "result": generate_mock_response(user_responses)["result"]
        }


# =============================================================================
# DETERMINISTIC HELPER FUNCTIONS
# =============================================================================

def _clamp_external_modifiers(external_risks: dict) -> dict:
    """
    Clamp external modifiers to bounds [-0.2, +0.3].
    This is a HARD CONSTRAINT that cannot be violated.
    """
    if not external_risks:
        return {
            'external_demand_risk_modifier': 0.0,
            'external_lead_time_risk_modifier': 0.0,
            'external_factors': [],
            'market_outlook': 'neutral'
        }
    
    demand_mod = external_risks.get('external_demand_risk_modifier', 0)
    lead_time_mod = external_risks.get('external_lead_time_risk_modifier', 0)
    
    # Clamp to bounds
    external_risks['external_demand_risk_modifier'] = max(-0.2, min(0.3, float(demand_mod)))
    external_risks['external_lead_time_risk_modifier'] = max(-0.2, min(0.3, float(lead_time_mod)))
    
    return external_risks


def _compute_risk_assessment(internal_risks: dict, external_risks: dict) -> dict:
    """
    Deterministic risk assessment calculation.
    
    Formula:
    - adjusted_demand = clamp(demand_risk + external_demand_modifier, 0, 1)
    - adjusted_supplier = clamp(supplier_risk + external_lead_time_modifier, 0, 1)
    - composite = (adjusted_demand × 0.35) + (adjusted_supplier × 0.35) + (warehouse × 0.30)
    
    Classification:
    - < 0.4 → LOW
    - < 0.7 → MODERATE
    - ≥ 0.7 → HIGH
    """
    # Get internal risks
    demand_risk = internal_risks.get('demand_risk', 0.5)
    supplier_risk = internal_risks.get('supplier_risk', 0.5)
    warehouse_stress = internal_risks.get('warehouse_stress', 0.5)
    cash_risk = internal_risks.get('cash_risk', 0.5)
    
    # Get external modifiers
    demand_mod = external_risks.get('external_demand_risk_modifier', 0)
    lead_time_mod = external_risks.get('external_lead_time_risk_modifier', 0)
    
    # Adjust risks (clamp to 0-1)
    adjusted_demand = max(0.0, min(1.0, demand_risk + demand_mod))
    adjusted_supplier = max(0.0, min(1.0, supplier_risk + lead_time_mod))
    
    # Compute composite (warehouse_stress and cash_risk unchanged)
    composite = (adjusted_demand * 0.35) + (adjusted_supplier * 0.35) + (warehouse_stress * 0.30)
    
    # Classify risk level
    if composite < 0.4:
        risk_level = "LOW"
    elif composite < 0.7:
        risk_level = "MODERATE"
    else:
        risk_level = "HIGH"
    
    return {
        "adjusted_risks": {
            "demand_risk": round(adjusted_demand, 2),
            "supplier_risk": round(adjusted_supplier, 2),
            "warehouse_stress": round(warehouse_stress, 2),
            "cash_flow_risk": round(cash_risk, 2)
        },
        "composite_risk_score": round(composite, 2),
        "risk_level": risk_level
    }


def _compute_buffer_policy(risk_assessment: dict) -> dict:
    """
    Deterministic buffer policy calculation.
    
    Policy Logic:
    - LOW → MINIMAL / LEAN / 90%
    - MODERATE → MODERATE / BALANCED / 95%
    - HIGH → AGGRESSIVE / PROTECTIVE / 98-99%
    
    Cash Constraint Adjustment:
    - If cash_flow_risk >= 0.7: Reduce buffer by one level
    """
    risk_level = risk_assessment.get('risk_level', 'MODERATE')
    adjusted_risks = risk_assessment.get('adjusted_risks', {})
    cash_risk = adjusted_risks.get('cash_flow_risk', 0.5)
    
    # Base policy based on risk level
    if risk_level == "LOW":
        buffer_posture = "MINIMAL"
        philosophy = "LEAN"
        service_target = "90%"
    elif risk_level == "MODERATE":
        buffer_posture = "MODERATE"
        philosophy = "BALANCED"
        service_target = "95%"
    else:  # HIGH
        buffer_posture = "AGGRESSIVE"
        philosophy = "PROTECTIVE"
        service_target = "98-99%"
    
    # Apply cash constraint (can only REDUCE, never increase)
    cash_constraint_applied = False
    if cash_risk >= 0.7:
        cash_constraint_applied = True
        if buffer_posture == "AGGRESSIVE":
            buffer_posture = "MODERATE"
            philosophy = "BALANCED"
            service_target = "95%"
        elif buffer_posture == "MODERATE":
            buffer_posture = "MINIMAL"
            philosophy = "LEAN"
            service_target = "90%"
        # MINIMAL stays MINIMAL
    
    return {
        "buffer_policy": {
            "risk_level": risk_level,
            "buffer_posture": buffer_posture,
            "inventory_philosophy": philosophy,
            "service_level_target": service_target,
            "cash_constraint_applied": cash_constraint_applied
        }
    }


def _extract_warehouse_inputs(context_summary: dict, raw_answers: dict) -> dict:
    """
    Extract warehouse inputs from context summary and raw answers.
    """
    warehouse_summary = context_summary.get('warehouse_summary', {})
    business_profile = context_summary.get('business_profile', {})
    
    # Map capacity_status to utilization estimate
    capacity_status = warehouse_summary.get('capacity_status', 'tight')
    status_to_utilization = {
        'comfortable': 0.4,
        'tight': 0.65,
        'critical': 0.85
    }
    
    # Estimate stock values (since we don't have actual numbers from onboarding)
    # In production, this would come from actual inventory data
    utilization = status_to_utilization.get(capacity_status.lower(), 0.65)
    max_capacity = 100  # Normalized
    current_stock = int(utilization * max_capacity)
    
    # Get perishability
    perishability = business_profile.get('perishability', 'medium')
    
    # Infer storage type from business profile
    products = business_profile.get('products', '').lower()
    if 'flower' in products or 'fresh' in products or 'food' in products:
        storage_type = 'refrigerated'
    elif 'frozen' in products or 'ice' in products:
        storage_type = 'cold'
    else:
        storage_type = 'ambient'
    
    return {
        'current_stock': current_stock,
        'max_capacity': max_capacity,
        'storage_type': storage_type,
        'perishability': perishability.lower()
    }


def _compute_warehouse_assessment(warehouse_inputs: dict, buffer_policy: dict) -> dict:
    """
    Deterministic warehouse assessment calculation.
    
    Process:
    1. Compute utilization = current_stock / max_capacity
    2. Classify stress: <0.5 LOW, 0.5-0.75 MEDIUM, ≥0.75 HIGH
    3. HIGH stress → SPLIT_DELIVERIES (hard constraint)
    4. High perishability → DAILY frequency
    
    WAREHOUSE CONSTRAINTS ARE NON-NEGOTIABLE.
    """
    current_stock = warehouse_inputs.get('current_stock', 50)
    max_capacity = warehouse_inputs.get('max_capacity', 100)
    perishability = warehouse_inputs.get('perishability', 'medium')
    
    # Compute utilization
    utilization = current_stock / max_capacity if max_capacity > 0 else 0.5
    
    # Classify capacity stress
    if utilization < 0.5:
        capacity_stress = "LOW"
    elif utilization < 0.75:
        capacity_stress = "MEDIUM"
    else:
        capacity_stress = "HIGH"
    
    # Determine execution mode (HARD CONSTRAINT)
    hard_constraint_triggered = False
    if utilization >= 0.75:
        execution_mode = "SPLIT_DELIVERIES"
        hard_constraint_triggered = True
        max_fill_guideline = "Do not exceed 85% capacity at any time"
    elif perishability == "high":
        execution_mode = "SPLIT_DELIVERIES"
        max_fill_guideline = "Fresh goods require frequent turnover"
    else:
        execution_mode = "BULK_ALLOWED"
        max_fill_guideline = "Standard capacity guidelines apply"
    
    # Determine preferred frequency
    if perishability == "high":
        preferred_frequency = "DAILY"
    elif utilization >= 0.75:
        preferred_frequency = "2-3x weekly"
    elif utilization >= 0.5:
        preferred_frequency = "weekly"
    else:
        preferred_frequency = "biweekly"
    
    return {
        "warehouse_assessment": {
            "warehouse_utilization": round(utilization, 2),
            "capacity_stress": capacity_stress,
            "execution_mode": execution_mode,
            "preferred_frequency": preferred_frequency,
            "max_fill_guideline": max_fill_guideline,
            "hard_constraint_triggered": hard_constraint_triggered
        }
    }


def _generate_default_context_summary(raw_answers: dict) -> dict:
    """
    Generate a default context summary if Router Agent fails.
    """
    return {
        "business_profile": {
            "industry": "retail",
            "products": raw_answers.get('q1', 'general goods'),
            "scale": "medium",
            "perishability": "medium"
        },
        "demand_summary": {
            "pattern": "stable",
            "drivers": [],
            "risk_level": "medium"
        },
        "supplier_summary": {
            "reliability": "medium",
            "delay_frequency": "occasional",
            "risk_level": "medium"
        },
        "warehouse_summary": {
            "capacity_status": "tight",
            "constraint_level": "medium"
        },
        "financial_summary": {
            "cash_flow_sensitivity": "medium"
        },
        "operational_summary": {
            "system_maturity": "manual",
            "key_gaps": []
        },
        "primary_business_goal": raw_answers.get('q10', 'optimize inventory'),
        "overall_context_narrative": "Business context extracted from onboarding answers."
    }


def _generate_fallback_decision(stages: dict) -> dict:
    """
    Generate a fallback decision if Orchestrator Agent fails.
    Uses outputs from previous stages to construct a valid response.
    """
    risk_assessment = stages.get('risk_assessment', {})
    warehouse_assessment = stages.get('warehouse_assessment', {})
    buffer_policy = stages.get('buffer_policy', {})
    
    risk_level = risk_assessment.get('risk_level', 'MODERATE')
    wa = warehouse_assessment.get('warehouse_assessment', warehouse_assessment)
    bp = buffer_policy.get('buffer_policy', buffer_policy)
    
    # Determine reorder timing from risk level
    timing_map = {'HIGH': 'EARLY', 'MODERATE': 'NORMAL', 'LOW': 'DELAYED'}
    reorder_timing = timing_map.get(risk_level, 'NORMAL')
    
    # Get order strategy from warehouse
    order_strategy = wa.get('execution_mode', 'SPLIT_DELIVERIES')
    
    # Confidence based on risk level
    confidence_map = {'HIGH': 0.80, 'MODERATE': 0.68, 'LOW': 0.58}
    confidence = confidence_map.get(risk_level, 0.68)
    
    return {
        "final_decision": {
            "reorder_timing": reorder_timing,
            "order_strategy": order_strategy,
            "risk_level": risk_level,
            "confidence": confidence
        },
        "what_we_understood": {
            "demand_situation": "Demand pattern analyzed from your inputs",
            "supplier_situation": "Supplier reliability assessed",
            "warehouse_situation": f"Storage at {wa.get('warehouse_utilization', 0.5)*100:.0f}% capacity",
            "key_constraint": "Warehouse capacity" if wa.get('hard_constraint_triggered') else "Risk management"
        },
        "detected_risks": [
            {
                "risk": "Overall Risk",
                "level": risk_level,
                "explanation": f"Composite risk assessment indicates {risk_level.lower()} risk level"
            }
        ],
        "why_this_decision": f"Based on your {risk_level.lower()} risk profile and {bp.get('buffer_posture', 'moderate').lower()} buffer strategy, we recommend {reorder_timing.lower()} reordering with {order_strategy.lower().replace('_', ' ')}.",
        "immediate_actions": [
            "Review current stock levels",
            "Contact suppliers for delivery scheduling",
            "Set up reorder alerts",
            "Monitor inventory weekly",
            "Track sales patterns"
        ],
        "warnings": ["Warehouse constraint active - avoid bulk orders"] if wa.get('hard_constraint_triggered') else []
    }


def run_quick_analysis(user_responses: dict) -> dict:
    """
    Run a faster single-stage analysis for quick results.
    Uses only the Router/Intake agent.
    """
    print("\n⚡ Running Quick Analysis Mode...")
    
    llm = None
    if Config.GOOGLE_API_KEY:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.3
        )
    
    if not llm:
        return generate_mock_response(user_responses)
    
    agents = get_all_agents(llm)
    
    try:
        intake_task = create_intake_analysis_task(
            agents["router_intake"],
            user_responses
        )
        
        crew = Crew(
            agents=[agents["router_intake"]],
            tasks=[intake_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        signals = extract_json_from_response(result.raw)
        
        # Generate a quick recommendation based on signals
        return {
            "success": True,
            "mode": "quick",
            "signals": signals,
            "result": quick_decision_from_signals(signals)
        }
        
    except Exception as e:
        print(f"Quick analysis error: {e}")
        return generate_mock_response(user_responses)


def quick_decision_from_signals(signals: dict) -> dict:
    """
    Generate a quick decision from intake signals without full pipeline.
    """
    demand = signals.get('demand_risk', 0.5)
    supplier = signals.get('supplier_risk', 0.5)
    warehouse = signals.get('warehouse_stress', 0.5)
    cash = signals.get('cash_risk', 0.5)
    
    composite = (demand + supplier + warehouse + cash) / 4
    
    # Quick decision rules
    if composite > 0.7:
        timing = "EARLY"
        strategy = "Split into smaller, frequent orders"
        risk = "HIGH"
    elif composite > 0.5:
        timing = "EARLY"
        strategy = "Standard orders with safety buffer"
        risk = "MODERATE"
    else:
        timing = "NORMAL"
        strategy = "Regular ordering schedule"
        risk = "LOW"
    
    if warehouse > 0.7:
        strategy = "Split into smaller, frequent orders"
    
    return {
        "final_decision": {
            "reorder_timing": timing,
            "order_strategy": strategy,
            "risk_level": risk,
            "confidence": 0.75
        },
        "what_we_understood": {
            "demand_situation": f"Demand variability is {'high' if demand > 0.6 else 'moderate' if demand > 0.4 else 'low'}",
            "supplier_situation": f"Supplier reliability is {'a concern' if supplier > 0.6 else 'moderate' if supplier > 0.4 else 'good'}",
            "warehouse_situation": f"Storage space is {'limited' if warehouse > 0.6 else 'adequate' if warehouse > 0.4 else 'ample'}",
            "key_constraint": "Supplier delays" if supplier >= max(demand, warehouse, cash) else 
                            "Demand volatility" if demand >= max(supplier, warehouse, cash) else
                            "Storage capacity" if warehouse >= max(supplier, demand, cash) else
                            "Cash flow"
        },
        "detected_risks": [
            {
                "risk": "Demand Volatility",
                "level": "HIGH" if demand > 0.7 else "MODERATE" if demand > 0.4 else "LOW",
                "explanation": "Your sales patterns show variability that needs buffer stock"
            },
            {
                "risk": "Supplier Delays",
                "level": "HIGH" if supplier > 0.7 else "MODERATE" if supplier > 0.4 else "LOW",
                "explanation": "Delivery times may vary, requiring earlier ordering"
            },
            {
                "risk": "Storage Constraints",
                "level": "HIGH" if warehouse > 0.7 else "MODERATE" if warehouse > 0.4 else "LOW",
                "explanation": "Limited space affects how much you can order at once"
            }
        ],
        "recommendation": {
            "timing": f"Reorder {7 if timing == 'EARLY' else 3 if timing == 'NORMAL' else 0} days earlier than usual",
            "quantity": strategy,
            "method": "Monitor stock weekly and adjust based on sales trends"
        },
        "why_this_decision": f"Based on your {risk.lower()} overall risk profile, we recommend {timing.lower()} reordering with {strategy.lower()}. This balances your storage constraints with the need to avoid stockouts.",
        "immediate_actions": [
            "Review your current stock levels today",
            f"Set a reminder to reorder {7 if timing == 'EARLY' else 3} days before usual",
            "Track your supplier delivery times for the next month",
            "Monitor your best-selling items more frequently"
        ],
        "warnings": ["Watch for seasonal demand changes"] if demand > 0.6 else []
    }


def generate_mock_response(user_responses: dict) -> dict:
    """
    Generate a realistic mock response when LLM is not available.
    Useful for testing and demo purposes.
    """
    # Extract business name from first response
    business_name = list(user_responses.values())[0] if user_responses else "Your Business"
    
    return {
        "success": True,
        "mode": "mock",
        "result": {
            "final_decision": {
                "reorder_timing": "EARLY",
                "order_strategy": "Split orders into weekly deliveries",
                "risk_level": "MODERATE",
                "confidence": 0.82
            },
            "what_we_understood": {
                "demand_situation": "Your demand shows moderate seasonal variation",
                "supplier_situation": "Suppliers have occasional delays of 2-5 days",
                "warehouse_situation": "Storage space is limited, needs careful planning",
                "key_constraint": "Warehouse capacity limits bulk ordering"
            },
            "detected_risks": [
                {
                    "risk": "Seasonal Demand Spike",
                    "level": "MODERATE",
                    "explanation": "Upcoming festival season may increase demand by 30-40%"
                },
                {
                    "risk": "Supplier Lead Time",
                    "level": "MODERATE",
                    "explanation": "Variable delivery times require safety buffer"
                },
                {
                    "risk": "Storage Capacity",
                    "level": "HIGH",
                    "explanation": "Limited space prevents bulk ordering"
                }
            ],
            "recommendation": {
                "timing": "Reorder 7-10 days earlier than usual",
                "quantity": "Order 20% less per order, but order twice as frequently",
                "method": "Weekly deliveries to manage space constraints"
            },
            "why_this_decision": "Your storage constraints limit bulk ordering, while supplier delays and seasonal demand require earlier reordering. Splitting orders into smaller, weekly deliveries balances these factors while maintaining stock availability.",
            "immediate_actions": [
                "Calculate your weekly consumption for top 5 products",
                "Contact supplier to arrange weekly delivery schedule",
                "Set up reorder alerts for 7 days before usual timing",
                "Clear slow-moving stock to free up storage space"
            ],
            "warnings": [
                "Watch for transport disruptions during festival season"
            ]
        }
    }
