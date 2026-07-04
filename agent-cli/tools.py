from pathlib import Path

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
    }
]


# tool functions
def read_file(path: str)-> str:
    return Path(path).read_text()

def list_dir(path: str)->str:
    return "\n".join(str(p) for p in Path(path).rglob("*") if p.is_file())

def write_file(path:str,content:str)-> str:
    Path(path).write_text(content)
    return f"Written to {path}"

TOOLS={
"read_file": read_file,
"list_dir": list_dir,
"write_file":write_file
}

def execute_tool(name, input_args):
    return TOOLS[name](**input_args)
