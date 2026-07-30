"""Multi-agent reasoning loop and orchestration for PyCalcAgent (Criterion 3: Orchestration & Logic)."""

import os
import re
from typing import Any

from pydantic import BaseModel

from pycalcagent.guardrails import HumanInTheLoopPolicy
from pycalcagent.memory import CalculationMemory
from pycalcagent.orchestrator import MultiAgentOrchestrator
from pycalcagent.tools import CalculationTools
from pycalcagent.tracer import default_tracer

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class AgentResponse(BaseModel):
    """Structured response from PyCalcAgent."""
    query: str
    answer: str
    executed_code: str
    result_value: str | None = None
    success: bool
    retries_used: int = 0
    recovery_instruction: str | None = None
    plan_steps: list[dict[str, Any]] = []


class PyCalcAgent:
    """Orchestrates multi-agent calculation workflow with HITL, security guardrails, and model routing."""

    def __init__(
        self,
        memory: CalculationMemory | None = None,
        model_name: str = "gemini-2.5-flash",
        max_retries: int = 2,
        hitl_policy: HumanInTheLoopPolicy | None = None,
    ):
        self.memory = memory or CalculationMemory()
        self.tools = CalculationTools(self.memory)
        self.model_name = model_name
        self.max_retries = max_retries
        self.orchestrator = MultiAgentOrchestrator(self.memory, hitl_policy=hitl_policy)

        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.client = None
        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception:  # noqa: BLE001
                self.client = None

    def _build_context_header(self) -> str:
        """Inject currently stored variables into Python script context."""
        vars_dict = self.memory.list_variables()
        if not vars_dict:
            return "# No stored session variables\n"
        lines = ["# Stored session variables from memory:"]
        for k, v in vars_dict.items():
            lines.append(f"{k} = {v}")
        return "\n".join(lines) + "\n\n"

    def _generate_python_code(self, query: str, model_tier: str, previous_error: str | None = None) -> str:
        """Generate Python code using routed model tier or deterministic fallback."""
        context_header = self._build_context_header()

        if self.client:
            prompt = (
                "You are PyCalcAgent, an expert math and calculation AI.\n"
                "Write concise, self-contained Python code to compute the user's request.\n"
                "MUST print() the final numerical result on the last line.\n"
                f"Existing memory context:\n{context_header}\n"
                f"User Query: {query}\n"
            )
            if previous_error:
                prompt += f"\nPREVIOUS ERROR TO FIX: {previous_error}\n"

            try:
                response = self.client.models.generate_content(
                    model=model_tier,
                    contents=prompt,
                    config={"tools": self.tools.get_llm_tool_schemas()},
                )
                code = self._extract_code_block(response.text)
                return context_header + code
            except Exception as e:  # noqa: BLE001
                default_tracer.log_event("LLM_FALLBACK", {"error": str(e), "tier": model_tier})

        return self._fallback_code_generator(query, context_header)

    def _extract_code_block(self, text: str) -> str:
        """Extract Python code from markdown blocks if present."""
        match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _fallback_code_generator(self, query: str, context_header: str) -> str:
        """Generate valid Python code for arithmetic expressions when running offline/without API key."""
        clean_query = query.strip()
        save_match = re.search(r"(?:save|store)\s+(.*?)\s+as\s+([a-zA-Z_]\w*)", clean_query, re.IGNORECASE)
        assign_match = re.match(r"([a-zA-Z_]\w*)\s*=\s*(.+)", clean_query)

        if save_match:
            expr = save_match.group(1).strip()
            var_name = save_match.group(2).strip()
            code = f"res = {expr}\nprint(res)"
            return context_header + code
        elif assign_match:
            var_name = assign_match.group(1).strip()
            expr = assign_match.group(2).strip()
            code = f"{var_name} = {expr}\nprint({var_name})"
            return context_header + code
        else:
            expr = re.sub(r"^(?:calculate|compute|what\s+is|evaluate)\s+", "", clean_query, flags=re.IGNORECASE)
            expr = expr.rstrip("?.!")
            code = f"res = {expr}\nprint(res)"
            return context_header + code

    def run(self, query: str) -> AgentResponse:
        """Execute the multi-agent reasoning and tool-calling loop for a user calculation query."""
        default_tracer.log_event("AGENT_START", {"query": query})
        retries = 0
        last_error = None
        last_recovery = None
        executed_code = ""

        while retries <= self.max_retries:
            workflow_res = self.orchestrator.execute_workflow(
                query=query,
                code_generator_fn=lambda q, tier, err=last_error: self._generate_python_code(
                    q, tier, previous_error=err
                ),
            )
            executed_code = workflow_res.get("executed_code", "")

            if workflow_res["success"]:
                result_str = str(workflow_res["result"]).strip()
                default_tracer.log_event("AGENT_SUCCESS", {"result": result_str, "retries": retries})

                save_match = re.search(r"(?:save|store)\s+(.*?)\s+as\s+([a-zA-Z_]\w*)", query, re.IGNORECASE)
                assign_match = re.match(r"([a-zA-Z_]\w*)\s*=\s*(.+)", query)
                var_name = None
                if save_match:
                    var_name = save_match.group(2).strip()
                elif assign_match:
                    var_name = assign_match.group(1).strip()

                if var_name:
                    try:
                        val_float = float(result_str.splitlines()[-1])
                        self.tools.save_variable(var_name, val_float, f"Saved from query: {query}")
                    except ValueError:
                        pass

                self.memory.add_history(query, executed_code, result_str)

                return AgentResponse(
                    query=query,
                    answer=f"Calculation successful. Result: {result_str}",
                    executed_code=executed_code,
                    result_value=result_str,
                    success=True,
                    retries_used=retries,
                    plan_steps=workflow_res.get("plan", []),
                )
            else:
                last_error = workflow_res["error"]
                last_recovery = workflow_res.get("recovery_instruction")
                default_tracer.log_event("AGENT_RETRY", {
                    "attempt": retries + 1,
                    "error": last_error,
                    "recovery": last_recovery,
                })
                retries += 1

        default_tracer.log_event("AGENT_FAILURE", {"query": query, "last_error": last_error})
        return AgentResponse(
            query=query,
            answer=f"Failed after {self.max_retries} retries. Error: {last_error}. {last_recovery or ''}".strip(),
            executed_code=executed_code,
            success=False,
            retries_used=retries,
            recovery_instruction=last_recovery,
        )
