"""
MAESTRO - MSME Inventory Intelligence System
Structured Intake Questions for Router Agent
"""

ONBOARDING_QUESTIONS = [
    {
        "id": 1,
        "question": "Welcome to MAESTRO! 🏭 Let's understand your business. Can you briefly describe your business — industry, products, and scale of operations?",
        "key": "business_context",
        "options": None,  # Free text
        "signal_type": "business_profile"
    },
    {
        "id": 2,
        "question": "How do you currently decide when to reorder stock and how much to order? (e.g., gut feeling, spreadsheet, software, supplier suggestions)",
        "key": "inventory_decision_method",
        "options": ["Gut feeling / Experience", "Manual spreadsheet tracking", "Basic inventory software", "Supplier recommendations", "No fixed method"],
        "signal_type": "process_maturity"
    },
    {
        "id": 3,
        "question": "In the past 6–12 months, have you faced stockouts or excess inventory? Which happens more often and why?",
        "key": "stock_issues",
        "options": ["Mostly stockouts", "Mostly excess inventory", "Both equally", "Neither - well managed", "Not sure"],
        "signal_type": "inventory_health"
    },
    {
        "id": 4,
        "question": "How predictable are your supplier delivery times? Do delays due to transport, festivals, strikes, or imports affect your business?",
        "key": "supplier_reliability",
        "options": ["Very reliable (±1-2 days)", "Mostly reliable (±1 week)", "Unpredictable (±2+ weeks)", "Highly variable (seasonal/import delays)", "Multiple suppliers with mixed reliability"],
        "signal_type": "lead_time_risk"
    },
    {
        "id": 5,
        "question": "Does your product demand change due to seasons, festivals, or sudden trends? How do you currently handle these changes?",
        "key": "demand_variability",
        "options": ["Stable demand year-round", "Mild seasonal variation (±20%)", "Strong seasonal peaks (±50%+)", "Unpredictable trend-driven spikes", "Festival/event-driven surges"],
        "signal_type": "demand_volatility"
    },
    {
        "id": 6,
        "question": "Have you ever reordered too late or too early because supplier delays or demand changes were not anticipated?",
        "key": "reorder_timing_issues",
        "options": ["Yes, frequently (monthly)", "Yes, occasionally (quarterly)", "Rarely (once or twice a year)", "Never faced this issue", "Hard to track"],
        "signal_type": "timing_accuracy"
    },
    {
        "id": 7,
        "question": "Do you have limitations in warehouse space, storage capacity, or handling that affect how much you can order at once?",
        "key": "warehouse_constraints",
        "options": ["Severe space constraints", "Moderate limitations", "Adequate space, some handling limits", "No significant constraints", "Using external warehousing"],
        "signal_type": "capacity_stress"
    },
    {
        "id": 8,
        "question": "Does overstocking block your working capital or affect your cash flow decisions?",
        "key": "cash_flow_impact",
        "options": ["Yes, major cash flow stress", "Yes, moderate impact", "Minor inconvenience", "No impact - well capitalized", "Cash flow is always tight regardless"],
        "signal_type": "financial_sensitivity"
    },
    {
        "id": 9,
        "question": "Do your current tools consider demand changes, supplier delays, and warehouse limits together while suggesting orders?",
        "key": "system_limitations",
        "options": ["No tools - all manual", "Basic tools - single factor only", "Some integration but gaps exist", "Good integration but not automated", "Fully integrated system"],
        "signal_type": "tech_readiness"
    },
    {
        "id": 10,
        "question": "If an intelligent system could automatically recommend optimal reorder timing and quantity, what problem would you want it to solve first?",
        "key": "desired_outcome",
        "options": None,  # Free text
        "signal_type": "priority_signal"
    }
]

# Signal interpretation mappings
SIGNAL_MAPPINGS = {
    "lead_time_risk": {
        "Very reliable (±1-2 days)": "low",
        "Mostly reliable (±1 week)": "medium",
        "Unpredictable (±2+ weeks)": "high",
        "Highly variable (seasonal/import delays)": "critical",
        "Multiple suppliers with mixed reliability": "medium-high"
    },
    "demand_volatility": {
        "Stable demand year-round": "low",
        "Mild seasonal variation (±20%)": "medium",
        "Strong seasonal peaks (±50%+)": "high",
        "Unpredictable trend-driven spikes": "critical",
        "Festival/event-driven surges": "high"
    },
    "capacity_stress": {
        "Severe space constraints": "critical",
        "Moderate limitations": "high",
        "Adequate space, some handling limits": "medium",
        "No significant constraints": "low",
        "Using external warehousing": "medium"
    },
    "financial_sensitivity": {
        "Yes, major cash flow stress": "critical",
        "Yes, moderate impact": "high",
        "Minor inconvenience": "medium",
        "No impact - well capitalized": "low",
        "Cash flow is always tight regardless": "critical"
    }
}

def get_question(question_id: int) -> dict:
    """Get a specific question by ID"""
    for q in ONBOARDING_QUESTIONS:
        if q["id"] == question_id:
            return q
    return None

def get_all_questions() -> list:
    """Get all onboarding questions"""
    return ONBOARDING_QUESTIONS

def interpret_signal(signal_type: str, answer: str) -> str:
    """Convert answer to risk signal level"""
    if signal_type in SIGNAL_MAPPINGS:
        return SIGNAL_MAPPINGS[signal_type].get(answer, "unknown")
    return "requires_analysis"

def extract_signals(answers: dict) -> dict:
    """Extract structured signals from all answers"""
    signals = {
        "business_profile": answers.get("business_context", ""),
        "process_maturity": answers.get("inventory_decision_method", ""),
        "inventory_health": answers.get("stock_issues", ""),
        "lead_time_risk": interpret_signal("lead_time_risk", answers.get("supplier_reliability", "")),
        "demand_volatility": interpret_signal("demand_volatility", answers.get("demand_variability", "")),
        "timing_accuracy": answers.get("reorder_timing_issues", ""),
        "capacity_stress": interpret_signal("capacity_stress", answers.get("warehouse_constraints", "")),
        "financial_sensitivity": interpret_signal("financial_sensitivity", answers.get("cash_flow_impact", "")),
        "tech_readiness": answers.get("system_limitations", ""),
        "priority_signal": answers.get("desired_outcome", "")
    }
    return signals
