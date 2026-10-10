import pymysql
import sqlite3

def init_mysql():
    conn = pymysql.connect(host='localhost', user='root', password='root', port=3306)
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS expenseflow_db")
    cursor.execute("USE expenseflow_db")

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

    conn.commit()
    cursor.execute("SHOW TABLES")
    tables = [r[0] for r in cursor.fetchall()]
    print("MySQL Tables in expenseflow_db:", tables)
    conn.close()

if __name__ == "__main__":
    init_mysql()
