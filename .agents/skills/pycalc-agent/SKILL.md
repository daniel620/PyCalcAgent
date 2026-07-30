---
name: pycalc-agent-dev
description: Developer skill for PyCalcAgent (AI in 5 Days Assessment Agent - 95/95 Ready), providing guidelines for multi-agent orchestration, SQLite vector memory, OpenTelemetry tracing, HITL, and IaC.
---

# PyCalcAgent Developer Skill (95/95 Evaluation Ready)

When working on **PyCalcAgent**, enforce these guidelines across all 5 evaluation criteria:

## 1. Development Commands
- **Activate Environment**: `source .venv/bin/activate`
- **Run Full 22-Test Suite**: `pytest -v` (Must always pass 22/22 tests, including golden dataset regression)
- **Run Linter**: `ruff check src/ tests/` (Must report 0 errors)

## 2. Criteria Implementation Rules
1. **Tool & Interface Design (`src/pycalcagent/tools.py`)**:
   - Explicitly validate inputs using Pydantic schemas (`ExecutePythonCodeInput.model_validate`).
   - All errors must return guided recovery instructions (`recovery_instruction`).
2. **Context & Memory (`src/pycalcagent/memory.py`)**:
   - Use SQLite database (`.calc_memory.db`) with relational tables and `vector_index`.
   - Use `set_variable_async` and `add_history_async` for non-blocking persistence.
3. **Orchestration & Logic (`src/pycalcagent/orchestrator.py` & `guardrails.py`)**:
   - Use `ModelRouter` for strategic routing (`gemini-2.5-flash` vs `gemini-2.5-pro`).
   - Use `SecurityGuardrail.inspect_code` for AST safety inspection.
   - Enforce HITL approval via `HumanInTheLoopPolicy`.
4. **Observability & Tracing (`src/pycalcagent/tracer.py`)**:
   - All traces must flow through OpenTelemetry (`opentelemetry.trace.get_tracer`).
   - Pass all payloads through `PIIRedactor.redact_payload` to scrub PII.
5. **Infrastructure & CI/CD (`src/pycalcagent/secrets.py` & `terraform/`)**:
   - Use `SecretManagerClient` to fetch credentials from Cloud Secret Manager.
   - Maintain Terraform IaC files (`terraform/main.tf`).
   - Ensure `tests/test_eval_golden_dataset.py` passes 100% against `data/golden_dataset.json`.
