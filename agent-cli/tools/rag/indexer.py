import hashlib
import os
from pathlib import Path

from . import settings as S
from .chunker import chunk_file
from .models import embed

def iter_source_files(root:Path):
    for dirpath,dirnames,filenames in os.walk(root):
        dirnames[:]=[d for d in dirnames if d not in S.SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            p=Path(dirpath)/name
            if name in S.SKIP_FILES or p.suffix.lower() not in S.CODE_EXTS:
                continue
            try:
                st=p.stat()
            except OSError:
                continue
            if 0<st.st_size<= S.MAX_FILE_BYTES:
                yield p,st

def _embed_text(c)->str:
    return f"file: {c.path}\n{c.kind}:{c.symbol or '-'}\n{c.text}"[:S.EMBED_CHAR_LIMIT]


def update_index(root: Path,store,vec,force:bool=False)->dict:
    root=Path(root).resolve()
    known=store.file_state()
    seen,changed=set(),[]

    for p,st in iter_source_files(root):
        rel=p.relative_to(root).as_posix()
        seen.add(rel)
        old=known.get(rel)
        if not force and old and old[0]==st.st_mtime and old[1]==st.st_size:
            continue
        try:
            data=p.read_bytes()
        except OSError:
            continue
        sha=hashlib.sha1(data).hexdigest()
        if not force and old and old[2] ==sha:
            store.touch_file(rel,st.st_mtime,st.st_size)
            continue
        try:
            text=data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        changed.append((rel,st,sha,text))


    removed=[r for r in known if r not in seen]
    for rel in removed:
        store.delete_file(rel)
        vec.delete_file(rel)

    total_chunks=0
    for n,(rel,st,sha,text) in enumerate(changed,1):
        chunks,symbols=chunk_file(Path(rel),text)
        ids = [f"{rel}:{i}:{c.start}-{c.end}" for i, c in enumerate(chunks)]
        store.delete_file(rel)
        vec.delete_file(rel)
        if chunks:
            vec.add(
                    ids,
                    embed([_embed_text(c) for c in chunks]),
                    [
                        {
                            "path": c.path,
                            "start": c.start,
                            "end": c.end,
                            "kind": c.kind,
                            "symbol": c.symbol
                        }
                        for c in chunks
                    ]
                )
            
        store.add_file(rel, st.st_mtime, st.st_size, sha, list(zip(ids, chunks)), symbols)
        total_chunks += len(chunks)
        if len(changed) > 50 and n % 50 == 0:
            print(f"[RAG] indexed {n}/{len(changed)} files…")
    
    return {
        "files_indexed": len(changed),
        "files_removed": len(removed),
        "chunks": total_chunks,
        "total_files": len(seen)
    }


    
