from .session_ops import get_recent_sessions, search_sessions, save_session
from rich.console import Console
from rich.panel import Panel
from . import file_ops
from .web_ops import web_search

console = Console()


TOOLS={
"read_file":file_ops.read_file,
"append_file":file_ops.append_file,
"read_file_section": file_ops.read_file_section,
"list_dir": file_ops.list_dir,
"write_file":file_ops.write_file,
"str_replace":file_ops.str_replace,
"search_codebase":file_ops.search_codebase,
"read_project_notes":file_ops.read_project_notes,
"write_project_notes":file_ops.write_project_notes,
"get_recent_sessions":get_recent_sessions,
"search_sessions":search_sessions,
"save_session":save_session,
'bash':file_ops.bash,
'web_search':web_search

}

def execute_tool(name, input_args):

    if name not in TOOLS:
        return f"Error: unknown tool"
    
    try:
        console.print(f"  [cyan]→ Tool:[/] {name}({input_args})")
        return TOOLS[name](**input_args)
    except Exception as e:
        return f"{type(e).__name__}: {e}"
