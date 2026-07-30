"""Unit tests for multi-agent orchestration and routing (Criterion 3)."""

import pytest

from pycalcagent.memory import CalculationMemory
from pycalcagent.orchestrator import ModelRouter, MultiAgentOrchestrator, PlannerAgent


@pytest.fixture
def memory(tmp_path):
    """Provide a clean temporary SQLite memory instance."""
    db_file = tmp_path / "test_orch.db"
    return CalculationMemory(db_path=str(db_file))


def test_model_router_selection():
    """Verify ModelRouter routes simple math to flash and complex math to pro."""
    assert ModelRouter.route_query("2 * 4") == "gemini-2.5-flash"
    assert ModelRouter.route_query("calculate the integral of x squared dx") == "gemini-2.5-pro"


def test_planner_agent_steps():
    """Verify PlannerAgent generates structured execution steps."""
    steps = PlannerAgent.create_plan("2 * 4")
    assert len(steps) >= 3
    assert steps[0].step_number == 1


def test_orchestrator_execution(memory):
    """Verify MultiAgentOrchestrator runs the workflow successfully."""
    orch = MultiAgentOrchestrator(memory)
    res = orch.execute_workflow("2 * 4", lambda q, tier: "res = 2 * 4\nprint(res)")
    assert res["success"] is True
    assert res["result"] == "8"
    assert len(res["plan"]) >= 3
