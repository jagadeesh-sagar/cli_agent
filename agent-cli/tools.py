from pathlib import Path
import subprocess
from session_management import get_recent_sessions, search_sessions, save_session

PROJECT_PATH = str(Path(".").resolve()) 

tools = [
    {
        "name": "read_file",
        "description": "Read the contents of a file at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file"
                }
            },
            "required": ["path"]
        }
    },

    {
        "name": "read_file_section",
        "description": "Read the contents of a file at the given path ."
        "The file is divided into chunks and start with 1 and end with any number and after first response decide the file chunk "
        "The main idea for this chunk-read tool is to reduce the tokens consumption ",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file"
                },
                "start_line": {
                "type": "integer",
                "description": "First line to read (1-indexed)"
            },
            "end_line": {
                "type": "integer",
                "description": "Last line to read (inclusive)"
            }
            },
            "required": ["path",'start_line','end_line']
        }
    },
    {
        "name":"list_dir",
        "description":"list all files in directory",
        "input_schema":{
            "type":"object",
            "properties":{
                "path":{
                    "type":"string",
                    "description":"Directory Path"
                }
            },
            "required":["path"]
        }
    }
    ,{
        "name":"write_file",
        "description":"write content to a file and at a given path . Creates the file if it doesn't exist.",
        "input_schema":{
            "type":"object",
            "properties":{
                "path":{
                    "type":"string",
                    "description":"File path to write"
                },
                "content":{
                    "type":"string",
                    "description":"Full content to write"
                }  
            }, 
                "required":["path","content"]
        }
    },
    {
        "name": "str_replace",
        "description": (
            "Replace an exact unique string in a file with new content. "
            "old_str must appear exactly once in the file. "
            "Prefer this over write_file for edits — safer and uses fewer tokens."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string", "description": "File path"},
                "old_str": {"type": "string", "description": "Exact string to find — must be unique in the file"},
                "new_str": {"type": "string", "description": "String to replace it with"}
            },
            "required": ["path", "old_str", "new_str"]
    }
},
{
        "name": "search_codebase",
        "description": (
            "Search for an exact pattern across all files in the codebase using ripgrep. "
            "Returns file path, line number, and matching line for each match. "
            "Use this FIRST before reading any file — find where something lives, then read only that section. "
            "Use specific names as patterns (e.g. 'num1' not 'num')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string", "description": "File path"},
                "pattern": {"type": "string", "description": "Exact pattern to find —"},

            },
            "required": ["path", "pattern"]
    }
},
{
        "name": "append_file",
        "description": (
            "Add the content to the existing file ."
            "search the file with other tools then append changes"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content that is going to append to the file"},

            },
            "required": ["path", "content"]
    }
},

{
        "name": "read_project_notes",
        "description": (
        "Read the AGENT.md file that stores persistent project context, "
        "previous decisions, architecture notes, coding conventions, "
        "known bugs, and work completed in earlier sessions."     
              ),
        "input_schema": {
            "type": "object",
            "properties": {}
         }
},

{
        "name": "write_project_notes",
        "description": (
            "Append new project notes to AGENT.md. "
            "Record important changes, files modified, bugs fixed, "
            "architectural decisions, and implementation patterns so future "
            "sessions have context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string",
                            "description": "Markdown text to append to AGENT.md"}
            },
            "required": ["content"]
    }
}
,{
        "name": "get_recent_sessions",
        "description": "Get the last N sessions to understand what was worked on before. Call this at startup after read_project_notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of recent sessions to fetch (default 5)"}
            },
            "required": []
        }
},
{
        "name": "search_sessions",
        "description": "Search past sessions by keyword — use when user asks 'what did we do with X' or 'when did we change Y'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Word to search in past session prompts and summaries"}
            },
            "required": ["keyword"]
        }
},
{
        "name": "save_session",
        "description": "Save the current session when work is complete. Call this at the end of every session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt":     {"type": "string", "description": "What the user asked for"},
                "summary":    {"type": "string", "description": "What was done — files changed, decisions made"},
                "tools_used": {"type": "array", "items": {"type": "string"}, "description": "List of tool names called"}
            },
            "required": ["prompt", "summary", "tools_used"]
        }
},
{
        "name": "bash",
        "description": (
            "Run a shell command inside a sandboxed Docker container. "
            "Use to run Python files, check output, run tests, install packages. "
            "The container has access to your project files . "
            "No internet access inside the container. Timeout: 30s."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run. e.g. 'python hello.py' or 'python -m pytest'"
                }
            },
            "required": ["command"]
    }
}
]


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

def write_file(path:str,content:str)-> str:
    Path(path).write_text(content)
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

def bash(command:str)->str:
    try:
        result=subprocess.run(
            ["docker","run","--rm",
            "--memory","256m",
            "--cpus","0.5",
            "--network","none",
            "--volume",f"{PROJECT_PATH}:/workspace",
            "--workdir","/workspace",
            "python:3.12-slim",
            "bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout
        if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
        return output or "(no output)"

    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 30s"
    except FileNotFoundError:
        return "ERROR: docker not found — is Docker running?"

def append_file(path: str, content: str) -> str:
    with open(path, 'a') as f:
        f.write(content)
    return f"Appended to {path}"

def read_project_notes()->str:
    path=Path('./AGENT.md')
    if not path.exists():
        return f'No project notes yet'
    return path.read_text()

def write_project_notes(content: str) -> str:
    with open("./AGENT.md", "a", encoding="utf-8") as f:
        f.write("\n\n" + content)
    return "Project notes updated."

TOOLS={
"read_file":read_file,
"append_file":append_file,
"read_file_section": read_file_section,
"list_dir": list_dir,
"write_file":write_file,
"str_replace":str_replace,
"search_codebase":search_codebase,
"read_project_notes":read_project_notes,
"write_project_notes":write_project_notes,
"get_recent_sessions":get_recent_sessions,
"search_sessions":search_sessions,
"save_session":save_session,
'bash':bash

}

def execute_tool(name, input_args):
    print(f"  → {name}({input_args})")
    return TOOLS[name](**input_args)
