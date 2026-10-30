import re
import sqlite3
import threading
from pathlib import Path

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PARTS = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "in", "on", "for",
    "and", "or", "not", "with", "as", "at", "by", "it", "its", "this", "that", "these",
    "those", "from", "how", "what", "where", "which", "who", "why", "when", "does", "do",
    "did", "can", "could", "should", "would", "me", "my", "we", "our", "you", "your",
    "show", "find", "get", "use", "used", "using", "code", "file", "files", "function",
    "functions", "method", "methods", "class", "classes", "defined", "define",
    "implementation", "implemented", "work", "works", "about", "there", "any", "all",
    "into", "then", "than", "so", "if", "else", "per", "handle", "handled", "logic",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
    path TEXT PRIMARY KEY, mtime REAL, size INTEGER, sha TEXT);
CREATE TABLE IF NOT EXISTS chunks(
    id TEXT PRIMARY KEY, path TEXT, start_line INTEGER, end_line INTEGER,
    kind TEXT, symbol TEXT, text TEXT);
CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
CREATE TABLE IF NOT EXISTS symbols(
    name TEXT, qualname TEXT, kind TEXT, path TEXT,
    start_line INTEGER, end_line INTEGER, signature TEXT);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_symbols_qual ON symbols(qualname COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_symbols_path ON symbols(path);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    id UNINDEXED, path, symbol, body, tokenize='unicode61');
"""

def split_identifier(ident:str)->list[str]:
    return [p.lower() for piece in ident.split("_") for p in _PARTS.findall(piece)]

def expand_for_index(text:str)->str:
    extra=set()
    for ident in set(IDENT.findall(text)):
        parts=split_identifier(ident)
        if len(parts)>1:
            extra.update(parts)
    return " ".join(sorted(extra))

def build_fts_query(query:str)->str:
    terms=set()
    for ident in IDENT.findall(query):
        low=ident.lower()
        if low in STOPWORDS or len(low)<2:
            continue 
        terms.add(low)
        terms.update(p for p in split_identifier(ident) if p not in STOPWORDS and len(p)>1)

    return " OR ".join(f'"{t}"' for t in sorted(terms))

class Store:
    def __init__(self,db_path: Path):
        self._lock=threading.RLock()
        self.con=sqlite3.connect(str(db_path),check_same_thread=False)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.executescript(SCHEMA)

    def file_state(self)-> dict:
        with self._lock:
            return {p: (m,s,h) for p,m,s,h in 
                    self.con.execute("SELECT path,mtime,size ,sha FROM files")
                    }

    def touch_file(self,path,mtime,size):
        with self._lock,self.con:
            self.con.execute("UPDATE files SET mtime=? ,size=? WHERE path=?",(mtime,size,path))

    def delete_file(self,path):
        with self._lock,self.con:
            self.con.execute("DELETE FROM chunks WHERE path=?",(path,))
            self.con.execute("DELETE FROM chunks_fts WHERE path=?",(path,))
            self.con.execute("DELETE FROM symbols WHERE path=?",(path,))
            self.con.execute("DELETE FROM files WHERE path=?",(path,))
            
    def add_file(self,path,mtime,size,sha,chunks_with_ids,symbols):
        with self._lock,self.con:
            self.con.executemany(
                "INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?)",
                [(cid,c.path,c.start,c.end,c.kind,c.symbol,c.text) for cid ,c in chunks_with_ids])
            self.con.executemany(
                "INSERT INTO chunks_fts(id,path,symbol,body) VALUES (?,?,?,?)",
                [(cid,c.path,
                  f"{c.symbol} {' '.join(split_identifier(c.symbol))}",
                     f"{c.text}\n{expand_for_index(c.text)}")
                                   for cid, c in chunks_with_ids])
            self.con.executemany(
                        "INSERT INTO symbols VALUES (?,?,?,?,?,?,?)",
                        [(s.name, s.qualname, s.kind, s.path, s.start, s.end, s.signature) for s in symbols])
            self.con.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?)", (path, mtime, size, sha))

    def bm25(self,query:str,limit:int)->list[str]:
        q=build_fts_query(query)
        if not q:
            return []
        with self._lock:
            try:
                rows=self.con.execute(
                  "SELECT id, bm25(chunks_fts, 0.0, 2.0, 6.0, 1.0) AS score FROM chunks_fts "
                    "WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?",(q,limit)).fetchall()
            except sqlite3.OperationalError:
                return []

        return [r[0] for r in rows]

    def find_symbols(self,names,limit:int=20):
        out=[]
        with self._lock:
            for n in names:
                rows=self.con.execute(
                    "SELECT name, qualname, kind, path, start_line, end_line, signature FROM symbols "
                    "WHERE name = ? COLLATE NOCASE OR qualname = ? COLLATE NOCASE LIMIT ?",
                    (n,n,limit)).fetchall()
                out.extend((n,r) for r in rows)
                
        return out 

    def chunks_covering(self, path, start, end, limit: int = 2) -> list[str]:
        with self._lock:
            return [r[0] for r in self.con.execute(
                "SELECT id FROM chunks WHERE path=? AND start_line<=? AND end_line>=? "
                "ORDER BY start_line LIMIT ?", (path, end, start, limit))]

    def chunks_for_path(self, name, limit: int = 5) -> list[str]:
        with self._lock:
            return [r[0] for r in self.con.execute(
                "SELECT id FROM chunks WHERE path=? OR path LIKE ? ORDER BY start_line LIMIT ?",
                (name, f"%/{name}", limit))]

    def get_chunks(self, ids) -> dict:
        if not ids:
            return {}
        q = ("SELECT id, path, start_line, end_line, kind, symbol, text FROM chunks "
             f"WHERE id IN ({','.join('?' * len(ids))})")
        with self._lock:
            return {r[0]: {"id": r[0], "path": r[1], "start": r[2], "end": r[3],
                           "kind": r[4], "symbol": r[5], "text": r[6]}
                    for r in self.con.execute(q, list(ids))}