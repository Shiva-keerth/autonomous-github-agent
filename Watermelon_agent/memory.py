import sqlite3
import json
from datetime import datetime

DB_NAME = "agent_memory.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
         CREATE TABLE IF NOT EXISTS execution_memory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instruction TEXT NOT NULL,
            plan_json TEXT NOT NULL,
            status TEXT NOT NULL,
            api_call_count INTEGER NOT NULL,
            duration_seconds REAL NOT NULL,
            error TEXT,
            created_at TEXT NOT NULL
         )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS capability_memory(
            action_name TEXT PRIMARY KEY,
            total_calls INTEGER NOT NULL DEFAULT 0,
            success_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS synthesized_capabilities(
            capability_name TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            filter_field TEXT NOT NULL,
            filter_type TEXT NOT NULL,
            action_to_apply TEXT NOT NULL,
            times_reused INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def save_execution(instruction: str, plan_json: str, status:str,
                   api_call_count: int, duration_seconds: float,
                   error: str = None):
    conn= get_connection()
    cursor =conn.cursor()

    cursor.execute("""
        INSERT INTO execution_memory
        (instruction, plan_json, status, api_call_count, duration_seconds, error, created_at)
        VALUES (?,?,?,?,?,?,?)
    """,(instruction, plan_json, status, api_call_count, duration_seconds, error,
             datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_similar_execution(instruction:str, limit:int =3) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT instruction, plan_json, status, api_call_count, duration_seconds, error, created_at
        FROM execution_memory
        WHERE status = 'success' AND LOWER(instruction) = LOWER(?)
        ORDER BY created_at DESC
        LIMIT ?
    """, (instruction, limit))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append({
            "instruction": row[0],
            "plan_json": row[1],
            "status": row[2],
            "api_call_count": row[3],
            "duration_seconds": row[4],
            "error": row[5],
            "created_at": row[6]
        })
    return results

def record_capability_use(action_name:str, success: bool, error: str=None):
    conn =get_connection()
    cursor =conn.cursor()

    cursor.execute("SELECT * FROM capability_memory WHERE action_name = ?", (action_name,))
    existing = cursor.fetchone()

    now = datetime.now().isoformat()

    if existing is None:
        cursor.execute("""
            INSERT INTO capability_memory
            (action_name, total_calls, success_count, failure_count, last_error, updated_at)
            VALUES (?, 1, ?, ? , ?, ?)
        """, (action_name, 1 if success else 0, 0 if success else 1, error, now))
    else:
        if success:
            cursor.execute("""
                UPDATE capability_memory
                SET total_calls = total_calls + 1,
                    success_count = success_count + 1,
                    updated_at = ?
                WHERE action_name = ?
            """, (now, action_name))
        else:
            cursor.execute("""
                UPDATE capability_memory
                SET total_calls = total_calls +1,
                    failure_count =failure_count + 1,
                    last_error = ?,
                    updated_at = ?
                WHERE action_name = ?
            """, (error, now, action_name))

    conn.commit()
    conn.close()

def save_synthesized_capability(capability_name: str, description: str, filter_field:str, filter_type: str, action_to_apply: str):
    conn =get_connection()
    cursor=conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO synthesized_capabilities
        (capability_name, description, filter_field, filter_type,action_to_apply, times_reused, created_at)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    """, (capability_name, description, filter_field, filter_type, action_to_apply,
          datetime.now().isoformat()))

    conn.commit()
    conn.close()

def get_synthesized_capability(capability_name: str) -> dict:
    conn =get_connection()
    cursor =conn.cursor()

    cursor.execute("SELECT * FROM synthesized_capabilities WHERE capability_name = ?",(capability_name,))
    row =cursor.fetchone()

    if row is None:
        conn.close()
        return None

    cursor.execute("""
        UPDATE synthesized_capabilities
        SET times_reused =times_reused + 1
        WHERE capability_name =?
    """, (capability_name,))
    conn.commit()
    conn.close()

    return {
        "capability_name": row[0],
        "description": row[1],
        "filter_field": row[2],
        "filter_type": row[3],
        "action_to_apply": row[4],
        "times_reused": row[5] + 1,
        "created_at": row[6]
    }

def get_capability_stats(action_name: str) -> dict:
    conn =get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM capability_memory WHERE action_name = ?", (action_name,))
    row =cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return{
        "action_name": row[0],
        "total_calls": row[1],
        "success_count": row[2],
        "failure_count": row[3],
        "last_error": row[4],
        "updated_at": row[5]
    }

if __name__ == "__main__":
    result1 =get_synthesized_capability("filter_and_close_by_title")
    print("Call 1:", result1["times_reused"])

    result2= get_synthesized_capability(("filter_and_close_by_title"))
    print("Call 2:", result2["times_reused"])