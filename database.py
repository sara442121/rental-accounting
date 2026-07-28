import sqlite3
import os
import hashlib

DB_NAME = 'rental_accounting.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Users table for Login
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'operator' -- admin, operator
    )''')
    
    # Expenses table
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        amount REAL,
        category TEXT, -- تعمیرات, اجاره, حقوق, غیره
        date TEXT
    )''')
    
    # Customers
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        c_code TEXT UNIQUE,
        name TEXT NOT NULL,
        phone TEXT,
        photo_path TEXT
    )''')
    
    # Tools
    c.execute('''CREATE TABLE IF NOT EXISTS tools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT NOT NULL,
        price_per_minute REAL DEFAULT 0,
        daily_price REAL DEFAULT 0,
        late_fee_per_minute REAL DEFAULT 0,
        total_stock INTEGER DEFAULT 0,
        current_stock INTEGER DEFAULT 0,
        barcode TEXT UNIQUE
    )''')
    
    # Rentals
    c.execute('''CREATE TABLE IF NOT EXISTS rentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        tool_id INTEGER,
        quantity_out INTEGER DEFAULT 1,
        quantity_in INTEGER DEFAULT 0,
        shortage INTEGER DEFAULT 0,
        start_time TEXT,
        end_time_planned TEXT,
        actual_return_time TEXT,
        total_amount REAL DEFAULT 0,
        status TEXT DEFAULT 'فعال',
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (tool_id) REFERENCES tools(id)
    )''')

    # Add default admin user if not exists
    admin_exists = c.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    if not admin_exists:
        hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", ('admin', hashed_pw, 'admin'))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
