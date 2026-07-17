"""
providers/openai_compat.py — OpenAI-compatible provider.

Works with ANY OpenAI-compatible API by just changing base_url + model:
  - Groq          base_url="https://api.groq.com/openai/v1"
  - DeepSeek      base_url="https://api.deepseek.com"
  - Together AI   base_url="https://api.together.xyz/v1"
  - OpenRouter    base_url="https://openrouter.ai/api/v1"
  - OpenAI        base_url=None  (default)

Set in .agent.yaml:
  provider: sarvam
  model: sarvam-105b

Set in .env:
  SARVAM_API_KEY=gsk_...
"""

import json
import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

from .base import BaseProvider
from config import cfg
from prompts import SYSTEM_PROMPT

load_dotenv()
logger = logging.getLogger(__name__)


# ── Tool call wrapper ──────────────────────────────────────────────────────────
# agent.py accesses tool.name, tool.input, tool.id  (Anthropic SDK shape).
# OpenAI returns tool_call.function.name, tool_call.function.arguments (str), tool_call.id
# This dataclass normalises OpenAI → the shape agent.py already expects.

@dataclass
class ToolCall:
    id: str
    name: str
    input: dict   # always a dict, never a raw JSON string


# ── Schema converter ───────────────────────────────────────────────────────────
# Your schemas.py uses Anthropic format.  OpenAI needs a different shape.
# This runs once per send() call — it's cheap.

def _to_openai_tools(anthropic_tools: list) -> list:
    """Convert Anthropic-format tool schemas → OpenAI function schema format."""
    openai_tools = []
    for tool in anthropic_tools:
        # strip Anthropic-only fields like cache_control before sending to OpenAI
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
            }
        })
    return openai_tools


# ── Provider map — which env key + base_url each named provider uses ──────────
_PROVIDER_CONFIG = {
    "groq":     {"env_key": "GROQ_API_KEY",     "base_url": "https://api.groq.com/openai/v1"},
    "deepseek": {"env_key": "DEEPSEEK_API_KEY",  "base_url": "https://api.deepseek.com"},
    "together": {"env_key": "TOGETHER_API_KEY",  "base_url": "https://api.together.xyz/v1"},
    "openrouter":{"env_key": "OPENROUTER_API_KEY","base_url": "https://openrouter.ai/api/v1"},
    "sarvam":   {"env_key": "SARVAM_API_KEY",    "base_url": "https://api.sarvam.ai/v1"},
    "openai":   {"env_key": "OPENAI_API_KEY",    "base_url": None},   # uses default
}


class OpenAICompatProvider(BaseProvider):
    """
    Single provider class that handles any OpenAI-compatible API.
    The `provider` value in .agent.yaml picks which endpoint to hit.
    """

    def __init__(self, provider_name: str):
        """
        Args:
            provider_name: one of the keys in _PROVIDER_CONFIG
                           (e.g. "groq", "deepseek", "openai")
        """
        config = _PROVIDER_CONFIG.get(provider_name)
        if config is None:
            raise ValueError(
                f"Unknown OpenAI-compatible provider '{provider_name}'. "
                f"Known: {list(_PROVIDER_CONFIG.keys())}"
            )

        api_key  = os.getenv(config["env_key"])
        base_url = config["base_url"]

        if not api_key:
            raise EnvironmentError(
                f"Missing env var '{config['env_key']}' for provider '{provider_name}'. "
                f"Add it to your .env file."
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"OpenAICompatProvider initialised: {provider_name} → {base_url or 'openai default'}")

    # ── Core API call ──────────────────────────────────────────────────────────

    def send(self, messages: list, tools: list) -> object:
        """
        Send messages to the API.

        Key differences from Anthropic:
         - system prompt is prepended as a {"role": "system"} message
         - tool schemas must be converted from Anthropic → OpenAI format
         - we do NOT mutate the caller's `messages` list
        """
        try:
            full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
            openai_tools  = _to_openai_tools(tools) if tools else None

            response = self.client.chat.completions.create(
                model=cfg.model,
                max_tokens=cfg.max_tokens,
                messages=full_messages,
                tools=openai_tools,
                parallel_tool_calls=False,  # one tool at a time → more reliable format
            )
            return response

        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise RuntimeError(f"API call failed: {e}")

    # ── Tool call detection ────────────────────────────────────────────────────

    def has_tool_calls(self, response) -> bool:
        return response.choices[0].finish_reason == "tool_calls"

    def get_tool_calls(self, response) -> list[ToolCall]:
        """
        OpenAI quirk: tool_call.function.arguments is a JSON *string*, not a dict.
        We parse it here so the caller always gets a dict.
        """
        raw_calls = response.choices[0].message.tool_calls or []
        return [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                input=json.loads(tc.function.arguments),  # string → dict
            )
            for tc in raw_calls
        ]

    # ── Result formatting ──────────────────────────────────────────────────────

    def format_tool_result(self, tool: ToolCall, result: str) -> dict:
        return {
            "role": "tool",
            "tool_call_id": tool.id,
            "content": result if isinstance(result, str) else json.dumps(result),
        }

    # ── Text extraction ────────────────────────────────────────────────────────

    def get_text(self, response) -> str:
        return response.choices[0].message.content or ""

    # ── Message appending ──────────────────────────────────────────────────────

    def append_assistant_message(self, messages: list, response) -> None:
        """
        For OpenAI, the assistant message must include tool_calls if any were made,
        otherwise the API will reject the next turn (it needs the full call→result pair).
        """
        msg = response.choices[0].message
        assistant_entry = {"role": "assistant", "content": msg.content}

        if msg.tool_calls:
            # include the raw tool_calls so the API can match them to tool results
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,  # keep as string
                    },
                }
                for tc in msg.tool_calls
            ]

        messages.append(assistant_entry)

    def append_tool_results(self, messages: list, tool_results: list) -> None:
        messages.extend(tool_results)  

    def user_shutdown_message(self, messages: list, content: str) -> None:
        messages.append({"role": "user", "content": content})
