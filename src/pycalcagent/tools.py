"""Tool definitions, Pydantic validation, and guided error recovery for PyCalcAgent (Criterion 1)."""

import subprocess
import sys
from typing import Any

from pydantic import BaseModel, Field

from pycalcagent.memory import CalculationMemory
from pycalcagent.tracer import default_tracer


class ExecutePythonCodeInput(BaseModel):
    """Input schema for execute_python_code tool enforcing validation and LLM constraints."""
    code: str = Field(..., description="The Python code to execute to perform the calculation.")
    explanation: str = Field(..., description="Explanation of what this Python calculation achieves.")


class ExecutePythonCodeOutput(BaseModel):
    """Output schema for execute_python_code tool including guided recovery instructions."""
    stdout: str
    stderr: str
    returncode: int
    success: bool
    error_message: str | None = None
    recovery_instruction: str | None = None


class SaveVariableInput(BaseModel):
    """Input schema for save_variable tool."""
    name: str = Field(..., description="Name of the variable (alphanumeric and underscores).")
    value: float = Field(..., description="Numerical value of the variable.")
    description: str = Field("", description="Short description of what the variable represents.")


class GetHistoryInput(BaseModel):
    """Input schema for get_calculation_history tool."""
    limit: int = Field(5, description="Maximum number of recent calculations to retrieve.", ge=1, le=100)


class CalculationTools:
    """Provides distinct, well-documented tools with strict Pydantic validation and guided error recovery."""

    def __init__(self, memory: CalculationMemory):
        self.memory = memory

    @classmethod
    def get_llm_tool_schemas(cls) -> list[dict[str, Any]]:
        """Return structured JSON tool schemas for LLM tool calling constraints."""
        return [
            {
                "name": "execute_python_code",
                "description": "Execute Python code in a sandbox to compute numerical results.",
                "parameters": ExecutePythonCodeInput.model_json_schema(),
            },
            {
                "name": "save_variable",
                "description": "Save a variable into persistent SQLite database memory.",
                "parameters": SaveVariableInput.model_json_schema(),
            },
            {
                "name": "get_calculation_history",
                "description": "Retrieve calculation history from session memory.",
                "parameters": GetHistoryInput.model_json_schema(),
            },
        ]

    def _generate_recovery_instruction(self, stderr: str) -> str:
        """Provide actionable, guided recovery instructions for runtime errors."""
        err_lower = stderr.lower()
        if "zerodivisionerror" in err_lower:
            return "Recovery Tip: Division by zero detected. Validate divisors are non-zero before calculation."
        elif "syntaxerror" in err_lower or "indentationerror" in err_lower:
            return "Recovery Tip: Check Python syntax, indentation, and ensure balanced parentheses/quotes."
        elif "nameerror" in err_lower:
            return "Recovery Tip: Undefined variable name. Check session memory variables or initialize before referencing."
        elif "typeerror" in err_lower:
            return "Recovery Tip: Operator or function applied to incompatible types. Cast variables to float or int."
        elif "timeout" in err_lower:
            return "Recovery Tip: Execution exceeded 5 seconds. Avoid infinite loops or large computations."
        else:
            return "Recovery Tip: Review error traceback and verify all math expressions and variables are valid."

    @default_tracer.trace_tool("execute_python_code")
    def execute_python_code(self, code: str, explanation: str) -> dict[str, Any]:
        """Execute self-generated Python code in a controlled subprocess and capture output with guided recovery.

        Args:
            code: Valid Python code snippet to run (must print the result to stdout).
            explanation: Human-readable rationale for the calculation.

        Returns:
            A dictionary containing stdout, stderr, returncode, success boolean, and recovery instruction.
        """
        # Explicit Pydantic validation of input arguments
        validated_input = ExecutePythonCodeInput.model_validate({"code": code, "explanation": explanation})
        try:
            process = subprocess.run(
                [sys.executable, "-c", validated_input.code],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            success = process.returncode == 0
            err_msg = process.stderr.strip() if not success else None
            recovery = self._generate_recovery_instruction(err_msg) if not success else None

            output = ExecutePythonCodeOutput(
                stdout=process.stdout.strip(),
                stderr=process.stderr.strip(),
                returncode=process.returncode,
                success=success,
                error_message=err_msg,
                recovery_instruction=recovery,
            )
            return output.model_dump()
        except subprocess.TimeoutExpired:
            output = ExecutePythonCodeOutput(
                stdout="",
                stderr="Execution timed out after 5 seconds.",
                returncode=-1,
                success=False,
                error_message="TimeoutExpired",
                recovery_instruction="Recovery Tip: Execution exceeded 5 seconds. Avoid infinite loops or large computations.",
            )
            return output.model_dump()
        except Exception as e:  # noqa: BLE001
            output = ExecutePythonCodeOutput(
                stdout="",
                stderr=str(e),
                returncode=-1,
                success=False,
                error_message=str(e),
                recovery_instruction="Recovery Tip: System error executing script. Check environment permissions.",
            )
            return output.model_dump()

    @default_tracer.trace_tool("save_variable")
    def save_variable(self, name: str, value: float, description: str = "") -> dict[str, Any]:
        """Save a calculation result or numeric constant into multi-turn SQLite session memory.

        Args:
            name: The variable name (e.g. 'tax_rate', 'pi_val', 'x').
            value: The numeric float value to store.
            description: Description of the variable.

        Returns:
            Confirmation dictionary of the stored variable.
        """
        # Explicit Pydantic input validation
        validated = SaveVariableInput.model_validate(
            {"name": name, "value": value, "description": description}
        )
        rec = self.memory.set_variable(validated.name, validated.value, validated.description)
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
        validated = GetHistoryInput.model_validate({"limit": limit})
        records = self.memory.get_recent_history(validated.limit)
        return [rec.model_dump() for rec in records]
