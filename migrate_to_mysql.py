import pymysql
import sqlite3
import datetime
from config import DEFAULT_CATEGORIES, DEFAULT_SETTINGS

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "expenseflow_db",
}

def migrate_sqlite_to_mysql():
    conn = pymysql.connect(
        host=MYSQL_CONFIG["host"],
        port=MYSQL_CONFIG["port"],
        user=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"],
        database=MYSQL_CONFIG["database"],
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    # 1. Users
    sq_conn = sqlite3.connect("expenses.db")
    sq_conn.row_factory = sqlite3.Row
    sq_cursor = sq_conn.cursor()

    sq_cursor.execute("SELECT * FROM users")
    for u in sq_cursor.fetchall():
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, salt, full_name, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE full_name=VALUES(full_name)
        """, (u["id"], u["username"], u["password_hash"], u["salt"], u["full_name"], u["created_at"]))

    # 2. Categories
    sq_cursor.execute("SELECT * FROM categories")
    for cat in sq_cursor.fetchall():
        cursor.execute("""
            INSERT INTO categories (id, `key`, label, icon_name, color, bg_color, is_custom)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE label=VALUES(label)
        """, (cat["id"], cat["key"], cat["label"], cat["icon_name"], cat["color"], cat["bg_color"], cat["is_custom"]))

    # 3. Expenses
    sq_cursor.execute("SELECT * FROM expenses")
    for exp in sq_cursor.fetchall():
        user_id = exp["user_id"] if "user_id" in exp.keys() and exp["user_id"] else 1
        created_by = exp["created_by"] if "created_by" in exp.keys() and exp["created_by"] else "admin"
        cursor.execute("""
            INSERT INTO expenses (id, uuid, title, amount, category, payment_mode, date, notes, user_id, created_by, synced, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE title=VALUES(title)
        """, (exp["id"], exp["uuid"], exp["title"], exp["amount"], exp["category"], exp["payment_mode"], exp["date"], exp["notes"], user_id, created_by, exp["synced"], exp["created_at"], exp["updated_at"]))

    # 4. Settings
    sq_cursor.execute("SELECT * FROM settings")
    for s in sq_cursor.fetchall():
        cursor.execute("""
            INSERT INTO settings (`key`, value) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE value=VALUES(value)
        """, (s["key"], s["value"]))

    conn.commit()

    cursor.execute("SELECT COUNT(*) as count FROM expenses")
    exp_count = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()["count"]

    print(f"Migration complete! MySQL has {exp_count} expenses and {user_count} users.")
    conn.close()
    sq_conn.close()

if __name__ == "__main__":
    migrate_sqlite_to_mysql()
