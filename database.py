import sqlite3
import json
import os
import hashlib
import secrets
from config import DEFAULTS

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poshmark_bot.db")


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

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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


# ── User auth ────────────────────────────────────────────────

def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()


def create_user(username, password):
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    # First user is automatically admin
    is_admin = 1 if user_count() == 0 else 0
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, is_admin) VALUES (?, ?, ?, ?)",
            (username, pw_hash, salt, is_admin),
        )
        conn.commit()
        return {"success": True}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Username already taken"}
    finally:
        conn.close()


def verify_user(username, password):
    conn = get_db()
    row = conn.execute(
        "SELECT password_hash, salt FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if not row:
        return False
    return _hash_password(password, row["salt"]) == row["password_hash"]


def user_exists(username):
    conn = get_db()
    row = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row is not None


def user_count():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    conn.close()
    return row["cnt"]


def is_admin(username):
    conn = get_db()
    row = conn.execute("SELECT is_admin FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row is not None and row["is_admin"] == 1


def list_users():
    conn = get_db()
    rows = conn.execute("SELECT id, username, is_admin, created_at FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_user(username):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE username = ? AND is_admin = 0", (username,))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0
