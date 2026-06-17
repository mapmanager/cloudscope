import sys
import sqlite3
import json

IS_NATIVE = '--native' in sys.argv or any('native=True' in arg for arg in sys.argv)
DB_PATH = "cloudscope_state.db"

def init_database_store():
    """Sets up a reliable local table to act as the central source of truth."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS application_state (
            id INTEGER PRIMARY KEY,
            selection_state TEXT,
            pool_rows TEXT,
            version INTEGER,
            last_updated_by TEXT
        )
    """)
    
    # Insert default starting state data if table is completely empty
    cursor.execute("SELECT COUNT(*) FROM application_state")
    if cursor.fetchone()[0] == 0:
        default_selection = {"file": "scan_001.tif", "channel": 1, "roi_id": 42}
        default_rows = [
            {"pool_row_id": 1, "status": "Pending", "notes": "Initial scan"},
            {"pool_row_id": 2, "status": "Processing", "notes": "High intensity"},
            {"pool_row_id": 3, "status": "Completed", "notes": "Clean data"},
        ]
        cursor.execute("""
            INSERT INTO application_state (id, selection_state, pool_rows, version, last_updated_by)
            VALUES (1, ?, ?, 1, 'system')
        """, (json.dumps(default_selection), json.dumps(default_rows)))
    conn.commit()
    conn.close()

def get_store_state():
    """Reads the current single frame data matrix packet out of our mailbox."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT selection_state, pool_rows, version, last_updated_by FROM application_state WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "selection_state": json.loads(row[0]),
            "pool_rows": json.loads(row[1]),
            "version": row[2],
            "last_updated_by": row[3]
        }
    return {}

def update_store_state(selection_dict, last_updated_by_string):
    """Saves updated selection configurations to the table and steps the version up."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get current version count to increment it step-by-step
    cursor.execute("SELECT version FROM application_state WHERE id=1")
    current_ver = cursor.fetchone()[0]
    
    cursor.execute("""
        UPDATE application_state 
        SET selection_state = ?, version = ?, last_updated_by = ? 
        WHERE id=1
    """, (json.dumps(selection_dict), current_ver + 1, last_updated_by_string))
    conn.commit()
    conn.close()

def update_pool_rows_state(rows_list):
    """Saves updated pool status rows to the source of truth matrix table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM application_state WHERE id=1")
    current_ver = cursor.fetchone()[0]
    
    cursor.execute("""
        UPDATE application_state 
        SET pool_rows = ?, version = ?, last_updated_by = 'system' 
        WHERE id=1
    """, (json.dumps(rows_list), current_ver + 1))
    conn.commit()
    conn.close()
