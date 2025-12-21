import sys
import os
import shutil
import sqlite3
import time
from datetime import datetime

# Add parent dir to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock loguru & others
from unittest.mock import MagicMock
sys.modules["loguru"] = MagicMock()
sys.modules["magic"] = MagicMock()
sys.modules["textract"] = MagicMock()
# sys.modules["analyse.forensic"] = MagicMock() # This is tricky if indexing imports it directly

import database
import indexing

# Setup Test Environment
TEST_DIR = "test_data"
TEST_DB = "test_leak.db"

def setup():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    # Override DB path in database module
    database.DB_PATH = TEST_DB
    database.init_db()

def create_file(filename, content="test content"):
    path = os.path.join(TEST_DIR, filename)
    with open(path, "w") as f:
        f.write(content)
    return path

def run_test():
    print("--- Starting Change Detection Verification ---")
    setup()
    
    # 1. Initial State: Empty Folder -> Should detect change (DB empty)
    print("\nTest 1: Initial Empty State")
    if indexing.detect_file_changes(TEST_DIR):
        print("PASS: Detected change on empty DB")
    else:
        print("FAIL: Should detect change on empty DB")

    # 2. Index files (Simulate first scan)
    print("\n[Action] Populating DB...")
    f1 = create_file("file1.txt", "Initial content")
    indexing.process_indexing(TEST_DIR)
    
    # 3. No Change -> Should return False
    print("\nTest 2: No Changes")
    if not indexing.detect_file_changes(TEST_DIR):
        print("PASS: No changes detected")
    else:
        print("FAIL: False positive detected")

    # 4. Modify Content -> Should return True
    print("\nTest 3: File Modification")
    time.sleep(1.1) # Ensure mtime changes significantly
    create_file("file1.txt", "Modified content")
    if indexing.detect_file_changes(TEST_DIR):
        print("PASS: Modification detected")
    else:
        print("FAIL: Modification missed")

    # Reset DB state
    indexing.process_indexing(TEST_DIR)

    # 5. Add File -> Should return True
    print("\nTest 4: File Addition")
    create_file("file2.txt", "New file")
    if indexing.detect_file_changes(TEST_DIR):
        print("PASS: Addition detected")
    else:
        print("FAIL: Addition missed")

    # Reset DB state
    indexing.process_indexing(TEST_DIR)

    # 6. Delete File -> Should return True
    print("\nTest 5: File Deletion")
    os.remove(os.path.join(TEST_DIR, "file2.txt"))
    if indexing.detect_file_changes(TEST_DIR):
        print("PASS: Deletion detected")
    else:
        print("FAIL: Deletion missed")
        
    # Cleanup
    # shutil.rmtree(TEST_DIR)
    # os.remove(TEST_DB)
    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    run_test()
