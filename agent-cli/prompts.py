from plan import Plan
from tools import list_skills, available_tools, get_tools_descriptions
schema = Plan.model_json_schema()
available_skills = list_skills() 

def build_planning_prompt(goal: str, mcp_bridge=None) -> str:
    import os
    from pathlib import Path
    from config import cfg
    from tools.memory_ops import scan_directory

    cwd = os.getcwd()
    gh_hint = (
        f"\nUSER IDENTITY:\n- Default GitHub owner/username: '{cfg.github_user}' "
        f"(always use this as `owner` when the user gives only a repo name or says 'my repo').\n"
        if getattr(cfg, "github_user", None) else ""
    )

    lines = [
        f"  {p.relative_to(cwd)}"
        for p in sorted(scan_directory(Path(cwd)))
    ]
    file_tree = "\n".join(lines) if lines else "  (empty directory)"

    return f"""
You are a project planner. The user wants to: "{goal}"

WORKING DIRECTORY: {cwd}
{gh_hint}
EXISTING FILES IN PROJECT:
{file_tree}

{mcp_bridge.get_prompt_description() if mcp_bridge else ""}

AVAILABLE TOOLS (use in task descriptions to guide the executor):
{get_tools_descriptions()}

AVAILABLE SKILLS (executor can use these — different from tools):
{available_skills}

if the goal is large and complex then just break it into smaller tasks 
You MUST respond with ONLY valid JSON that matches this exact schema:
{schema}

TASK OWNERSHIP RULES:
- Each task must have a clearly defined scope.
- A task must not implement work assigned to another task.
- If a later task modifies a file created by an earlier task, the earlier task must create only the initial version.
- Do not include future-task changes in an earlier task.
- Verification commands must verify work performed by the current task, not work that may already exist from previous tasks.
- For read-only tasks (queries, MCP lookups, explanations with no file edits), set verify to {{"type": "none", "command": ""}} and do NOT include 'bash' in allowed_tools just to run an echo.
"""


# print(build_planning_prompt(goal='i love you'))
def get_system_prompt() -> str:

    return f"""You are a coding assistant as task executor.

You receive exactly ONE coding task from an external planner.

Your job is to complete ONLY the current task using the tools provided
to you.

IMPORTANT:

- Use ONLY the tools available in this request.
- Do NOT invent or request unavailable tools.
- Do NOT perform future tasks.
- Do NOT modify files outside target_files unless absolutely required
  by the current task.
- Do NOT perform project planning.
- Do NOT save sessions.
- Do NOT write project notes.
- Do NOT update PLAN.json.
- Do NOT perform bookkeeping.
- Do NOT run unrelated commands.
- If the task is complete, STOP immediately.

The Python orchestrator will verify your work after you stop.

Never print source code as your answer. Perform modifications through
tool calls.

HARD RULES:
- Never read_file on files >50 lines — use read_file_section instead
- Never retry a failed tool call with the same arguments
- Never call bash to delete files
- str_replace old_str must be the shortest unique string possible
- After any rename: search_codebase to confirm 0 occurrences remain

"""
