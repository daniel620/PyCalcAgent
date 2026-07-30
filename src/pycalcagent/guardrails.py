"""Security guardrails, AST policy inspection, and Human-in-the-Loop confirmation (Criterion 3)."""

import ast
from collections.abc import Callable
from typing import ClassVar

from pydantic import BaseModel

from pycalcagent.tracer import default_tracer


class GuardrailResult(BaseModel):
    """Result of code security inspection."""
    safe: bool
    risk_level: str  # 'LOW', 'MODERATE', 'HIGH'
    reason: str


class SecurityGuardrail:
    """Security policy plugin that statically inspects Python AST for dangerous operations."""

    FORBIDDEN_MODULES: ClassVar[set[str]] = {
        "os", "sys", "subprocess", "shutil", "socket", "urllib", "requests", "http"
    }
    FORBIDDEN_CALLS: ClassVar[set[str]] = {"eval", "exec", "open", "__import__", "input", "compile"}

    @classmethod
    def inspect_code(cls, code: str) -> GuardrailResult:
        """Parse Python AST and verify code safety."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return GuardrailResult(safe=False, risk_level="HIGH", reason=f"SyntaxError in code: {e}")

        for node in ast.walk(tree):
            # Check import statements
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in cls.FORBIDDEN_MODULES:
                        return GuardrailResult(
                            safe=False,
                            risk_level="HIGH",
                            reason=f"Forbidden module import detected: {alias.name}",
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in cls.FORBIDDEN_MODULES:
                    return GuardrailResult(
                        safe=False,
                        risk_level="HIGH",
                        reason=f"Forbidden module import detected: {node.module}",
                    )
            # Check function calls
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in cls.FORBIDDEN_CALLS
            ):
                return GuardrailResult(
                    safe=False,
                    risk_level="HIGH",
                    reason=f"Forbidden built-in call detected: {node.func.id}()",
                )

        # Check for loops or complex structures that might time out
        has_loops = any(isinstance(node, ast.For | ast.While) for node in ast.walk(tree))
        risk = "MODERATE" if has_loops else "LOW"
        return GuardrailResult(safe=True, risk_level=risk, reason="Code AST verified safe.")


class HumanInTheLoopPolicy:
    """Policy manager enforcing Human-in-the-Loop (HITL) confirmation for moderate/high risk actions."""

    def __init__(self, confirmation_callback: Callable[[str, str], bool] | None = None):
        self.confirmation_callback = confirmation_callback or self._default_auto_confirm

    @staticmethod
    def _default_auto_confirm(code: str, risk_level: str) -> bool:
        """Default non-interactive confirmation callback for automated environments."""
        default_tracer.log_event("HITL_AUTO_CONFIRM", {"risk_level": risk_level, "code": code})
        return True

    def verify_execution_permission(self, code: str, risk_level: str) -> bool:
        """Check if execution is permitted under HITL policy."""
        if risk_level in ("MODERATE", "HIGH"):
            default_tracer.log_event("HITL_REQUIRED", {"risk_level": risk_level})
            approved = self.confirmation_callback(code, risk_level)
            default_tracer.log_event("HITL_DECISION", {"approved": approved, "risk_level": risk_level})
            return approved
        return True
