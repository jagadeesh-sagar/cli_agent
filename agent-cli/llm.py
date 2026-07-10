import anthropic
from dotenv import load_dotenv
from pathlib import Path

from prompts import SYSTEM_PROMPT
from tools import execute_tool
from config import cfg

from rich.console import Console
from rich.panel import Panel

console = Console()

load_dotenv()
client=anthropic.Anthropic()

MAX_HISTORY_TURNS = cfg.max_history_calls  # keep last 10 turns

def trim_messages(messages):
    limit = MAX_HISTORY_TURNS * 2
    if len(messages) > limit:
        trimmed = messages[-limit:]
        # make sure we start on a user turn
        if trimmed and trimmed[0]["role"] != "user":
            trimmed = trimmed[1:]
        messages[:] = trimmed

def ask(messages,tools=None):

    trim_messages(messages)
    response=client.messages.create(
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
        tools=tools,
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
    )

    print(f"Tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
    print(f"Cache: {response.usage.cache_creation_input_tokens} created / {response.usage.cache_read_input_tokens} read")

    MAX_TOOL_CALLS=cfg.max_tool_calls
    tool_calls=0

    conversation_end=None # using this to strip the shutdown messages

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

            print(tool.name)

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
            model=cfg.model,
            max_tokens=cfg.max_tokens_tool,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=tools,
            messages=messages,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )

    final_text=response.content[0].text

    messages.append({
        'role':'assistant',
        'content':response.content
    })
    
    conversation_end = len(messages)

    messages.append({
        'role':'user',
        'content':"Task complete. Run shutdown sequence: write_project_notes "
        "if anything new was learned, then save_session with the prompt, summary, and tools used."
            })
    
    shutdown_response=client.messages.create(
        model=cfg.model,
        max_tokens=cfg.max_tokens_tool,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=tools,
        messages=messages,
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
    )
    shutdown_calls=0

    while shutdown_response.stop_reason=='tool_use':
        shutdown_calls+=1

        if shutdown_calls>cfg.max_shutdown_calls:
            break

        tool_use_block=[b for b in shutdown_response.content if b.type=='tool_use'] 

        messages.append({
            "role": "assistant",
            "content": shutdown_response.content
        })

        tool_results=[]

        for tool in tool_use_block:

            print(tool.name)

            result=execute_tool(tool.name,tool.input) # calls tools
            tool_results.append({
                "type":"tool_result",
                "tool_use_id":tool.id,
                "content":result,
            })

        messages.append({
            'role':"user",
            "content":tool_results
        })

        shutdown_response=client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens_tool,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=tools,
            messages=messages,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )

    del messages[conversation_end:]

    return final_text