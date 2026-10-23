'''
here mcp library uses async but all my code is sync soo we use these file handle my sync calls by converting to async

Your code calls ──►  connect() / call_tool() / disconnect()   ← normal functions
                         │  _run_sync() hands the job to the background thread
                         
                    _connect / _call_tool / _disconnect / _server_loop   ← async, background thread
                         │
                        
                    npx mcp-server-github (separate program)

=>read-only helpers: get_tool_schemas, get_prompt_description, has_tool
=>these just read the self.tools dict, so they need no async at all


'''

import asyncio
import concurrent.futures
import os
import threading
import yaml
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()


CONNECT_TIMEOUT = 120
CALL_TIMEOUT = 60

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None


def _ensure_loop():
    global _loop, _thread
    if _loop is not None and _loop.is_running():
        return
    _loop = asyncio.new_event_loop()
    _thread = threading.Thread(target=_loop.run_forever, daemon=True)
    _thread.start()


def _run_sync(coro, timeout: float = CALL_TIMEOUT):
    _ensure_loop()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise TimeoutError(f"MCP operation timed out after {timeout}s")


class MCPBridge:
    def __init__(self):
        self.servers = {}
        self.tools = {}
        self.capabilities = {}
        self._server_tasks = {}
        self._exit_events = {}
        self._connect_errors = {}

    def __str__(self):
        return f"<MCPBridge(servers={len(self.servers)}, tools={len(self.tools)})>"

    async def _server_loop(self, name: str, command: str, args: list[str], description: str,
                           env: Optional[dict[str, str]], ready_event: asyncio.Event):
        connected = False
        try:
            server_params = StdioServerParameters(command=command, args=args, env=env)
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.list_tools()

                    self.servers[name] = {
                        "session": session,
                        "command": command,
                        "args": args,
                    }

                    for tool in response.tools:
                        full_name = f"{name}__{tool.name}"
                        self.tools[full_name] = {
                            "server": name,
                            "original_name": tool.name,
                            "session": session,
                            "schema": {
                                "name": full_name,
                                "description": tool.description or "",
                                "input_schema": tool.input_schema,
                            },
                        }

                    self.capabilities[name] = {"description": description}
                    print(f"[MCP] Connected '{name}' ({len(response.tools)} tools)")

                    exit_event = asyncio.Event()
                    self._exit_events[name] = exit_event
                    connected = True
                    ready_event.set()

                    await exit_event.wait()

        except asyncio.CancelledError:
            raise
        except BaseException as e:
            if connected:
                print(f"[MCP] Server '{name}' error: {e}")
            else:
                self._connect_errors[name] = e
        finally:
            self.servers.pop(name, None)
            self.tools = {k: v for k, v in self.tools.items() if v["server"] != name}
            self.capabilities.pop(name, None)
            self._exit_events.pop(name, None)
            self._server_tasks.pop(name, None)
            if connected:
                print(f"[MCP] Disconnected '{name}'")
            ready_event.set()

    async def _connect(self, name: str, command: str, args: list[str], description: str,
                       env: Optional[dict[str, str]] = None):
        if name in self.servers:
            raise ValueError(f"MCP server '{name}' is already connected")

        self._connect_errors.pop(name, None)
        ready_event = asyncio.Event()
        task = asyncio.create_task(
            self._server_loop(name, command, args, description, env, ready_event)
        )
        self._server_tasks[name] = task

        try:
            await ready_event.wait()
        except asyncio.CancelledError:
            task.cancel()
            raise

        error = self._connect_errors.pop(name, None)
        if error is not None:
            raise RuntimeError(f"{type(error).__name__}: {error}") from error
        if name not in self.servers:
            raise RuntimeError(f"Failed to connect to MCP server '{name}'")

    async def _call_tool(self, tool_name: str, args: dict) -> str:
        if tool_name not in self.tools:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

        tool = self.tools[tool_name]
        result = await tool["session"].call_tool(tool["original_name"], arguments=args)

        texts = []
        for block in result.content:
            texts.append(block.text if hasattr(block, "text") else str(block))
        output = "\n".join(texts) if texts else "(no output from MCP tool)"

        if getattr(result, "isError", False):
            return f"TOOL_ERROR: MCP {tool_name}: {output}"
        return output

    async def _disconnect(self, name: str):
        event = self._exit_events.get(name)
        task = self._server_tasks.get(name)
        if event:
            event.set()
        if task:
            await task

    async def _disconnect_all(self):
        for name in list(self._server_tasks.keys()):
            await self._disconnect(name)

    def connect(self, name: str, command: str, args: list[str],
                description: str, env: Optional[dict[str, str]] = None):
        _run_sync(self._connect(name, command, args, description, env), timeout=CONNECT_TIMEOUT)

    def call_tool(self, tool_name: str, args: dict) -> str:
        return _run_sync(self._call_tool(tool_name, args), timeout=CALL_TIMEOUT)

    def disconnect(self, name: str):
        _run_sync(self._disconnect(name))

    def disconnect_all(self):
        _run_sync(self._disconnect_all())

    def get_server_tools(self, server_name: str) -> list[dict]:
        results = []
        for tool_name, tool in self.tools.items():
            if tool["server"] == server_name:
                results.append({
                    "name": tool_name,
                    "description": tool["schema"]["description"].split(".")[0] + ".",
                })
        return results

    def get_tool_schemas(self, tool_names: list[str]) -> list[dict]:
        return [self.tools[name]["schema"] for name in tool_names if name in self.tools]

    def get_all_schemas(self) -> list[dict]:
        return [tool["schema"] for tool in self.tools.values()]

    def get_prompt_description(self) -> str:
        if not self.servers:
            return ""

        lines = ["MCP SERVERS (external tool servers):"]
        for name, info in self.capabilities.items():
            lines.append(f"  - {name}: {info['description']}")

            tool_names = [tn for tn, t in self.tools.items() if t["server"] == name]
            shown = tool_names[:10]
            remaining = len(tool_names) - len(shown)
            tools_str = ", ".join(shown)
            if remaining > 0:
                tools_str += f" (+{remaining} more)"
            lines.append(f"    Tools: {tools_str}")

        return "\n".join(lines)

    def has_tool(self, name: str) -> bool:
        return name in self.tools


def create_mcp_bridge() -> MCPBridge:
    bridge = MCPBridge()
    mcp_conf_path = Path(__file__).parent.parent / ".mcp.yaml"

    try:
        with open(mcp_conf_path, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("[MCP] No .mcp.yaml found — starting without MCP servers.")
        return bridge

    if not config or not config.get("mcp_servers"):
        return bridge

    for server in config["mcp_servers"]:
        env = server.get("env")
        if env:
            env = {key: os.path.expandvars(value) for key, value in env.items()}

        try:
            bridge.connect(
                name=server["name"],
                command=server["command"],
                args=server.get("args", []),
                description=server.get("description", ""),
                env=env,
            )
        except Exception as e:
            print(f"[MCP] Failed to connect '{server['name']}': {e}")

    return bridge


if __name__ == "__main__":
    bridge = create_mcp_bridge()
    print(bridge)
    print(bridge.get_prompt_description())
    print(f"Total tools: {len(bridge.tools)}")

    if bridge.tools:
        first_tool = list(bridge.tools.keys())[0]
        print(f"\nFirst tool schema: {bridge.get_tool_schemas([first_tool])}")

    bridge.disconnect_all()
