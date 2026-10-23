import subprocess,os ,shlex

def git(command:str)->str:

    ALLOWED={"status", "diff", "log", "add", "commit", "branch", 
               "checkout", "stash", "show", "reset"}

    try:
        parts=shlex.split(command)
    except ValueError as e:
        return f"TOOL_ERROR: invalid command syntax: {e}"

    if not parts:
        return "TOOL_ERROR: empty git command"

    if parts[0] != "git":
        return "TOOL_ERROR: command must start with git"

    if len(parts) < 2:
        return "TOOL_ERROR: missing git subcommand"

    if "--force" in parts or '-f' in parts:
        return "TOOL_ERROR: --force flag is not allowed"
    
    subcommand =parts[1]

    if subcommand not in ALLOWED:
        return f"TOOL_ERROR : git {subcommand} is not allowed"

    result=subprocess.run(
        parts,
        capture_output=True,
        text=True,
        timeout=15,
        cwd=os.getcwd())

    output=result.stdout
    if result.stderr:
        output+=f'\n[stderr]\n{result.stderr}'
    return output or "(no output)"

