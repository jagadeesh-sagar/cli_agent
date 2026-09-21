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
from config import cfg

console = Console()

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

# ── REPL ───────────────────────────────────────────────────────────────────────

def run_agent():
    """Interactive REPL mode — keeps conversation history across turns."""
    from agent import ask, planner
    from tools.schemas import tools
    from tasks import verify_task
    import plan as plan_mod

    init_db()
    model=rag_model()

    console.print(Panel(
        "[bold green]CLI Agent ready![/]\n"
        f"[dim]Model: {cfg.model}  |  Type 'exit' or 'quit' to stop[/]",
        title="🤖 CLI Agent",
        style="green"
    ))

    messages = []   # persists across turns so the agent remembers context

    while True:
        try:
            user_input = input("\n🤖 What should I do? > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye![/]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            console.print("[dim]Bye![/]")
            break

        # ── Phase 1: Planning ──────────────────────────────────────────────────
        cwd = os.getcwd()
        cwd_context = f"[Working directory: {cwd}]"

        console.print("\n[bold yellow]🧠 Planning…[/]")
        raw_json = planner(user_input)          # planner LLM → raw JSON string

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

            # Scope the executor strictly to this ONE task.
            messages = []
            messages.append({"role": "user", "content": (
                f"{cwd_context}\n\n"
                f"{skill_context}"
                f"CURRENT TASK (do ONLY this, nothing else):\n"
                f"{task.description}\n\n"
                f"When done, stop. Do not work on any future tasks."
            )})
            response = ask(messages, tools=tools,model=model)

            result = verify_task(task.model_dump())   # verify via bash

            if result["passed"]:
                plan_mod.mark_task_done(goal_plan, task.id)
                console.print(f"[bold green]✅ Task {task.id} verified[/]")

            else:
                retries = plan_mod.increment_retries(goal_plan, task.id)
                console.print(f"[yellow]⚠  Verification failed (attempt {retries}/{MAX_RETRIES_PER_TASK})[/]")
                console.print(f"[dim]   {result['detail'][:120]}[/]")

                if retries >= MAX_RETRIES_PER_TASK:
                    plan_mod.mark_task_failed(goal_plan, task.id, result["detail"])
                    console.print(f"[bold red]✗ Task {task.id} failed after {MAX_RETRIES_PER_TASK} retries — stopping.[/]")
                    break
                else:
                    # Clean slate — drop the entire failed conversation.
                    # Appending to poisoned messages makes the model spiral
                    # further. A fresh context with just what failed is enough.
                    messages = []
                    messages.append({"role": "user", "content": (
                        f"{cwd_context}\n\n"
                        f"{skill_context}"
                        f"Previous attempt failed with: {result['detail'][:300]}\n\n"
                        f"RETRY THIS TASK (do ONLY this, nothing else):\n"
                        f"{task.description}\n\n"
                        f"When done, stop."
                    )})
                    ask(messages, tools=tools)

        console.print(f"\n[bold green]✅[/] {response}")




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
