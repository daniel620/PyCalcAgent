"""Unit tests for PyCalcAgent memory and state persistence (Criterion 2: Context & Memory)."""

from pycalcagent.memory import CalculationMemory


def test_variable_persistence(tmp_path):
    """Test saving variables and loading them across memory instances."""
    storage = tmp_path / "calc_memory.json"
    mem1 = CalculationMemory(storage_path=str(storage))
    mem1.set_variable("pi_val", 3.14159, "Pi approximation")
    mem1.set_variable("base", 10.0, "Base number")

    # Re-instantiate from the same storage path
    mem2 = CalculationMemory(storage_path=str(storage))
    assert mem2.get_variable("pi_val") == 3.14159
    assert mem2.get_variable("base") == 10.0
    assert "pi_val" in mem2.list_variables()


def test_history_persistence_and_limit(tmp_path):
    """Test calculation history recording and limit retrieval."""
    storage = tmp_path / "calc_memory.json"
    mem = CalculationMemory(storage_path=str(storage))
    for i in range(10):
        mem.add_history(f"query {i}", f"print({i})", str(i))

    recent = mem.get_recent_history(limit=3)
    assert len(recent) == 3
    assert recent[-1].result == "9"


def test_clear_memory(tmp_path):
    """Test clearing all stored session variables and history."""
    storage = tmp_path / "calc_memory.json"
    mem = CalculationMemory(storage_path=str(storage))
    mem.set_variable("x", 42.0)
    mem.add_history("2 * 4", "print(8)", "8")

    mem.clear()
    assert len(mem.list_variables()) == 0
    assert len(mem.get_recent_history()) == 0
    assert not storage.exists()
