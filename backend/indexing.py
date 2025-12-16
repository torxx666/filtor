import os
import json
import traceback
from datetime import datetime
from loguru import logger
from database import get_db_connection
from analyse.forensic import DataExfiltrationAnalyzer

# Global indexing state
indexing_state = {
    "status": "idle",
    "current": 0,
    "total": 0,
    "current_file": "",
    "message": ""
}

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

def extract_text_content(filepath, mime_type):
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
        import textract
        # textract returns bytes, we need to decode
        raw_text = textract.process(filepath)
        
        try:
            text = raw_text.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = raw_text.decode('cp1255')
            except:
                text = raw_text.decode('utf-8', errors='ignore')
                
        return text
        
    except Exception as e:
        logger.warning(f"Text extraction failed for {filepath}: {e}")
        return ""

def process_indexing(folder_path):
    global indexing_state
    
    logger.info(f"Starting indexing for folder: {folder_path}")
    analyzer = DataExfiltrationAnalyzer()
    
    try:
        # --- PHASE 1: DISCOVERY & TEXT EXTRACTION (FAST) ---
        indexing_state["status"] = "scanning"
        indexing_state["message"] = "Phase 1: Fast Indexing & Text Extraction..."
        
        all_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                all_files.append(os.path.join(root, file))
        
        indexing_state["total"] = len(all_files)
        logger.info(f"Found {len(all_files)} files to index")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Reset DB (as requested by reload logic)
        c.execute("DELETE FROM docs_fts")
        c.execute("DELETE FROM docs")
        c.execute("DELETE FROM files")
        conn.commit()

        processed_count = 0
        file_ids_map = {} # Map path -> db_id for phase 2
        
        for filepath in all_files:
            filename = os.path.basename(filepath)
            indexing_state["current"] = processed_count + 1
            indexing_state["current_file"] = f"Indexing: {filename}"
            
            try:
                # Basic Stats
                stat = os.stat(filepath)
                size = stat.st_size
                ctime = datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                ext = os.path.splitext(filename)[1].lower()
                
                # Basic Mime (fast)
                import mimetypes
                mime_type, _ = mimetypes.guess_type(filepath)
                if not mime_type: mime_type = "application/octet-stream"
                
                # Insert Initial Record (Risk PENDING)
                c.execute('''
                    INSERT INTO files (filename, path, size, type, created_at, true_type, has_text, info, details, risk_level, risk_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    filename, filepath, size, ext, ctime, mime_type, 0, 
                    "Indexing...", "{}", "PENDING", 0.0
                ))
                file_id = c.lastrowid
                file_ids_map[filepath] = file_id
                
                # Extract Text IMMEDIATELY
                text = extract_text_content(filepath, mime_type)
                
                if text and len(text.strip()) > 0:
                    c.execute("INSERT INTO docs (file_id, content, page_num) VALUES (?, ?, ?)", (file_id, text, 0))
                    doc_id = c.lastrowid
                    c.execute("INSERT INTO docs_fts (rowid, content) VALUES (?, ?)", (doc_id, text))
                    c.execute("UPDATE files SET has_text = 1 WHERE id = ?", (file_id,))
                
            except Exception as e:
                logger.error(f"Phase 1 error on {filepath}: {e}")
            
            processed_count += 1
            if processed_count % 10 == 0:
                conn.commit()
                
        conn.commit()
        logger.success(f"Phase 1 Complete: {processed_count} files indexed for search")
        
        # --- PHASE 2: DEEP FORENSIC ANALYSIS (SLOW) ---
        indexing_state["message"] = "Phase 2: Deep Forensic Analysis..."
        processed_count = 0
        
        for filepath in all_files:
            filename = os.path.basename(filepath)
            indexing_state["current"] = processed_count + 1
            indexing_state["current_file"] = f"Analyzing: {filename}"
            
            file_id = file_ids_map.get(filepath)
            if not file_id: continue
            
            try:
                # Run Analyzer
                forensic_res = analyzer.analyze_file(filepath)
                
                # Serialize details
                details_json = json.dumps({
                    'risk_level': forensic_res.risk_level,
                    'risk_score': forensic_res.risk_score,
                    'detections': forensic_res.detections,
                    'metadata': forensic_res.metadata,
                    'recommendations': forensic_res.recommendations
                })
                
                # Info summary
                info_parts = []
                if forensic_res.is_sensitive:
                    info_parts.append(f"RISK: {forensic_res.risk_level} ({forensic_res.risk_score})")
                if forensic_res.detections.get('sensitive_content', {}).get('total_matches', 0) > 0:
                    info_parts.append("Sensitive Content")
                    
                info = " | ".join(info_parts) if info_parts else "Clean"
                
                # Update DB with Risk Info
                true_type = forensic_res.detections.get('file_type', {}).get('mime_type', 'Unknown')
                
                c.execute('''
                    UPDATE files 
                    SET info = ?, details = ?, risk_level = ?, risk_score = ?, true_type = ?
                    WHERE id = ?
                ''', (info, details_json, forensic_res.risk_level, forensic_res.risk_score, true_type, file_id))
                
            except Exception as e:
                logger.error(f"Phase 2 error on {filepath}: {e}")
                
            processed_count += 1
            if processed_count % 5 == 0:
                conn.commit()
                
        conn.commit()
        conn.close()
        
        indexing_state["status"] = "idle"
        indexing_state["message"] = "Analysis finished!"
        logger.success(f"Phase 2 Complete: Deep analysis done")
        
    except Exception as e:
        logger.error(f"Indexing fatal error: {e}")
        traceback.print_exc()
        indexing_state["status"] = "error"
        indexing_state["message"] = f"Error during indexing: {str(e)}"
