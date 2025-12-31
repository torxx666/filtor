import sqlite3
import urllib.request
import json

DB_PATH = "leak.db"

def force_rescan():
    print("Resetting mtimes in DB to force re-scan...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE files SET mtime = 0")
    print(f"Updated {c.rowcount} files.")
    conn.commit()
    conn.close()
    
    print("Triggering re-scan via API...")
    try:
        req = urllib.request.Request("http://localhost:9000/load?mode=DEEP", method="POST")
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
            print(f"Response: {data}")
    except Exception as e:
        print(f"Error triggering scan: {e}")

if __name__ == "__main__":
    force_rescan()
