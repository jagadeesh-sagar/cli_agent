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
},
# cache_control on the LAST tool = caches system prompt + ALL tool schemas as one block
{
    "name": "web_search",
    "description": "Search the web for real-time information. Use for docs, APIs, or anything not in the codebase.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Number of results (default 3)"}
        },
        "required": ["query"]
    },
    "cache_control": {"type": "ephemeral"}
}
]
