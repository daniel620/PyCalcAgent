"""Unit tests for SecurityGuardrail and HumanInTheLoopPolicy (Criterion 3)."""

from pycalcagent.guardrails import HumanInTheLoopPolicy, SecurityGuardrail


def test_security_guardrail_safe_code():
    """Verify standard arithmetic code passes security inspection."""
    res = SecurityGuardrail.inspect_code("res = 2 * 4\nprint(res)")
    assert res.safe is True
    assert res.risk_level == "LOW"


def test_security_guardrail_blocks_dangerous_import():
    """Verify AST guardrail blocks forbidden module imports."""
    res = SecurityGuardrail.inspect_code("import os\nos.system('whoami')")
    assert res.safe is False
    assert "Forbidden module import detected" in res.reason


def test_security_guardrail_blocks_dangerous_call():
    """Verify AST guardrail blocks forbidden function calls."""
    res = SecurityGuardrail.inspect_code("eval('2 + 2')")
    assert res.safe is False
    assert "Forbidden built-in call detected" in res.reason


def test_hitl_policy_approval():
    """Verify Human-in-the-Loop policy callback invocation."""
    calls = []

    def mock_callback(code: str, risk_level: str) -> bool:
        calls.append((code, risk_level))
        return False  # Reject

    policy = HumanInTheLoopPolicy(confirmation_callback=mock_callback)
    permitted = policy.verify_execution_permission("for i in range(10): pass", "MODERATE")
    assert permitted is False
    assert len(calls) == 1
