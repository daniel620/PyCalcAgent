"""Unit tests for PyCalcAgent orchestration and reasoning loop (Criterion 3: Orchestration & Logic)."""

import pytest

from pycalcagent.agent import PyCalcAgent
from pycalcagent.memory import CalculationMemory


@pytest.fixture
def agent(tmp_path):
    """Provide a PyCalcAgent instance with clean temporary SQLite memory."""
    mem_file = tmp_path / "test_memory.db"
    memory = CalculationMemory(db_path=str(mem_file))
    return PyCalcAgent(memory=memory)


def test_agent_simple_calculation(agent):
    """Test standard arithmetic calculation via multi-agent workflow."""
    response = agent.run("2 * 4")
    assert response.success is True
    assert response.result_value == "8"
    assert "8" in response.answer
    assert len(response.plan_steps) >= 3


def test_agent_save_variable(agent):
    """Test saving a variable through natural language calculation query."""
    response = agent.run("save 2 * 4 as x")
    assert response.success is True
    assert response.result_value == "8"

    assert agent.memory.get_variable("x") == 8.0


def test_agent_use_saved_variable(agent):
    """Test using a saved session variable in subsequent calculations."""
    agent.memory.set_variable("base_tax", 10.0, "Base tax amount")
    response = agent.run("base_tax * 5")
    assert response.success is True
    assert response.result_value == "50.0"
