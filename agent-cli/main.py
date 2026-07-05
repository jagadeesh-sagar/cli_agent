from llm import ask
from tools import tools
from session_management import init_db

init_db()

messages=[
{"role": "user", "content": "in ./leetcodes.py file write a python max heap code "}]

response = ask(messages,tools=tools)

print(response)