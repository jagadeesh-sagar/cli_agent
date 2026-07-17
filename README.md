# 🤖 CLI Agent

> A modular, autonomous AI coding assistant that reads, writes, and edits files on your local machine — right from your terminal.

---

## 📖 Overview

**CLI Agent** is a local AI agent designed to interact autonomously with your codebase. You give it a task in plain English via an interactive REPL, and it will read files, write code, run bash commands, and save a record of everything it did until the job is done.

It features **persistent session memory** via SQLite so the agent can recall past interactions, and a **project notes system** (`memory/AGENT.md`) that keeps long-running architectural decisions and coding conventions intact across sessions.

Best of all, it has a **modular provider architecture**. You can easily switch between Anthropic, Groq, DeepSeek, Sarvam, or any OpenAI-compatible endpoint with a single line change in your config!

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔌 **Modular Providers** | Easily swap between Anthropic and OpenAI-compatible APIs (Groq, DeepSeek, Sarvam). |
| 🔁 **Interactive REPL** | Chat directly with the agent. It remembers context across turns. |
| ✏️ **Local File & Command Access** | The agent can read/write files and execute bash commands on your machine. |
| 🧠 **Session Memory** | SQLite database (`sessions.db`) stores every session's prompt, summary, and tools used. |
| 📝 **Project Notes** | `memory/AGENT.md` persists project-level context between sessions automatically. |
| ⚙️ **YAML Configuration** | Centralised `.agent.yaml` configuration file for zero-code configuration. |

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10+
- An API key for your preferred provider (Anthropic, Groq, DeepSeek, etc.)

### 2. Clone & Set Up

```bash
git clone <your-repo-url>
cd cli_agent

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
cd agent-cli
pip install -r requirements.txt
```

### 3. Configure Your Provider & API Key

First, define your environment variables. Create a `.env` file inside `agent-cli/`:

```env
# Add whichever API keys you plan to use:
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
SARVAM_API_KEY=...
```

Next, open `.agent.yaml` to choose your provider and model:

```yaml
# Select your provider (anthropic, groq, deepseek, sarvam, openai, together, openrouter)
provider: groq

# Select your model
model: llama-3.3-70b-versatile
```
*(Tip: For Groq, `llama-3.3-70b-versatile` or `llama3-groq-70b-8192-tool-use-preview` are highly recommended for robust tool calling).*

### 4. Run the Agent

Start the interactive CLI:

```bash
python main.py
```

Type your prompt (e.g., `"Write a binary search function in search.py"`). The agent will autonomously read, write, and execute commands to accomplish the goal!

---

## 🛠️ CLI Commands

The entry point `main.py` provides some handy subcommands to inspect the agent's memory:

```bash
# Start the interactive REPL
python main.py

# List the last 10 sessions the agent worked on
python main.py --history

# Search past sessions for a specific topic
python main.py --search "binary search"

# Print the agent's internal project notes
python main.py --notes
```

---

## ⚙️ Configuration (`.agent.yaml`)

Your agent's behaviour is entirely driven by `.agent.yaml`:

| Setting | Purpose | Default Example |
|---|---|---|
| `model` | The exact LLM model string | `claude-haiku-4-5-20251001` |
| `provider` | Routes to the correct API (`anthropic`, `groq`, etc.) | `anthropic` |
| `max_tool_calls` | Hard limit on how many tools the agent can use in one loop | `15` |
| `max_shutdown_calls` | Hard limit on tools used during the memory-save loop | `5` |
| `project_notes` | Path to the agent's knowledge markdown file | `memory/AGENT.md` |
| `db_path` | SQLite file location | `sessions.db` |

---

## 🔌 Adding New LLM Providers

If you want to use an OpenAI-compatible API that isn't built in:
1. Open `providers/openai_compat.py`.
2. Add your provider's base URL and env key to the `_PROVIDER_CONFIG` dictionary.
3. Open `providers/__init__.py` and add the provider name to the `name in (...)` check.
4. Set `provider: your_provider` in `.agent.yaml`.

---

## 🗂️ Project Structure

```
cli_agent/
└── agent-cli/
    ├── main.py               # Minimal entry point (delegates to cli.py)
    ├── cli.py                # CLI commands, argument parsing, and the REPL
    ├── agent.py              # The core agentic loop (execute tools, send to LLM)
    ├── config.py             # Loads and validates .agent.yaml
    ├── llm.py                # Legacy LLM abstractions (now replaced by providers/)
    ├── prompts.py            # System prompts and agent lifecycle rules
    ├── .agent.yaml           # Easy configuration file
    ├── memory/
    │   └── AGENT.md          # Auto-updated project knowledge base
    ├── providers/            # Modular LLM factory
    │   ├── __init__.py       # Provider registry & lazy-loading singleton
    │   ├── anthropic.py      # Anthropic SDK implementation
    │   ├── openai_compat.py  # Handles Groq, DeepSeek, Sarvam, OpenAI, etc.
    │   └── base.py           # Abstract Base Class for providers
    ├── tools/                # Tool implementations and JSON schemas
    └── sessions.db           # SQLite database (auto-created)
```

---

## 🔐 Security Notes

- **Never commit your `.env` file**. It is included in `.gitignore`.
- The agent has a raw **Bash tool**. Be careful with the directories you run this in, as it can modify, delete, and execute files locally.
- Runaway loops are prevented by `max_tool_calls` in `.agent.yaml`.
