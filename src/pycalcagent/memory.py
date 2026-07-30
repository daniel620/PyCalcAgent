"""Persistent session memory and context management for PyCalcAgent (Criterion 2: Context & Memory)."""

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class VariableRecord(BaseModel):
    """Schema representing a stored numerical variable or constant."""
    name: str
    value: float
    description: str
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CalculationRecord(BaseModel):
    """Schema representing an executed calculation history entry."""
    query: str
    python_code: str
    result: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CalculationMemory:
    """Manages multi-turn conversation memory, saved variables, and calculation history."""

    def __init__(self, storage_path: str = ".calc_memory.json"):
        self.storage_path = Path(storage_path)
        self.variables: dict[str, VariableRecord] = {}
        self.history: list[CalculationRecord] = []
        self._load_memory()

    def _load_memory(self) -> None:
        """Load persisted variables and history from disk if available."""
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.get("variables", {}).items():
                    self.variables[k] = VariableRecord(**v)
                for item in data.get("history", []):
                    self.history.append(CalculationRecord(**item))
        except Exception:  # noqa: BLE001
            # If storage file is corrupted or empty, reset cleanly
            self.variables = {}
            self.history = []

    def save_memory(self) -> None:
        """Persist variables and history to disk."""
        data = {
            "variables": {k: v.model_dump() for k, v in self.variables.items()},
            "history": [rec.model_dump() for rec in self.history[-50:]],  # Keep last 50 calculations
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def set_variable(self, name: str, value: float, description: str = "") -> VariableRecord:
        """Save or update a named calculation variable."""
        record = VariableRecord(name=name, value=value, description=description)
        self.variables[name] = record
        self.save_memory()
        return record

    def get_variable(self, name: str) -> float | None:
        """Retrieve a variable value by name."""
        if name in self.variables:
            return self.variables[name].value
        return None

    def list_variables(self) -> dict[str, float]:
        """Return a dictionary of all stored variable names and values."""
        return {k: v.value for k, v in self.variables.items()}

    def add_history(self, query: str, python_code: str, result: str) -> CalculationRecord:
        """Record a completed calculation into memory history."""
        rec = CalculationRecord(query=query, python_code=python_code, result=result)
        self.history.append(rec)
        self.save_memory()
        return rec

    def get_recent_history(self, limit: int = 5) -> list[CalculationRecord]:
        """Return the most recent calculation records."""
        return self.history[-limit:]

    def clear(self) -> None:
        """Clear all stored variables and history."""
        self.variables.clear()
        self.history.clear()
        if self.storage_path.exists():
            self.storage_path.unlink()
