"""
file_memory_db.py - Track uploaded files with PSA personality
Remembers what users upload and connects to their memory
"""

import sqlite3
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


def _db_path(username: str) -> str:
    """Get path to user's file memory database."""
    return f"file_memory_{username}.db"


def _connect(username: str) -> sqlite3.Connection:
    """Connect to file memory database and ensure schema."""
    conn = sqlite3.connect(_db_path(username))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection):
    """Create file_uploads table if it doesn't exist."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS file_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            description TEXT,
            extracted_info TEXT,
            conv_id TEXT,
            UNIQUE(file_hash)
        )
    """)
    conn.commit()


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file for duplicate detection."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def add_file_upload(
    username: str,
    filename: str,
    file_type: str,
    file_path: str,
    conv_id: str,
    description: str = "",
    extracted_info: Dict = None
) -> tuple[bool, str, Optional[Dict]]:
    """
    Add file upload to memory.
    
    Returns:
        (is_duplicate, message, previous_upload_info)
    """
    try:
        file_hash = calculate_file_hash(file_path)
        
        conn = _connect(username)
        cur = conn.cursor()
        
        # Check if file was uploaded before
        cur.execute(
            "SELECT * FROM file_uploads WHERE file_hash = ?",
            (file_hash,)
        )
        existing = cur.fetchone()
        
        if existing:
            # File was uploaded before!
            prev_info = {
                'filename': existing['filename'],
                'upload_date': existing['upload_date'],
                'description': existing['description'],
                'conv_id': existing['conv_id']
            }
            conn.close()
            return True, "I remember this file!", prev_info
        
        # New file - save it
        cur.execute("""
            INSERT INTO file_uploads 
            (filename, file_type, file_hash, file_path, upload_date, 
             description, extracted_info, conv_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            file_type,
            file_hash,
            file_path,
            datetime.now().isoformat(),
            description,
            json.dumps(extracted_info) if extracted_info else None,
            conv_id
        ))
        
        conn.commit()
        conn.close()
        
        return False, "New file saved!", None
        
    except Exception as e:
        return False, f"Error saving file: {e}", None


def get_recent_uploads(username: str, limit: int = 5) -> List[Dict]:
    """Get recent file uploads."""
    try:
        conn = _connect(username)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT filename, file_type, upload_date, description
            FROM file_uploads
            ORDER BY upload_date DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'filename': row['filename'],
                'file_type': row['file_type'],
                'upload_date': row['upload_date'],
                'description': row['description']
            })
        
        conn.close()
        return results
        
    except Exception:
        return []


def get_similar_files(username: str, file_type: str, limit: int = 3) -> List[Dict]:
    """Get previously uploaded files of same type."""
    try:
        conn = _connect(username)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT filename, upload_date, description
            FROM file_uploads
            WHERE file_type = ?
            ORDER BY upload_date DESC
            LIMIT ?
        """, (file_type, limit))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'filename': row['filename'],
                'upload_date': row['upload_date'],
                'description': row['description']
            })
        
        conn.close()
        return results
        
    except Exception:
        return []


def search_files(username: str, query: str) -> List[Dict]:
    """Search files by filename or description."""
    try:
        conn = _connect(username)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT filename, file_type, upload_date, description
            FROM file_uploads
            WHERE filename LIKE ? OR description LIKE ?
            ORDER BY upload_date DESC
        """, (f"%{query}%", f"%{query}%"))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'filename': row['filename'],
                'file_type': row['file_type'],
                'upload_date': row['upload_date'],
                'description': row['description']
            })
        
        conn.close()
        return results
        
    except Exception:
        return []