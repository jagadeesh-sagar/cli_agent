from config import cfg
from tools import execute_tool
from providers import get_provider

MAX_HISTORY_TURNS = cfg.max_history_calls  # keep last 10 turns

provider = get_provider()   


def trim_messages(messages):
    limit = MAX_HISTORY_TURNS * 2
    if len(messages) > limit:
        trimmed = messages[-limit:]
        # make sure we start on a user turn
        if trimmed and trimmed[0]["role"] != "user":
            trimmed = trimmed[1:]
        messages[:] = trimmed

def run_conversation(messages,tools):
    response=provider.send(messages=messages,tools=tools)


    MAX_TOOL_CALLS=cfg.max_tool_calls
    calls=0

    conversation_end=None # using this to strip the shutdown messages

    # handle tool request  (as tool request breaks the llm api call soo we write this logic to add another call)
    while provider.has_tool_calls(response): 
        calls+=1
        
        if calls>MAX_TOOL_CALLS:
            raise RuntimeError("Too many calls")
        
        tool_calls = provider.get_tool_calls(response)

        provider.append_assistant_message(messages=messages,response=response)

        tool_results = []

        for tool in tool_calls:
            result = execute_tool(
                tool.name,
                tool.input)

            tool_results.append(
                provider.format_tool_result(
                    tool,
                    result))
            print(tool_results,'jaggu',messages)

        provider.append_tool_results(
            messages=messages,
            tool_results=tool_results)
        
        response=provider.send(messages=messages,tools=tools)

    # final_text=provider.get_text(response=response)

    provider.append_assistant_message(messages=messages,response=response)

    return response


def run_shutdown(messages, tools):

    conversation_end = len(messages)

    provider.user_shutdown_message(messages=messages,content="Task complete. Run shutdown sequence: write_project_notes "
    "if anything new was learned, then save_session with the prompt, summary, and tools used."
        )
    
    shutdown_response=provider.send(messages=messages,tools=tools)

    shutdown_calls=0

    while provider.has_tool_calls(shutdown_response):
        shutdown_calls+=1

        if shutdown_calls>cfg.max_shutdown_calls:
            break

        provider.append_assistant_message(messages=messages,response=shutdown_response)

        tool_calls = provider.get_tool_calls(shutdown_response)

        tool_results = []

        for tool in tool_calls:
            result = execute_tool(
                tool.name,
                tool.input)

            tool_results.append(
                provider.format_tool_result(
                    tool,
                    result))

        provider.append_tool_results(
            messages,
            tool_results)
        
        shutdown_response=provider.send(messages=messages,tools=tools)

    del messages[conversation_end:]

        # return final_text


def ask(messages,tools=None):
    response = run_conversation(messages, tools)

    run_shutdown(messages, tools)

    return provider.get_text(response)