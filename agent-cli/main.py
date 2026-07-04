from llm import ask
from tools import TOOLS,execute_tool,read_file,list_dir,tools

messages=[
{"role": "user", "content": "Find all variables named exactly num1 and num2 in the codebase and rename them to number1 and number2 and also find exactly find nums in code base and change to numbers ."}
]

response = ask(messages,tools=tools)

print(response)