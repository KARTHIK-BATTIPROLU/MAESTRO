"""
MAESTRO - MSME Inventory Intelligence System
Production Task Definitions for CrewAI Agents  (refactored)

5-STAGE PIPELINE:
1. Intake Analysis        → Structured Signals
2. External Risk Research → Risk Modifiers
3. Warehouse Assessment   → Feasibility Constraints
4. Risk Assessment        → Composite Risk Score
5. Policy                 → Buffer Posture
6. Inventory Decision     → Correlated Recommendation
7. Final Orchestration    → User-Ready Output

DETERMINISTIC BYPASS:
- create_inventory_decision_task_deterministic → rule-based engine, no LLM

DESIGN PRINCIPLES (vs. original):
- Typed schemas (dataclasses) replace untyped dicts with nested .get() chains
- Prompts live in prompt_templates.py — tasks.py contains only wiring
- Constants (weights, thresholds, key-maps) live in constants.py — single source of truth
- All risk values are clamped at construction time via schema __post_init__
- No arithmetic in LLM prompts — deterministic math stays in decision_engine.py
"""

from __future__ import annotations

from crewai import Task

from agents import execute_inventory_decision
from constants import (
    DEFAULT_RISK,
    Q_KEY_MAP,
    NUM_QUESTIONS,
)
from schemas import (
    StandardizedResponses,
    InternalRisks,
    ExternalModifiers,
    WarehouseInputs,
    BufferPolicy,
    RiskAssessment,
    BusinessContext,
    BusinessProfile,
    WarehouseAssessment,
    LeadTimeContext,
    _clamp,
)
import prompt_templates as PT


# =============================================================================
# HELPERS
# =============================================================================

def _standardize_responses(user_responses: dict) -> StandardizedResponses:
    """
    Convert arbitrary user-response dicts into a typed StandardizedResponses.

    Handles three key formats:
      1. Already q1–q10  → pass through
      2. Named keys       → map via Q_KEY_MAP
      3. Unknown keys     → fill next open slot sequentially
    """
    slots: dict[str, str] = {}

    for key, value in user_responses.items():
        if key.startswith("q") and key[1:].isdigit():
            slots[key] = str(value)
        elif key in Q_KEY_MAP:
            slots[Q_KEY_MAP[key]] = str(value)
        else:
            idx = len(slots) + 1
            if idx <= NUM_QUESTIONS:
                slots[f"q{idx}"] = str(value)

    return StandardizedResponses(**{k: v for k, v in slots.items()})


def _extract_business_context(raw: dict) -> BusinessContext:
    """Build a typed BusinessContext from the raw dict returned by the Router Agent."""
    bp = raw.get("business_profile", {})
    ds = raw.get("demand_summary", {})
    ss = raw.get("supplier_summary", {})

    return BusinessContext(
        business_profile=BusinessProfile(
            industry=bp.get("industry", "retail"),
            products=bp.get("products", "general goods"),
            scale=bp.get("scale", "medium"),
            perishability=bp.get("perishability", "medium"),
        ),
        demand_pattern=ds.get("pattern", "stable"),
        demand_risk_level=ds.get("risk_level", "medium"),
        supplier_reliability=ss.get("reliability", "medium"),
        overall_context_narrative=raw.get("overall_context_narrative", ""),
        primary_business_goal=raw.get("primary_business_goal", ""),
    )


def _extract_internal_risks(raw: dict) -> InternalRisks:
    """Pull internal risk signals from nested-or-flat dict."""
    inner = raw.get("internal_risks", raw)
    return InternalRisks(
        demand_risk=inner.get("demand_risk", DEFAULT_RISK),
        supplier_risk=inner.get("supplier_risk", DEFAULT_RISK),
        warehouse_stress=inner.get("warehouse_stress", DEFAULT_RISK),
        cash_flow_risk=inner.get("cash_flow_risk", inner.get("cash_risk", DEFAULT_RISK)),
    )


def _extract_external_modifiers(raw: dict) -> ExternalModifiers:
    inner = raw.get("external_modifiers", raw)
    return ExternalModifiers(
        demand_modifier=inner.get("external_demand_risk_modifier", 0.0),
        lead_time_modifier=inner.get("external_lead_time_risk_modifier", 0.0),
    )


def _extract_warehouse_inputs(raw: dict) -> WarehouseInputs:
    inner = raw.get("warehouse_inputs", raw)
    return WarehouseInputs(
        current_stock=int(inner.get("current_stock", 50)),
        max_capacity=int(inner.get("max_capacity", 100)),
        storage_type=str(inner.get("storage_type", "ambient")),
        perishability=str(inner.get("perishability", "medium")),
    )


def _extract_buffer_policy(raw: dict) -> BufferPolicy:
    inner = raw.get("buffer_policy", raw)
    return BufferPolicy(
        risk_level=inner.get("risk_level", "MODERATE"),
        buffer_posture=inner.get("buffer_posture", "MODERATE"),
        inventory_philosophy=inner.get("inventory_philosophy", "BALANCED"),
        service_level_target=inner.get("service_level_target", "95%"),
        cash_constraint_applied=bool(inner.get("cash_constraint_applied", False)),
    )


def _extract_risk_assessment(raw: dict) -> RiskAssessment:
    adj = raw.get("adjusted_risks", {})
    return RiskAssessment(
        adjusted_risks=InternalRisks(
            demand_risk=adj.get("demand_risk", DEFAULT_RISK),
            supplier_risk=adj.get("supplier_risk", DEFAULT_RISK),
            warehouse_stress=adj.get("warehouse_stress", DEFAULT_RISK),
            cash_flow_risk=adj.get("cash_flow_risk", DEFAULT_RISK),
        ),
        composite_risk_score=raw.get("composite_risk_score", DEFAULT_RISK),
        risk_level=raw.get("risk_level", raw.get("overall_risk_level", "MODERATE")),
    )


def _extract_warehouse_assessment(raw: dict) -> WarehouseAssessment:
    inner = raw.get("warehouse_assessment", raw)
    return WarehouseAssessment(
        warehouse_utilization=inner.get("warehouse_utilization", 0.5),
        capacity_stress=inner.get("capacity_stress", "MEDIUM"),
        execution_mode=inner.get("execution_mode", "SPLIT_DELIVERIES"),
        preferred_frequency=inner.get("preferred_frequency", "weekly"),
        max_fill_guideline=inner.get("max_fill_guideline", ""),
        hard_constraint_triggered=bool(inner.get("hard_constraint_triggered", False)),
    )


# =============================================================================
# TASK FACTORIES
# =============================================================================

def create_intake_analysis_task(agent, user_responses: dict) -> Task:
    """Task 1: Router / Context-Summarization Agent."""
    responses = _standardize_responses(user_responses)
    return Task(
        description=PT.INTAKE_DESCRIPTION.format(
            formatted_input=responses.to_formatted_json(),
        ),
        expected_output=PT.INTAKE_EXPECTED,
        agent=agent,
    )


def create_external_risk_task(agent, business_context: dict) -> Task:
    """Task 2: External Data / Risk Scout Agent."""
    ctx = _extract_business_context(business_context)
    bp = ctx.business_profile
    return Task(
        description=PT.EXTERNAL_RISK_DESCRIPTION.format(
            industry=bp.industry,
            products=bp.products,
            scale=bp.scale,
            perishability=bp.perishability,
            demand_pattern=ctx.demand_pattern,
            demand_risk=ctx.demand_risk_level,
            supplier_reliability=ctx.supplier_reliability,
            overall_context=ctx.overall_context_narrative,
            primary_goal=ctx.primary_business_goal,
        ),
        expected_output=PT.EXTERNAL_RISK_EXPECTED,
        agent=agent,
    )


def create_warehouse_assessment_task(agent, intake_signals: dict) -> Task:
    """Task 3: Warehouse Capacity Agent."""
    wh = _extract_warehouse_inputs(intake_signals)
    bp = _extract_buffer_policy(intake_signals)
    return Task(
        description=PT.WAREHOUSE_DESCRIPTION.format(
            current_stock=wh.current_stock,
            max_capacity=wh.max_capacity,
            storage_type=wh.storage_type,
            perishability=wh.perishability,
            utilization=wh.utilization,
            risk_level=bp.risk_level,
            buffer_posture=bp.buffer_posture,
            inventory_philosophy=bp.inventory_philosophy,
            service_level_target=bp.service_level_target,
            cash_constraint_applied=bp.cash_constraint_applied,
        ),
        expected_output=PT.WAREHOUSE_EXPECTED,
        agent=agent,
    )


def create_risk_assessment_task(agent, all_signals: dict) -> Task:
    """Task 4: Risk Assessment Agent."""
    risks = _extract_internal_risks(all_signals)
    mods = _extract_external_modifiers(all_signals)
    return Task(
        description=PT.RISK_ASSESSMENT_DESCRIPTION.format(
            demand_risk=risks.demand_risk,
            supplier_risk=risks.supplier_risk,
            warehouse_stress=risks.warehouse_stress,
            cash_flow_risk=risks.cash_flow_risk,
            ext_demand_mod=mods.demand_modifier,
            ext_supply_mod=mods.lead_time_modifier,
        ),
        expected_output=PT.RISK_ASSESSMENT_EXPECTED,
        agent=agent,
    )


def create_policy_task(agent, policy_input: dict) -> Task:
    """Task 5: Policy Agent."""
    ra = _extract_risk_assessment(policy_input)
    adj = ra.adjusted_risks
    return Task(
        description=PT.POLICY_DESCRIPTION.format(
            demand_risk=adj.demand_risk,
            supplier_risk=adj.supplier_risk,
            warehouse_stress=adj.warehouse_stress,
            cash_flow_risk=adj.cash_flow_risk,
            composite_risk_score=ra.composite_risk_score,
            risk_level=ra.risk_level,
        ),
        expected_output=PT.POLICY_EXPECTED,
        agent=agent,
    )


def create_inventory_decision_task(agent, all_signals: dict) -> Task:
    """Task 6: Inventory Decision Engine (LLM-based)."""
    return Task(
        description=PT.INVENTORY_DECISION_DESCRIPTION.format(
            adjusted_demand_risk=all_signals.get("adjusted_demand_risk",
                                                  all_signals.get("demand_risk", DEFAULT_RISK)),
            adjusted_supplier_risk=all_signals.get("adjusted_supplier_risk",
                                                    all_signals.get("supplier_risk", DEFAULT_RISK)),
            warehouse_stress=all_signals.get("warehouse_stress", DEFAULT_RISK),
            cash_risk=all_signals.get("cash_risk", DEFAULT_RISK),
            feasible_strategy=all_signals.get("feasible_strategy", "SPLIT_ORDERS"),
            buffer_policy=all_signals.get("buffer_policy", "MEDIUM"),
            overall_risk_level=all_signals.get("overall_risk_level", "MEDIUM"),
        ),
        expected_output=PT.INVENTORY_DECISION_EXPECTED,
        agent=agent,
    )


def create_orchestrator_task(agent, all_analysis: dict) -> Task:
    """Task 7: Decision Orchestrator Agent."""
    ra = all_analysis.get("risk_assessment", {})
    wh_raw = all_analysis.get("warehouse_assessment", all_analysis.get("warehouse", {}))
    wh = _extract_warehouse_assessment(wh_raw) if wh_raw else WarehouseAssessment()
    bp = _extract_buffer_policy(all_analysis.get("buffer_policy", {}))
    lt = all_analysis.get("lead_time_context", {})

    return Task(
        description=PT.ORCHESTRATOR_DESCRIPTION.format(
            context_summary=all_analysis.get("context_summary",
                                              all_analysis.get("business_context", {})),
            external_risks=all_analysis.get("external_risks",
                                             all_analysis.get("external", {})),
            effective_lead_time_days=lt.get("effective_lead_time_days"),
            lead_time_override_applied=lt.get("lead_time_override_applied", False),
            risk_level=ra.get("risk_level", "MODERATE"),
            composite_risk=ra.get("composite_risk_score", DEFAULT_RISK),
            adjusted_risks=ra.get("adjusted_risks", {}),
            buffer_posture=bp.buffer_posture,
            inventory_philosophy=bp.inventory_philosophy,
            buffer_policy=all_analysis.get("buffer_policy", {}),
            execution_mode=wh.execution_mode,
            hard_constraint=wh.hard_constraint_triggered,
            warehouse_utilization=wh.warehouse_utilization,
            warehouse_assessment=wh_raw,
        ),
        expected_output=PT.ORCHESTRATOR_EXPECTED,
        agent=agent,
    )


# =============================================================================
# DETERMINISTIC TASK (rule-based, no LLM arithmetic)
# =============================================================================

def create_inventory_decision_task_deterministic(agent, risk_inputs: dict) -> Task:
    """
    Wrap the deterministic decision engine in a CrewAI Task.

    The LLM simply calls the tool — all math happens in decision_engine.py.
    """
    risks = InternalRisks(
        demand_risk=risk_inputs.get("demand_risk", DEFAULT_RISK),
        supplier_risk=risk_inputs.get("supplier_risk", DEFAULT_RISK),
        warehouse_stress=risk_inputs.get("warehouse_stress", DEFAULT_RISK),
        cash_flow_risk=risk_inputs.get("cash_risk", DEFAULT_RISK),
    )

    risk_summary = (
        f"  - Demand Risk:      {risks.demand_risk:.2f}\n"
        f"  - Supplier Risk:    {risks.supplier_risk:.2f}\n"
        f"  - Warehouse Stress: {risks.warehouse_stress:.2f}\n"
        f"  - Cash Risk:        {risks.cash_flow_risk:.2f}"
    )

    return Task(
        description=PT.DETERMINISTIC_DECISION_DESCRIPTION.format(
            risk_summary=risk_summary,
            demand_risk=risks.demand_risk,
            supplier_risk=risks.supplier_risk,
            warehouse_stress=risks.warehouse_stress,
            cash_risk=risks.cash_flow_risk,
        ),
        expected_output=PT.DETERMINISTIC_DECISION_EXPECTED,
        agent=agent,
    )


# =============================================================================
# STANDALONE (no CrewAI)
# =============================================================================

def run_inventory_decision_task_standalone(risk_inputs: dict) -> dict:
    """
    Direct passthrough to the deterministic decision engine.

    Useful for testing, health-check endpoints, or when the full
    CrewAI pipeline is unnecessary.
    """
    return execute_inventory_decision(risk_inputs)
