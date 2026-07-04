from llm import ask
from tools import TOOLS,execute_tool,read_file,list_dir,tools

messages=[
    {"role": "user", "content": "Read hello.py, add a docstring to every function(if not exists create a function) that doesn't have one, and write the updated file back"}
]

response = ask(messages,tools=tools)

print(response)