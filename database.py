import sqlite3
import os

DB_NAME = 'rental_accounting.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Customers table
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        c_code TEXT UNIQUE,
        name TEXT NOT NULL,
        phone TEXT,
        photo_path TEXT
    )''')
    # Tools/Items table
    c.execute('''CREATE TABLE IF NOT EXISTS tools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT NOT NULL,
        hourly_price REAL,
        daily_price REAL,
        weekly_price REAL,
        monthly_price REAL,
        late_fee_per_hour REAL DEFAULT 0,
        status TEXT DEFAULT 'در انبار'
    )''')
    # Rentals table
    c.execute('''CREATE TABLE IF NOT EXISTS rentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        tool_id INTEGER,
        start_time TEXT,
        end_time_planned TEXT,
        actual_return_time TEXT,
        period TEXT,
        amount REAL,
        status TEXT DEFAULT 'فعال',
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (tool_id) REFERENCES tools(id)
    )''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
