import sqlite3
from datetime import datetime

DB_PATH='sessions.db'

def init_db():
    con=sqlite3.connect(DB_PATH)
    con.execute("""
      CREATE TABLE IF NOT EXISTS sessions(
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp  TEXT NOT NULL,
        prompt     TEXT NOT NULL,
        summary    TEXT ,
        tools_used TEXT            
        )
        """
    )

    con.commit()
    con.close()

def save_session(prompt:str,summary:str,tools_used:list[str]):
    con=sqlite3.connect(DB_PATH)
    con.execute(
        """
            INSERT INTO sessions (timestamp,prompt,summary,tools_used) VALUES(?,?,?,?)""",
            (datetime.now().isoformat(),prompt,summary,",".join(tools_used))

    )
    con.commit()
    con.close()

    return "Session saved."

def get_recent_sessions(limit:int=5)->str:
    con=sqlite3.connect(DB_PATH)
    rows=con.execute(
        "SELECT timestamp,prompt,summary from sessions ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()

    con.close()
    
    result = []
    for ts, prompt, summary in rows:
        result.append(f"[{ts[:10]}] {prompt}\n  → {summary}")
    return "\n\n".join(result)

def search_sessions(keyword: str) -> str:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        """SELECT timestamp, prompt, summary FROM sessions 
           WHERE prompt LIKE ? OR summary LIKE ?
           ORDER BY id DESC""",
        (f"%{keyword}%", f"%{keyword}%")
    ).fetchall()
    con.close()

    if not rows:
        return f"No sessions found for '{keyword}'."
    
    result = []
    for ts, prompt, summary in rows:
        result.append(f"[{ts[:10]}] {prompt}\n  → {summary}")
    return "\n\n".join(result)
