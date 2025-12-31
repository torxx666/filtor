import sqlite3
import os

DB_PATH = "leak.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Enable Write-Ahead Logging for concurrency
    c.execute('PRAGMA journal_mode=WAL;')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            path TEXT,
            size INTEGER,
            mtime REAL,
            type TEXT,
            created_at TEXT,
            true_type TEXT,
            has_text INTEGER,
            info TEXT,
            details TEXT,
            risk_level TEXT,
            risk_score REAL
        )
    ''')
    
    # Simple migration to add mtime if it doesn't exist
    try:
        c.execute('ALTER TABLE files ADD COLUMN mtime REAL')
    except sqlite3.OperationalError:
        # Column likely already exists
        pass
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            content TEXT,
            src TEXT,
            page_num INTEGER,
            FOREIGN KEY(file_id) REFERENCES files(id)
        )
    ''')
    
    # Simple migration to add src if it doesn't exist
    try:
        c.execute('ALTER TABLE docs ADD COLUMN src TEXT')
    except sqlite3.OperationalError:
        pass
        
    # Simple migration to add scan_mode if it doesn't exist
    try:
        c.execute('ALTER TABLE files ADD COLUMN scan_mode TEXT')
    except sqlite3.OperationalError:
        pass
        
    # Simple migration to add keywords_hash if it doesn't exist (for tracking keyword changes)
    try:
        c.execute('ALTER TABLE files ADD COLUMN keywords_hash TEXT')
    except sqlite3.OperationalError:
        pass

    # Custom keywords table
    c.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE
        )
    ''')
    
    # FTS5 virtual table for full-text search
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(content, content='docs', content_rowid='id')
    ''')
    
    conn.commit()
    conn.close()
