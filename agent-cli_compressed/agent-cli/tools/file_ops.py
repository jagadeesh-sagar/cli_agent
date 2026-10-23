from pathlib import Path
import subprocess
import os

def get_project_path() -> str:
    """
    Return the current working directory at call time.

    Using a function instead of a module-level constant means the agent
    always operates on whatever folder the user is in when they run it,
    not the folder Python was in when this module was first imported.
    """
    return os.getcwd()


# tool functions
def read_file(path: str)-> str:
    return Path(path).read_text()

def read_file_section(path: str,start_line:int,end_line:int)-> str:
    lines= Path(path).read_text().splitlines()
    total_lines=len(lines)

    # sticking to the file length
    start=max(1,start_line)
    end=min(total_lines,end_line)

    chunk=lines[start-1:end]
    return '\n'.join(f"{start+i} :{line}" for i,line in enumerate(chunk))

def list_dir(path: str)->str:
    return "\n".join(str(p) for p in Path(path).rglob("*") if p.is_file())

def write_file(path: str, content: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)   # create parent dirs if missing
    p.write_text(content)
    return f"Written to {path}"

def str_replace(path:str,old_str:str,new_str:str)->str:
    content= Path(path).read_text()
    count=content.count(old_str)

    if count==0:
        return f"Error the old_str is not Found"
    elif count>1:
        return f'Error :{count} occurrences found -old_str must be unique in the file' 
    Path(path).write_text(content.replace(old_str,new_str,1))

    return f"Replaced 1 occurrence in {path}"

def search_codebase(pattern:str,path:str='.')->str:
    result=subprocess.run(
        ['rg',"--line-number","--with-filename",
         "--word-regexp",         # whole words only
        "--glob", "!.git",        # skip git folder
        "--glob", "!venv",        
        "--glob", "!__pycache__", # skip bytecode
         pattern,
         path],
         
        capture_output=True,
        text=True
    )
    # check the subprocess doc for more info
    if result.returncode == 1:   # rg returns 1 when no matches — not an error
        return "No matches found"
    if result.returncode > 1:    # actual error (bad path, rg not installed etc)
        return f"ERROR: {result.stderr}"
    
    return result.stdout

def bash(command: str) -> str:
    """
    Run a shell command. Tries Docker sandbox first; falls back to local shell
    if Docker is not available. Always appends [exit_code: N] so callers can
    reliably detect success (exit_code: 0) vs failure.
    """
    def _run_local():
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True, text=True, timeout=30,
            cwd=get_project_path()
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        output += f"\n[exit_code: {result.returncode}]"
        return output or f"(no output)\n[exit_code: {result.returncode}]"

    try:
        result = subprocess.run(
            ["docker", "run", "--rm",
             "--memory", "256m", "--cpus", "0.5", "--network", "none",
             "--volume", f"{get_project_path()}:/workspace",
             "--workdir", "/workspace",
             "agent-sandbox", "bash", "-c", command],
            capture_output=True, text=True, timeout=30
        )
        # If Docker daemon isn't running, docker CLI exits with code 1 and
        # prints a "failed to connect" error — treat that as unavailable too.
        if result.returncode != 0 and (
            "failed to connect" in result.stderr or
            "Cannot connect" in result.stderr or
            "docker.sock" in result.stderr
        ):
            return _run_local()

        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        output += f"\n[exit_code: {result.returncode}]"
        return output or f"(no output)\n[exit_code: {result.returncode}]"

    except FileNotFoundError:
        # Docker binary not installed at all — run locally
        return _run_local()
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 30s\n[exit_code: 1]"

def append_file(path: str, content: str) -> str:
    with open(path, 'a') as f:
        f.write(content)
    return f"Appended to {path}"

def read_project_notes() -> str:
    from config import cfg
    path = Path(__file__).parent.parent / cfg.project_notes
    if not path.exists():
        return 'No project notes yet'
    return path.read_text()

def write_project_notes(content: str) -> str:
    from config import cfg
    path = Path(__file__).parent.parent / cfg.project_notes
    path.parent.mkdir(parents=True, exist_ok=True)  # create memory/ if missing
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n\n" + content)
    return "Project notes updated."