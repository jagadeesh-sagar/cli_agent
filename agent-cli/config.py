from dataclasses import dataclass, field
from pathlib import Path
import yaml


CONFIG_PATH = Path(__file__).parent / ".agent.yaml"

# ── default values──────────────
DEFAULTS = {
    "model": "claude-haiku-4-5-20251001",
    "provider": "anthropic",
    "max_tool_calls": 15,
    "max_shutdown_calls": 5,
    "db_path": "sessions.db",
    "project_notes": "AGENT.md",
    "max_tokens": 1024,
    "max_tokens_tool": 4096,
    "max_history_calls": 10
}


@dataclass
class AgentConfig:
    model: str
    provider: str
    max_tool_calls: int
    max_shutdown_calls: int
    db_path: str
    project_notes: str
    max_tokens: int
    max_tokens_tool: int
    max_history_calls:int


def load_config() -> AgentConfig:
    """Read .agent.yaml and merge with defaults."""
    data = {}

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
    else:
        print(f"⚠️  Warning: {CONFIG_PATH} not found — using built-in defaults.")

    # Merge: YAML values override defaults
    merged = {**DEFAULTS, **data}

    return AgentConfig(
        model=merged["model"],
        provider=merged["provider"],
        max_tool_calls=int(merged["max_tool_calls"]),
        max_shutdown_calls=int(merged["max_shutdown_calls"]),
        db_path=merged["db_path"],
        project_notes=merged["project_notes"],
        max_tokens=int(merged["max_tokens"]),
        max_tokens_tool=int(merged["max_tokens_tool"]),
        max_history_calls=int(merged['max_history_calls'])
    )

cfg = load_config()
