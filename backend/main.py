# backend/main.py – VERSION FINALE 100% FONCTIONNELLE 2025
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, os, subprocess, shutil
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_PATH = os.getenv("DATA_PATH", "/data")
DB_PATH = os.getenv("DB_PATH", "/db/leak.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

class Result(BaseModel):
    filename: str
    lineno: int
    line: str
    highlight: str

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path, lineno, content, tokenize='unicode61');")
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA cache_size = -2000000")
    conn.commit()
    return conn

@app.post("/load")
def load():
    # 1. Vide l’ancien index
    conn = get_conn()
    conn.execute("DELETE FROM docs;")
    conn.commit()
    conn.close()

    # 2. Lance rga sur tout le dossier /data (extracted + incoming)
    proc = subprocess.Popen([
        "rga", "--line-number", "--no-messages", ".*", DATA_PATH
    ], stdout=subprocess.PIPE, text=True, bufsize=1)

    conn = get_conn()
    cur = conn.cursor()
    batch = []
    total = 0

    for line in proc.stdout:
        if ":" not in line: continue
        parts = line.strip().split(":", 2)
        if len(parts) < 3: continue
        fullpath, lineno, content = parts
        filename = os.path.basename(fullpath)
        relpath = os.path.relpath(fullpath, DATA_PATH)
        display_path = f"{filename} ← {relpath}" if relpath != filename else filename
        batch.append((display_path, int(lineno), content))
        total += 1

        if len(batch) >= 50_000:
            cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
            conn.commit()
            batch.clear()

    if batch:
        cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
        conn.commit()
    conn.close()
    return {"status": "loaded", "lines_indexed": total}

@app.get("/reindex")
def reindex():
    return load()   # même chose que /load

@app.get("/search")
def search(q: str = "", limit: int = 200):
    conn = get_conn()
    cur = conn.cursor()

    if not q.strip():
        # Recherche vide → 10 ou 200 derniers ajoutés
        cur.execute(f"""
            SELECT path, lineno, content,
                   snippet(docs, 2, '<b style="background:yellow;color:black">', '</b>', '...', 64) as hl
            FROM docs ORDER BY rowid DESC LIMIT ?
        """, (limit,))
    else:
        cur.execute(f"""
            SELECT path, lineno, content,
                   highlight(docs, 2, '<b style="background:yellow;color:black">', '</b>') as hl
            FROM docs WHERE content MATCH ? ORDER BY rank LIMIT ?
        """, (q, limit))

    results = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in results:
        r["highlight"] = r.get("hl") or r["content"]
        r["filename"] = r["path"]
        del r["hl"], r["path"], r["content"]
    return results

@app.get("/recent")
def recent():
    return search("", 10)