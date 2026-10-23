from tools import execute_tool
from agent import ask

def verify_task(task: dict) -> dict:
    v = task["verify"]

    if v["type"] == "none" or not v.get("command", "").strip():
        return {"passed": True, "detail": "read-only task (no shell verification needed)"}

    if v["type"] == "command":
        output = execute_tool("bash", {"command": v["command"]})
        passed = "[exit_code: 0]" in output
        return {"passed": passed, "detail": output}

    elif v["type"] == "review":
        # a FRESH context — not the conversation that did the work
        judge_prompt = f"""Task: {task['description']}
Acceptance criteria: {v['criteria']}

{execute_tool("bash", {"command": f"cat {task['file']}"})}

Does this satisfy the criteria? Answer PASS or FAIL, then one line why."""
        verdict = ask([{"role": "user", "content": judge_prompt}], tools=None)
        return {"passed": verdict.strip().startswith("PASS"), "detail": verdict}