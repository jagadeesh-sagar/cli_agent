"""
cli.py — Argparse definitions, REPL loop, and CLI sub-commands.

Run via main.py:
    python main.py                    # interactive REPL
    python main.py --history          # last 10 sessions
    python main.py --history 20       # last 20 sessions
    python main.py --search "heap"    # search sessions
    python main.py --notes            # print AGENT.md
"""

import argparse
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from tools.session_ops import init_db, get_recent_sessions, search_sessions
from tools.sandbox_ops import start_sandbox,cleanup
from config import cfg

console = Console()
import re

from tools.mcp_bridge import create_mcp_bridge


def build_task_roadmap(goal_plan, current_task_id: int) -> str:
    """
    Build a compact roadmap of ALL tasks so the executor knows
    what's done, what's current, and what's coming next.
    This prevents the model from doing future tasks' work.
    """
    lines = ["TASK ROADMAP (for orientation only — do NOT work on future tasks):"]
    for t in goal_plan.tasks:
        if t.status == "done":
            marker = "✅"
        elif t.id == current_task_id:
            marker = "▶ YOU ARE HERE"
        elif t.status == "failed":
            marker = "✗"
        else:
            marker = "○"
        files_info = ""
        if t.status == "done" and t.files_changed:
            files_info = f"  [created: {', '.join(t.files_changed)}]"
        lines.append(f"  {marker} Task {t.id}: {t.description}{files_info}")
    lines.append("")
    return "\n".join(lines)

def extract_changed_files(response: str) -> list[str]:
    """
    Parse model response for file paths it wrote/edited based on tool result patterns.
    """
    patterns = [
        r"Written to (.+)",
        r"Replaced \d+ occurrence[s]? in (.+)",
        r"Appended to (.+)",
    ]
    found = []
    for pat in patterns:
        found.extend(re.findall(pat, response))
    return list(dict.fromkeys(found))   # deduplicate, preserve order

# ── Sub-commands ───────────────────────────────────────────────────────────────

def cmd_history(limit: int = 10):
    """Print the last N sessions in a rich table."""
    init_db()
    raw = get_recent_sessions(limit=limit)

    if not raw.strip():
        console.print("[yellow]No sessions found.[/]")
        return

    table = Table(
        title=f"📚 Last {limit} Sessions",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("Date", style="dim", width=12)
    table.add_column("Prompt", style="white", ratio=1)
    table.add_column("Summary", style="green", ratio=2)

    for block in raw.split("\n\n"):
        lines = block.strip().splitlines()
        if not lines:
            continue
        header  = lines[0]                                   # "[2026-07-09] the prompt"
        summary = lines[1].lstrip("  → ") if len(lines) > 1 else "—"
        date    = header[1:11] if header.startswith("[") else "?"
        prompt  = header[13:]  if header.startswith("[") else header
        table.add_row(date, prompt, summary)

    console.print(table)


def cmd_search(keyword: str):
    """Search past sessions and print matches."""
    init_db()
    raw = search_sessions(keyword=keyword)

    if raw.startswith("No sessions"):
        console.print(f"[yellow]{raw}[/]")
        return

    console.print(Panel(
        f"[bold]Search results for:[/] [cyan]\"{keyword}\"[/]",
        style="blue"
    ))

    for block in raw.split("\n\n"):
        lines = block.strip().splitlines()
        if not lines:
            continue
        header  = lines[0]
        summary = lines[1].lstrip("  → ") if len(lines) > 1 else "—"
        console.print(f"\n[bold cyan]{header}[/]")
        console.print(f"  [green]{summary}[/]")


def cmd_notes():
    """Print the contents of AGENT.md."""
    notes_path = Path(__file__).parent / cfg.project_notes
    if not notes_path.exists():
        console.print(f"[yellow]No project notes found at {notes_path}[/]")
        return
    content = notes_path.read_text()
    console.print(Panel(content, title="📝 Project Notes (AGENT.md)", style="green"))

def rag_model():
    import chromadb
    from config import cfg 
    from sentence_transformers import SentenceTransformer
    from pathlib import Path

    model=SentenceTransformer("all-MiniLM-L6-v2")
  
    return model


def save_project_context(goal_plan,cwd):
    import datetime
    context_path= Path(cwd) / "memory/AGENT.md"
    
    if context_path.exists() :
        existing =    context_path.read_text() 
    else :
        context_path.touch(exist_ok=True)
        existing=''

    files_created = []
    task_summaries = []
    
    for t in goal_plan.tasks:
        if t.files_changed:
            files_created.extend(t.files_changed)
            
        status_icon = "✅" if t.status == 'done' else ("❌" if t.status == 'failed' else "⏳")
        summary_line = f"  {status_icon} Task {t.id}: {t.description}"
        if t.detail:
            summary_line += f"\n     Note: {t.detail}"
        task_summaries.append(summary_line)

    tasks_str = "\n".join(task_summaries)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry = f"""
            ## Goal: {goal_plan.goal} (Completed at {timestamp})
            - Status: {'completed' if all(t.status == 'done' for t in goal_plan.tasks) else 'partial'}
            - Progress: {sum(1 for t in goal_plan.tasks if t.status == 'done')}/{len(goal_plan.tasks)} tasks
            - Files created/modified: {', '.join(files_created) if files_created else 'None'}
            
            ### Task Breakdown:
{tasks_str}
            """
    
    context_path.write_text(existing+entry)

# ── REPL ───────────────────────────────────────────────────────────────────────

def run_agent():
    """Interactive REPL mode — keeps conversation history across turns."""
    from agent import ask, planner, get_unrecovered_tool_errors, classify_failure
    from tools.schemas import tools
    from tasks import verify_task
    import plan as plan_mod
    # MCP bridge — fully synchronous now
    mcp_bridge = create_mcp_bridge()
    mcp_tool_info = mcp_bridge.get_prompt_description()

    session_turns=[]

    init_db()

    console.print(Panel(
        "[bold green]CLI Agent ready![/]\n"
        f"[dim]Model: {cfg.model}  |  Type 'exit' or 'quit' to stop[/]",
        title="🤖 CLI Agent",
        style="green"
    ))

    # messages = []   # persists across turns so the agent remembers context
    
    # Inject short term memory if exists
    cwd = os.getcwd()
    context_path = Path(cwd) / "memory/AGENT.md"
    project_memory = context_path.read_text().strip() if context_path.exists() else ""

    try:
        start_sandbox()
    except Exception as e:
        console.print(f"[yellow]⚠ Docker sandbox unavailable: {e}. Using local bash.[/]")

    while True:
        try:
            user_input = input("\n🤖 What should I do? > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye![/]")
            try:
                cleanup()
            except Exception:
                pass
            mcp_bridge.disconnect_all()
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            console.print("[dim]Bye![/]")
            try:
                cleanup()
            except Exception:
                pass
            mcp_bridge.disconnect_all()
            break

        # ── Phase 1: Planning ──────────────────────────────────────────────────
        cwd = os.getcwd()
        cwd_context = f"[Working directory: {cwd}]"

        console.print("\n[bold yellow]🧠 Planning…[/]")
        raw_json = planner(user_input, mcp_bridge=mcp_bridge,project_memory=project_memory[-3000:],session_turns=session_turns[-5:])          # planner LLM → raw JSON string

        try:
            goal_plan = plan_mod.validate_json(raw_json)   # parse + validate
        except ValueError as e:
            console.print(f"[red]Planning failed:[/] {e}")
            continue

        plan_mod.save_plan(goal_plan)           # write PLAN.json to disk
        console.print(f"[green]✅ Plan saved:[/] {len(goal_plan.tasks)} tasks for '{goal_plan.goal}'")
        # Show the plan summary so user can see what was decided
        for t in goal_plan.tasks:
            skill_tag = f" [dim][skill: {t.skill}][/]" if t.skill else ""
            console.print(f"  [dim]{t.id}.[/] {t.description}{skill_tag}")

        # ── Phase 2: Execute tasks one by one ─────────────────────────────────
        MAX_RETRIES_PER_TASK = 3
        response = ""
        last_state = None  # Reset state handoff for new goal
        retry_notes: dict[int, str] = {}  # task_id -> last failure reason


        while (task := plan_mod.get_next_pending_task(goal_plan)):
            total = len(goal_plan.tasks)
            done  = sum(1 for t in goal_plan.tasks if t.status == "done")
            console.rule(f"[bold cyan]Task {task.id}/{total}[/] ({done} done, {total-done-1} remaining)")
            console.print(f"[bold cyan]▶[/] {task.description}")
            console.print(f"[dim]  verify: {task.verify.command}[/]")
            if task.skill:
                console.print(f"[dim]  skill:  {task.skill}[/]")
            plan_mod.mark_task_running(goal_plan, task.id)

            # Load the skill the planner chose for this task (if any)
            skill_context = ""
            if task.skill:
                from tools.skills_ops import load_skill
                skill_content = load_skill(task.skill)
                if not skill_content.startswith("Error"):
                    skill_context = f"[Skill: {task.skill}]\n{skill_content}\n---\n"
                else:
                    console.print(f"[yellow]  ⚠ skill '{task.skill}' not found, continuing without it[/]")

            context = ""
            if task.context_files:
                for f in task.context_files:
                    try:
                        numbered = "\n".join(
                            f"{i+1} | {line}"
                            for i, line in enumerate(Path(f).read_text().splitlines()[:120])
                        )
                        context += f"\n--- {f} (first 120 lines) ---\n{numbered}\n"
                    except Exception as e:
                        context += f"\n--- {f} ---\n[Could not read file: {e}]\n"

            # Prepare previous state context
            prev_context = ""
            if last_state:
                prev_context = (
                    f"PREVIOUS TASK COMPLETED: {last_state['completed_task']}\n"
                    f"FILES NOW EXIST: {', '.join(last_state['files_changed'])}\n"
                    f"PREVIOUS TASK FINDINGS:\n{last_state.get('findings', '')}\n"
                    f"VERIFY OUTPUT: {last_state['verify_output']}\n\n"
                )

            # Build task roadmap so executor sees the full picture
            roadmap = build_task_roadmap(goal_plan, task.id)

            retry_context = ""
            if task.id in retry_notes:
                retry_context = (
                    f"⚠ RETRY: previous attempt at this task failed with:\n"
                    f"{retry_notes[task.id]}\nFix the cause; do not repeat the same failing call.\n\n"
                )
                        # Lightweight handoff from the immediately preceding user turn (if any)
            last_turn_context = ""
            if session_turns:
                last = session_turns[-1]
                last_turn_context = (
                    f"PREVIOUS USER TURN (for reference only — do NOT re-execute):\n"
                    f"- User asked: {last['user']}\n"
                    f"- Status: {last['status']}\n"
                    f"- Output summary: {last['assistant_reply'][:600]}\n\n"
                )

            # Scope the executor strictly to this ONE task.
            messages = []
            messages.append({"role": "user", "content": (
                f"OVERALL GOAL: {goal_plan.goal}\n\n"
                f"{roadmap}\n"
                f"{last_turn_context}"
                f"{prev_context}"
                f"{cwd_context}\n"
                f"{skill_context}"
                f"Relevant files you will need:\n{context}\n"
                f"{retry_context}"
                f"═══════════════════════════════════════════\n"
                f"YOUR CURRENT TASK (Task {task.id}): {task.description}\n"
                f"Write to: {task.target_files}\n"
                f"═══════════════════════════════════════════\n"
                f"STRICT RULES:\n"
                f"- Do ONLY Task {task.id}. Do NOT do any future tasks.\n"
                f"- Tasks marked ○ above will be handled later by separate calls.\n"
                f"- When Task {task.id} is complete, STOP immediately.\n"
            )})

    
            # print('---------------------jaggu----------------',messages)
            
            from tools import get_tool_schemas
            from tools.schemas import tools as ALL_TOOLS_LIST
            allowed_names = task.allowed_tools if task.allowed_tools is not None else [t["name"] for t in ALL_TOOLS_LIST]  
            task_tools = get_tool_schemas(allowed_names)
            
            if mcp_bridge:
                for name in (task.allowed_tools or []):
                    if name in mcp_bridge.tools:
                        task_tools.append(mcp_bridge.tools[name]['schema'])
                        
            console.print(f"[dim]  tools:  {[t['name'] for t in task_tools]}[/]")
            
            response = ask(messages, tools=task_tools, mcp_bridge=mcp_bridge)

            result = verify_task(task.model_dump())   # verify via bash

            tool_errors = get_unrecovered_tool_errors()
            if result["passed"] and tool_errors:
                result = {
                    "passed": False,
                    "detail": "Tool call(s) failed and were never recovered: " + " | ".join(tool_errors),
                }

            if result["passed"]:
                plan_mod.mark_task_done(goal_plan, task.id)
                console.print(f"[bold green]✅ Task {task.id} verified[/]")
                files_changed = extract_changed_files(response)
                task.files_changed = files_changed
                last_state = {
                    "completed_task": task.description,
                    "files_changed": files_changed,
                    "verify_output": result["detail"],
                    "findings": response[:1500]
                }

            else:
                kind = classify_failure(result["detail"])
                if kind == "permanent":
                    plan_mod.mark_task_failed(goal_plan, task.id, result["detail"])
                    console.print(f"[bold red]✗ Task {task.id} failed with a non-retryable error — stopping immediately:[/]")
                    console.print(f"[dim]   {result['detail'][:200]}[/]")
                    break

                retries = plan_mod.increment_retries(goal_plan, task.id)
                console.print(f"[yellow]⚠  Verification failed (attempt {retries}/{MAX_RETRIES_PER_TASK})[/]")
                console.print(f"[dim]   {result['detail'][:120]}[/]")

                if retries >= MAX_RETRIES_PER_TASK:
                    plan_mod.mark_task_failed(goal_plan, task.id, result["detail"])
                    console.print(f"[bold red]✗ Task {task.id} failed after {MAX_RETRIES_PER_TASK} retries — stopping.[/]")
                    break
                else:
                    if kind == "rate_limit":
                        import time
                        wait_s = 5 * (3 ** (retries - 1))  # 5s, 15s, 45s
                        console.print(f"[dim yellow]   ⏳ Rate-limited/timed-out — waiting {wait_s}s before retry…[/]")
                        time.sleep(wait_s)
                    # Clean slate — the next loop pass rebuilds a fresh context for this task
                    # (with the failure reason) and runs verify again on the retry.
                    retry_notes[task.id] = result["detail"][:300]
                    task.status = "pending"
                    plan_mod.save_plan(goal_plan)

        save_project_context(goal_plan=goal_plan, cwd=cwd)
        if context_path.exists():
            project_memory = context_path.read_text().strip()

        any_failed = any(t.status != "done" for t in goal_plan.tasks)
        failed_details = [t.detail for t in goal_plan.tasks if t.status == "failed" and t.detail]

        session_turns.append({
        "turn": len(session_turns)+1,
        "user": user_input,
        "goal": goal_plan.goal,
        "status": "failed" if any_failed else "Completed",
        "tasks_summary": [f"{t.id}. {t.description} [{t.status}]" for t in goal_plan.tasks],
        "files_changed": [f for t in goal_plan.tasks for f in t.files_changed],
        "assistant_reply": response[:1200],  
        "error": failed_details[-1][:300] if failed_details else None
         })
         
        status_prefix = "[bold red]❌[/]" if any_failed else "[bold green]✅[/]"
        console.print(f"\n{status_prefix} {response}")


# ── Argparse + Entry point ─────────────────────────────────────────────────────

def main():
    """Parse CLI arguments and dispatch to the right command."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="🤖 CLI Agent — AI coding assistant powered by Claude",
    )
    parser.add_argument(
        "--history",
        nargs="?",       # --history  OR  --history 20
        const=10,
        metavar="N",
        type=int,
        help="List the last N sessions (default: 10)",
    )
    parser.add_argument(
        "--search",
        metavar="KEYWORD",
        type=str,
        help='Search past sessions by keyword  e.g. --search "heap"',
    )
    parser.add_argument(
        "--notes",
        action="store_true",
        help="Print the project notes (AGENT.md)",
    )
    parser.add_argument(
        "--project",
        metavar="PATH",
        type=str,
        default=None,
        help="Project folder to work in (default: current directory)",
    )

    args = parser.parse_args()

    # Change into the target project folder so every tool call,
    # os.getcwd(), and get_project_path() all return the right path.
    
    if args.project:
        target = Path(args.project).expanduser().resolve()
        if not target.is_dir():
            console.print(f"[red]--project path does not exist: {target}[/]")
            raise SystemExit(1)
        os.chdir(target)
        console.print(f"[dim]📁 Working in: {target}[/]")

    if args.history is not None:
        cmd_history(limit=args.history)
    elif args.search:
        cmd_search(keyword=args.search)
    elif args.notes:
        cmd_notes()
    else:
        run_agent()
