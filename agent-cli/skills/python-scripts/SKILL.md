---
name: python-scripts
description: Python scripting patterns — CLI tools, file processing, subprocess, argparse, logging. Use when building standalone Python scripts or CLI tools.
---

# Python Scripts

## Script Template
```python
#!/usr/bin/env python3
"""
Brief description of what this script does.
Usage: python script.py --input data.csv --output out.json
"""
import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",  required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input.exists():
        log.error(f"Input file not found: {args.input}")
        return 1

    log.info(f"Processing {args.input}")
    # ... do work ...

    if not args.dry_run:
        args.output.write_text("result")
        log.info(f"Written to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## File Operations
```python
from pathlib import Path

# Read
text  = Path("file.txt").read_text(encoding="utf-8")
lines = Path("file.txt").read_text().splitlines()
data  = Path("file.json").read_bytes()

# Write
Path("out.txt").write_text("content", encoding="utf-8")
Path("out/dir/file.txt").parent.mkdir(parents=True, exist_ok=True)

# Iterate files
for f in Path("src").rglob("*.py"):   # recursive
    print(f, f.stat().st_size)

# CSV
import csv
with open("data.csv") as f:
    rows = list(csv.DictReader(f))   # list of dicts

# JSON
import json
data = json.loads(Path("data.json").read_text())
Path("out.json").write_text(json.dumps(data, indent=2))
```

## Subprocess
```python
import subprocess

# Simple — raises on error
result = subprocess.run(
    ["git", "log", "--oneline", "-5"],
    capture_output=True, text=True, check=True
)
print(result.stdout)

# With shell (avoid when possible — injection risk)
result = subprocess.run("ls -la | grep py", shell=True, capture_output=True, text=True)

# Stream output live
with subprocess.Popen(["python", "long_script.py"],
                      stdout=subprocess.PIPE, text=True) as proc:
    for line in proc.stdout:
        print(line, end="")
```

## Progress + Rich output
```python
from rich.progress import track
from rich.console import Console

console = Console()

for item in track(items, description="Processing..."):
    process(item)

console.print("[bold green]Done![/]")
console.print_json(json.dumps(data))
```

## Error Handling Pattern
```python
class AppError(Exception):
    """Base error with exit code."""
    def __init__(self, msg: str, code: int = 1):
        super().__init__(msg)
        self.code = code

def main() -> int:
    try:
        run()
        return 0
    except AppError as e:
        log.error(str(e))
        return e.code
    except KeyboardInterrupt:
        log.info("Interrupted")
        return 130
```

## Rules
- Always `if __name__ == "__main__": sys.exit(main())` — never bare calls
- Return int exit codes from `main()` — 0 = success, nonzero = failure
- Use `Path` not `os.path` — cleaner API, works on all platforms
- Log with `logging`, not `print`, in library code
- Use `check=True` in subprocess.run unless you need to handle errors manually
