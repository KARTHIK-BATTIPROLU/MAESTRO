"""
MAESTRO - Typed Schemas for Pipeline Data

Dataclasses enforce structure at dev time and catch key mismatches early.
Every pipeline stage consumes and produces a well-defined schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional

from constants import DEFAULT_RISK


# =============================================================================
# INPUT SCHEMAS
# =============================================================================

@dataclass
class StandardizedResponses:
    """Onboarding answers in q1–q10 format."""
    q1: str = ""
    q2: str = ""
    q3: str = ""
    q4: str = ""
    q5: str = ""
    q6: str = ""
    q7: str = ""
    q8: str = ""
    q9: str = ""
    q10: str = ""

    def to_formatted_json(self) -> str:
        """Render as indented key-value block for prompt injection."""
        lines = [f'  "q{i}": "{getattr(self, f"q{i}")}"' for i in range(1, 11)]
        return "\n".join(lines)


@dataclass
class InternalRisks:
    """Normalized internal risk signals  (all ∈ [0.0, 1.0])."""
    demand_risk: float = DEFAULT_RISK
    supplier_risk: float = DEFAULT_RISK
    warehouse_stress: float = DEFAULT_RISK
    cash_flow_risk: float = DEFAULT_RISK

    def __post_init__(self) -> None:
        self.demand_risk = _clamp(self.demand_risk)
        self.supplier_risk = _clamp(self.supplier_risk)
        self.warehouse_stress = _clamp(self.warehouse_stress)
        self.cash_flow_risk = _clamp(self.cash_flow_risk)


@dataclass
class ExternalModifiers:
    """Bounded external risk modifiers  (∈ [-0.2, +0.3])."""
    demand_modifier: float = 0.0
    lead_time_modifier: float = 0.0

    def __post_init__(self) -> None:
        self.demand_modifier = _clamp(self.demand_modifier, -0.2, 0.3)
        self.lead_time_modifier = _clamp(self.lead_time_modifier, -0.2, 0.3)


@dataclass
class WarehouseInputs:
    """Physical warehouse parameters."""
    current_stock: int = 50
    max_capacity: int = 100
    storage_type: str = "ambient"
    perishability: str = "medium"

    @property
    def utilization(self) -> float:
        return self.current_stock / self.max_capacity if self.max_capacity > 0 else 0.5


@dataclass
class BufferPolicy:
    """Output of the Policy Agent — defines stock protection strategy."""
    risk_level: str = "MODERATE"
    buffer_posture: str = "MODERATE"
    inventory_philosophy: str = "BALANCED"
    service_level_target: str = "95%"
    cash_constraint_applied: bool = False


@dataclass
class RiskAssessment:
    """Output of the Risk Assessment Agent."""
    adjusted_risks: InternalRisks = field(default_factory=InternalRisks)
    composite_risk_score: float = DEFAULT_RISK
    risk_level: str = "MODERATE"


@dataclass
class WarehouseAssessment:
    """Output of the Warehouse Agent."""
    warehouse_utilization: float = 0.5
    capacity_stress: str = "MEDIUM"
    execution_mode: str = "SPLIT_DELIVERIES"
    preferred_frequency: str = "weekly"
    max_fill_guideline: str = ""
    hard_constraint_triggered: bool = False


@dataclass
class BusinessProfile:
    """Structured profile from the Router Agent."""
    industry: str = "retail"
    products: str = "general goods"
    scale: str = "medium"
    perishability: str = "medium"


@dataclass
class BusinessContext:
    """Full structured context from the Router Agent."""
    business_profile: BusinessProfile = field(default_factory=BusinessProfile)
    demand_pattern: str = "stable"
    demand_risk_level: str = "medium"
    supplier_reliability: str = "medium"
    overall_context_narrative: str = ""
    primary_business_goal: str = ""


@dataclass
class LeadTimeContext:
    """Supplier lead time information."""
    effective_lead_time_days: Optional[float] = None
    lead_time_override_applied: bool = False


# =============================================================================
# HELPERS
# =============================================================================

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a numeric value to [lo, hi], treating None as the midpoint."""
    if value is None:
        return (lo + hi) / 2
    return max(lo, min(hi, float(value)))
