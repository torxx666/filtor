from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import json
import threading
from loguru import logger

# Import from new modules
from database import init_db, get_db_connection
from indexing import process_indexing, indexing_state, detect_file_changes

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Configure loguru
logger.add("backend.log", rotation="10 MB")



app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()} - Body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Must specify exact origin when using credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
UPLOAD_DIR = "/data"  # Matches docker-compose volume: ./incoming:/data
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize DB on startup
init_db()

@app.get("/")
def read_root():
    return {"message": "Filtor Pro Backend API"}


class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
async def login(credentials: LoginRequest, background_tasks: BackgroundTasks):
    # Simple demo auth
    if not (
        (credentials.username == "admin" and credentials.password == "GrosRelou22!!") or
        (credentials.username == "demo" and credentials.password == "demo")
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info(f"Login successful for user: {credentials.username}")
    
    # Auto-scan trigger (Request #3)
    AUTO_SCAN_ON_LOGIN = True
    
    if AUTO_SCAN_ON_LOGIN:
        if indexing_state["status"] == "idle":
            # Check for changes before triggering
            if detect_file_changes(UPLOAD_DIR):
                logger.info("Auto-scan: Changes detected (or DB empty), triggering indexing...")
                background_tasks.add_task(process_indexing, UPLOAD_DIR, mode="FAST")
            else:
                logger.info("Auto-scan: No file changes detected, skipping scan.")
        else:
            logger.info("Auto-scan: Indexing already in progress, skipping trigger")
            
    return {"status": "ok", "message": "Login successful"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    return {"info": f"file '{file.filename}' saved at '{file_location}'"}

@app.post("/load")
async def load(background_tasks: BackgroundTasks, mode: str = "DEEP"):
    if indexing_state["status"] == "scanning":
        logger.warning("Scan already in progress")
        return JSONResponse(status_code=400, content={"detail": "Scan already in progress"})
    
    # Start background task
    logger.info(f"Starting background indexing ({mode}) for {UPLOAD_DIR}")
    background_tasks.add_task(process_indexing, UPLOAD_DIR, mode=mode)
    
    return {"status": "started", "message": "Indexing started in background"}

@app.get("/status")
def get_status():
    return indexing_state

@app.get("/files")
def get_files(risk_level: str = None):
    logger.info(f"Fetching files (risk_level={risk_level})")
    conn = get_db_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM files"
    params = []
    
    if risk_level and risk_level != "All":
        query += " WHERE risk_level = ?"
        params.append(risk_level)
    
    # Order by risk score descending by default
    query += " ORDER BY risk_score DESC, id DESC"
    
    files = c.execute(query, params).fetchall()
    conn.close()
    logger.success(f"Returning {len(files)} files")
    return {"files": [dict(f) for f in files]}

@app.get("/export-db")
def export_db():
    db_path = "leak.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database not found")
    return FileResponse(path=db_path, filename="leak.db", media_type='application/x-sqlite3')

@app.post("/import-db")
async def import_db(file: UploadFile = File(...)):
    if not file.filename.endswith('.db'):
        raise HTTPException(status_code=400, detail="File must be .db")
    
    # Backup current? (Optional, skipped for simplicity)
    
    # Overwrite
    with open("leak.db", "wb+") as f:
        shutil.copyfileobj(file.file, f)
        
    # Re-init logic if needed, or just rely on file replacement
    # Trigger re-index might be needed if user wants to sync files, but import usually implies restoration
    return {"message": "Database imported successfully"}

@app.get("/search")
def search_files(q: str, mode: str = "default"):
    logger.info(f"Search query: '{q}' (mode: {mode})")
    conn = get_db_connection()
    c = conn.cursor()
    
    if mode == "regex":
        # Regex search mode for quick filters
        import re
        pattern = re.compile(q, re.IGNORECASE)
        
        results = c.execute("""
            SELECT DISTINCT f.*, d.content AS doc_content, d.src FROM files f
            LEFT JOIN docs d ON d.file_id = f.id
        """).fetchall()
        
        # Build response with regex matches and snippets
        response = []
        for row in results:
            file_dict = dict(row)
            content = file_dict.pop('doc_content', None)
            src = file_dict.pop('src', 'content') # Default to 'content' if missing
            file_dict['src'] = src
            
            # Special handling for metadata
            if src == 'metadata' and content:
                try:
                    file_dict['metadata'] = json.loads(content)
                    logger.debug(f"Metadata loaded for {file_dict.get('filename')}")
                except Exception as e:
                    logger.error(f"Failed to parse metadata JSON: {e}")
                    file_dict['metadata'] = None
            
            # Check for matches in content, filename, or path
            match_found = False
            snippet = None
            
            # 1. Check filename/path
            if pattern.search(file_dict.get('filename', '')) or pattern.search(file_dict.get('path', '')):
                match_found = True
            
            # 2. Check content
            if content:
                # For metadata, search in the raw JSON string
                matches = list(pattern.finditer(content))
                if matches:
                    match_found = True
                    
                    if src != 'metadata':
                        # Get first match for snippet
                        match = matches[0]
                        matched_text = match.group(0)
                        pos = match.start()
                        
                        # Extract snippet around match
                        start = max(0, pos - 100)
                        end = min(len(content), pos + len(matched_text) + 100)
                        snippet = content[start:end]
                        
                        # Highlight the match in the snippet (relative position)
                        relative_pos = pos - start
                        snippet = (
                            snippet[:relative_pos] + 
                            f"<mark>{snippet[relative_pos:relative_pos + len(matched_text)]}</mark>" + 
                            snippet[relative_pos + len(matched_text):]
                        ).strip()
                    
                    # removed ellipsis per user request
                    
                    file_dict['match_count'] = len(matches)
            
            if match_found:
                file_dict['snippet'] = snippet
                response.append(file_dict)
        
        conn.close()
        logger.info(f"Found {len(response)} results")
        return response
    else:
        # Normal LIKE search
        results = c.execute("""
            SELECT DISTINCT f.*, d.content AS doc_content, d.src FROM files f
            LEFT JOIN docs d ON d.file_id = f.id
            WHERE d.content LIKE ? OR f.filename LIKE ? OR f.path LIKE ?
            ORDER BY f.risk_score DESC
        """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    
        # Build response with snippets
        response = []
        for row in results:
            file_dict = dict(row)
            content = file_dict.pop('doc_content', None)
            src = file_dict.pop('src', 'content') # Default to 'content' if missing
            file_dict['src'] = src
            
            if src == 'metadata' and content:
                logger.debug("Inside metadata block")
                try:
                    file_dict['metadata'] = json.loads(content)
                    logger.debug("JSON parse success")
                except Exception as e:
                    logger.error(f"JSON parse error: {e}")
                    file_dict['metadata'] = None

            # Extract snippet around the match
            if content and q.lower() in content.lower():
                # For metadata, we still want to indicate a match, but maybe not show a snippet if we show the DB
                if src == 'metadata':
                     file_dict['snippet'] = None # UI will handle metadata display
                else:
                    # Find position of query in content (case-insensitive)
                    pos = content.lower().find(q.lower())
                    # Extract 100 chars before and after
                    start = max(0, pos - 100)
                    end = min(len(content), pos + len(q) + 100)
                    snippet = content[start:end]
                    
                    # Highlight the match
                    relative_pos = pos - start
                    # Get the actual matched text with original case
                    matched_text = content[pos:pos + len(q)]
                    snippet = (
                        snippet[:relative_pos] + 
                        f"<mark>{matched_text}</mark>" + 
                        snippet[relative_pos + len(q):]
                    ).strip()
                
                    # removed ellipsis per user request
                    
                    file_dict['snippet'] = snippet
            else:
                file_dict['snippet'] = None
            
            response.append(file_dict)
        
        conn.close()
        logger.info(f"Found {len(response)} results")
        return response

@app.get("/recent")
def get_recent(mode: str = "default"):
    # Return empty for now - could implement recent searches later
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)