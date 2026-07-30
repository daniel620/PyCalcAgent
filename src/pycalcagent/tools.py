"""Tool definitions and Pydantic schemas for PyCalcAgent (Criterion 1: Tool & Interface Design)."""

import subprocess
import sys
from typing import Any

from pydantic import BaseModel, Field

from pycalcagent.memory import CalculationMemory
from pycalcagent.tracer import default_tracer


class ExecutePythonCodeInput(BaseModel):
    """Input schema for execute_python_code tool."""
    code: str = Field(..., description="The Python code to execute to perform the calculation.")
    explanation: str = Field(..., description="Explanation of what this Python calculation achieves.")


class ExecutePythonCodeOutput(BaseModel):
    """Output schema for execute_python_code tool."""
    stdout: str
    stderr: str
    returncode: int
    success: bool
    error_message: str | None = None


class SaveVariableInput(BaseModel):
    """Input schema for save_variable tool."""
    name: str = Field(..., description="Name of the variable (alphanumeric and underscores).")
    value: float = Field(..., description="Numerical value of the variable.")
    description: str = Field(..., description="Short description of what the variable represents.")


class GetHistoryInput(BaseModel):
    """Input schema for get_calculation_history tool."""
    limit: int = Field(5, description="Maximum number of recent calculations to retrieve.")


class CalculationTools:
    """Provides distinct, well-documented tools for Python code execution and memory management."""

    def __init__(self, memory: CalculationMemory):
        self.memory = memory

    @default_tracer.trace_tool("execute_python_code")
    def execute_python_code(self, code: str, explanation: str) -> dict[str, Any]:
        """Execute self-generated Python code in a controlled subprocess and capture the output.

        Args:
            code: Valid Python code snippet to run (must print the result to stdout).
            explanation: Human-readable rationale for the calculation.

        Returns:
            A dictionary containing stdout, stderr, returncode, and success boolean.
        """
        try:
            # Execute python code in a subprocess with a 5-second timeout
            process = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            success = process.returncode == 0
            output = {
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
                "returncode": process.returncode,
                "success": success,
                "error_message": process.stderr.strip() if not success else None,
            }
            return output
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Execution timed out after 5 seconds.",
                "returncode": -1,
                "success": False,
                "error_message": "TimeoutExpired",
            }
        except Exception as e:  # noqa: BLE001
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "success": False,
                "error_message": str(e),
            }

    @default_tracer.trace_tool("save_variable")
    def save_variable(self, name: str, value: float, description: str = "") -> dict[str, Any]:
        """Save a calculation result or numeric constant into multi-turn session memory.

        Args:
            name: The variable name (e.g. 'tax_rate', 'pi_val', 'x').
            value: The numeric float value to store.
            description: Description of the variable.

        Returns:
            Confirmation dictionary of the stored variable.
        """
        rec = self.memory.set_variable(name, value, description)
        return {
            "status": "saved",
            "name": rec.name,
            "value": rec.value,
            "description": rec.description,
        }

    @default_tracer.trace_tool("list_saved_variables")
    def list_saved_variables(self) -> dict[str, float]:
        """List all variables currently stored in session memory.

        Returns:
            Dictionary mapping variable names to float values.
        """
        return self.memory.list_variables()

    @default_tracer.trace_tool("get_calculation_history")
    def get_calculation_history(self, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve recent calculation records from session memory.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of dictionaries representing recent calculation queries and results.
        """
        records = self.memory.get_recent_history(limit)
        return [rec.model_dump() for rec in records]
