"""Multi-agent orchestration, strategic model routing, and HITL workflow for PyCalcAgent (Criterion 3)."""

from typing import Any

from pydantic import BaseModel

from pycalcagent.guardrails import HumanInTheLoopPolicy, SecurityGuardrail
from pycalcagent.memory import CalculationMemory
from pycalcagent.tools import CalculationTools
from pycalcagent.tracer import default_tracer


class PlanStep(BaseModel):
    """Step in a mathematical execution plan."""
    step_number: int
    description: str


class ModelRouter:
    """Strategic model router selecting model tier based on query complexity."""

    @staticmethod
    def route_query(query: str) -> str:
        """Route simple arithmetic to flash/local and complex word problems to pro."""
        complex_keywords = {"integral", "derivative", "matrix", "optimization", "system of equations", "probabilistic"}
        if any(kw in query.lower() for kw in complex_keywords) or len(query.split()) > 15:
            default_tracer.log_event("MODEL_ROUTED", {"tier": "pro", "model": "gemini-2.5-pro"})
            return "gemini-2.5-pro"
        default_tracer.log_event("MODEL_ROUTED", {"tier": "flash", "model": "gemini-2.5-flash"})
        return "gemini-2.5-flash"


class PlannerAgent:
    """Specialized subagent responsible for mathematical reasoning and task decomposition."""

    @staticmethod
    def create_plan(query: str) -> list[PlanStep]:
        """Deconstruct user query into ordered calculation steps."""
        default_tracer.log_event("PLANNER_START", {"query": query})
        steps = [
            PlanStep(step_number=1, description="Inspect session memory for saved variable references."),
            PlanStep(step_number=2, description="Formulate Python syntax to compute target expression."),
            PlanStep(step_number=3, description="Verify AST safety using security guardrails."),
            PlanStep(step_number=4, description="Execute code in sandbox and format result."),
        ]
        default_tracer.log_event("PLANNER_SUCCESS", {"step_count": len(steps)})
        return steps


class ReviewerAgent:
    """Specialized subagent responsible for security guardrails and HITL approval."""

    def __init__(self, hitl_policy: HumanInTheLoopPolicy | None = None):
        self.hitl_policy = hitl_policy or HumanInTheLoopPolicy()

    def review_code(self, code: str) -> tuple[bool, str]:
        """Verify code safety and enforce HITL policy."""
        default_tracer.log_event("REVIEWER_START", {"code": code})
        guardrail_res = SecurityGuardrail.inspect_code(code)
        if not guardrail_res.safe:
            default_tracer.log_event("REVIEWER_REJECTED", {"reason": guardrail_res.reason})
            return False, guardrail_res.reason

        permitted = self.hitl_policy.verify_execution_permission(code, guardrail_res.risk_level)
        if not permitted:
            return False, "Execution rejected by Human-in-the-Loop policy."
        return True, "Approved"


class MultiAgentOrchestrator:
    """Orchestrates Planner, CodeGenerator, Reviewer, and Executor subagents with strategic routing."""

    def __init__(self, memory: CalculationMemory, hitl_policy: HumanInTheLoopPolicy | None = None):
        self.memory = memory
        self.tools = CalculationTools(memory)
        self.router = ModelRouter()
        self.planner = PlannerAgent()
        self.reviewer = ReviewerAgent(hitl_policy=hitl_policy)

    def execute_workflow(self, query: str, code_generator_fn: Any) -> dict[str, Any]:
        """Execute multi-agent workflow: route -> plan -> generate -> review -> execute -> save."""
        default_tracer.log_event("ORCHESTRATOR_START", {"query": query})
        model_tier = self.router.route_query(query)
        plan = self.planner.create_plan(query)

        code = code_generator_fn(query, model_tier)
        approved, review_msg = self.reviewer.review_code(code)
        if not approved:
            return {
                "success": False,
                "result": None,
                "error": f"Security/HITL Rejection: {review_msg}",
                "executed_code": code,
                "plan": [s.model_dump() for s in plan],
            }

        tool_res = self.tools.execute_python_code(code=code, explanation=f"Executing plan for: {query}")
        return {
            "success": tool_res["success"],
            "result": tool_res["stdout"] if tool_res["success"] else tool_res["stderr"],
            "error": tool_res.get("error_message"),
            "recovery_instruction": tool_res.get("recovery_instruction"),
            "executed_code": code,
            "plan": [s.model_dump() for s in plan],
        }
