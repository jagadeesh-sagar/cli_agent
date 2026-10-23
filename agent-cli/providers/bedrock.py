"""
providers/bedrock.py — AWS Bedrock API provider.

Uses the AWS Bedrock Converse API to interact with Claude and other Bedrock models.
Requires `boto3` to be installed and standard AWS credentials configured in the environment.

Set in .agent.yaml:
  provider: bedrock
  model: anthropic.claude-3-5-sonnet-20240620-v1:0
"""

import os
import json
import logging
from dataclasses import dataclass
import requests
from dotenv import load_dotenv

load_dotenv()

from .base import BaseProvider
from config import cfg
from prompts import get_system_prompt

logger = logging.getLogger(__name__)

@dataclass
class ToolCall:
    id: str
    name: str
    input: dict

def _to_bedrock_tools(anthropic_tools: list) -> list:
    bedrock_tools = []
    for tool in anthropic_tools:
        bedrock_tools.append({
            "toolSpec": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "inputSchema": {
                    "json": tool["input_schema"]
                }
            }
        })
    return bedrock_tools

def _convert_messages_to_bedrock(messages: list) -> list:
    bedrock_msgs = []
    for m in messages:
        if m["role"] == "user":
            if isinstance(m["content"], str):
                bedrock_msgs.append({"role": "user", "content": [{"text": m["content"]}]})
            elif isinstance(m["content"], list):
                blocks = []
                for b in m["content"]:
                    if b.get("type") == "tool_result":
                        blocks.append({
                            "toolResult": {
                                "toolUseId": b["tool_use_id"],
                                "content": [{"text": b["content"]}]
                            }
                        })
                    else:
                        blocks.append({"text": str(b.get("text", b.get("content", "")))})
                bedrock_msgs.append({"role": "user", "content": blocks})
        elif m["role"] == "assistant":
            if isinstance(m["content"], str):
                bedrock_msgs.append({"role": "assistant", "content": [{"text": m["content"]}]})
            elif isinstance(m["content"], list):
                blocks = []
                for b in m["content"]:
                    if b.get("type") == "text":
                        blocks.append({"text": b["text"]})
                    elif b.get("type") == "tool_use":
                        blocks.append({
                            "toolUse": {
                                "toolUseId": b["id"],
                                "name": b["name"],
                                "input": b["input"]
                            }
                        })
                bedrock_msgs.append({"role": "assistant", "content": blocks})
    return bedrock_msgs

class BedrockProvider(BaseProvider):
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.api_key = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
        
        if not self.api_key:
            raise ValueError("AWS_BEARER_TOKEN_BEDROCK is missing. Please set it in your .env file.")

    def _call_converse(self, model: str, payload: dict) -> dict:
        from urllib.parse import quote
        url = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{quote(model, safe='')}/converse"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        res = requests.post(url, json=payload, headers=headers, timeout=120)
        if not res.ok:
            raise RuntimeError(
                f"Bedrock HTTP Error {res.status_code} (model={model}, region={self.region}): {res.text}"
            )
        return res.json()

    def send(self, messages: list, tools: list):
        try:
            bedrock_msgs = _convert_messages_to_bedrock(messages)
            bedrock_tools = _to_bedrock_tools(tools)
            
            payload = {
                "messages": bedrock_msgs,
                "system": [{"text": get_system_prompt()}],
            }
            if bedrock_tools:
                payload["toolConfig"] = {"tools": bedrock_tools}
                
            return self._call_converse(cfg.model, payload)
        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            raise RuntimeError(f"Bedrock API call failed: {e}")

    def raw_send(self, system_prompt: str, user_message: str) -> str:
        model = getattr(cfg, "planner_model", None) or cfg.model
        try:
            payload = {
                "messages": [{"role": "user", "content": [{"text": user_message}]}],
                "system": [{"text": system_prompt}]
            }
            response = self._call_converse(model, payload)
            return response["output"]["message"]["content"][0]["text"]
        except Exception as e:
            logger.error(f"raw_send failed: {e}")
            raise RuntimeError(f"raw_send failed: {e}")

    def has_tool_calls(self, response) -> bool:
        content_blocks = response["output"]["message"].get("content", [])
        for block in content_blocks:
            if "toolUse" in block:
                return True
        return False

    def get_tool_calls(self, response) -> list[ToolCall]:
        calls = []
        content_blocks = response["output"]["message"].get("content", [])
        for block in content_blocks:
            if "toolUse" in block:
                tu = block["toolUse"]
                calls.append(ToolCall(id=tu["toolUseId"], name=tu["name"], input=tu["input"]))
        return calls

    def format_tool_result(self, tool: ToolCall, result: str) -> dict:
        return {
            "type": "tool_result",
            "tool_use_id": tool.id,
            "content": result if isinstance(result, str) else json.dumps(result),
        }

    def get_text(self, response) -> str:
        texts = []
        content_blocks = response["output"]["message"].get("content", [])
        for block in content_blocks:
            if "text" in block:
                texts.append(block["text"])
        return "\n".join(texts)

    def append_assistant_message(self, messages, response):
        content_blocks = response["output"]["message"].get("content", [])
        blocks = []

        for b in content_blocks:
            if "text" in b:
                blocks.append({"type": "text", "text": b["text"]})
            elif "toolUse" in b:
                tu = b["toolUse"]
                blocks.append({
                    "type": "tool_use",
                    "id": tu["toolUseId"],
                    "name": tu["name"],
                    "input": tu["input"],
                })

        messages.append({"role": "assistant", "content": blocks})
        
    def append_tool_results(self, messages: list, tool_results: list):
        messages.append({
            "role": "user",
            "content": tool_results
        })

    def user_shutdown_message(self, messages: list, content: str):
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": content}]
        })
