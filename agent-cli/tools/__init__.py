from .session_ops import get_recent_sessions, search_sessions, save_session
from rich.console import Console
from . import file_ops
from .skills_ops import load_skill,list_skills
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
'web_search':web_search,
'list_skills':list_skills,
'load_skill':load_skill

}

def execute_tool(name, input_args):

    print(input_args)

    if name not in TOOLS:
        return f"Error: unknown tool"
    
    try:
        console.print(f"  [cyan]→ Tool:[/] {name}({input_args})")
        result = str(TOOLS[name](**input_args))  # str() so .strip() never crashes

        if not result.strip():
            result = f"(no output from {name})"
        return result
    
    except Exception as e:
        return f"{type(e).__name__}: {e}"


