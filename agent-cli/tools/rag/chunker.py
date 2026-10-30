import ast
import re
from dataclasses import dataclass
from pathlib import Path

from . import settings as S

@dataclass
class Chunk:
    path:str
    start:int 
    end:int 
    kind:str
    symbol:str
    text:str

@dataclass
class Symbol:
    name:str
    qualname:str
    kind:str
    path:str
    start:int 
    end:int 
    signature:str 

_FUNCS=(ast.FunctionDef,ast.AsyncFunctionDef)

def chunk_file(path:Path,text:str)->tuple[list[Chunk],list[Symbol]]:
    if path.suffix==".py":
        try:
            return _chunk_python(str(path),text)
        except SyntaxError:
            pass
    lines=text.splitlines()
    symbols=_regex_symbols(str(path),lines) if path.suffix in S.REGEX_SYMBOL_EXTS else []
    return _window_chunks(str(path),lines,1,len(lines),"window",""),symbols

def _windows(start:int,end:int):
    step=max(1,S.WINDOW_LINES-S.WINDOW_OVERLAP)
    s=start
    while s<=end:
        e=min(s+S.WINDOW_LINES-1,end)
        yield s,e
        if e==end:
            break
        s+=step


def _window_chunks(path,lines,start,end,kind,symbol):
    out=[]
    for s,e in _windows(start,end):
        body="\n".join(lines[s-1:e])
        if body.strip():
            out.append(Chunk(path,s,e,kind,symbol,body))
    return out 


def _spank_chunks(path,lines,start,end,kind,symbol):
    if end-start+1<=S.MAX_CHUNK_LINES:
        body="\n".join(lines[start-1:end])
        return [Chunk(path,start,end,kind,symbol,body)] if body.strip() else []
    return _window_chunks(path,lines,start,end,kind,symbol)


def _start(node) -> int:
    return min([d.lineno for d in getattr(node, "decorator_list", [])] + [node.lineno])


def _sig(lines,node)->str:
    return lines[node.lineno-1].strip()[:200]

def _chunk_python(path:str,text:str):
    tree=ast.parse(text)
    lines=text.splitlines()
    chunks:list[Chunk]=[]
    symbols:list[Symbol]=[]
    covered=[False]*(len(lines)+2)

    def take(start,end,kind,symbol):
        chunks.extend(_spank_chunks(path,lines,start,end,kind,symbol))
        for i in range(start,end+1):
            covered[i]=True

    for node in tree.body:
        if isinstance(node,_FUNCS):
            s,e=_start(node),node.end_lineno
            symbols.append(Symbol(node.name,node.name,"function",path,s,e,_sig(lines, node)))
            take(s,e,"function",node.name)

        elif isinstance(node,ast.ClassDef):
            s,e=_start(node),node.end_lineno
            symbols.append(Symbol(node.name,node.name,"class",path,s,e,_sig(lines,node)))
            methods=[n for n in node.body if isinstance(n,_FUNCS)]
            for m in methods:
                symbols.append(Symbol(m.name,f"{node.name}.{m.name}","method",path,
                                      _start(m),m.end_lineno,_sig(lines,m)))
            if e-s+1<=S.MAX_CHUNK_LINES or not methods:
                take(s, e, "class", node.name)
            else:
                first = _start(methods[0])
                if first > s:
                    take(s, first - 1, "class", node.name)
                for m in methods:
                    take(_start(m), m.end_lineno, "method", f"{node.name}.{m.name}")
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    symbols.append(Symbol(t.id, t.id, "variable", path, node.lineno,
                                          node.end_lineno, lines[node.lineno - 1].strip()[:200]))
    i=1
    while i<=len(lines):
        if covered[i]:
            i+=1
            continue
        j=i
        while j+1<=len(lines) and not covered[j+1]:
            j+=1
        chunks.extend(_spank_chunks(path,lines,i,j,"module",""))
        i=j+1

    chunks.sort(key=lambda c:c.start)
    return chunks,symbols


_PATTERNS = [
    (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)"), "function"),
    (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)"), "class"),
    (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?"
                r"(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)"), "function"),
    (re.compile(r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"), "function"),
    (re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)"), "function"),
    (re.compile(r"^\s*(?:export\s+)?(?:pub\s+)?(?:struct|enum|trait|interface|type)\s+([A-Za-z_]\w*)"), "type"),
    (re.compile(r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\)\s*\{"), "function"),
]


def _regex_symbols(path: str, lines: list[str]) -> list[Symbol]:
    out = []
    for i, line in enumerate(lines, 1):
        for rx, kind in _PATTERNS:
            m = rx.match(line)
            if m:
                out.append(Symbol(m.group(1), m.group(1), kind, path, i,
                                  min(i + 40, len(lines)), line.strip()[:200]))
                break
    return out