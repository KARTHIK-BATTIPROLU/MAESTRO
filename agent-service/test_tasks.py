"""
MAESTRO - tasks_refactored unit / smoke tests

Run:  python -m pytest test_tasks.py -v
"""

from tasks import (
    _standardize_responses,
    run_inventory_decision_task_standalone,
)
from schemas import InternalRisks, ExternalModifiers, StandardizedResponses


# ---------------------------------------------------------------------------
# Standardized Responses
# ---------------------------------------------------------------------------

def test_standardize_named_keys():
    raw = {"business_context": "Flower trading", "desired_outcome": "Reduce waste"}
    resp = _standardize_responses(raw)
    assert resp.q1 == "Flower trading"
    assert resp.q10 == "Reduce waste"
    assert resp.q5 == ""           # unset stays empty


def test_standardize_q_keys():
    raw = {"q1": "A", "q3": "C"}
    resp = _standardize_responses(raw)
    assert resp.q1 == "A"
    assert resp.q3 == "C"


def test_standardize_mixed_keys():
    raw = {"q1": "A", "desired_outcome": "B"}
    resp = _standardize_responses(raw)
    assert resp.q1 == "A"
    assert resp.q10 == "B"


# ---------------------------------------------------------------------------
# Schema Clamping
# ---------------------------------------------------------------------------

def test_internal_risks_clamp():
    r = InternalRisks(demand_risk=1.5, supplier_risk=-0.3)
    assert r.demand_risk == 1.0
    assert r.supplier_risk == 0.0


def test_internal_risks_none_handling():
    r = InternalRisks(demand_risk=None)
    assert r.demand_risk == 0.5   # midpoint of [0, 1]


def test_external_modifiers_clamp():
    m = ExternalModifiers(demand_modifier=0.9, lead_time_modifier=-0.5)
    assert m.demand_modifier == 0.3
    assert m.lead_time_modifier == -0.2


# ---------------------------------------------------------------------------
# Formatted Output
# ---------------------------------------------------------------------------

def test_formatted_json():
    resp = StandardizedResponses(q1="Hello", q2="World")
    out = resp.to_formatted_json()
    assert '"q1": "Hello"' in out
    assert '"q2": "World"' in out


# ---------------------------------------------------------------------------
# Deterministic Decision Standalone (integration smoke test)
# ---------------------------------------------------------------------------

HIGH_RISK = {
    "demand_risk": 0.75,
    "supplier_risk": 0.65,
    "warehouse_stress": 0.82,
    "cash_risk": 0.7,
}

LOW_RISK = {
    "demand_risk": 0.25,
    "supplier_risk": 0.2,
    "warehouse_stress": 0.35,
    "cash_risk": 0.3,
}

CASH_CONSTRAINED = {
    "demand_risk": 0.5,
    "supplier_risk": 0.4,
    "warehouse_stress": 0.5,
    "cash_risk": 0.8,
}


def test_standalone_high_risk():
    result = run_inventory_decision_task_standalone(HIGH_RISK)
    assert result["final_decision"]["reorder_timing"] == "EARLY"
    assert "confidence" in result


def test_standalone_low_risk():
    result = run_inventory_decision_task_standalone(LOW_RISK)
    assert result["final_decision"]["reorder_timing"] == "DELAYED"


def test_standalone_cash_constrained():
    result = run_inventory_decision_task_standalone(CASH_CONSTRAINED)
    assert result["final_decision"]["reorder_timing"] in ("EARLY", "NORMAL", "DELAYED")


# ---------------------------------------------------------------------------
# Run manually
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    # Quick manual runner when pytest isn't installed
    test_funcs = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failures = 0
    for fn in test_funcs:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except Exception as exc:
            print(f"  FAIL  {fn.__name__}: {exc}")
            failures += 1
    print(f"\n{'='*60}")
    print(f"{len(test_funcs) - failures}/{len(test_funcs)} passed")
    sys.exit(1 if failures else 0)
