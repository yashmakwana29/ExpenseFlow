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
    return "SQLite (Local Mobile Storage expenses.db)"


def get_database_health() -> Dict[str, Any]:
    """
    Returns comprehensive diagnostic information about the active database
    (whether MySQL on server/PC or SQLite on mobile device) and sync status.
    """
    is_mysql = is_using_mysql()
    exp_count, user_count, cat_count, synced_count = 0, 0, 0, 0
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM expenses")
        res = cur.fetchone()
        exp_count = res["count"] if res else 0
        cur.execute("SELECT COUNT(*) as count FROM users")
        res = cur.fetchone()
        user_count = res["count"] if res else 0
        cur.execute("SELECT COUNT(*) as count FROM categories")
        res = cur.fetchone()
        cat_count = res["count"] if res else 0
        cur.execute("SELECT COUNT(*) as count FROM expenses WHERE synced = 1")
        res = cur.fetchone()
        synced_count = res["count"] if res else 0
        conn.close()
    except Exception:
        pass

    if is_mysql:
        ver = "Unknown"
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
            ver_res = cur.fetchone()
            if ver_res:
                ver = ver_res["version"]
            conn.close()
        except Exception:
            pass

        return {
            "is_mysql": True,
            "engine": "MySQL Server",
            "status_text": "CONNECTED & ACTIVE",
            "is_healthy": True,
            "host": f"{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}",
            "database": MYSQL_CONFIG["database"],
            "user": MYSQL_CONFIG["user"],
            "version": ver,
            "expenses_count": exp_count,
            "users_count": user_count,
            "categories_count": cat_count,
            "synced_count": synced_count,
            "unsynced_count": exp_count - synced_count,
            "message": "Connected directly to MySQL database server."
        }
    else:
        return {
            "is_mysql": False,
            "engine": "SQLite (Mobile Local Storage)",
            "status_text": "ACTIVE & HEALTHY",
            "is_healthy": True,
            "host": "Local Device (expenses.db)",
            "database": "expenses.db",
            "user": "local_device",
            "version": f"SQLite {sqlite3.sqlite_version}",
            "expenses_count": exp_count,
            "users_count": user_count,
            "categories_count": cat_count,
            "synced_count": synced_count,
            "unsynced_count": exp_count - synced_count,
            "message": "Mobile Offline-First Mode: SQLite stores all records safely and instantly on your phone. Synchronizes with PC/Server via Google Sheets 2-Way Cloud Sync."
        }


def test_mysql_connection() -> Dict[str, Any]:
    """Tests MySQL connectivity and retrieves real-time database stats."""
    return get_database_health()


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
            email VARCHAR(150) UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            salt VARCHAR(64) NOT NULL,
            full_name VARCHAR(150),
            role VARCHAR(20) DEFAULT 'user',
            is_active INT DEFAULT 1,
            email_verified INT DEFAULT 0,
            created_at VARCHAR(50) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # Ensure all user columns exist for role-based access & email OTP
    user_alter_mysql = [
        "ALTER TABLE users ADD COLUMN email VARCHAR(150) UNIQUE",
        "ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'",
        "ALTER TABLE users ADD COLUMN is_active INT DEFAULT 1",
        "ALTER TABLE users ADD COLUMN email_verified INT DEFAULT 0",
    ]
    for q in user_alter_mysql:
        try:
            cursor.execute(q)
            conn.commit()
        except Exception:
            pass

    # OTP Verifications Table for Registration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_verifications (
            email VARCHAR(150) PRIMARY KEY,
            otp_code VARCHAR(10) NOT NULL,
            created_at VARCHAR(50) NOT NULL,
            expires_at VARCHAR(50) NOT NULL
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
            INSERT INTO users (username, email, password_hash, salt, full_name, role, is_active, email_verified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
        """, ("admin", "admin@expenseflow.com", default_pwd_hash, default_salt, "Administrator", "admin", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    else:
        try:
            cursor.execute("UPDATE users SET email = 'admin@expenseflow.com', role = 'admin', is_active = 1, email_verified = 1 WHERE username = 'admin' AND (role IS NULL OR role = '')")
        except Exception:
            pass

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
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            email_verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    user_alter_sqlite = [
        "ALTER TABLE users ADD COLUMN email TEXT",
        "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'",
        "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0",
    ]
    for q in user_alter_sqlite:
        try:
            cursor.execute(q)
            conn.commit()
        except Exception:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_verifications (
            email TEXT PRIMARY KEY,
            otp_code TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
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


def create_user(username: str, email: str, password: str, full_name: str = "", role: str = "user") -> Tuple[Optional[Dict[str, Any]], str]:
    """Register a new user account with distinct email, username, and password."""
    clean_user = username.strip()
    clean_email = email.strip().lower()
    clean_name = full_name.strip() if full_name else clean_user

    if not clean_email or "@" not in clean_email or "." not in clean_email:
        return None, "Please enter a valid email address (e.g. name@example.com)."
    if len(clean_user) < 3:
        return None, "User ID / Username must be at least 3 characters long."
    if len(password) < 4:
        return None, "Password must be at least 4 characters long."

    conn = get_connection()
    cursor = conn.cursor()

    # Check if email is already registered (case-insensitive)
    cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (clean_email,))
    if cursor.fetchone():
        conn.close()
        return None, f"An account with email '{clean_email}' already exists. Please log in or use another email."

    # Check if username is already registered (case-insensitive)
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (clean_user,))
    if cursor.fetchone():
        conn.close()
        return None, f"User ID '{clean_user}' is already taken. Please choose another username."

    salt = secrets.token_hex(16)
    pwd_hash = hash_password(password, salt)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO users (username, email, password_hash, salt, full_name, role, is_active, email_verified, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
    """, (clean_user, clean_email, pwd_hash, salt, clean_name, role, now_str))

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": user_id,
        "username": clean_user,
        "email": clean_email,
        "full_name": clean_name,
        "role": role,
        "is_active": 1,
        "email_verified": 1,
        "created_at": now_str,
    }, ""

def generate_and_send_registration_otp(email: str, username: str = "") -> Tuple[bool, str]:
    """Generates a 6-digit OTP, stores it in database with 10-minute expiry, and emails it via Gmail SMTP."""
    clean_email = email.strip().lower()
    if not clean_email or "@" not in clean_email or "." not in clean_email:
        return False, "Please enter a valid email address."

    conn = get_connection()
    cursor = conn.cursor()

    # Check if email is already taken
    cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (clean_email,))
    if cursor.fetchone():
        conn.close()
        return False, f"Email '{clean_email}' is already registered. Please sign in instead."

    # Generate 6-digit OTP
    otp_code = str(secrets.randbelow(900000) + 100000)
    now = datetime.datetime.now()
    expires_at = (now + datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Store in otp_verifications
    try:
        if conn.is_mysql:
            cursor.execute("""
                INSERT INTO otp_verifications (email, otp_code, created_at, expires_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE otp_code = VALUES(otp_code), created_at = VALUES(created_at), expires_at = VALUES(expires_at)
            """, (clean_email, otp_code, now_str, expires_at))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO otp_verifications (email, otp_code, created_at, expires_at)
                VALUES (?, ?, ?, ?)
            """, (clean_email, otp_code, now_str, expires_at))
        conn.commit()
    except Exception as e:
        conn.close()
        return False, f"Failed to record OTP: {str(e)}"
    finally:
        conn.close()

    # Send email via email_service
    import email_service
    return email_service.send_otp_email(clean_email, otp_code, username)

def verify_registration_otp(email: str, entered_code: str) -> Tuple[bool, str]:
    """Verifies that the entered 6-digit OTP matches and has not expired."""
    clean_email = email.strip().lower()
    clean_code = entered_code.strip()

    if not clean_code or len(clean_code) != 6:
        return False, "Please enter the 6-digit verification code sent to your email."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT otp_code, expires_at FROM otp_verifications WHERE LOWER(email) = LOWER(?)", (clean_email,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False, "No verification request found for this email. Please request a new OTP."

    expires_at = row["expires_at"]
    if datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") > expires_at:
        conn.close()
        return False, "Verification code has expired. Please request a fresh OTP."

    if secrets.compare_digest(str(row["otp_code"]), clean_code):
        # Delete verified OTP
        cursor.execute("DELETE FROM otp_verifications WHERE LOWER(email) = LOWER(?)", (clean_email,))
        conn.commit()
        conn.close()
        return True, "Email address verified successfully!"

    conn.close()
    return False, "Incorrect verification code. Please check your email and try again."

def authenticate_user(login_id: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify username OR email & password. Returns user dict on success, None on failure."""
    clean_id = login_id.strip()
    if not clean_id or not password:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)", (clean_id, clean_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    # Check password hash using constant-time comparison
    expected_hash = row["password_hash"]
    test_hash = hash_password(password, row["salt"])
    if not secrets.compare_digest(expected_hash, test_hash):
        return None

    # Check active status
    is_act = row.get("is_active", 1)
    if is_act is not None and int(is_act) == 0:
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "email": row.get("email", ""),
        "full_name": row["full_name"],
        "role": row.get("role", "admin" if row["username"] == "admin" else "user"),
        "is_active": int(is_act) if is_act is not None else 1,
        "email_verified": int(row.get("email_verified", 0) or 0),
        "created_at": row["created_at"],
    }

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch user details by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, is_active, email_verified, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "username": row["username"],
            "email": row.get("email", ""),
            "full_name": row["full_name"],
            "role": row.get("role", "admin" if row["username"] == "admin" else "user"),
            "is_active": int(row.get("is_active", 1) or 1),
            "email_verified": int(row.get("email_verified", 0) or 0),
            "created_at": row["created_at"],
        }
    return None

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Fetch user details by username."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, is_active, email_verified, created_at FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "username": row["username"],
            "email": row.get("email", ""),
            "full_name": row["full_name"],
            "role": row.get("role", "admin" if row["username"] == "admin" else "user"),
            "is_active": int(row.get("is_active", 1) or 1),
            "email_verified": int(row.get("email_verified", 0) or 0),
            "created_at": row["created_at"],
        }
    return None

def admin_get_all_users() -> List[Dict[str, Any]]:
    """Fetches all registered users along with expense count and total spending metrics."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, is_active, email_verified, created_at FROM users ORDER BY id ASC")
    users = cursor.fetchall()

    user_list = []
    for u in users:
        u_id = u["id"]
        cursor.execute("SELECT COUNT(*) as exp_count, COALESCE(SUM(amount), 0) as total_spend FROM expenses WHERE user_id = ?", (u_id,))
        exp_row = cursor.fetchone()
        u_dict = {
            "id": u["id"],
            "username": u["username"],
            "email": u.get("email") or "N/A",
            "full_name": u.get("full_name") or u["username"],
            "role": u.get("role") or ("admin" if u["username"] == "admin" else "user"),
            "is_active": int(u.get("is_active", 1) or 1),
            "email_verified": int(u.get("email_verified", 0) or 0),
            "created_at": u["created_at"],
            "expenses_count": exp_row["exp_count"] if exp_row else 0,
            "total_spend": float(exp_row["total_spend"]) if exp_row else 0.0,
        }
        user_list.append(u_dict)

    conn.close()
    return user_list

def admin_reset_user_password(user_id: int, new_password: str, send_email: bool = True) -> Tuple[bool, str]:
    """Admin function to reset any user's password and optionally notify them via email."""
    if len(new_password) < 4:
        return False, "Password must be at least 4 characters long."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return False, "User not found."

    salt = secrets.token_hex(16)
    pwd_hash = hash_password(new_password, salt)

    cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (pwd_hash, salt, user_id))
    conn.commit()
    conn.close()

    # Notify user via email if email exists
    email_status = ""
    if send_email and user.get("email"):
        import email_service
        ok, em_msg = email_service.send_password_reset_email(user["email"], user["username"], new_password)
        if ok:
            email_status = f" New password was emailed to {user['email']}."
        else:
            email_status = f" (Email delivery note: {em_msg})"

    return True, f"Password for '{user['username']}' was successfully reset!{email_status}"

def admin_toggle_user_status(user_id: int, new_status: int) -> Tuple[bool, str]:
    """Admin function to activate (1) or deactivate (0) a user account."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return False, "User not found."

    if user["username"] == "admin" and new_status == 0:
        conn.close()
        return False, "Cannot deactivate the primary Administrator account."

    cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
    conn.commit()
    conn.close()

    action = "activated" if new_status == 1 else "deactivated"
    return True, f"User '{user['username']}' has been {action}."

def admin_delete_user(user_id: int) -> Tuple[bool, str]:
    """Admin function to delete a user account and associated expenses."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return False, "User not found."

    if user["username"] == "admin":
        conn.close()
        return False, "Cannot delete the primary Administrator account."

    cursor.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return True, f"User '{user['username']}' and all associated transactions have been permanently deleted."

def admin_update_user_role(user_id: int, new_role: str) -> Tuple[bool, str]:
    """Admin function to update a user's role ('admin' or 'user')."""
    if new_role not in ["admin", "user"]:
        return False, "Role must be either 'admin' or 'user'."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return False, "User not found."

    if user["username"] == "admin" and new_role != "admin":
        conn.close()
        return False, "Cannot demote the primary Administrator account."

    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()

    return True, f"User '{user['username']}' role updated to {new_role.upper()}."

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

    curr_user = get_current_session_user()
    if curr_user:
        user_id = curr_user["id"]
        created_by = curr_user["username"]
    else:
        user_id = user_id or 1
        created_by = (created_by or "admin").strip()

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

def upsert_expense_from_sync(
    uuid_str: str,
    title: str,
    amount: float,
    category: str,
    payment_mode: str,
    date: str,
    notes: str = "",
    created_by: str = "admin",
    synced_at: str = ""
) -> bool:
    """
    Inserts or updates an expense pulled from Google Sheets into the local DB.
    Guarantees idempotency via UUID matching:
    - If record with uuid_str already exists locally, marks synced = 1 and returns False.
    - If new, resolves category, user_id, and inserts with synced = 1, returning True.
    """
    clean_uuid = uuid_str.strip()
    if not clean_uuid:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Check if expense already exists locally by UUID
    cursor.execute("SELECT id, synced FROM expenses WHERE uuid = ?", (clean_uuid,))
    existing = cursor.fetchone()
    if existing:
        if not existing.get("synced"):
            cursor.execute("UPDATE expenses SET synced = 1 WHERE uuid = ?", (clean_uuid,))
            conn.commit()
        conn.close()
        return False

    # 2. Resolve user_id from created_by username
    creator = (created_by or "admin").strip()
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (creator,))
    user_row = cursor.fetchone()
    if user_row:
        user_id = user_row["id"]
    else:
        curr_session = get_current_session_user()
        if curr_session and curr_session["username"].lower() == creator.lower():
            user_id = curr_session["id"]
        else:
            user_id = 1

    # 3. Ensure category exists in categories table
    cat_clean = category.strip() if category else "Other"
    cursor.execute("SELECT id FROM categories WHERE LOWER(`key`) = LOWER(?)", (cat_clean,))
    if not cursor.fetchone():
        try:
            detected = auto_detect_category_info(cat_clean)
            cursor.execute("""
                INSERT INTO categories (`key`, label, icon_name, color, bg_color, is_custom)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (detected["key"], detected["label"], detected["icon_name"], detected["color"], detected["bg_color"]))
        except Exception:
            pass

    now_str = synced_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO expenses (uuid, title, amount, category, payment_mode, date, notes, user_id, created_by, synced, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    """, (clean_uuid, title.strip(), float(amount), cat_clean, payment_mode.strip() or "Cash", date.strip(), notes.strip(), user_id, creator, now_str, now_str))

    conn.commit()
    conn.close()
    return True

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
    """Retrieve expenses with optional filters and sorting, strictly enforcing multi-user isolation."""
    curr_user = get_current_session_user()
    if curr_user and curr_user.get("role") != "admin":
        user_id = curr_user["id"]
        username = curr_user["username"]

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

def get_unsynced_expenses(user_id: Optional[int] = None, username: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all expenses that have not yet been synced to Google Sheets, isolated by user."""
    curr_user = get_current_session_user()
    if curr_user and curr_user.get("role") != "admin":
        user_id = curr_user["id"]
        username = curr_user["username"]

    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM expenses WHERE synced = 0"
    params: List[Any] = []
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    elif username and username != "All":
        query += " AND created_by = ?"
        params.append(username)
    query += " ORDER BY date ASC, id ASC"

    cursor.execute(query, params)
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
    curr_user = get_current_session_user()
    if curr_user and curr_user.get("role") != "admin":
        user_id = curr_user["id"]
        username = curr_user["username"]

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
    Compute comprehensive statistics strictly isolated by user for non-admin accounts.
    """
    curr_user = get_current_session_user()
    if curr_user and curr_user.get("role") != "admin":
        user_id = curr_user["id"]
        username = curr_user["username"]

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
