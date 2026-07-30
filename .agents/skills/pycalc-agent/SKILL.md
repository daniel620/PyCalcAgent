---
name: pycalc-agent-dev
description: Developer skill for PyCalcAgent (AI in 5 Days Assessment Agent), providing guidelines for modifying tools, memory, tracing, and tests.
---

# PyCalcAgent Developer Skill

When working on **PyCalcAgent**, follow these architecture guidelines and development commands to ensure all 5 evaluation criteria remain satisfied.

## 1. Development Commands
- **Activate Environment**: `source .venv/bin/activate`
- **Run Unit Tests**: `pytest -v` (Must always pass 10/10 tests)
- **Run Linter**: `ruff check src/ tests/` (Must report 0 errors)
- **Test CLI Execution**:
  ```bash
  python -m pycalcagent.cli "2 * 4"
  python -m pycalcagent.cli "save 100 * 0.08 as tax"
  python -m pycalcagent.cli "tax + 50"
  ```

## 2. Core Evaluation Criteria Guidelines
1. **Tool & Interface Design (`src/pycalcagent/tools.py`)**:
   - All tools must use Pydantic input/output schemas (`BaseModel`) and include Google-style docstrings.
   - Decorate every tool method with `@default_tracer.trace_tool("tool_name")`.
2. **Context & Memory (`src/pycalcagent/memory.py`)**:
   - Variables saved with `save_variable(name, value)` are stored in `CalculationMemory.variables` and persisted to `.calc_memory.json`.
   - Always verify multi-turn variable recall in tests.
3. **Orchestration & Logic (`src/pycalcagent/agent.py`)**:
   - `PyCalcAgent` injects saved variables into self-generated Python scripts.
   - If execution fails (`ZeroDivisionError`, syntax error), `PyCalcAgent` automatically catches the stderr traceback and retries up to `max_retries`.
4. **Observability & Tracing (`src/pycalcagent/tracer.py`)**:
   - `EventTracer` writes structured JSON logs to `.logs/calc_agent.jsonl`.
   - Never suppress or disable tracing in core tools.
5. **Infrastructure & CI/CD**:
   - Ensure new dependencies are added to both `pyproject.toml` and `requirements.txt`.
   - Keep GitHub Actions CI (`.github/workflows/ci.yml`) and `Dockerfile` up to date.
