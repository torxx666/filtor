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
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            content TEXT,
            page_num INTEGER,
            FOREIGN KEY(file_id) REFERENCES files(id)
        )
    ''')
    
    # FTS5 virtual table for full-text search
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(content, content='docs', content_rowid='id')
    ''')
    
    conn.commit()
    conn.close()
