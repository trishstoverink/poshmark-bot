import sqlite3
import json
import os
from config import DEFAULTS

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "poshmark_bot.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            detail TEXT,
            status TEXT DEFAULT 'success'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS seen_likes (
            listing_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            offered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (listing_id, user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS session_data (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Seed default settings
    for key, value in DEFAULTS.items():
        c.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )

    conn.commit()
    conn.close()


def get_setting(key):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return DEFAULTS.get(key)


def set_setting(key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(value)),
    )
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: json.loads(row["value"]) for row in rows}


def log_activity(action, detail="", status="success"):
    conn = get_db()
    conn.execute(
        "INSERT INTO activity_log (action, detail, status) VALUES (?, ?, ?)",
        (action, detail, status),
    )
    conn.commit()
    conn.close()


def get_activity_log(limit=50):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def has_seen_like(listing_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM seen_likes WHERE listing_id = ? AND user_id = ?",
        (listing_id, user_id),
    ).fetchone()
    conn.close()
    return row is not None


def mark_like_seen(listing_id, user_id):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO seen_likes (listing_id, user_id) VALUES (?, ?)",
        (listing_id, user_id),
    )
    conn.commit()
    conn.close()


def save_session(key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO session_data (key, value) VALUES (?, ?)",
        (key, json.dumps(value)),
    )
    conn.commit()
    conn.close()


def load_session(key):
    conn = get_db()
    row = conn.execute("SELECT value FROM session_data WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return None


def clear_session():
    conn = get_db()
    conn.execute("DELETE FROM session_data")
    conn.commit()
    conn.close()
