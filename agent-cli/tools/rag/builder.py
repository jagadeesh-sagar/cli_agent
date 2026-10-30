from collections import defaultdict
from pathlib import Path

from . import settings as S 

LANG = {".py": "python", ".js": "javascript", ".jsx": "jsx", ".ts": "typescript", ".tsx": "tsx",
        ".go": "go", ".rs": "rust", ".sh": "bash", ".sql": "sql", ".md": "markdown",
        ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".html": "html", ".css": "css",
        ".java": "java", ".c": "c", ".cpp": "cpp", ".toml": "toml"}

def _merge(spans: list[dict])-> list[dict]:
    merged=[]
    for h in sorted(spans,key=lambda h: h["start"]):
        label={h["symbol"]} if h["symbol"] else set()
        if merged and h["start"] <=merged[-1]["end"]+3:
            m=merged[-1]
            m["end"]=max(m["end"],h["end"])
            m["labels"] |=label
            m["sources"]|=set(h["sources"])
        else:
            merged.append({"start":h["start"],"end":h["end"],"labels":label,
                           "sources":set(h["sources"]),"text":h["text"]})
    return merged


def build_context(query:str,hits:list[dict],root:Path)->str:
    if not hits:
        return (f'No relevant code found for "{query}".'
                f"Try other keywords (exact function/class names work best).")

    by_file = defaultdict(list)
    for h in hits:
        by_file[h["path"]].append(h)
    file_order = list(dict.fromkeys(h["path"] for h in hits))

    blocks, used = [], 0
    for path in file_order:
        try:
            lines = (Path(root) / path).read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = None
        for m in _merge(by_file[path]):
            body = lines[m["start"] - 1:m["end"]] if lines else m["text"].splitlines()
            width = len(str(m["end"]))
            numbered = "\n".join(f"{str(m['start'] + i).rjust(width)} | {line}"
                                 for i, line in enumerate(body))
            label = ", ".join(sorted(m["labels"])) or "module code"
            header = (f"### {path}  (lines {m['start']}-{m['end']} · {label} · "
                      f"found by {'+'.join(sorted(m['sources']))})")
            block = f"{header}\n```{LANG.get(Path(path).suffix, '')}\n{numbered}\n```"
            if used + len(block) > S.CONTEXT_CHAR_BUDGET:
                remaining = S.CONTEXT_CHAR_BUDGET - used
                if remaining > 400:
                    blocks.append(block[:remaining] +
                                  "\n... (truncated — use read_file_section for the rest)\n```")
                used = S.CONTEXT_CHAR_BUDGET
                break
            blocks.append(block)
            used += len(block)
        if used >= S.CONTEXT_CHAR_BUDGET:
            break

    head = f'Code search results for: "{query}"  ({len(blocks)} snippets, {len(file_order)} files)\n'
    return head + "\n\n".join(blocks)