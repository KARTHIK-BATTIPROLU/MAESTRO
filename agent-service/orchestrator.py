"""
MAESTRO - MSME Inventory Intelligence System
Production Orchestrator - Multi-Agent Pipeline

PIPELINE FLOW:
1. Router/Intake Agent → Structured Signals
2. Research Agent → External Risk Modifiers  
3. Warehouse Agent → Feasibility Constraints
4. Decision Agent → Correlated Recommendation
5. Orchestrator Agent → Final User Output

DETERMINISTIC PIPELINE (run_maestro_pipeline):
- Pure rule-based decision engine
- No LLM calls required
- Predictable, explainable outputs
"""
import json
import re
from crewai import Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI

from agents import get_all_agents
from tasks import (
    create_intake_analysis_task,
    create_external_risk_task,
    create_warehouse_assessment_task,
    create_inventory_decision_task,
    create_orchestrator_task
)
from config import Config

# Import deterministic decision engine components
from risk_signals import build_risk_profile
from inventory_decision_agent import run_inventory_decision_agent


# =============================================================================
# DETERMINISTIC MAESTRO PIPELINE
# =============================================================================

def run_maestro_pipeline(input_context: dict) -> dict:
    """
    Execute the deterministic MAESTRO pipeline for inventory decisions.
    
    This pipeline uses pure rule-based logic without LLM calls.
    It converts raw business inputs into structured risk signals,
    then produces a deterministic inventory decision.
    
    Args:
        input_context: Dictionary containing:
            - demand_type (str): "steady", "seasonal", "volatile"
            - seasonal_event (bool): Whether seasonal event is expected
            - supplier_delay (str): "none", "minor", "frequent", "major"
            - external_disruption (bool): Whether external disruption exists
            - current_stock (int): Current inventory level
            - max_capacity (int): Maximum warehouse capacity
            - cash_flow (str): "healthy", "tight", "critical"
    
    Returns:
        Dictionary containing:
            - success (bool): Whether pipeline executed successfully
            - final_decision: {reorder_timing, order_strategy, risk_level}
            - explanation (str): Human-readable decision explanation
            - confidence (float): Decision confidence score (0.0-1.0)
            - risk_profile: Detailed risk breakdown
    
    Example:
        >>> context = {
        ...     "demand_type": "seasonal",
        ...     "seasonal_event": True,
        ...     "supplier_delay": "frequent",
        ...     "external_disruption": False,
        ...     "current_stock": 60,
        ...     "max_capacity": 100,
        ...     "cash_flow": "tight"
        ... }
        >>> result = run_maestro_pipeline(context)
        >>> result["final_decision"]["reorder_timing"]
        'EARLY'
    """
    print("\n" + "="*60)
    print("🚀 MAESTRO DETERMINISTIC PIPELINE - Starting")
    print("="*60 + "\n")
    
    try:
        # ========================================
        # STAGE 1: BUILD RISK PROFILE
        # ========================================
        print("📊 Stage 1: Building Risk Profile from inputs...")
        
        risk_profile = build_risk_profile(input_context)
        
        print(f"✅ Risk Profile: demand={risk_profile['demand_risk']:.2f}, "
              f"supplier={risk_profile['supplier_risk']:.2f}, "
              f"warehouse={risk_profile['warehouse_stress']:.2f}, "
              f"cash={risk_profile['cash_risk']:.2f}")
        
        # ========================================
        # STAGE 2: RUN DECISION AGENT
        # ========================================
        print("\n🎯 Stage 2: Running Inventory Decision Agent...")
        
        decision_result = run_inventory_decision_agent(risk_profile)
        
        print(f"✅ Decision: {decision_result['final_decision']['reorder_timing']} + "
              f"{decision_result['final_decision']['order_strategy']} "
              f"(Risk: {decision_result['final_decision']['risk_level']}, "
              f"Confidence: {decision_result['confidence']:.2f})")
        
        print("\n" + "="*60)
        print("✅ MAESTRO DETERMINISTIC PIPELINE COMPLETE")
        print("="*60 + "\n")
        
        # ========================================
        # BUILD FINAL RESPONSE
        # ========================================
        return {
            "success": True,
            "pipeline": "deterministic",
            "final_decision": decision_result["final_decision"],
            "explanation": decision_result["explanation"],
            "confidence": decision_result["confidence"],
            "risk_profile": risk_profile,
            "input_context": input_context
        }
        
    except Exception as e:
        print(f"\n❌ Pipeline error: {str(e)}")
        return {
            "success": False,
            "pipeline": "deterministic",
            "error": str(e),
            "final_decision": {
                "reorder_timing": "NORMAL",
                "order_strategy": "BULK",
                "risk_level": "MODERATE"
            },
            "explanation": "Unable to process inputs. Defaulting to standard recommendation.",
            "confidence": 0.5,
            "risk_profile": {},
            "input_context": input_context
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


def run_full_pipeline(user_responses: dict) -> dict:
    """
    Execute the complete 5-agent MAESTRO pipeline.
    
    Args:
        user_responses: Dict of user answers from onboarding
        
    Returns:
        Final orchestrated recommendation
    """
    print("\n" + "="*60)
    print("🚀 MAESTRO PIPELINE - Starting Full Analysis")
    print("="*60 + "\n")
    
    # Initialize LLM
    llm = None
    if Config.GOOGLE_API_KEY:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.3
        )
    
    if not llm:
        print("⚠️ No LLM configured - returning mock response")
        return generate_mock_response(user_responses)
    
    # Get all agents
    agents = get_all_agents(llm)
    
    # Accumulated analysis data
    analysis_data = {}
    
    try:
        # ========================================
        # STAGE 1: INTAKE ANALYSIS
        # ========================================
        print("\n📋 STAGE 1: Router/Intake Agent - Extracting Signals...")
        
        intake_task = create_intake_analysis_task(
            agents["router_intake"],
            user_responses
        )
        
        intake_crew = Crew(
            agents=[agents["router_intake"]],
            tasks=[intake_task],
            process=Process.sequential,
            verbose=True
        )
        
        intake_result = intake_crew.kickoff()
        intake_signals = extract_json_from_response(intake_result.raw)
        
        print(f"✅ Intake signals extracted: {list(intake_signals.keys())}")
        analysis_data['intake'] = intake_signals
        analysis_data['business_context'] = intake_signals.get('business_context', {})
        analysis_data['signals'] = {
            'demand_variability': intake_signals.get('demand_variability', 0.5),
            'supplier_delay_risk': intake_signals.get('supplier_delay_risk', 0.5),
            'warehouse_capacity_stress': intake_signals.get('warehouse_capacity_stress', 0.5),
            'cash_flow_sensitivity': intake_signals.get('cash_flow_sensitivity', 0.5)
        }
        
        # ========================================
        # STAGE 2: EXTERNAL RISK ANALYSIS
        # ========================================
        print("\n🌐 STAGE 2: Research Agent - Analyzing External Factors...")
        
        external_task = create_external_risk_task(
            agents["research_risk"],
            analysis_data['business_context']
        )
        
        external_crew = Crew(
            agents=[agents["research_risk"]],
            tasks=[external_task],
            process=Process.sequential,
            verbose=True
        )
        
        external_result = external_crew.kickoff()
        external_signals = extract_json_from_response(external_result.raw)
        
        print(f"✅ External factors analyzed")
        analysis_data['external'] = external_signals
        analysis_data['signals']['external_demand_risk_modifier'] = external_signals.get('external_demand_risk_modifier', 0)
        analysis_data['signals']['external_lead_time_risk_modifier'] = external_signals.get('external_lead_time_risk_modifier', 0)
        
        # ========================================
        # STAGE 3: WAREHOUSE ASSESSMENT
        # ========================================
        print("\n🏭 STAGE 3: Warehouse Agent - Assessing Storage Constraints...")
        
        warehouse_task = create_warehouse_assessment_task(
            agents["warehouse"],
            intake_signals
        )
        
        warehouse_crew = Crew(
            agents=[agents["warehouse"]],
            tasks=[warehouse_task],
            process=Process.sequential,
            verbose=True
        )
        
        warehouse_result = warehouse_crew.kickoff()
        warehouse_signals = extract_json_from_response(warehouse_result.raw)
        
        print(f"✅ Warehouse constraints assessed")
        analysis_data['warehouse'] = warehouse_signals
        analysis_data['signals']['warehouse_stress'] = warehouse_signals.get('warehouse_stress', 
            analysis_data['signals']['warehouse_capacity_stress'])
        
        # ========================================
        # STAGE 4: INVENTORY DECISION
        # ========================================
        print("\n🎯 STAGE 4: Decision Agent - Correlating Risks...")
        
        decision_task = create_inventory_decision_task(
            agents["inventory_decision"],
            analysis_data['signals']
        )
        
        decision_crew = Crew(
            agents=[agents["inventory_decision"]],
            tasks=[decision_task],
            process=Process.sequential,
            verbose=True
        )
        
        decision_result = decision_crew.kickoff()
        decision_output = extract_json_from_response(decision_result.raw)
        
        print(f"✅ Decision generated: {decision_output.get('reorder_timing', 'N/A')}")
        analysis_data['decision'] = decision_output
        
        # ========================================
        # STAGE 5: FINAL ORCHESTRATION
        # ========================================
        print("\n🎭 STAGE 5: Orchestrator - Creating Final Recommendation...")
        
        orchestrator_task = create_orchestrator_task(
            agents["orchestrator"],
            analysis_data
        )
        
        orchestrator_crew = Crew(
            agents=[agents["orchestrator"]],
            tasks=[orchestrator_task],
            process=Process.sequential,
            verbose=True
        )
        
        final_result = orchestrator_crew.kickoff()
        final_output = extract_json_from_response(final_result.raw)
        
        print("\n" + "="*60)
        print("✅ MAESTRO PIPELINE COMPLETE")
        print("="*60 + "\n")
        
        # Return the final orchestrated output
        return {
            "success": True,
            "pipeline_complete": True,
            "analysis": analysis_data,
            "result": final_output
        }
        
    except Exception as e:
        print(f"\n❌ Pipeline error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "result": generate_mock_response(user_responses)["result"]
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
    demand = signals.get('demand_variability', 0.5)
    supplier = signals.get('supplier_delay_risk', 0.5)
    warehouse = signals.get('warehouse_capacity_stress', 0.5)
    cash = signals.get('cash_flow_sensitivity', 0.5)
    
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
