import os
import sqlite3
import time
from database import get_db_connection

# Mock setup
def verify_indexing(filename):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if file exists in DB
    file_row = c.execute("SELECT id, path, size, mtime, info, scan_mode, details FROM files WHERE filename LIKE ?", (f"%{filename}%",)).fetchone()
    if not file_row:
        print(f"File {filename} NOT found in DB.")
        conn.close()
        return

    # Map path for Windows verification
    # DB has /data/filename -> Local is ../incoming/filename
    fid = file_row['id']
    fname = os.path.basename(file_row['path'])
    local_path = os.path.join("..", "incoming", fname)
    
    print(f"File found: {file_row['path']} (ID: {fid})")
    print(f"DB Mtime: {file_row['mtime']}")
    
    try:
        if os.path.exists(local_path):
            print(f"OS Mtime: {os.path.getmtime(local_path)}")
            print(f"Size diff: {os.path.getsize(local_path) - file_row['size']}")
        else:
            print(f"Local file not found at {local_path}")
    except Exception as e:
        print(f"Error accessing local file: {e}")

    print(f"Info: {file_row['info']}")
    print(f"Scan Mode: {file_row['scan_mode']}")

    # Check content in docs
    doc_row = c.execute("SELECT content FROM docs WHERE file_id = ?", (fid,)).fetchone()
    if doc_row:
        content = doc_row['content']
        print(f"Content Length: {len(content)}")
        print(f"Preview (Last 200 chars): {content[-200:]}")
        
        # Check for secrets in detections
        det = file_row['details']
        if det:
            import json
            try:
                j = json.loads(det)
                sec = j.get('detections', {}).get('security_issues', {}).get('values', [])
                print(f"Detected Secrets/Values: {sec}")
            except:
                print("Could not parse details JSON")
    else:
        print("No content indexed for this file.")
        
    conn.close()

if __name__ == "__main__":
    verify_indexing("data_aws.txt")
