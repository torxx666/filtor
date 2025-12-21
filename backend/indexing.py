import os
import json
import traceback
from datetime import datetime
from loguru import logger
from database import get_db_connection
from analyse.deep_forensics import DeepFileAnalyzer, DeepAnalysisResult
from analyse.meta_video import extract_all_metadata

# Global indexing state
indexing_state = {
    "status": "idle",
    "current": 0,
    "total": 0,
    "current_file": "",
    "message": "",
    "mode": "FAST"
}

def calculate_risk_score(result: DeepAnalysisResult):
    """Calculates a numeric risk score (0-100) from deep analysis findings"""
    score = 0.0
    
    # Issues and Indicators
    score += len(result.security_issues) * 20
    score += len(result.risk_indicators) * 5
    
    # Specific high-risk detections
    if result.hidden_content.get('polyglot'):
        score += 40
    
    if 'text' in result.findings:
        secrets = result.findings['text'].get('secrets_found', [])
        score += len(secrets) * 30
    
    if 'pdf' in result.findings:
        if result.findings['pdf'].get('has_javascript'): score += 20
        
    if 'office' in result.findings:
        if result.findings['office'].get('has_macros'): score += 30
        
    return min(100.0, score)

def get_risk_level(score: float):
    if score >= 70: return "CRITICAL"
    if score >= 50: return "HIGH"
    if score >= 25: return "MEDIUM"
    return "LOW"

class Files:
    """Helper to detect file types (legacy)"""
    @staticmethod
    def detect_legacy_type(filepath):
        # ... logic ...
        # Since we use forensic.py effectively, this might be redundant, 
        # but let's keep the basic mapping for 'true_type' if forensic fails or for fallback
        ext = os.path.splitext(filepath)[1].lower()
        if ext in ['.zip', '.rar', '.7z']: return "ZIP Archive"
        if ext == '.jar': return "JAR Archive"
        return "Unknown"

def extract_text_content(filepath, mime_type, mode="DEEP"):
    """Robust text extraction with Hebrew support and PDF fallback"""
    text = ""
    try:
        # 1. Text files - try UTF-8 then CP1255 (Hebrew)
        if mime_type.startswith('text/') or mime_type in ['application/sql', 'application/json', 'application/xml']:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                try:
                    with open(filepath, 'r', encoding='cp1255') as f:
                        return f.read()
                except:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
                        
        # 2. PDF/Office - Use textract but handle Hebrew/Encoding better
        
        # FAST MODE OPTIMIZATION: SKIP Textract (OCR) for non-text heavy files if requested
        # User specified: "ne vas chercher ... avec tesseract en mode DEEP ya tt"
        # Implies: FAST mode should NOT use Tesseract.
        # Textract uses Tesseract for images/scanned PDFs.
        
        if mode == "FAST":
            # For images, skip extraction entirely in FAST mode
            if mime_type.startswith('image/'):
                logger.info(f"FAST MODE: Skipping OCR for image {filepath}")
                return ""
                
            # For PDFs, try to extract text ONLY (no OCR fallback)
            # textract doesn't easily allow disabling OCR via method="pdfminer" only without modification,
            # but we can try basic pdf extraction or just skip if it seems like a scan.
            # For now, let's proceed but maybe we should use pypdf directly for speed?
            # Keeping textract but noting potential OCR risk.
            pass

        # 3. Check for unsupported binary extensions BEFORE importing/using textract
        # Textract fails hard on .exe, .dll, etc.
        binary_exts = ['.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.db', '.sqlite']
        if any(filepath.lower().endswith(ext) for ext in binary_exts):
             return ""
        
        # Also skip if mime is strictly octet-stream and not one of our handled types
        if mime_type == 'application/octet-stream':
             return ""

        import textract
        # textract returns bytes, we need to decode
        try:
             # STRICT FAST MODE LOGIC: Prevent Tesseract usage completely
             if mode == "FAST":
                 ext_lower = os.path.splitext(filepath)[1].lower()
                 
                 # Only whitelist specific Safe extensions for FAST extraction
                 # PDF (via pdfminer), Office (docx, etc.), HTML/XML if fell through
                 safe_fast_exts = ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.odt']
                 
                 if ext_lower not in safe_fast_exts:
                     # Skip everything else in FAST mode (Images, Unknowns, etc.) to guarantee no OCR
                     return ""
                     
                 # SPECIAL HANDLING FOR PDF TO AVOID OCR FALLBACK
                 if ext_lower == '.pdf':
                     # Force pdfminer to ensure no Tesseract fallback
                     raw_text = textract.process(filepath, method='pdfminer')
                 else:
                     # Standard processing for Office documents (xml parsing)
                     raw_text = textract.process(filepath)
             else:
                 # DEEP MODE: Allow default behavior (including OCR for images)
                 raw_text = textract.process(filepath)

            
             try:
                 text = raw_text.decode('utf-8')
             except UnicodeDecodeError:
                 try:
                     text = raw_text.decode('cp1255')
                 except:
                     text = raw_text.decode('utf-8', errors='ignore')
        except Exception as tx_err:
             # Only log warning if it's NOT an .exe (which we tried to catch above)
             if not filepath.lower().endswith('.exe'):
                 logger.warning(f"Textract failed ({mode}) on {filepath}: {tx_err}")
             return ""
                
        return text
        
    except Exception as e:
        logger.warning(f"Text extraction failed for {filepath}: {e}")
        return ""

def get_file_diff(folder_path, requested_mode="DEEP"):
    """
    Compares current filesystem with DB to identify changes.
    Also checks if simpler scan needs upgrade (FAST -> DEEP).
    Returns: (to_add, to_update, to_delete, db_files_map)
    """
    # Get DB files
    conn = get_db_connection()
    c = conn.cursor()
    # Check if scan_mode column exists (it should due to init_db but safe to handle old rows gracefully)
    try:
        rows = c.execute("SELECT id, path, size, mtime, scan_mode FROM files").fetchall()
    except:
        # Fallback if column missing in runtime cache somehow
        rows = c.execute("SELECT id, path, size, mtime FROM files").fetchall()
        
    conn.close()
    
    db_files = {}
    for row in rows:
        p = os.path.normpath(row['path'])
        # Handle missing scan_mode (treat as 'unknown' or 'fast' implicitly? safer to assume None)
        mode = row['scan_mode'] if 'scan_mode' in row.keys() else None
        db_files[p] = {'id': row['id'], 'size': row['size'], 'mtime': row['mtime'], 'scan_mode': mode}
        
    # Get Current files
    fs_files = {}
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                stat = os.stat(filepath)
                p = os.path.normpath(filepath)
                fs_files[p] = {'size': stat.st_size, 'mtime': stat.st_mtime, 'abspath': filepath}
            except Exception as e:
                logger.warning(f"Could not stat file {filepath}: {e}")

    to_add = []
    to_update = []
    to_delete = []
    
    # Check Adds and Updates
    for path, stats in fs_files.items():
        if path not in db_files:
            to_add.append(path)
        else:
            db_stats = db_files[path]
            # Check for modification
            is_modified = False
            if stats['size'] != db_stats['size']:
                is_modified = True
            elif db_stats['mtime'] is None or abs(stats['mtime'] - db_stats['mtime']) > 0.001:
                is_modified = True
            
            # Check for Mode Upgrade (FAST -> DEEP)
            # If current DB is FAST, and we request DEEP, we must re-scan.
            # If current DB is DEEP, and we request FAST, no need to re-scan (unless modified).
            needs_upgrade = False
            stored_mode = db_stats.get('scan_mode')
            if requested_mode == "DEEP" and stored_mode != "DEEP":
                 needs_upgrade = True
                 
            if is_modified or needs_upgrade:
                to_update.append(path)
                
    # Check Deletes
    for path in db_files:
        if path not in fs_files:
            to_delete.append(path)
            
    return to_add, to_update, to_delete, db_files

def detect_file_changes(folder_path):
    """
    Checks if there are any changes (wrapper for main.py compatibility).
    """
    try:
        to_add, to_update, to_delete, _ = get_file_diff(folder_path)
        has_changes = bool(to_add or to_update or to_delete)
        if has_changes:
            logger.info(f"Change detection: Found changes (+{len(to_add)}, ~{len(to_update)}, -{len(to_delete)})")
        else:
            logger.info("Change detection: No changes found.")
        return has_changes
    except Exception as e:
        logger.error(f"Change detection failed: {e}")
        return True

def process_indexing(folder_path, mode="DEEP"):
    global indexing_state
    indexing_state["mode"] = mode
    
    logger.info(f"Starting indexing for folder: {folder_path} (mode: {mode})")
    analyzer = DeepFileAnalyzer()
    
    try:
        indexing_state["status"] = "scanning"
        indexing_state["message"] = "Calculating file changes..."
        
        # 1. Calculate Diff
        to_add, to_update, to_delete, db_files_map = get_file_diff(folder_path, requested_mode=mode)
        
        total_changes = len(to_add) + len(to_update) + len(to_delete)
        if total_changes == 0:
            logger.info("No changes detected. consistency check passed.")
            indexing_state["status"] = "idle"
            indexing_state["message"] = "No changes detected."
            return

        logger.info(f"Diff: +{len(to_add)} added, ~{len(to_update)} modified, -{len(to_delete)} deleted")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # 2. Handle Deletions
        if to_delete:
            indexing_state["message"] = f"Cleaning up {len(to_delete)} deleted files..."
            for path in to_delete:
                file_id = db_files_map[path]['id']
                c.execute("DELETE FROM docs_fts WHERE rowid IN (SELECT rowid FROM docs WHERE file_id = ?)", (file_id,))
                c.execute("DELETE FROM docs WHERE file_id = ?", (file_id,))
                c.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
            
        # 3. Process Adds and Updates
        files_to_process = to_add + to_update
        indexing_state["total"] = len(files_to_process)
        
        processed_count = 0
        file_ids_map = {} # Only for currently processed files
        
        # PHASE 1: Text Extraction & Basic Indexing
        indexing_state["message"] = "Phase 1: Updating File Index..."
        
        for p_path in files_to_process:
            # Re-stat file to get fresh info (or use what we had in diff but easier to re-do safely)
            try:
                # We need the original path format if we normalized? 
                # Actually p_path from get_file_diff keys are normalized.
                # But fs_files stored abspath? Let's rely on os.stat again or similar logic.
                # Wait, I need valid abspath.
                # get_file_diff keys are normalized paths.
                # I should probably store abspath in the diff if needed.
                # Let's fix get_file_diff to return abspaths or a dict.
                # Actually, standardizing on os.path.normpath is good, assuming it resolves to same string.
                # Windows paths: c:\\... vs c:/... 
                
                filepath = p_path # It is an absolute path from os.walk -> normpath
                filename = os.path.basename(filepath)
                
                indexing_state["current"] = processed_count + 1
                indexing_state["current_file"] = f"Indexing: {filename}"
                
                # Cleanup existing records if Updating
                if p_path in to_update:
                     fid = db_files_map[p_path]['id']
                     c.execute("DELETE FROM docs_fts WHERE rowid IN (SELECT rowid FROM docs WHERE file_id = ?)", (fid,))
                     c.execute("DELETE FROM docs WHERE file_id = ?", (fid,))
                     c.execute("DELETE FROM files WHERE id = ?", (fid,))
                
                # ... Insert Logic from original ...
                stat = os.stat(filepath)
                size = stat.st_size
                mtime = stat.st_mtime
                ctime = datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                ext = os.path.splitext(filename)[1].lower()
                
                import mimetypes
                mime_type, _ = mimetypes.guess_type(filepath)
                if not mime_type: mime_type = "application/octet-stream"
                
                c.execute('''
                    INSERT INTO files (filename, path, size, type, created_at, true_type, has_text, info, details, risk_level, risk_score, mtime, scan_mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    filename, filepath, size, ext, ctime, mime_type, 0, 
                    "Indexing...", "{}", "PENDING", 0.0, mtime, mode
                ))
                file_id = c.lastrowid
                file_ids_map[filepath] = file_id
                
                # Extract Text/Meta
                text = ""
                src_type = "content"
                
                if mime_type.startswith("video/") or mime_type.startswith("audio/"):
                     try:
                         meta = extract_all_metadata(filepath, depth=mode)
                         if meta:
                             text = json.dumps(meta, indent=2, ensure_ascii=False)
                             src_type = "metadata"
                     except Exception as e:
                         logger.error(f"Media meta error {filename}: {e}")
                else:
                     text = extract_text_content(filepath, mime_type, mode=mode)
                     
                if text and len(text.strip()) > 0:
                    c.execute("INSERT INTO docs (file_id, content, src, page_num) VALUES (?, ?, ?, ?)", (file_id, text, src_type, 0))
                    doc_id = c.lastrowid
                    c.execute("INSERT INTO docs_fts (rowid, content) VALUES (?, ?)", (doc_id, text))
                    c.execute("UPDATE files SET has_text = 1 WHERE id = ?", (file_id,))
                    
                processed_count += 1
                if processed_count % 10 == 0:
                    conn.commit()

            except Exception as e:
                logger.error(f"Phase 1 error on {p_path}: {e}")
                
        conn.commit()
        
        # PHASE 2: Deep Analysis (Only for processed files)
        if not files_to_process:
             # Just deletions handled
             conn.close()
             indexing_state["status"] = "idle"
             indexing_state["message"] = "Cleanup complete."
             return
             
        indexing_state["message"] = "Phase 2: Deep Forensic Analysis..."
        processed_count = 0
        
        for filepath in files_to_process:
            filename = os.path.basename(filepath)
            indexing_state["current"] = processed_count + 1
            indexing_state["current_file"] = f"Analyzing: {filename}"
            
            file_id = file_ids_map.get(filepath)
            if not file_id: continue
            
            try:
                res = analyzer.analyze(filepath, depth=mode)
                
                # Scoring
                risk_score = calculate_risk_score(res)
                risk_level = get_risk_level(risk_score)
                
                details_json = json.dumps({
                    'risk_level': risk_level,
                    'risk_score': risk_score,
                    'detections': {
                        'security_issues': {'indicators': res.security_issues, 'risk_points': len(res.security_issues) * 10},
                        'risk_indicators': {'indicators': res.risk_indicators, 'risk_points': len(res.risk_indicators) * 5},
                        'hidden_content': {'findings': res.hidden_content, 'risk_points': 20 if res.hidden_content.get('polyglot') else 0}
                    },
                    'metadata': {**res.metadata_extracted, 'true_type': res.file_type},
                    'recommendations': res.security_issues
                })
                
                info_parts = []
                if res.security_issues: info_parts.append(f"ISSUES: {len(res.security_issues)}")
                if res.risk_indicators: info_parts.append(f"RISK: {risk_level}")
                info = " | ".join(info_parts) if info_parts else "Clean"
                
                c.execute('''
                    UPDATE files 
                    SET info = ?, details = ?, risk_level = ?, risk_score = ?, true_type = ?, scan_mode = ?
                    WHERE id = ?
                ''', (info, details_json, risk_level, risk_score, res.file_type, mode, file_id))
                
                # FAST MODE STOP
                if mode == "FAST" and risk_score >= 90:
                    logger.warning(f"FAST MODE: Critical risk on {filename}. Stopping.")
                    indexing_state["message"] = f"FAST MODE: Stopped at critical risk ({filename})"
                    conn.commit()
                    conn.close()
                    indexing_state["status"] = "idle"
                    return
                    
            except Exception as e:
                logger.error(f"Phase 2 error on {filepath}: {e}")
                
            processed_count += 1
            if processed_count % 5 == 0:
                conn.commit()
                
        conn.commit()
        conn.close()
        
        indexing_state["status"] = "idle"
        indexing_state["message"] = "Analysis finished!"
        logger.success(f"Deep analysis complete ({len(files_to_process)} files processed)")

    except Exception as e:
        logger.error(f"Indexing fatal error: {e}")
        traceback.print_exc()
        indexing_state["status"] = "error"
        indexing_state["message"] = f"Error during indexing: {str(e)}"
