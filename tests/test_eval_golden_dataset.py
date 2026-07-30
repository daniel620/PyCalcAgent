"""Automated evaluation suite against a golden dataset to measure agent regressions (Criterion 5)."""

import json
from pathlib import Path

import pytest

from pycalcagent.agent import PyCalcAgent
from pycalcagent.memory import CalculationMemory


@pytest.fixture
def golden_dataset():
    """Load the benchmark golden dataset from disk."""
    dataset_path = Path(__file__).parent.parent / "data" / "golden_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_golden_dataset_regression_eval(golden_dataset, tmp_path):
    """Execute PyCalcAgent across the golden dataset and assert 100% accuracy without regressions."""
    db_path = tmp_path / "eval_memory.db"
    memory = CalculationMemory(db_path=str(db_path))
    agent = PyCalcAgent(memory=memory)

    passed = 0
    total = len(golden_dataset)

    for item in golden_dataset:
        query = item["query"]
        expected = item["expected"]

        response = agent.run(query)
        assert response.success is True, f"Failed regression query: {query} with error: {response.answer}"
        result_val = str(response.result_value).strip()
        assert expected in result_val or float(expected) == float(result_val), (
            f"Regression mismatch for query '{query}': expected '{expected}', got '{result_val}'"
        )
        passed += 1

    accuracy = (passed / total) * 100.0
    assert accuracy == 100.0, f"Golden dataset evaluation regression detected. Accuracy: {accuracy}%"
