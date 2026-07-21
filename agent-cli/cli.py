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
        header  = lines[0]                                          # "[2026-07-09] the prompt"
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


# ── REPL ───────────────────────────────────────────────────────────────────────

def run_agent():
    """Interactive REPL mode — keeps conversation history across turns."""
    from agent import ask
    from tools.schemas import tools

    init_db()
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

        messages.append({"role": "user", "content": user_input})
        response = ask(messages, tools=tools)
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

    args = parser.parse_args()

    if args.history is not None:
        cmd_history(limit=args.history)
    elif args.search:
        cmd_search(keyword=args.search)
    elif args.notes:
        cmd_notes()
    else:
        run_agent()
