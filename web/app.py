from flask import Flask, render_template, request, redirect, url_for, flash
import sys
import os
from datetime import datetime, timedelta

# افزودن مسیر اصلی پروژه برای دسترسی به database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = "secret_key_for_session"

# ایجاد دیتابیس در اولین اجرا
with app.app_context():
    init_db()

@app.route('/')
def dashboard():
    conn = get_db_connection()
    c_count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    t_count = conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
    r_count = conn.execute("SELECT COUNT(*) FROM rentals WHERE status='فعال'").fetchone()[0]
    recent_rentals = conn.execute("""SELECT r.*, cu.name as cname, t.name as tname 
                                     FROM rentals r JOIN customers cu ON r.customer_id=cu.id 
                                     JOIN tools t ON r.tool_id=t.id ORDER BY r.id DESC LIMIT 5""").fetchall()
    conn.close()
    return render_template('index.html', c_count=c_count, t_count=t_count, r_count=r_count, recent_rentals=recent_rentals)

@app.route('/customers')
def customer_list():
    conn = get_db_connection()
    customers = conn.execute("SELECT * FROM customers").fetchall()
    conn.close()
    return render_template('customers.html', customers=customers)

@app.route('/tools')
def tools_list():
    conn = get_db_connection()
    tools = conn.execute("SELECT * FROM tools").fetchall()
    conn.close()
    return render_template('tools.html', tools=tools)

@app.route('/rentals')
def rentals_list():
    conn = get_db_connection()
    rentals = conn.execute("""SELECT r.*, cu.name as cname, t.name as tname 
                              FROM rentals r JOIN customers cu ON r.customer_id=cu.id 
                              JOIN tools t ON r.tool_id=t.id ORDER BY r.id DESC""").fetchall()
    conn.close()
    return render_template('rentals.html', rentals=rentals)

@app.route('/add_customer', methods=['POST'])
def add_customer():
    name = request.form['name']
    c_code = request.form['c_code']
    phone = request.form['phone']
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO customers (c_code, name, phone) VALUES (?,?,?)", (c_code, name, phone))
        conn.commit()
    except:
        flash("خطا: کد ملی تکراری است")
    conn.close()
    return redirect(url_for('customer_list'))

@app.route('/add_tool', methods=['POST'])
def add_tool():
    name = request.form['name']
    code = request.form['code']
    d_price = request.form['daily_price']
    conn = get_db_connection()
    conn.execute("INSERT INTO tools (code, name, daily_price) VALUES (?,?,?)", (code, name, d_price))
    conn.commit()
    conn.close()
    return redirect(url_for('tools_list'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
