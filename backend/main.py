from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, subprocess, os, tempfile
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = "/data"
DB_PATH = "/db/leak.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path, lineno, content, tokenize='unicode61');")
    return conn

def extract_pdf_text(pdf_path):
    """Extrait TOUT le texte d'un PDF arXiv avec pdftotext + fallback OCR"""
    try:
        # pdftotext = extraction texte principale (pour PDF texte comme arXiv)
        result = subprocess.run(["pdftotext", pdf_path, "-"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.splitlines()
    except:
        pass

    # Fallback OCR avec tesseract (pour scans)
    try:
        result = subprocess.run(["tesseract", pdf_path, "stdout", "-l", "eng"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.splitlines()
    except:
        pass

    return []

@app.post("/load")
def load():
    conn = get_conn()
    conn.execute("DELETE FROM docs;")
    conn.commit()
    conn.close()

    total_lines = 0
    conn = get_conn()
    cur = conn.cursor()
    batch = []

    # 1. Fichiers non-PDF (TXT, ZIP, RAR, DOCX) avec rga
    for root, dirs, files in os.walk(DATA_PATH):
        for file in files:
            if file.endswith(('.txt', '.log', '.csv', '.json', '.xml')):
                fullpath = os.path.join(root, file)
                relpath = os.path.relpath(fullpath, DATA_PATH)
                with open(fullpath, 'r', errors='ignore') as f:
                    for lineno, line in enumerate(f, 1):
                        line = line.strip()
                        if line:
                            batch.append((f"{file} ← {relpath}", lineno, line))
                            total_lines += 1
                            if len(batch) >= 50000:
                                cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
                                conn.commit()
                                batch.clear()

    # 2. PDF (spécial pour arXiv)
    for root, dirs, files in os.walk(DATA_PATH):
        for file in files:
            if file.endswith('.pdf'):
                fullpath = os.path.join(root, file)
                relpath = os.path.relpath(fullpath, DATA_PATH)
                lines = extract_pdf_text(fullpath)
                for lineno, line in enumerate(lines, 1):
                    line = line.strip()
                    if line:
                        batch.append((f"{file} ← {relpath}", lineno, line))
                        total_lines += 1
                        if len(batch) >= 50000:
                            cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
                            conn.commit()
                            batch.clear()

    if batch:
        cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
        conn.commit()
    conn.close()
    return {"status": "ok", "indexed": total_lines}

@app.get("/search")
def search(q: str = ""):
    conn = get_conn()
    cur = conn.cursor()

    if not q.strip():
        cur.execute("SELECT path, lineno, content FROM docs ORDER BY rowid DESC LIMIT 20")
    else:
        # ÉCHAPPEMENT ULTRA-SÉCURISÉ POUR FTS5
        # On entoure TOUT entre guillemets → FTS5 traite ça comme phrase exacte
        # Et on échappe les guillemets internes
        escaped = q.replace('\\', '\\\\').replace('"', '\\"')
        fts5_query = f'"{escaped}"'   # ← C’EST LA CLÉ

        cur.execute(f"""
            SELECT path, lineno, content, 
                   highlight(docs, 2, '<b class="bg-yellow-300 text-black font-bold">', '</b>') as hl 
            FROM docs 
            WHERE content MATCH ? 
            ORDER BY rank 
            LIMIT 200
        """, (fts5_query,))

    rows = cur.fetchall()
    conn.close()
    return [{"filename": r["path"], "lineno": r["lineno"], "highlight": r["hl"] or r["content"]} for r in rows]