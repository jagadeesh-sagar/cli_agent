# 🤖 CLI Agent

> An autonomous AI coding assistant powered by Claude (Anthropic) that reads, writes, and edits files on your local machine — right from your terminal.

---

## 📖 Overview

**CLI Agent** is a local AI agent that uses Claude's tool-use capabilities to interact with your codebase. Give it a task in plain English, and it will autonomously read files, write code, search your codebase, and save a record of everything it did — all in a loop until the job is done.

It features **persistent session memory** via SQLite so the agent can recall what it worked on in previous runs, and a **project notes system** (`AGENT.md`) that keeps long-running architectural decisions and coding conventions intact across sessions.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Codebase Search** | Uses `ripgrep` to find exact patterns before touching any file |
| 📖 **Smart File Reading** | Chunk-based file reading to minimise token usage |
| ✏️ **Safe File Editing** | `str_replace` for surgical edits; `write_file` for new files |
| 🧠 **Session Memory** | SQLite database stores every session's prompt, summary & tools used |
| 📝 **Project Notes** | `AGENT.md` persists project-level context between sessions |
| 🔁 **Agentic Loop** | Automatically handles multi-step tool calls until the task is complete |
| 🛑 **Shutdown Sequence** | Agent always saves notes & session before exiting |

---

## 🗂️ Project Structure

```
cli_agent/
└── agent-cli/
    ├── main.py               # Entry point — set your task here
    ├── llm.py                # Agentic loop: calls Claude + handles tool use
    ├── tools.py              # Tool definitions (schemas) + implementations
    ├── prompts.py            # System prompt with agent lifecycle rules
    ├── session_management.py # SQLite-backed session save/search/recall
    ├── AGENT.md              # Auto-updated project notes (written by the agent)
    ├── sessions.db           # SQLite database (auto-created)
    ├── requirements.txt      # Python dependencies
    └── .env                  # Your API key (not committed)
```

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10+
- [`ripgrep`](https://github.com/BurntSushi/ripgrep) installed and on your `PATH`
- An [Anthropic API key](https://console.anthropic.com/)

### 2. Clone & Set Up

```bash
git clone <your-repo-url>
cd cli_agent

# Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r agent-cli/requirements.txt
```

### 3. Configure API Key

Create a `.env` file inside `agent-cli/`:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Run the Agent

Edit the task in `agent-cli/main.py`:

```python
messages = [
    {"role": "user", "content": "In ./my_file.py, add a binary search function"}
]
```

Then run:

```bash
cd agent-cli
python main.py
```

The agent will autonomously search, read, write, and document everything it does.

---

## 🛠️ Available Tools

The agent has access to the following tools:

| Tool | Purpose |
|---|---|
| `read_file` | Read entire file contents |
| `read_file_section` | Read a specific line range (token-efficient) |
| `list_dir` | List all files in a directory |
| `write_file` | Write/create a file |
| `str_replace` | Surgically replace a unique string in a file |
| `append_file` | Append content to an existing file |
| `search_codebase` | Search for patterns using ripgrep |
| `read_project_notes` | Load `AGENT.md` for project context |
| `write_project_notes` | Append new notes to `AGENT.md` |
| `get_recent_sessions` | Recall last N sessions from SQLite |
| `search_sessions` | Search past sessions by keyword |
| `save_session` | Persist the current session on shutdown |

---

## 🧠 How the Agent Loop Works

```
User Prompt
    │
    ▼
Claude (claude-haiku-4-5) ──► tool_use? ──YES──► Execute Tool ──► Back to Claude
    │                                                                     ▲
    │ (stop_reason = end_turn)                                            │
    ▼                                                            (up to 15 calls)
Final Response
    │
    ▼
Shutdown Sequence
  ├─ write_project_notes (if new knowledge gained)
  └─ save_session (always)
```

- The loop runs until `stop_reason == "end_turn"` or 15 tool calls are exhausted.
- A second **shutdown loop** (max 5 calls) runs after every task to persist knowledge.

---

## ⚙️ Configuration

| Setting | Location | Default |
|---|---|---|
| Claude Model | `llm.py` | `claude-haiku-4-5-20251001` |
| Max Tool Calls | `llm.py` | `15` |
| Max Shutdown Calls | `llm.py` | `5` |
| DB Path | `session_management.py` | `sessions.db` |
| Project Notes | `tools.py` | `./AGENT.md` |

---

## 📦 Dependencies

```
anthropic       # Claude API client
python-dotenv   # Load .env API key
```

> **Optional**: Install `ripgrep` for codebase search support.
> Ubuntu/Debian: `sudo apt install ripgrep`
> macOS: `brew install ripgrep`

---

## 🔐 Security Notes

- Your `.env` file (containing the API key) is listed in `.gitignore` — **never commit it**.
- The agent can read and write files on your machine. Point it at project directories you trust.
- Tool call depth is capped at 15 to prevent runaway loops.

## 🗺️ Roadmap

- [ ] Interactive REPL / chat mode
- [ ] Multi-file awareness and project-wide refactoring
- [ ] Support for `run_command` / shell execution tool
- [ ] Web search tool integration
- [ ] Upgrade to Claude Sonnet/Opus for complex tasks
- [ ] YAML-based task config files
- [ ] Token usage tracking and cost estimation

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

---
