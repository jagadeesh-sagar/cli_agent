---
name: agent-meta
description: Step-by-step workflow examples for common coding tasks. Load this skill if you are unsure how to sequence tool calls for a task.
---

# Workflow Examples

## Write a new function in a new file
1. list_dir(path=".")                          — check if file already exists
2. write_file(path="x.py", content="...")      — create it (never just print code in response)
3. bash(command="python x.py")                 — verify no syntax errors
4. write_project_notes / save_session

## Add a function to an existing file
1. search_codebase(pattern="filename")         — find exact path
2. read_file_section(start=1, end=20)          — read import block for context
3. str_replace(old_str="...", new_str="...")   — make the edit
4. bash(command="python -m py_compile file")   — verify
5. write_project_notes / save_session

## Rename a symbol across all files
1. search_codebase(pattern="old_name")         — find all occurrences
2. str_replace each file one by one
3. search_codebase(pattern="old_name")         — verify 0 remain
4. bash to syntax-check changed files
5. save_session

## Fix a failing test
1. bash(command="pytest -x")                   — run, stop on first failure
2. search_codebase(pattern="failing_fn_name")  — locate the broken code
3. read_file_section around the hit
4. str_replace to apply the fix
5. bash(command="pytest -x")                   — confirm fix
6. Repeat until all pass, then save_session

## Answer a conceptual question
1. search_sessions(keyword="topic")            — check if discussed before
2. web_search(query="...")                     — get current info
3. Answer in text — no file edits needed
4. save_session
