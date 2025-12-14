from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
import shutil
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, subprocess, os, tempfile, re
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = "/data"
DB_PATH = "/db/leak.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path, lineno, content, tokenize='unicode61');")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            path TEXT,
            type TEXT,
            size INTEGER,
            created_at REAL,
            has_text BOOLEAN,
            info TEXT
        );
    """)
    return conn

def detect_file_type(path):
    """Detects file type using magic numbers (signature) & ZIP inspection"""
    try:
        with open(path, 'rb') as f:
            header = f.read(16)
            
        # 1. ZIP Inspection (Office files are ZIPs)
        if header.startswith(b'PK\x03\x04'):
            try:
                import zipfile
                with zipfile.ZipFile(path, 'r') as z:
                    names = z.namelist()
                    if 'ppt/presentation.xml' in names: return 'Microsoft PowerPoint'
                    if 'word/document.xml' in names: return 'Microsoft Word'
                    if 'xl/workbook.xml' in names: return 'Microsoft Excel'
                    if 'META-INF/MANIFEST.MF' in names: return 'JAR Archive'
            except:
                pass
            return 'ZIP Archive'

        if header.startswith(b'%PDF'): return 'PDF Document'
        if header.startswith(b'Rar!'): return 'RAR Archive'
        if header.startswith(b'\x7fELF'): return 'ELF Executable'
        if header.startswith(b'MZ'): return 'Windows Executable'
        if header.startswith(b'\x89PNG\r\n\x1a\n'): return 'PNG Image'
        if header.startswith(b'\xff\xd8\xff'): return 'JPEG Image'
        if header.startswith(b'GIF8'): return 'GIF Image'
        if header.startswith(b'ID3') or header.startswith(b'\xff\xfb'): return 'MP3 Audio'
        if header.startswith(b'\x25\x21\x50\x53'): return 'PostScript'
        if header.startswith(b'\x1f\x8b'): return 'GZIP Archive'
        if header.startswith(b'SQLi'): return 'SQLite Database'

        # Text checks
        try:
            with open(path, 'r', encoding='utf-8') as f:
                f.read(1024)
            return 'Text File'
        except:
            pass
            
        return 'Unknown Binary'
            
    except:
        return 'Unknown/Error'

def extract_pptx_text(path):
    """Extract text from PPTX slides (XML)"""
    text_content = []
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        
        with zipfile.ZipFile(path, 'r') as z:
            # Find all slides
            slides = [n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
            # Sort likely required (slide1, slide2...) - naive sort is ok-ish
            slides.sort() 
            
            for slide in slides:
                try:
                    xml_content = z.read(slide)
                    root = ET.fromstring(xml_content)
                    # Extract all text (a:t tags usually)
                    # Namespace map might be needed, but naive iter works often
                    slide_text = []
                    for elem in root.iter():
                        if elem.text and elem.text.strip():
                            slide_text.append(elem.text.strip())
                    if slide_text:
                        text_content.append(" ".join(slide_text))
                except:
                    continue
    except Exception as e:
        print(f"PPTX error: {e}")
    return text_content

def extract_docx_text(path):
    """Extract text from DOCX (paragraph based)"""
    text_content = []
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        
        with zipfile.ZipFile(path, 'r') as z:
            xml_content = z.read('word/document.xml')
            root = ET.fromstring(xml_content)
            
            # Iterate over paragraphs
            for elem in root.iter():
                # w:p indicates a paragraph
                if elem.tag.endswith('}p'):
                    para_text = []
                    # Find all texts in this paragraph
                    for node in elem.iter():
                        if node.tag.endswith('}t') and node.text:
                            para_text.append(node.text)
                    
                    if para_text:
                        text_content.append("".join(para_text))
                        
    except Exception as e:
        print(f"DOCX error: {e}")
    return text_content

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

@app.post("/login")
def login():
    return {"status": "ok"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_location = os.path.join(DATA_PATH, file.filename)
    with open(file_location, "wb+") as file_object:
        file_object.write(await file.read())
    return {"info": f"file '{file.filename}' saved at '{file_location}'"}

@app.get("/recent")
def recent(mode: str = "default"):
    return []

@app.get("/files")
def get_files():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT filename, path, type, size, created_at, has_text, info FROM files ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

@app.post("/load")
def load():
    conn = get_conn()
    conn.execute("DELETE FROM docs;")
    conn.execute("DROP TABLE IF EXISTS files;") # Force schema update
    conn.commit()
    conn.close()

    total_lines = 0
    total_files = 0
    conn = get_conn() # Will recreate 'files' table with new schema via get_conn()
    cur = conn.cursor()
    batch = []
    files_batch = []

    # Iterate over ALL files
    for root, dirs, files in os.walk(DATA_PATH):
        for file in files:
            total_files += 1
            fullpath = os.path.join(root, file)
            relpath = os.path.relpath(fullpath, DATA_PATH)
            
            # 1. Metadata
            try:
                stat = os.stat(fullpath)
                size = stat.st_size
                ctime = stat.st_ctime
            except:
                size = 0
                ctime = 0

            # 2. True Type Detection
            true_type = detect_file_type(fullpath)
            has_text = False
            info = ""

            # 3. Text Extraction Logic
            try:
                # PPTX
                if true_type == 'Microsoft PowerPoint':
                    lines = extract_pptx_text(fullpath)
                    if lines:
                        has_text = True
                        info = f"Slides: {len(lines)}"
                        for lineno, line in enumerate(lines, 1):
                            line = line.strip()
                            if line:
                                batch.append((f"{file} \u2190 {relpath}", lineno, line))
                                total_lines += 1
                                if len(batch) >= 50000:
                                    cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
                                    conn.commit()
                                    batch.clear()
                                    
                # DOCX
                elif true_type == 'Microsoft Word':
                    lines = extract_docx_text(fullpath)
                    if lines:
                        has_text = True
                        info = "DOCX"
                        for lineno, line in enumerate(lines, 1):
                            line = line.strip()
                            if line:
                                batch.append((f"{file} \u2190 {relpath}", lineno, line))
                                total_lines += 1
                                if len(batch) >= 50000:
                                    cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
                                    conn.commit()
                                    batch.clear()

                # PDF
                elif true_type == 'PDF Document' or file.lower().endswith('.pdf'):
                    lines = extract_pdf_text(fullpath)
                    if lines:
                        has_text = True
                        info = f"Pages/Blocks: {len(lines)}"
                        for lineno, line in enumerate(lines, 1):
                            line = line.strip()
                            if line:
                                batch.append((f"{file} \u2190 {relpath}", lineno, line))
                                total_lines += 1
                                if len(batch) >= 50000:
                                    cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
                                    conn.commit()
                                    batch.clear()

                # Text Files (Generic)
                elif true_type == 'Text File' or file.lower().endswith(('.txt', '.log', '.csv', '.json', '.xml', '.md', '.ini', '.cfg')):
                    with open(fullpath, 'r', errors='ignore') as f:
                        for lineno, line in enumerate(f, 1):
                            line = line.strip()
                            if line:
                                batch.append((f"{file} \u2190 {relpath}", lineno, line))
                                total_lines += 1
                                has_text = True
                                if len(batch) >= 50000:
                                    cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
                                    conn.commit()
                                    batch.clear()
            
            except Exception as e:
                print(f"Error processing {file}: {e}")
                info = "Error: " + str(e)

            files_batch.append((file, relpath, true_type, size, ctime, has_text, info))


    if batch:
        cur.executemany("INSERT INTO docs VALUES(?, ?, ?)", batch)
    
    if files_batch:
        cur.executemany("INSERT INTO files (filename, path, type, size, created_at, has_text, info) VALUES (?, ?, ?, ?, ?, ?, ?)", files_batch)

    conn.commit()
    conn.close()
    return {"status": "ok", "lines_indexed": total_lines, "files_detected": total_files}

@app.get("/search")
def search(q: str = "", mode: str = "default"):
    conn = get_conn()
    conn.create_function("regexp", 2, lambda expr, item: 1 if item and re.search(expr, item, re.IGNORECASE) else 0)
    cur = conn.cursor()

    rows = []
    if not q.strip():
        cur.execute("SELECT path, lineno, content FROM docs ORDER BY rowid DESC LIMIT 20")
        rows = cur.fetchall()
        return [{"filename": r["path"], "lineno": r["lineno"], "highlight": r["content"]} for r in rows]

    if mode == "regex":
        try:
            # Recherche via REGEXP (scan complet ou partiel), pas d'index FTS possible pour REGEXP pur
            # On limite drastiquement pour la perf ou on assume que c'est ok pour le dataset local
            cur.execute("SELECT path, lineno, content FROM docs WHERE content REGEXP ? LIMIT 200", (q,))
            results = cur.fetchall()
            
            # Highlight manuel en Python pour le mode regex
            formatted = []
            pattern = re.compile(q, re.IGNORECASE)
            for r in results:
                # On highlighte juste la première occurrence pour l'affichage
                def replace_match(m):
                    return f'<b class="bg-yellow-300 text-black font-bold">{m.group(0)}</b>'
                
                hl_content = pattern.sub(replace_match, r["content"])
                formatted.append({
                    "filename": r["path"], 
                    "lineno": r["lineno"], 
                    "highlight": hl_content
                })
            conn.close()
            return formatted
        except Exception as e:
            print(f"Regex error: {e}")
            conn.close()
            return []

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

# EXPORT : Télécharge la base SQLite actuelle
# EXPORT : Télécharge la base SQLite actuelle
@app.get("/export-db")
def export_db():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Base de données non trouvée")
    return FileResponse(
        path=DB_PATH,
        filename="leak.db",
        media_type="application/octet-stream"
    )

# IMPORT : Upload une nouvelle base SQLite (remplace l'ancienne)
@app.post("/import-db")
async def import_db(file: UploadFile = File(...)):
    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="Fichier doit être .db")

    # Sauvegarde temporaire
    temp_path = "/tmp/uploaded.db"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Remplace la base actuelle
    shutil.move(temp_path, DB_PATH)

    # Ré-indexe automatiquement après import (optionnel mais pratique)
    load()

    return {"status": "ok", "message": "Base importée et ré-indexée"}        