import sqlite3
import json

db_path = "leak.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- Checking docs with src='metadata' ---")
rows = c.execute("SELECT file_id, substr(content, 1, 100), length(content) FROM docs WHERE src='metadata'").fetchall()
for r in rows:
    print(f"FileID: {r[0]}, Len: {r[2]}, Start: {r[1]}")
    # Try to load full content
    full_c = c.execute("SELECT content FROM docs WHERE file_id=?", (r[0],)).fetchone()[0]
    try:
        json.loads(full_c)
        print("JSON parse: SUCCESS")
    except Exception as e:
        print(f"JSON parse: FAILED - {e}")

print("\n--- Checking recent files ---")
files = c.execute("SELECT id, filename FROM files ORDER BY id DESC LIMIT 5").fetchall()
for f in files:
    print(f"File: {f}")

conn.close()
