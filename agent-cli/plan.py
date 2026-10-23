"""
plan.py — Pydantic schema + all PLAN.json CRUD operations.

The LLM generates the JSON once. After that, only Python touches PLAN.json.
The executor LLM never reads or writes this file directly.
"""

import json
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, ValidationError

# ── Schema ─────────────────────────────────────────────────────────────────────

class VerifyStep(BaseModel):
    type: Literal["command", "none"]
    command: str = ""

class Task(BaseModel):
    id: int
    description: str
    status: Literal["pending", "running", "done", "failed"]
    allowed_tools: Optional[List[str]] = None
    target_files: Optional[List[str]] = None
    context_files: Optional[List[str]] = None
    verify: VerifyStep
    skill: Optional[str] = None   # planner sets this; executor loads the skill
    retries: int = 0              # Python manages this — not in LLM output
    detail: str = ""          # failure reason, populated by mark_task_failed
    files_changed: List[str] = [] # populated by Python after task finishes

class Plan(BaseModel):
    goal: str
    tasks: List[Task]

# ── File location ──────────────────────────────────────────────────────────────

PLAN_PATH = Path(__file__).parent / "PLAN.json"

# ── CRUD ───────────────────────────────────────────────────────────────────────

def load_plan() -> Plan:
    """Read PLAN.json from disk and return a validated Plan object."""
    if not PLAN_PATH.exists() or PLAN_PATH.stat().st_size == 0:
        raise FileNotFoundError("PLAN.json does not exist or is empty. Run the planner first.")
    data = json.loads(PLAN_PATH.read_text())
    return Plan(**data)


def save_plan(plan: Plan) -> None:
    """Write the Plan object back to PLAN.json."""
    PLAN_PATH.write_text(plan.model_dump_json(indent=2))


def get_next_pending_task(plan: Plan) -> Task | None:
    """Return the first task with status='pending', or None if all done/failed."""
    for task in plan.tasks:
        if task.status == "pending":
            return task
    return None


def mark_task_running(plan: Plan, task_id: int) -> None:
    """Set a task to 'running' and persist to disk."""
    for task in plan.tasks:
        if task.id == task_id:
            task.status = "running"
    save_plan(plan)


def mark_task_done(plan: Plan, task_id: int) -> None:
    """Set a task to 'done' and persist to disk."""
    for task in plan.tasks:
        if task.id == task_id:
            task.status = "done"
    save_plan(plan)


def mark_task_failed(plan: Plan, task_id: int, detail: str = "") -> None:
    """Set a task to 'failed' with a reason and persist to disk."""
    for task in plan.tasks:
        if task.id == task_id:
            task.status = "failed"
            task.detail = detail
    save_plan(plan)


def increment_retries(plan: Plan, task_id: int) -> int:
    """Bump retry count for a task and return the new count."""
    for task in plan.tasks:
        if task.id == task_id:
            task.retries += 1
            save_plan(plan)
            return task.retries
    return 0

# ── validate_json ──────────────────────────────────────────────────────────────

def validate_json(raw: str) -> Plan:
    """
    Parse and validate the raw JSON string returned by the planner LLM.

    Handles common LLM mistakes:
      - Wrapping output in markdown code fences (```json ... ```)
      - Leading/trailing whitespace

    Raises ValueError with a clear message if the JSON is invalid or
    doesn't match the Plan schema, so the caller can retry.
    """
    # Strip markdown fences if the model wrapped output in ```json ... ```
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # drop first line (```json or ```) and last line (```)
        cleaned = "\n".join(lines[1:-1]).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\n\nRaw output:\n{raw[:500]}")

    try:
        plan = Plan(**data)
    except ValidationError as e:
        raise ValueError(f"JSON does not match Plan schema:\n{e}\n\nParsed data:\n{data}")

    # Normalise: all tasks must start as pending (LLM sometimes sets wrong status)
    for task in plan.tasks:
        task.status = "pending"
        task.retries = 0
        task.detail = ""

    return plan
