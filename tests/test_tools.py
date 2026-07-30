"""Unit tests for PyCalcAgent tools (Criterion 1: Tool & Interface Design)."""

import pytest

from pycalcagent.memory import CalculationMemory
from pycalcagent.tools import CalculationTools


@pytest.fixture
def memory(tmp_path):
    """Provide a clean temporary memory instance."""
    mem_file = tmp_path / "test_memory.json"
    return CalculationMemory(storage_path=str(mem_file))


@pytest.fixture
def tools(memory):
    """Provide a CalculationTools instance."""
    return CalculationTools(memory=memory)


def test_execute_python_code_success(tools):
    """Test successful Python code execution."""
    code = "res = 2 * 4\nprint(res)"
    res = tools.execute_python_code(code, "Multiply 2 and 4")
    assert res["success"] is True
    assert res["stdout"] == "8"
    assert res["returncode"] == 0
    assert res["error_message"] is None


def test_execute_python_code_error(tools):
    """Test handling of runtime errors in executed Python code."""
    code = "print(10 / 0)"
    res = tools.execute_python_code(code, "Zero division test")
    assert res["success"] is False
    assert res["returncode"] != 0
    assert "ZeroDivisionError" in res["stderr"]
    assert res["error_message"] is not None


def test_save_and_list_variable(tools):
    """Test saving a variable and retrieving it."""
    res = tools.save_variable("tax_rate", 0.08, "Sales tax rate")
    assert res["status"] == "saved"
    assert res["name"] == "tax_rate"
    assert res["value"] == 0.08

    vars_dict = tools.list_saved_variables()
    assert vars_dict == {"tax_rate": 0.08}


def test_get_calculation_history(tools):
    """Test retrieving calculation history."""
    tools.memory.add_history("2 * 4", "print(8)", "8")
    tools.memory.add_history("10 + 5", "print(15)", "15")

    history = tools.get_calculation_history(limit=5)
    assert len(history) == 2
    assert history[0]["query"] == "2 * 4"
    assert history[1]["result"] == "15"
