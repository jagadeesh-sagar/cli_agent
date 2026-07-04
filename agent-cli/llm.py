import anthropic
from dotenv import load_dotenv
from pathlib import Path
from pprint import pprint

from prompts import SYSTEM_PROMPT
from tools import execute_tool

load_dotenv()


client=anthropic.Anthropic()


def ask(messages,tools=None):

    response=client.messages.create(

        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
        tools=tools
    )


    MAX_TOOL_CALLS=3
    tool_calls=0

    # handle tool request  (as tool request breaks the llm api call soo we write this logic to add another call)
    while response.stop_reason=='tool_use':  # while loop for multi tool call

        tool_calls+=1
        
        if tool_calls>MAX_TOOL_CALLS:
            raise RuntimeError("Too many calls")
        
        tool_use_block=[b for b in response.content if b.type=='tool_use'] # helps in handling multi tool calls
        
        messages.append({
            "role": "assistant",
            "content": response.content
        })
        
        tool_results=[]

        for tool in tool_use_block:
            result=execute_tool(tool.name,tool.input) # calls tools

            tool_results.append({
                "type":"tool_result",
                "tool_use_id":tool.id,
                "content":result,
            })

        # append the multi tool response too
        messages.append({
            'role':"user",
            "content":tool_results
        })

        # second call — now Claude has the file content and can answer
        response=client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system = SYSTEM_PROMPT,
        tools=tools,
        messages=messages
        )

    return (response.content[0].text)