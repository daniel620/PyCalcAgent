"""Unit tests for PyCalcAgent SQLite memory and async persistence (Criterion 2)."""

import pytest

from pycalcagent.memory import CalculationMemory


def test_variable_persistence(tmp_path):
    """Test saving variables and loading them across SQLite memory instances."""
    storage = tmp_path / "calc_memory.db"
    mem1 = CalculationMemory(db_path=str(storage))
    mem1.set_variable("pi_val", 3.14159, "Pi approximation")
    mem1.set_variable("base", 10.0, "Base number")

    mem2 = CalculationMemory(db_path=str(storage))
    assert mem2.get_variable("pi_val") == 3.14159
    assert mem2.get_variable("base") == 10.0
    assert "pi_val" in mem2.list_variables()


@pytest.mark.asyncio
async def test_async_variable_and_history(tmp_path):
    """Test async non-blocking variable and history storage in SQLite."""
    storage = tmp_path / "calc_memory.db"
    mem = CalculationMemory(db_path=str(storage))
    await mem.set_variable_async("async_x", 100.0, "Async test var")
    await mem.add_history_async("100 * 2", "print(200)", "200")

    assert mem.get_variable("async_x") == 100.0
    recent = mem.get_recent_history(1)
    assert recent[0].result == "200"


def test_history_persistence_and_semantic_search(tmp_path):
    """Test calculation history recording, sliding limit, and keyword vector search."""
    storage = tmp_path / "calc_memory.db"
    mem = CalculationMemory(db_path=str(storage))
    mem.add_history("calculate integral of x squared", "print(3.33)", "3.33")
    mem.add_history("2 * 4", "print(8)", "8")

    recent = mem.get_recent_history(limit=5)
    assert len(recent) == 2

    # Test keyword semantic search
    matches = mem.search_history_semantic("integral")
    assert len(matches) == 1
    assert matches[0].result == "3.33"


def test_clear_memory(tmp_path):
    """Test clearing all stored session variables, history, and vector index."""
    storage = tmp_path / "calc_memory.db"
    mem = CalculationMemory(db_path=str(storage))
    mem.set_variable("x", 42.0)
    mem.add_history("2 * 4", "print(8)", "8")

    mem.clear()
    assert len(mem.list_variables()) == 0
    assert len(mem.get_recent_history()) == 0
