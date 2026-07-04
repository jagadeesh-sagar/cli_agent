from pathlib import Path
import subprocess

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

TOOLS={
"read_file":read_file,
"read_file_section": read_file_section,
"list_dir": list_dir,
"write_file":write_file,
"str_replace":str_replace,
"search_codebase":search_codebase
}

def execute_tool(name, input_args):
    print(f"  → {name}({input_args})")
    return TOOLS[name](**input_args)
