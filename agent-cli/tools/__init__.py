from .session_ops import get_recent_sessions, search_sessions, save_session
from rich.console import Console
from . import file_ops
from .skills_ops import load_skill, list_skills
from .web_ops import web_search
import os
from .memory_ops import index_project,scan_directory,semantic_search
from .schemas import tools

console = Console()


TOOLS = {
    "read_file":          file_ops.read_file,
    "append_file":        file_ops.append_file,
    "read_file_section":  file_ops.read_file_section,
    "list_dir":           file_ops.list_dir,
    "write_file":         file_ops.write_file,
    "str_replace":        file_ops.str_replace,
    "search_codebase":    file_ops.search_codebase,
    "read_project_notes": file_ops.read_project_notes,
    "write_project_notes":file_ops.write_project_notes,
    "get_recent_sessions":get_recent_sessions,
    "search_sessions":    search_sessions,
    "save_session":       save_session,
    "bash":               file_ops.bash,
    "web_search":         web_search,
    "list_skills":        list_skills,
    "load_skill":         load_skill,
    "index_project":     index_project,
    "scan_directory": scan_directory,
    "semantic_search": semantic_search,
}

# Paths the model hallucinates when it loses context.
# These come from its training data (Docker containers, cloud VMs, CI runners).
_HALLUCINATED_PREFIXES = (
    "/workspace",
    "/mnt",
    "/tmp/agent",
    "/tmp/project",
    "/home/user/project",
    "/home/ubuntu/",
    "/app",
)

def _sanitize_paths(args: dict) -> dict:
    """
    Silently redirect hallucinated paths to the real CWD.

    When smaller models lose context they default to paths from their training
    data (/workspace, /mnt ...). Instead of letting the tool fail and adding
    more error noise to the conversation, we redirect silently so execution
    continues correctly.
    """
    cwd = os.getcwd()
    sanitized = {}
    for k, v in args.items():
        if isinstance(v, str):
            for fake in _HALLUCINATED_PREFIXES:
                if v.startswith(fake):
                    real = cwd + v[len(fake):]
                    console.print(f"  [dim yellow]⚑ path redirect: {v} → {real}[/]")
                    v = real
                    break
        sanitized[k] = v
    return sanitized


def execute_tool(name, input_args,model=None):
    if name not in TOOLS:
        return "TOOL_ERROR: unknown tool — check tool name"

    try:
        clean_args = _sanitize_paths(input_args)
        console.print(f"  [cyan]→ Tool:[/] {name}({clean_args})")
        if name in {"index_project", "semantic_search"}:
            result = TOOLS[name](
                **clean_args,
                model=model
            )

        else:
            result = TOOLS[name](**clean_args)
            
        result = str(result)

        if not result.strip():
            result = f"(no output from {name})"
        return result

    except Exception as e:
        return f"TOOL_ERROR: {type(e).__name__}: {e}"

available_tools = [
    "read_file",
    "append_file",
    "read_file_section",
    "list_dir",
    "write_file",
    "str_replace",
    "search_codebase",
    "read_project_notes",
    "write_project_notes",
    "get_recent_sessions",
    "search_sessions",
    "save_session",
    "bash",
    "web_search",
    "list_skills",
    "load_skill",
    "index_project","scan_directory","semantic_search"
]

# def list_tools(available_tools:list[str])->list[str]:
#     return available_tools