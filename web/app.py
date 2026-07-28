from flask import Flask, render_template, request, redirect, url_for, flash, session
import sys
import os
import pandas as pd
from datetime import datetime

# افزودن مسیر اصلی پروژه برای دسترسی به database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = "commercial_accounting_secret"
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    income = conn.execute("SELECT SUM(total_amount) FROM rentals WHERE status='تسویه شده'").fetchone()[0] or 0
    expenses = conn.execute("SELECT SUM(amount) FROM expenses").fetchone()[0] or 0
    conn.close()
    return render_template('index.html', income=income, expenses=expenses, profit=income-expenses)

@app.route('/import_tools', methods=['POST'])
def import_tools():
    if 'file' not in request.files: return redirect(request.url)
    file = request.files['file']
    if file.filename == '': return redirect(request.url)
    
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    
    try:
        df = pd.read_excel(path) if path.endswith('.xlsx') else pd.read_csv(path)
        conn = get_db_connection()
        for _, row in df.iterrows():
            conn.execute("INSERT OR IGNORE INTO tools (code, name, total_stock, current_stock) VALUES (?,?,?,?)",
                         (row['کد'], row['نام'], row['تعداد'], row['تعداد']))
        conn.commit()
        conn.close()
        flash("کالاها با موفقیت وارد شدند")
    except Exception as e:
        flash(f"خطا در پردازش فایل: {e}")
    
    return redirect(url_for('dashboard'))

# متدهای login و logout مشابه قبل...
if __name__ == '__main__':
    app.run(debug=True, port=5000)
