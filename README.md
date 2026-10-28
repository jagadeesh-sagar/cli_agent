# 🤖 CLI Agent

> An autonomous, Dual-LLM (**Planner + Executor**) AI coding assistant with **MCP (Model Context Protocol)** tool servers, **Docker + Squid proxy sandboxing**, **on-demand Domain Skills**, **Hybrid Code RAG**, and **multi-turn session continuity** — running right from your terminal.

---

## 📖 Overview

**CLI Agent** is a modular, production-inspired local coding agent built to autonomously plan, execute, and verify multi-step software engineering tasks across any project directory.

Unlike single-loop chat wrappers, CLI Agent separates **high-level architectural reasoning** from **surgical task execution**:
1. **🧠 The Planner Agent** (configurable as a larger reasoning model) inspects your project tree, past project memory (`memory/AGENT.md`), recent session turns, available skills, and connected MCP servers to produce a strict, schema-validated `PLAN.json` roadmap.
2. **⚡ The Executor Agent** (configurable as a fast tool-calling model) executes one task at a time with scoped tools, handoff state from previous tasks, and automatic verification + self-healing retries.

---

## 🏗️ System Architecture

```
User Goal (Interactive REPL)
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. PLANNER AGENT (planner_provider / planner_model)                     │
│    • Reads project file tree + memory/AGENT.md + recent session_turns   │
│    • Discovers connected MCP servers & local Skills dynamically         │
│    • Outputs Pydantic-validated PLAN.json (tasks, target_files, verify) │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. ORCHESTRATOR LOOP (cli.py)                                           │
│    For each pending Task in PLAN.json:                                  │
│      ├─ Injects scoped allowed_tools + chosen Skill (SKILL.md)          │
│      ├─ Injects previous task handoff (last_state) & last-turn context  │
│      ▼                                                                  │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ 3. EXECUTOR AGENT (agent.py)                                    │  │
│    │    • Calls Local Tools (file_ops, git, rag, web_search)         │  │
│    │    • Executes bash inside isolated Docker + Squid Proxy Sandbox │  │
│    │    • Calls external MCP servers via thread-safe async bridge    │  │
│    │    • Guarded against hallucinated paths & infinite tool loops   │  │
│    └──────────────────────────────┬──────────────────────────────────┘  │
│                                   │                                     │
│                                   ▼                                     │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ 4. VERIFICATION & SMART RETRY ENGINE (tasks.py / agent.py)      │  │
│    │    • Runs verify command (or verify: "none" for read-only MCP)  │  │
│    │    • Detects unrecovered TOOL_ERRORs automatically              │  │
│    │    • Classifies failures:                                       │  │
│    │        - Permanent (404/401/403/invalid args) → Fail fast       │  │
│    │        - Rate-limit / Timeout (429) → Exponential backoff       │  │
│    │        - Retryable → Clean-slate retry with failure notes       │  │
│    └─────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
   Updates memory/AGENT.md + in-memory session_turns ledger for next turn
```

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🧠 **Dual-Model Planner / Executor** | Use a frontier reasoning model (e.g., Gemini Pro / Claude Sonnet) for planning and a fast, low-cost model (e.g., Sarvam, Haiku, Llama, DeepSeek) for execution. |
| 🔌 **Multi-Provider Support** | Native support for **Anthropic**, **AWS Bedrock** (Converse API via Bearer Token), **Google Gemini**, **Groq**, **DeepSeek**, **Sarvam AI**, **OpenRouter**, **Together AI**, and **OpenAI**. |
| 🌐 **MCP (Model Context Protocol) Bridge** | Connect any stdio MCP server (e.g., `@modelcontextprotocol/server-github`) via `.mcp.yaml`. Uses a persistent background `asyncio` event loop bridged synchronously via `run_coroutine_threadsafe`. |
| 🐳 **Docker + Squid ACL Sandbox** | Executes `bash` commands inside an isolated `agent-sandbox` container routed through an internal Docker network and a Squid proxy (`tools/squid.conf`) with `--force` git guardrails injected at startup. |
| 🔄 **Two-Tier Memory & Continuity** | Combines long-term timestamped project notes (`memory/AGENT.md`), SQLite session logs (`memory/sessions.db`), and an in-memory `session_turns` ledger for pronoun resolution and follow-up continuity across turns. |
| 🛡️ **Smart Failure Classification & Self-Healing** | Tracks tool errors across turns, aborts immediately on permanent 404/401/403 errors, backs off exponentially on 429 rate limits, and retries transient failures with a clean-slate context. |
| 📚 **On-Demand Domain Skills** | Loads specialized `skills/<name>/SKILL.md` guides (`fastapi`, `react`, `sqlalchemy`, `celery`, `drf-api-design`, `pdf-processing`, `git-workflow`, `python`) only for tasks that need them—saving prompt tokens. |
| 🔍 **Codebase Search & RAG** | Fast ripgrep (`search_codebase`) alongside semantic/hybrid code indexing (`tools/rag/`, ChromaDB + SentenceTransformers + AST chunking). |

---

## 🚀 Getting Started

### 1. Prerequisites

- **Python 3.10+**
- **`ripgrep` (`rg`)** installed on your system (used by `search_codebase`)
- **Docker** *(optional but recommended for sandboxed `bash` execution)*
- **Node.js / `npx`** *(optional, required only if using Node-based MCP servers like GitHub MCP)*

### 2. Clone & Install

```bash
git clone <your-repo-url>
cd cli_agent

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r agent-cli/requirements.txt
```

### 3. Configure Environment Variables (`agent-cli/.env`)

Create `agent-cli/.env` with keys for the providers and integrations you use:

```env
# LLM Provider Keys (add whichever you use)
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
SARVAM_API_KEY=...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...

# AWS Bedrock API Key (Bearer Token) & Region
AWS_BEARER_TOKEN_BEDROCK=...
AWS_REGION=us-east-1

# Tool & MCP Keys
TAVILY_API_KEY=tvly-...
GITHUB_TOKEN=ghp_...
```

### 4. Configure `.agent.yaml`

Edit `agent-cli/.agent.yaml` to pick your executor and planner models:

```yaml
# Executor model & provider
provider: sarvam          # anthropic | bedrock | google | groq | deepseek | openrouter | together | openai | sarvam
model: sarvam-105b

# Planner model & provider (falls back to executor provider/model if omitted)
planner_provider: google
planner_model: gemini-3.5-flash-lite

# Execution & context limits
max_tool_calls: 100
max_shutdown_calls: 5
max_tokens: 4096
max_tokens_tool: 10000
max_history_calls: 10

# Storage paths
db_path: memory/sessions.db
vector_db_path: memory/
project_notes: memory/AGENT.md
```

### 5. Configure MCP Servers (`agent-cli/.mcp.yaml`)

Connect external MCP servers (optional):

```yaml
mcp_servers:
  - name: "github"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    description: >
      Interact with GitHub repositories, source code,
      issues, branches, commits, and pull requests.
    transport: "stdio"
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "$GITHUB_TOKEN"
      GITHUB_TOKEN: "$GITHUB_TOKEN"
```

---

## 💻 Usage

### Run from Anywhere via the `./agent` Wrapper

The repository includes a root launcher script (`./agent`) that activates the virtual environment and automatically passes your current working directory via `--project`:

```bash
# Run inside the current folder
./agent

# Or target a specific project directory
python agent-cli/main.py --project /path/to/your/project
```

### CLI Flags

```bash
# Start the interactive REPL in the current directory
python agent-cli/main.py

# Target a specific project directory
python agent-cli/main.py --project ~/Desktop/my_app

# View the last N saved sessions (default: 10)
python agent-cli/main.py --history 20

# Search past sessions by keyword
python agent-cli/main.py --search "authentication"

# Print project notes (memory/AGENT.md)
python agent-cli/main.py --notes
```

---

## 🧰 Built-in Tools & Capabilities

| Category | Tools | Description |
|---|---|---|
| **File Operations** | `read_file`, `read_file_section`, `write_file`, `append_file`, `str_replace`, `list_dir` | Token-efficient chunked reading (`read_file_section`), unique-match surgical edits (`str_replace`), and automatic hallucinated-path redirection (`/workspace` → real CWD). |
| **Code Search & RAG** | `search_codebase`, `index_project`, `semantic_search` / `code_search` | Exact word-boundary regex search via `ripgrep` (`rg`) + AST-aware and vector-backed code retrieval. |
| **Sandboxed Execution** | `bash`, `git` | Executes shell commands inside the Docker sandbox (`agent-sandbox`) with timeout protection and whitelisted `git` subcommands (`--force` / `-f` blocked). |
| **External Context** | `web_search`, `<server>__<tool>` (MCP) | Live web search via Tavily and dynamic tool injection from connected MCP servers. |
| **Memory & Skills** | `list_skills`, `load_skill`, `read_project_notes`, `write_project_notes`, `save_session`, `get_recent_sessions`, `search_sessions` | Progressive loading of `SKILL.md` domain playbooks and persistent cross-session memory. |

---

## 🗂️ Project Structure

```text
cli_agent/
├── agent                         # Shell launcher (activates venv & forwards caller's CWD)
├── README.md                     # Project documentation
└── agent-cli/
    ├── main.py                   # Entry point
    ├── cli.py                    # REPL orchestrator, task verification loop, session continuity
    ├── agent.py                  # Executor conversation loop, infinite-loop guard, failure classifier
    ├── plan.py                   # Pydantic schemas (Plan, Task, VerifyStep) & PLAN.json CRUD
    ├── tasks.py                  # Task verification runner (command & none modes)
    ├── prompts.py                # Dynamic Planner & Executor prompt builders
    ├── config.py                 # Loads and merges .agent.yaml with defaults
    ├── .agent.yaml               # Provider, model, and limit settings
    ├── .mcp.yaml                 # External MCP server definitions
    ├── requirements.txt          # Python dependencies
    ├── memory/
    │   ├── AGENT.md              # Auto-updated timestamped project memory
    │   └── sessions.db           # SQLite session history
    ├── providers/
    │   ├── __init__.py           # Provider factory (get_provider, get_planner_provider)
    │   ├── base.py               # Abstract BaseProvider interface
    │   ├── anthropic.py          # Native Anthropic SDK provider (with ephemeral prompt caching)
    │   ├── bedrock.py            # AWS Bedrock Converse API provider
    │   └── openai_compat.py      # Unified provider for Groq, DeepSeek, Sarvam, Google, OpenRouter, OpenAI
    ├── skills/                   # Domain-specific SKILL.md playbooks
    │   ├── agent-meta/
    │   ├── celery/
    │   ├── drf-api-design/
    │   ├── fastapi/
    │   ├── git-workflow/
    │   ├── pdf-processing/
    │   ├── python/
    │   ├── react/
    │   └── sqlalchemy/
    └── tools/
        ├── __init__.py           # Tool registry, path sanitizer, and dispatcher
        ├── schemas.py            # JSON tool schemas for LLM tool-use
        ├── mcp_bridge.py         # Thread-safe async-to-sync MCP client bridge
        ├── sandbox_ops.py        # Docker container & Squid proxy lifecycle + bash execution
        ├── squid.conf            # Squid proxy ACL configuration for the Docker sandbox
        ├── file_ops.py           # File read/write/replace & ripgrep search
        ├── git_ops.py            # Whitelisted git tool with safety checks
        ├── memory_ops.py         # Directory scanner & vector indexing helpers
        ├── rag/                  # Modular Hybrid Code RAG package (AST chunker, store, settings)
        ├── session_ops.py        # SQLite session persistence
        ├── skills_ops.py         # Skill discovery and loader
        └── web_ops.py            # Tavily web search integration
```

---

## 🔌 Adding a New LLM Provider

1. **OpenAI-Compatible APIs:** Add your provider's `base_url` and API key env var to `_PROVIDER_CONFIG` in `agent-cli/providers/openai_compat.py`, and include its name in `agent-cli/providers/__init__.py`.
2. **Custom APIs (like AWS Bedrock):** Create a new file in `agent-cli/providers/` inheriting from `BaseProvider` (`send`, `raw_send`, `has_tool_calls`, `get_tool_calls`, `format_tool_result`, `get_text`, `append_assistant_message`, `append_tool_results`), and register it in `providers/__init__.py`.

---

## 🔐 Security & Safety Guardrails

- **Network-Restricted Docker Sandbox:** `sandbox_ops.py` creates an `--internal` Docker network (`agent-internal-net`) where the `agent-sandbox` container can only reach the internet through `agent-proxy` (Squid ACLs in `tools/squid.conf`).
- **Git Destructive Flag Blocking:** Both the `git` tool (`git_ops.py`) and a `/usr/local/bin/git` wrapper injected inside the Docker container block `--force` and `-f` flags.
- **Hallucinated Path Sanitizer:** `_sanitize_paths()` in `tools/__init__.py` intercepts common LLM training-data paths (`/workspace`, `/mnt`, `/app`, `/tmp/project`) and redirects them to your real working directory.
- **Infinite Tool-Call Loop Detection:** `agent.py` tracks consecutive `(tool_name, args)` signatures and aborts immediately if a model repeats the exact same failing call twice.
