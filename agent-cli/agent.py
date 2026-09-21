from config import cfg
from tools import execute_tool
from providers import get_provider,get_planner_provider

MAX_HISTORY_TURNS = cfg.max_history_calls  # keep last 10 turns

provider = get_provider()   
planner_provider=get_planner_provider()


def trim_messages(messages):
    limit = MAX_HISTORY_TURNS * 2
    if len(messages) > limit:
        trimmed = messages[-limit:]
        # make sure we start on a user turn
        if trimmed and trimmed[0]["role"] != "user":
            trimmed = trimmed[1:]
        messages[:] = trimmed

def run_conversation(messages, tools,model=None):
    response = provider.send(messages=messages, tools=tools)

    MAX_TOOL_CALLS = cfg.max_tool_calls
    calls = 0
    last_call_signature = None   # tracks (tool_name, args_str) of the previous call

    # handle tool requests — LLMs return tool_use, we execute and loop back
    while provider.has_tool_calls(response):
        calls += 1

        if calls > MAX_TOOL_CALLS:
            raise RuntimeError("Too many calls")

        tool_calls = provider.get_tool_calls(response)

        # ── Infinite-loop guard ──────────────────────────────────────────────
        # smaller models with small context will fall more into this loops soo to avoid that
        # If the model calls the exact same tool with the exact same args as
        # the previous turn, it's stuck. Break now instead of burning all 15
        # tool call slots and then crashing with RuntimeError.(need to add proper retry thats later)
        
        current_signature = (tool_calls[0].name, str(tool_calls[0].input))
        if current_signature == last_call_signature:
            provider.append_assistant_message(messages=messages, response=response)
            bail_msg = (
                f"TOOL_ERROR: infinite loop detected — '{tool_calls[0].name}' was called "
                f"twice in a row with identical arguments. The tool is failing. "
                f"Stop retrying and tell the user what went wrong."
            )
            provider.append_tool_results(
                messages=messages,
                tool_results=[provider.format_tool_result(tool_calls[0], bail_msg)]
            )
            response = provider.send(messages=messages, tools=tools)
            break
        last_call_signature = current_signature
        # ─────────────────────────────────────────────────────────────────────

        provider.append_assistant_message(messages=messages, response=response)

        tool_results = []

        for tool in tool_calls:
            result = execute_tool(tool.name, tool.input,model=model)
            tool_results.append(provider.format_tool_result(tool, result))

        provider.append_tool_results(messages=messages, tool_results=tool_results)

        response = provider.send(messages=messages, tools=tools)


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


def ask(messages,tools=None,model=None):
    response = run_conversation(messages, tools,model=model)

    run_shutdown(messages, tools)

    return provider.get_text(response)

def planner(user_goal: str) -> str:
    """
    Call the planner LLM with no tools and return raw JSON string.
    Uses get_planner_provider() which may be a different model than the executor(basically the planner is bigger model).
    """
    from providers import get_planner_provider
    from prompts import build_planning_prompt

    planner_provider = get_planner_provider()
    system_prompt = "You are a project planner. Output ONLY raw JSON, no markdown, no explanation."
    user_message = build_planning_prompt(user_goal)
    return planner_provider.raw_send(system_prompt, user_message)