from .session_ops import get_recent_sessions, search_sessions, save_session
from rich.console import Console
from . import file_ops
from .sandbox_ops import start_sandbox,cleanup
from .skills_ops import load_skill, list_skills
from .web_ops import web_search
import os
from .memory_ops import scan_directory
from .rag import index_project, code_search
from .schemas import tools
from .git_ops import git

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
    "bash":               sandbox_ops.bash,
    "web_search":         web_search,
    "list_skills":        list_skills,
    "load_skill":         load_skill,
    "index_project":     index_project,
    "scan_directory": scan_directory,
    "code_search":code_search,
    "git":git
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


def execute_tool(name, input_args,model=None,mcp_bridge=None):

    if name in TOOLS:
        try:
            clean_args = _sanitize_paths(input_args)
            console.print(f"  [cyan]→ Tool:[/] {name}({clean_args})")

            result = TOOLS[name](**clean_args)              
            result = str(result)

            if not result.strip():
                result = f"(no output from {name})"
            return result
        except Exception as e:
            return f"TOOL_ERROR: MCP {name}: {type(e).__name__}: {e}"
    
    if mcp_bridge and name in mcp_bridge.tools:
        try:
            result = mcp_bridge.call_tool(name, input_args)
            return str(result) if result else f'(no output from MCP tool {name})'
        except Exception as e:
            return f"TOOL_ERROR: {name}: {type(e).__name__}: {e}"
    return "TOOL_ERROR: unknown tool — check tool name"

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
    "index_project","scan_directory","code_search"
    "get_tool_schemas",
    "git"
]

def get_tool_schemas(allowed_names: list[str]) -> list[dict]:
    """Return only the tool schemas requested, for token efficiency."""
    from .schemas import TOOL_SCHEMAS
    name_set = set(allowed_names)
    return [schema for name, schema in TOOL_SCHEMAS.items() if name in name_set]

def get_tools_descriptions() -> str:
    """Return a compact string of tool names and descriptions for system prompts."""
    from .schemas import TOOL_SCHEMAS
    lines = []
    for name, schema in TOOL_SCHEMAS.items():
        desc = schema.get("description", "").split(".")[0]  # Just the first sentence
        lines.append(f"- {name}: {desc}.")
    return "\n".join(lines)