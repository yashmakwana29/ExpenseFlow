"""
Database Management for ExpenseFlow (MySQL Primary with SQLite Offline Fallback).
Supports offline-first storage, sync state tracking, and fast analytics.
Default connection: MySQL localhost:3306 (user: root, password: root, database: expenseflow_db).
"""
import os
import uuid
import datetime
import hashlib
import secrets
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

import pymysql
import pymysql.cursors
import flet as ft

from config import DEFAULT_SETTINGS, DEFAULT_CATEGORIES, auto_detect_category_info, MYSQL_CONFIG, USE_MYSQL

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.db")


class DBWrapperCursor:
    """Unified cursor that transparently normalizes queries across PyMySQL and SQLite."""
    def __init__(self, raw_cursor, is_mysql: bool = False):
        self._c = raw_cursor
        self.is_mysql = is_mysql

    def execute(self, sql: str, params: Any = None):
        if self.is_mysql:
            # 1. Transform SQLite ? placeholders to MySQL %s
            sql_trans = sql.replace("?", "%s")

            # 2. Transform SQLite ON CONFLICT to MySQL ON DUPLICATE KEY UPDATE
            if "ON CONFLICT(key) DO UPDATE" in sql_trans or "ON CONFLICT(`key`) DO UPDATE" in sql_trans:
                sql_trans = "INSERT INTO settings (`key`, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value = VALUES(value)"

            # 3. Transform SQLite INSERT OR IGNORE to MySQL INSERT IGNORE
            if "INSERT OR IGNORE" in sql_trans:
                sql_trans = sql_trans.replace("INSERT OR IGNORE", "INSERT IGNORE")

            # 4. Ensure `key` column has backticks in queries (key is reserved in MySQL)
            sql_trans = sql_trans.replace("settings (key,", "settings (`key`,")
            sql_trans = sql_trans.replace("settings WHERE key", "settings WHERE `key`")
            sql_trans = sql_trans.replace("categories (key,", "categories (`key`,")
            sql_trans = sql_trans.replace("WHERE LOWER(key)", "WHERE LOWER(`key`)")
            sql_trans = sql_trans.replace("SELECT key,", "SELECT `key`,")
            sql_trans = sql_trans.replace("SELECT key ", "SELECT `key` ")

            if params is not None:
                p = tuple(params) if isinstance(params, (list, tuple)) else params
                return self._c.execute(sql_trans, p)
            return self._c.execute(sql_trans)
        else:
            if params is not None:
                p = tuple(params) if isinstance(params, (list, tuple)) else params
                return self._c.execute(sql, p)
            return self._c.execute(sql)

    def fetchone(self):
        row = self._c.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self._c.fetchall()
        if not rows:
            return []
        return [dict(r) for r in rows]

    @property
    def lastrowid(self):
        return self._c.lastrowid

    def close(self):
        return self._c.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DBWrapperConnection:
    """Unified connection managing either PyMySQL or SQLite with identical semantics."""
    def __init__(self, raw_conn, is_mysql: bool = False):
        self._conn = raw_conn
        self.is_mysql = is_mysql

    def cursor(self):
        return DBWrapperCursor(self._conn.cursor(), self.is_mysql)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


def get_connection():
    """
    Connect to MySQL (user: root, password: root, host: localhost:3306, db: expenseflow_db).
    Automatically falls back to local SQLite if MySQL is unreachable.
    """
    if USE_MYSQL:
        try:
            raw_conn = pymysql.connect(
                host=MYSQL_CONFIG["host"],
                port=MYSQL_CONFIG["port"],
                user=MYSQL_CONFIG["user"],
                password=MYSQL_CONFIG["password"],
                database=MYSQL_CONFIG["database"],
                cursorclass=pymysql.cursors.DictCursor,
                charset="utf8mb4",
                autocommit=False,
                connect_timeout=3
            )
            return DBWrapperConnection(raw_conn, is_mysql=True)
        except Exception:
            # Fall back to SQLite offline storage
            pass

    # SQLite Local Database Fallback
    raw_conn = sqlite3.connect(DB_FILE)
    raw_conn.row_factory = sqlite3.Row
    return DBWrapperConnection(raw_conn, is_mysql=False)


def is_using_mysql() -> bool:
    """Returns True if MySQL is active and connected."""
    try:
        conn = get_connection()
        is_my = conn.is_mysql
        conn.close()
        return is_my
    except Exception:
        return False


def get_db_type() -> str:
    """Returns friendly human-readable database backend name."""
    if is_using_mysql():
        return f"MySQL ({MYSQL_CONFIG['user']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']})"
    return "SQLite (Local Fallback expenses.db)"


def test_mysql_connection() -> Dict[str, Any]:
    """Tests MySQL connectivity and retrieves real-time database stats."""
    try:
        conn = pymysql.connect(
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"],
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=3
        )
        cur = conn.cursor()
        cur.execute("SELECT VERSION() as version")
        ver = cur.fetchone()["version"]

        cur.execute("SELECT COUNT(*) as count FROM expenses")
        exp_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM users")
        user_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM categories")
        cat_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM expenses WHERE synced = 1")
        synced_count = cur.fetchone()["count"]

        conn.close()
        return {
            "success": True,
            "version": ver,
            "host": f"{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}",
            "database": MYSQL_CONFIG["database"],
            "user": MYSQL_CONFIG["user"],
            "expenses_count": exp_count,
            "users_count": user_count,
            "categories_count": cat_count,
            "synced_count": synced_count,
            "unsynced_count": exp_count - synced_count,
            "message": f"Successfully connected to MySQL {ver} on {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}"
        }
    except Exception as e:
        return {
            "success": False,
            "version": "N/A",
            "host": f"{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}",
            "database": MYSQL_CONFIG["database"],
            "user": MYSQL_CONFIG["user"],
            "expenses_count": 0,
            "users_count": 0,
            "categories_count": 0,
            "synced_count": 0,
            "unsynced_count": 0,
            "message": f"MySQL connection error: {str(e)}"
        }


# ----------------- User Authentication & Security Helpers -----------------

def hash_password(password: str, salt: str) -> str:
    """Computes PBKDF2 HMAC SHA-256 hash with 100,000 iterations for secure credential storage."""
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()


def _init_mysql_db():
    """Ensure database expenseflow_db and all required tables exist in MySQL."""
    try:
        admin_conn = pymysql.connect(
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            charset="utf8mb4",
            connect_timeout=3
        )
        admin_cur = admin_conn.cursor()
        admin_cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_CONFIG['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        admin_conn.commit()
        admin_conn.close()
    except Exception:
        pass

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            salt VARCHAR(64) NOT NULL,
            full_name VARCHAR(150),
            created_at VARCHAR(50) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            `key` VARCHAR(100) UNIQUE NOT NULL,
            label VARCHAR(100) NOT NULL,
            icon_name VARCHAR(100) NOT NULL,
            color VARCHAR(20) NOT NULL,
            bg_color VARCHAR(20) NOT NULL,
            is_custom INT DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uuid VARCHAR(64) UNIQUE NOT NULL,
            title VARCHAR(255) NOT NULL,
            amount DOUBLE NOT NULL,
            category VARCHAR(100) NOT NULL,
            payment_mode VARCHAR(100) NOT NULL,
            date VARCHAR(20) NOT NULL,
            notes TEXT,
            user_id INT DEFAULT 1,
            created_by VARCHAR(100) DEFAULT 'admin',
            synced INT DEFAULT 0,
            created_at VARCHAR(50) NOT NULL,
            updated_at VARCHAR(50) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            `key` VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # Populate default categories if empty
    cursor.execute("SELECT COUNT(*) as count FROM categories")
    if cursor.fetchone()["count"] == 0:
        for cat in DEFAULT_CATEGORIES:
            cursor.execute("""
                INSERT IGNORE INTO categories (`key`, label, icon_name, color, bg_color, is_custom)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (cat["key"], cat["label"], cat["icon_name"], cat["color"], cat["bg_color"]))

    # Populate default settings if not exists
    for key, val in DEFAULT_SETTINGS.items():
        cursor.execute("INSERT IGNORE INTO settings (`key`, value) VALUES (?, ?)", (key, str(val)))

    # Populate default user (admin / admin123) if no users exist
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
        default_salt = secrets.token_hex(16)
        default_pwd_hash = hash_password("admin123", default_salt)
        cursor.execute("""
            INSERT INTO users (username, password_hash, salt, full_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", default_pwd_hash, default_salt, "Administrator", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()


def _init_sqlite_db():
    """Initialize local SQLite database fallback tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            payment_mode TEXT NOT NULL,
            date TEXT NOT NULL,
            notes TEXT,
            user_id INTEGER DEFAULT 1,
            created_by TEXT DEFAULT 'admin',
            synced INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    try:
        cursor.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE expenses ADD COLUMN created_by TEXT DEFAULT 'admin'")
    except Exception:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            `key` TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            `key` TEXT UNIQUE NOT NULL,
            label TEXT NOT NULL,
            icon_name TEXT NOT NULL,
            color TEXT NOT NULL,
            bg_color TEXT NOT NULL,
            is_custom INTEGER DEFAULT 0
        )
    """)

    cursor.execute("SELECT COUNT(*) as count FROM categories")
    if cursor.fetchone()["count"] == 0:
        for cat in DEFAULT_CATEGORIES:
            cursor.execute("""
                INSERT OR IGNORE INTO categories (`key`, label, icon_name, color, bg_color, is_custom)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (cat["key"], cat["label"], cat["icon_name"], cat["color"], cat["bg_color"]))

    for key, val in DEFAULT_SETTINGS.items():
        cursor.execute("INSERT OR IGNORE INTO settings (`key`, value) VALUES (?, ?)", (key, str(val)))

    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
        default_salt = secrets.token_hex(16)
        default_pwd_hash = hash_password("admin123", default_salt)
        cursor.execute("""
            INSERT INTO users (username, password_hash, salt, full_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", default_pwd_hash, default_salt, "Administrator", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()


def init_db():
    """Initialize database tables, default categories, users, and settings on active backend."""
    if is_using_mysql():
        _init_mysql_db()
    else:
        _init_sqlite_db()


def create_user(username: str, password: str, full_name: str = "") -> Tuple[Optional[Dict[str, Any]], str]:
    """Register a new user account with unique username/ID and password."""
    clean_user = username.strip()
    clean_name = full_name.strip() if full_name else clean_user

    if len(clean_user) < 3:
        return None, "User ID / Username must be at least 3 characters long."
    if len(password) < 4:
        return None, "Password must be at least 4 characters long."

    conn = get_connection()
    cursor = conn.cursor()

    # Check if username exists (case-insensitive)
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (clean_user,))
    if cursor.fetchone():
        conn.close()
        return None, f"User ID '{clean_user}' is already taken. Please choose another."

    salt = secrets.token_hex(16)
    pwd_hash = hash_password(password, salt)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO users (username, password_hash, salt, full_name, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (clean_user, pwd_hash, salt, clean_name, now_str))

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": user_id,
        "username": clean_user,
        "full_name": clean_name,
        "created_at": now_str,
    }, ""

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify username & password. Returns user dict on success, None on failure."""
    clean_user = username.strip()
    if not clean_user or not password:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (clean_user,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    # Check password hash using constant-time comparison
    expected_hash = row["password_hash"]
    test_hash = hash_password(password, row["salt"])
    if secrets.compare_digest(expected_hash, test_hash):
        return {
            "id": row["id"],
            "username": row["username"],
            "full_name": row["full_name"],
            "created_at": row["created_at"],
        }
    return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch user details by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "username": row["username"],
            "full_name": row["full_name"],
            "created_at": row["created_at"],
        }
    return None

def change_user_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
    """Change user password after verifying old password."""
    if len(new_password) < 4:
        return False, "New password must be at least 4 characters long."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False, "User not found."

    test_hash = hash_password(old_password, row["salt"])
    if not secrets.compare_digest(row["password_hash"], test_hash):
        conn.close()
        return False, "Incorrect current password."

    new_salt = secrets.token_hex(16)
    new_hash = hash_password(new_password, new_salt)
    cursor.execute("""
        UPDATE users SET password_hash = ?, salt = ? WHERE id = ?
    """, (new_hash, new_salt, user_id))
    conn.commit()
    conn.close()
    return True, "Password updated successfully!"

def get_current_session_user() -> Optional[Dict[str, Any]]:
    """Get the currently logged-in user from settings session."""
    active_id = get_setting("active_user_id", "")
    if active_id and active_id.isdigit():
        return get_user_by_id(int(active_id))
    return None

def set_current_session_user(user_id: Optional[int]):
    """Set or clear the currently logged-in user session."""
    if user_id is not None:
        set_setting("active_user_id", str(user_id))
    else:
        set_setting("active_user_id", "")

def get_all_users() -> List[Dict[str, Any]]:
    """Fetch list of all registered users for team switcher and filter."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, created_at FROM users ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------- Category Helpers -----------------

def get_categories() -> List[Dict[str, Any]]:
    """Fetch all active categories (default + user created) with resolved ft.Icons."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY is_custom ASC, id ASC")
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        icon_name = r["icon_name"]
        icon_obj = getattr(ft.Icons, icon_name, ft.Icons.LABEL)
        result.append({
            "id": r["id"],
            "key": r["key"],
            "label": r["label"],
            "icon_name": icon_name,
            "icon": icon_obj,
            "color": r["color"],
            "bg_color": r["bg_color"],
            "is_custom": bool(r["is_custom"]),
        })
    return result

def get_category_map() -> Dict[str, Dict[str, Any]]:
    """Returns a dict mapping category name to its styling tokens."""
    cats = get_categories()
    cmap = {c["key"]: c for c in cats}
    return cmap

def add_category(name: str) -> Dict[str, Any]:
    """
    Adds a new category with its symbol and color automatically deduced.
    """
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Category name cannot be empty")

    conn = get_connection()
    cursor = conn.cursor()

    # Check if already exists
    cursor.execute("SELECT * FROM categories WHERE LOWER(`key`) = LOWER(?)", (clean_name,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        icon_obj = getattr(ft.Icons, existing["icon_name"], ft.Icons.LABEL)
        return {
            "id": existing["id"],
            "key": existing["key"],
            "label": existing["label"],
            "icon_name": existing["icon_name"],
            "icon": icon_obj,
            "color": existing["color"],
            "bg_color": existing["bg_color"],
            "is_custom": bool(existing["is_custom"]),
        }

    # Automatically detect icon and color based on category name keywords
    detected = auto_detect_category_info(clean_name)

    cursor.execute("""
        INSERT INTO categories (`key`, label, icon_name, color, bg_color, is_custom)
        VALUES (?, ?, ?, ?, ?, 1)
    """, (detected["key"], detected["label"], detected["icon_name"], detected["color"], detected["bg_color"]))

    cat_id = cursor.lastrowid
    conn.commit()
    conn.close()

    detected["id"] = cat_id
    detected["is_custom"] = True
    return detected

# ----------------- Settings Helpers -----------------

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE `key` = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    if conn.is_mysql:
        cursor.execute("""
            INSERT INTO settings (`key`, value) VALUES (?, ?)
            ON DUPLICATE KEY UPDATE value = VALUES(value)
        """, (key, str(value)))
    else:
        cursor.execute("""
            INSERT INTO settings (`key`, value) VALUES (?, ?)
            ON CONFLICT(`key`) DO UPDATE SET value = excluded.value
        """, (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT `key`, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


# ----------------- Expense CRUD Operations -----------------

def add_expense(
    title: str,
    amount: float,
    category: str,
    payment_mode: str,
    date: str,
    notes: str = "",
    synced: int = 0,
    user_id: Optional[int] = None,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """Insert a new expense record tagged with user ID / creator."""
    conn = get_connection()
    cursor = conn.cursor()
    
    item_uuid = str(uuid.uuid4())
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if user_id is None or created_by is None:
        curr_user = get_current_session_user()
        if curr_user:
            user_id = user_id or curr_user["id"]
            created_by = created_by or curr_user["username"]
        else:
            user_id = user_id or 1
            created_by = created_by or "admin"

    cursor.execute("""
        INSERT INTO expenses (uuid, title, amount, category, payment_mode, date, notes, user_id, created_by, synced, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (item_uuid, title.strip(), float(amount), category, payment_mode, date, notes.strip(), user_id, created_by, synced, now_str, now_str))

    item_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": item_id,
        "uuid": item_uuid,
        "title": title.strip(),
        "amount": float(amount),
        "category": category,
        "payment_mode": payment_mode,
        "date": date,
        "notes": notes.strip(),
        "user_id": user_id,
        "created_by": created_by,
        "synced": synced,
        "created_at": now_str,
        "updated_at": now_str
    }

def update_expense(
    expense_id: int,
    title: str,
    amount: float,
    category: str,
    payment_mode: str,
    date: str,
    notes: str = ""
):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE expenses
        SET title = ?, amount = ?, category = ?, payment_mode = ?, date = ?, notes = ?, synced = 0, updated_at = ?
        WHERE id = ?
    """, (title.strip(), float(amount), category, payment_mode, date, notes.strip(), now_str, expense_id))

    conn.commit()
    conn.close()

def delete_expense(expense_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

def get_expense_by_id(expense_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_expenses(
    limit: Optional[int] = None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    payment_mode: Optional[str] = None,
    month: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve expenses with optional filters and sorting, supporting multi-user isolation."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM expenses WHERE 1=1"
    params: List[Any] = []

    if search:
        query += " AND (title LIKE ? OR notes LIKE ? OR created_by LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    if payment_mode and payment_mode != "All":
        query += " AND payment_mode = ?"
        params.append(payment_mode)

    if month and month != "All":
        query += " AND date LIKE ?"
        params.append(f"{month}%")

    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    elif username and username != "All":
        query += " AND created_by = ?"
        params.append(username)

    query += " ORDER BY date DESC, id DESC"

    if limit:
        query += f" LIMIT {int(limit)}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_unsynced_expenses() -> List[Dict[str, Any]]:
    """Get all expenses that have not yet been synced to Google Sheets."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE synced = 0 ORDER BY date ASC, id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_expenses_as_synced(uuids: List[str]):
    """Mark a list of expenses as synced."""
    if not uuids:
        return
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in uuids)
    cursor.execute(f"UPDATE expenses SET synced = 1 WHERE uuid IN ({placeholders})", uuids)
    conn.commit()
    conn.close()

def mark_all_expenses_as_synced():
    """Mark all expenses as synced."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE expenses SET synced = 1")
    conn.commit()
    conn.close()

def clear_all_expenses():
    """Remove all expenses (for reset)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses")
    conn.commit()
    conn.close()

# ----------------- Statistics and Reporting -----------------

def get_available_months(user_id: Optional[int] = None, username: Optional[str] = None) -> List[str]:
    """Get distinct year-month strings from expenses, filtered by user if requested."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT DISTINCT SUBSTR(date, 1, 7) as ym FROM expenses WHERE 1=1"
    params = []
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    elif username and username != "All":
        query += " AND created_by = ?"
        params.append(username)
    query += " ORDER BY ym DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [r["ym"] for r in rows if r["ym"]]


def get_stats(
    month_str: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compute comprehensive statistics with optional month and multi-user filter.
    """
    conn = get_connection()
    cursor = conn.cursor()

    conditions = ["1=1"]
    params = []
    if month_str and month_str != "All":
        conditions.append("date LIKE ?")
        params.append(f"{month_str}%")

    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)
    elif username and username != "All":
        conditions.append("created_by = ?")
        params.append(username)

    where_clause = "WHERE " + " AND ".join(conditions)

    # 1. Total & Averages
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total_count,
            COALESCE(SUM(amount), 0.0) as total_amount,
            COALESCE(AVG(amount), 0.0) as avg_amount,
            COALESCE(MAX(amount), 0.0) as max_amount
        FROM expenses {where_clause}
    """, params)
    raw_kpis = cursor.fetchone() or {}
    kpis = {
        "total_count": int(raw_kpis.get("total_count", 0)),
        "total_amount": float(raw_kpis.get("total_amount", 0.0) or 0.0),
        "avg_amount": float(raw_kpis.get("avg_amount", 0.0) or 0.0),
        "max_amount": float(raw_kpis.get("max_amount", 0.0) or 0.0),
    }

    # 2. Category Breakdown
    cursor.execute(f"""
        SELECT 
            category,
            SUM(amount) as total_amount,
            COUNT(*) as count
        FROM expenses {where_clause}
        GROUP BY category
        ORDER BY total_amount DESC
    """, params)
    category_rows = [dict(r) for r in cursor.fetchall()]

    # Calculate percentages
    total_spent = kpis["total_amount"]
    for row in category_rows:
        row["total_amount"] = float(row.get("total_amount", 0.0) or 0.0)
        row["count"] = int(row.get("count", 0))
        row["percent"] = (row["total_amount"] / total_spent * 100) if total_spent > 0 else 0.0

    # 3. Payment Mode Breakdown
    cursor.execute(f"""
        SELECT 
            payment_mode,
            SUM(amount) as total_amount,
            COUNT(*) as count
        FROM expenses {where_clause}
        GROUP BY payment_mode
        ORDER BY total_amount DESC
    """, params)
    payment_rows = [dict(r) for r in cursor.fetchall()]
    for row in payment_rows:
        row["total_amount"] = float(row.get("total_amount", 0.0) or 0.0)
        row["count"] = int(row.get("count", 0))
        row["percent"] = (row["total_amount"] / total_spent * 100) if total_spent > 0 else 0.0

    # 4. Daily Spending Trend (Last 14 days or days in month)
    cursor.execute(f"""
        SELECT 
            date,
            SUM(amount) as daily_total,
            COUNT(*) as count
        FROM expenses {where_clause}
        GROUP BY date
        ORDER BY date ASC
    """, params)
    daily_rows = [dict(r) for r in cursor.fetchall()]
    for row in daily_rows:
        row["daily_total"] = float(row.get("daily_total", 0.0) or 0.0)
        row["count"] = int(row.get("count", 0))

    conn.close()


    return {
        "kpis": kpis,
        "categories": category_rows,
        "payment_modes": payment_rows,
        "daily_trends": daily_rows,
    }

# ----------------- Sample Data Seeder -----------------

def seed_sample_data():
    """Seeds realistic sample expenses so the user can immediately test reports."""
    today = datetime.date.today()
    
    sample_records = [
        ("Grocery & Vegetables", 1250.0, "Groceries", "UPI", 0, "Weekly fresh veggies & dairy"),
        ("Starbucks Coffee & Snacks", 380.0, "Food & Dining", "UPI", 1, "Coffee with colleagues"),
        ("Uber Ride to Office", 240.0, "Transport", "UPI", 1, "Cab due to rain"),
        ("Monthly Electricity Bill", 2450.0, "Bills & Utilities", "Net Banking", 2, "Power bill for the month"),
        ("Weekend Movie & Popcorn", 850.0, "Entertainment", "Credit Card", 3, "IMAX Movie tickets"),
        ("Dining at Olive Bistro", 1950.0, "Food & Dining", "Credit Card", 4, "Dinner with friends"),
        ("Pharmacy & Vitamins", 620.0, "Health & Medical", "Debit Card", 5, "Multivitamins & cold meds"),
        ("Fuel / Petrol Fill-up", 1800.0, "Transport", "Credit Card", 6, "Full tank petrol"),
        ("Amazon Shopping - Shoes", 3200.0, "Shopping", "Credit Card", 7, "Running sneakers"),
        ("Broadband Internet Bill", 999.0, "Bills & Utilities", "UPI", 8, "Monthly fiber optic plan"),
        ("Python Masterclass Book", 750.0, "Education", "UPI", 9, "Technical programming book"),
        ("Supermarket Monthly Ration", 4600.0, "Groceries", "Debit Card", 11, "Pantry essentials"),
        ("Zomato Late Night Pizza", 590.0, "Food & Dining", "UPI", 12, "Pizza delivery"),
        ("Metro Smart Card Recharge", 500.0, "Transport", "UPI", 14, "Metro monthly recharge"),
        ("Mutual Fund SIP Investment", 5000.0, "Investments", "Net Banking", 15, "Automated monthly SIP"),
        ("Gym Membership Fee", 1500.0, "Health & Medical", "UPI", 18, "Monthly subscription"),
        ("Weekend Road Trip Tolls", 420.0, "Travel", "Cash", 20, "Highway toll and snacks"),
        ("Online Course Subscription", 1200.0, "Education", "Credit Card", 22, "Cloud certification course"),
    ]

    for title, amount, cat, mode, days_ago, notes in sample_records:
        rec_date = (today - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
        add_expense(
            title=title,
            amount=amount,
            category=cat,
            payment_mode=mode,
            date=rec_date,
            notes=notes,
            synced=0
        )
