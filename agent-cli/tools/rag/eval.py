import sys
import time

from .retrieve import hybrid_retrieve
from .search import _engine, _root, index_project

CASES = [
    ("Where is MAX_RETRIES_PER_TASK defined?", "cli.py"),
    ("MCPBridge._server_loop", "tools/mcp_bridge.py"),
    ("how does the docker sandbox restrict internet access", "tools/sandbox_ops.py"),
    ("which function validates the planner JSON output", "plan.py"),
    ("classify_failure rate limit backoff", "agent.py"),
    ("load the content of a skill markdown file", "tools/skills_ops.py"),
    ("infinite loop guard for repeated tool calls", "agent.py"),
    ("sanitize hallucinated paths like /workspace", "tools/__init__.py"),
]


def main(path: str = "."):
    print(index_project(path))
    eng = _engine(_root(path))
    h1 = hk = 0
    for q, expected in CASES:
        t = time.time()
        res = hybrid_retrieve(q, eng["store"], eng["vec"], 5)
        dt = (time.time() - t) * 1000
        files = [r["path"] for r in res]
        ok1 = bool(files) and files[0].endswith(expected)
        okk = any(f.endswith(expected) for f in files)
        h1 += ok1
        hk += okk
        mark = "✅" if ok1 else ("🟡" if okk else "❌")
        top = f"{files[0]} L{res[0]['start']} via {'+'.join(res[0]['sources'])}" if res else "-"
        print(f"{mark} {dt:6.0f}ms  {q!r}\n      top: {top}")
    n = len(CASES)
    print(f"\nhit@1 = {h1}/{n}   hit@5 = {hk}/{n}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")