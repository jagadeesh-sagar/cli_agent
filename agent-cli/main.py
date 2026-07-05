from llm import ask
from tools import tools
from session_management import init_db

init_db()

messages=[
{"role": "user", "content": "explain in short 10 lines about what we have done in last 2 sessions"}]

response = ask(messages,tools=tools)

print(response)