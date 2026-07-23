import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3
from datetime import datetime, timedelta, date
import os
import subprocess
import tempfile
import re

# ======================== Database Setup ========================
DB_NAME = 'rental_accounting.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Items
    c.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rate_per_minute REAL,
        rate_per_hour REAL,
        rate_per_day REAL,
        rate_per_week REAL,
        rate_per_month REAL,
        late_fee_per_hour REAL DEFAULT 0,
        grace_minutes INTEGER DEFAULT 0
    )''')
    # Customers
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT
    )''')
    # Rentals
    c.execute('''CREATE TABLE IF NOT EXISTS rentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        item_id INTEGER,
        unit TEXT CHECK(unit IN ('minute','hour','day','week','month')),
        rate_used REAL,
        quantity REAL,
        start_time TEXT,
        end_time_planned TEXT,
        actual_return_time TEXT,
        status TEXT DEFAULT 'active',
        total_rent REAL DEFAULT 0,
        late_fee REAL DEFAULT 0,
        final_amount REAL DEFAULT 0,
        is_paid INTEGER DEFAULT 0,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (item_id) REFERENCES items(id)
    )''')
    # Pre-invoices
    c.execute('''CREATE TABLE IF NOT EXISTS pre_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        invoice_date TEXT,
        due_date TEXT,
        status TEXT DEFAULT 'draft',
        notes TEXT,
        total_amount REAL DEFAULT 0,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pre_invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pre_invoice_id INTEGER,
        description TEXT,
        quantity REAL,
        unit_price REAL,
        amount REAL,
        FOREIGN KEY (pre_invoice_id) REFERENCES pre_invoices(id)
    )''')
    # Invoices (final)
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        invoice_date TEXT,
        due_date TEXT,
        total_amount REAL,
        status TEXT DEFAULT 'unpaid',   -- unpaid, paid, partially
        notes TEXT,
        origin_type TEXT,   -- 'rental' or 'pre_invoice'
        origin_id INTEGER,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )''')
    # Payments
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        amount REAL,
        payment_date TEXT,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id)
    )''')
    conn.commit()
    conn.close()

init_db()

# ======================== Utility Functions ========================
def get_customers():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name FROM customers")
    rows = c.fetchall()
    conn.close()
    return rows

def get_items():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name FROM items")
    rows = c.fetchall()
    conn.close()
    return rows

def item_by_id(item_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    conn.close()
    return row

def calculate_end_time(start_time_str, unit, quantity):
    start = datetime.fromisoformat(start_time_str)
    if unit == 'minute':
        return (start + timedelta(minutes=quantity)).isoformat()
    elif unit == 'hour':
        return (start + timedelta(hours=quantity)).isoformat()
    elif unit == 'day':
        return (start + timedelta(days=quantity)).isoformat()
    elif unit == 'week':
        return (start + timedelta(weeks=quantity)).isoformat()
    elif unit == 'month':
        return (start + timedelta(days=30*quantity)).isoformat()
    else:
        raise ValueError("Invalid unit")

def calculate_late_fee(planned_end_str, actual_return_str, grace_minutes, late_fee_per_hour):
    planned = datetime.fromisoformat(planned_end_str)
    actual = datetime.fromisoformat(actual_return_str)
    if actual <= planned:
        return 0.0
    delay_seconds = (actual - planned).total_seconds()
    delay_minutes = delay_seconds / 60
    effective_delay = max(0, delay_minutes - grace_minutes)
    return (effective_delay / 60) * late_fee_per_hour

def update_invoice_status_from_payments(invoice_id):
    """Calculate total paid and update invoice status."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM payments WHERE invoice_id=?", (invoice_id,))
    paid = c.fetchone()[0] or 0.0
    c.execute("SELECT total_amount FROM invoices WHERE id=?", (invoice_id,))
    total = c.fetchone()[0]
    if paid >= total:
        status = 'paid'
    elif paid > 0:
        status = 'partially'
    else:
        status = 'unpaid'
    c.execute("UPDATE invoices SET status=? WHERE id=?", (status, invoice_id))
    conn.commit()
    conn.close()

def refresh_treeview(tree, query, params=()):
    for i in tree.get_children():
        tree.delete(i)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    for row in c.fetchall():
        tree.insert("", "end", values=row)
    conn.close()

# ======================== PDF & Excel Export ========================
def export_to_pdf(data, columns, title="گزارش", filename=None):
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import mm
    except ImportError:
        messagebox.showerror("خطا", "کتابخانه reportlab نصب نیست. با pip install reportlab نصب کنید.")
        return
    if not filename:
        filename = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not filename:
            return
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4), topMargin=15*mm, bottomMargin=15*mm)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(title, styles['Title']))
    # Build table data
    table_data = [columns]
    for row in data:
        table_data.append([str(cell) if cell is not None else "" for cell in row])
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)
    messagebox.showinfo("موفق", f"فایل PDF ذخیره شد:\n{filename}")

def export_to_excel(data, columns, title="گزارش", filename=None):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
    except ImportError:
        messagebox.showerror("خطا", "کتابخانه openpyxl نصب نیست. با pip install openpyxl نصب کنید.")
        return
    if not filename:
        filename = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not filename:
            return
    wb = Workbook()
    ws = wb.active
    ws.title = title[:30]
    ws.append(columns)
    for row in data:
        ws.append(row)
    # style header
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    wb.save(filename)
    messagebox.showinfo("موفق", f"فایل Excel ذخیره شد:\n{filename}")

def print_pdf(pdf_path):
    """Open PDF with default application and send to printer."""
    try:
        if os.name == 'nt':
            os.startfile(pdf_path, 'print')
        else:
            subprocess.run(['lpr', pdf_path], check=True)
    except Exception as e:
        messagebox.showerror("خطا", f"امکان چاپ وجود ندارد: {e}")

# ======================== Main Application ========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("حسابداری اجاره کالا و ابزار - نسخه کامل")
        self.geometry("900x700")
        self.configure(bg="#f0f0f0")
        self.create_menu()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        self.build_tabs()

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="خروج", command=self.destroy)
        menubar.add_cascade(label="فایل", menu=file_menu)

    def build_tabs(self):
        # Dashboard
        dash_frame = ttk.Frame(self.notebook)
        self.notebook.add(dash_frame, text="داشبورد")
        tk.Label(dash_frame, text="به نرم‌افزار حسابداری اجاره خوش آمدید", font=('Tahoma', 14)).pack(pady=30)

        # Rentals
        rental_frame = ttk.Frame(self.notebook)
        self.notebook.add(rental_frame, text="اجاره‌ها")
        self.build_rental_tab(rental_frame)

        # Invoices
        invoice_frame = ttk.Frame(self.notebook)
        self.notebook.add(invoice_frame, text="فاکتورها")
        self.build_invoice_tab(invoice_frame)

        # Pre-invoices
        preinv_frame = ttk.Frame(self.notebook)
        self.notebook.add(preinv_frame, text="پیش‌فاکتورها")
        self.build_preinvoice_tab(preinv_frame)

        # Payments
        payment_frame = ttk.Frame(self.notebook)
        self.notebook.add(payment_frame, text="پرداخت‌ها")
        self.build_payment_tab(payment_frame)

        # Reports
        report_frame = ttk.Frame(self.notebook)
        self.notebook.add(report_frame, text="گزارشات")
        self.build_report_tab(report_frame)

        # Management
        manage_frame = ttk.Frame(self.notebook)
        self.notebook.add(manage_frame, text="مدیریت")
        self.build_management_tab(manage_frame)

    # ======================== Management Tab ========================
    def build_management_tab(self, parent):
        btn_frame = tk.Frame(parent)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="مدیریت کالاها", width=20, command=self.manage_items).pack(side='left', padx=5)
        tk.Button(btn_frame, text="مدیریت مشتریان", width=20, command=self.manage_customers).pack(side='left', padx=5)

    def manage_items(self):
        win = tk.Toplevel(self)
        win.title("مدیریت کالاها")
        win.geometry("750x450")
        columns = ("کد","نام","نرخ/دقیقه","نرخ/ساعت","نرخ/روز","نرخ/هفته","نرخ/ماه","جریمه/ساعت","مهلت(دقیقه)")
        tree = ttk.Treeview(win, columns=columns, show='headings')
        for col in columns:
            tree.heading(col, text=col)
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        refresh_treeview(tree, "SELECT * FROM items")

        def add_item():
            dialog = tk.Toplevel(win)
            dialog.title("افزودن کالا")
            fields = ["نام","نرخ/دقیقه","نرخ/ساعت","نرخ/روز","نرخ/هفته","نرخ/ماه","جریمه/ساعت","مهلت(دقیقه)"]
            entries = []
            for i, f in enumerate(fields):
                tk.Label(dialog, text=f).grid(row=i, column=0, sticky='e')
                e = tk.Entry(dialog); e.grid(row=i, column=1); entries.append(e)
            def save():
                try:
                    name = entries[0].get()
                    rates = [float(e.get()) for e in entries[1:6]]
                    late = float(entries[6].get())
                    grace = int(entries[7].get())
                except ValueError:
                    messagebox.showerror("خطا", "مقادیر عددی صحیح وارد کنید")
                    return
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute('''INSERT INTO items (name,rate_per_minute,rate_per_hour,rate_per_day,rate_per_week,rate_per_month,late_fee_per_hour,grace_minutes)
                             VALUES (?,?,?,?,?,?,?,?)''', (name, *rates, late, grace))
                conn.commit()
                conn.close()
                refresh_treeview(tree, "SELECT * FROM items")
                dialog.destroy()
            tk.Button(dialog, text="ذخیره", command=save).grid(row=len(fields), columnspan=2, pady=10)

        btn_frame2 = tk.Frame(win)
        btn_frame2.pack()
        tk.Button(btn_frame2, text="افزودن", command=add_item).pack(side='left', padx=5)
        tk.Button(btn_frame2, text="حذف", command=lambda: self.delete_record(tree, 'items')).pack(side='left')

    def manage_customers(self):
        win = tk.Toplevel(self)
        win.title("مدیریت مشتریان")
        win.geometry("500x400")
        columns = ("کد","نام","تلفن")
        tree = ttk.Treeview(win, columns=columns, show='headings')
        for col in columns:
            tree.heading(col, text=col)
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        refresh_treeview(tree, "SELECT * FROM customers")

        def add_customer():
            dialog = tk.Toplevel(win)
            dialog.title("افزودن مشتری")
            tk.Label(dialog, text="نام").grid(row=0, column=0)
            name_entry = tk.Entry(dialog); name_entry.grid(row=0, column=1)
            tk.Label(dialog, text="تلفن").grid(row=1, column=0)
            phone_entry = tk.Entry(dialog); phone_entry.grid(row=1, column=1)
            def save():
                name = name_entry.get()
                phone = phone_entry.get()
                if not name: return
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO customers (name, phone) VALUES (?,?)", (name, phone))
                conn.commit()
                conn.close()
                refresh_treeview(tree, "SELECT * FROM customers")
                dialog.destroy()
            tk.Button(dialog, text="ذخیره", command=save).grid(row=2, columnspan=2, pady=10)

        btn_frame2 = tk.Frame(win)
        btn_frame2.pack()
        tk.Button(btn_frame2, text="افزودن", command=add_customer).pack(side='left', padx=5)
        tk.Button(btn_frame2, text="حذف", command=lambda: self.delete_record(tree, 'customers')).pack(side='left')

    def delete_record(self, tree, table):
        sel = tree.selection()
        if not sel: return
        item_id = tree.item(sel[0])['values'][0]
        if messagebox.askyesno("تایید", "آیا از حذف این مورد اطمینان دارید؟"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
            conn.commit()
            conn.close()
            refresh_treeview(tree, f"SELECT * FROM {table}")

    # ======================== Rental Tab ========================
    def build_rental_tab(self, parent):
        btn_frame = tk.Frame(parent)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="ثبت اجاره جدید", command=self.new_rental).pack(side='left', padx=5)
        tk.Button(btn_frame, text="برگشت کالا", command=self.return_rental).pack(side='left', padx=5)
        tk.Button(btn_frame, text="بروزرسانی لیست", command=lambda: self.refresh_rentals_list(self.rental_tree)).pack(side='left', padx=5)

        self.rental_tree = ttk.Treeview(parent, columns=("کد","مشتری","کالا","واحد","تعداد","شروع","پایان","وضعیت"), show='headings')
        for col in self.rental_tree["columns"]:
            self.rental_tree.heading(col, text=col)
        self.rental_tree.pack(fill='both', expand=True, padx=10, pady=5)
        self.refresh_rentals_list(self.rental_tree)
        self.rental_tree.bind("<Double-1>", lambda e: self.view_rental_details(self.rental_tree))

    def refresh_rentals_list(self, tree):
        query = """SELECT r.id, cu.name, i.name, r.unit, r.quantity, r.start_time, r.end_time_planned, r.status
                   FROM rentals r
                   JOIN customers cu ON r.customer_id = cu.id
                   JOIN items i ON r.item_id = i.id
                   ORDER BY r.id DESC"""
        refresh_treeview(tree, query)

    def new_rental(self):
        win = tk.Toplevel(self)
        win.title("ثبت اجاره جدید")
        win.geometry("400x450")
        
        customers = get_customers()
        items = get_items()

        tk.Label(win, text="مشتری").grid(row=0, column=0, sticky='e')
        cust_cb = ttk.Combobox(win, values=[f"{c[0]}-{c[1]}" for c in customers]); cust_cb.grid(row=0, column=1)

        tk.Label(win, text="کالا").grid(row=1, column=0, sticky='e')
        item_cb = ttk.Combobox(win, values=[f"{i[0]}-{i[1]}" for i in items]); item_cb.grid(row=1, column=1)

        tk.Label(win, text="واحد").grid(row=2, column=0, sticky='e')
        unit_cb = ttk.Combobox(win, values=['minute','hour','day','week','month']); unit_cb.grid(row=2, column=1); unit_cb.set('day')

        tk.Label(win, text="تعداد").grid(row=3, column=0, sticky='e')
        qty_entry = tk.Entry(win); qty_entry.insert(0, "1"); qty_entry.grid(row=3, column=1)

        tk.Label(win, text="زمان شروع").grid(row=4, column=0, sticky='e')
        start_entry = tk.Entry(win); start_entry.insert(0, datetime.now().isoformat(sep=' ', timespec='minutes')); start_entry.grid(row=4, column=1)

        def save():
            try:
                c_id = int(cust_cb.get().split('-')[0])
                i_id = int(item_cb.get().split('-')[0])
                unit = unit_cb.get()
                qty = float(qty_entry.get())
                start_t = start_entry.get().replace(' ', 'T')
                
                item = item_by_id(i_id)
                rate_map = {'minute':2, 'hour':3, 'day':4, 'week':5, 'month':6}
                rate = item[rate_map[unit]]
                total_rent = rate * qty
                planned_end = calculate_end_time(start_t, unit, qty)

                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute('''INSERT INTO rentals (customer_id, item_id, unit, rate_used, quantity, start_time, end_time_planned, total_rent, status)
                             VALUES (?,?,?,?,?,?,?,?,?)''', (c_id, i_id, unit, rate, qty, start_t, planned_end, total_rent, 'active'))
                conn.commit()
                conn.close()
                messagebox.showinfo("موفق", "اجاره ثبت شد")
                self.refresh_rentals_list(self.rental_tree)
                win.destroy()
            except Exception as e:
                messagebox.showerror("خطا", f"خطا در ثبت: {e}")

        tk.Button(win, text="ثبت نهایی", command=save).grid(row=5, columnspan=2, pady=20)

    def return_rental(self):
        win = tk.Toplevel(self)
        win.title("برگشت کالا")
        win.geometry("400x200")
        tk.Label(win, text="شماره قرارداد").grid(row=0, column=0, sticky='e')
        rental_id_entry = tk.Entry(win); rental_id_entry.grid(row=0, column=1)
        tk.Label(win, text="زمان برگشت (YYYY-MM-DD HH:MM)").grid(row=1, column=0, sticky='e')
        ret_entry = tk.Entry(win); ret_entry.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M")); ret_entry.grid(row=1, column=1)

        def process():
            rental_id = rental_id_entry.get()
            ret_time = ret_entry.get()
            if not rental_id or not ret_time:
                messagebox.showerror("خطا", "فیلدها را پر کنید")
                return
            try:
                ret_dt = datetime.strptime(ret_time, "%Y-%m-%d %H:%M")
            except:
                messagebox.showerror("خطا", "فرمت تاریخ نادرست")
                return
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM rentals WHERE id=?", (rental_id,))
            rental = c.fetchone()
            if not rental:
                messagebox.showerror("خطا", "قرارداد یافت نشد")
                conn.close()
                return
            if rental[9] != 'active':
                messagebox.showerror("خطا", "قرارداد فعال نیست")
                conn.close()
                return
            item = item_by_id(rental[2])
            late_fee = calculate_late_fee(rental[7], ret_dt.isoformat(), item[8], item[7])
            final_amount = rental[10] + late_fee
            c.execute('''UPDATE rentals SET actual_return_time=?, status='returned', late_fee=?, final_amount=?
                         WHERE id=?''', (ret_dt.isoformat(), late_fee, final_amount, rental_id))
            # Auto-create invoice from rental
            c.execute('''INSERT INTO invoices (customer_id, invoice_date, total_amount, notes, origin_type, origin_id)
                         VALUES (?,?,?,?,?,?)''', (rental[1], datetime.now().isoformat(), final_amount, 'فاکتور خودکار اجاره', 'rental', rental_id))
            invoice_id = c.lastrowid
            conn.commit()
            conn.close()
            messagebox.showinfo("موفق", f"برگشت ثبت شد و فاکتور شماره {invoice_id} ایجاد گردید.\nمبلغ نهایی: {final_amount:,.0f}")
            win.destroy()
            self.refresh_rentals_list(self.rental_tree)
            self.refresh_invoices_list()

        tk.Button(win, text="ثبت برگشت", command=process).grid(row=2, columnspan=2, pady=15)

    def view_rental_details(self, tree):
        sel = tree.selection()
        if not sel:
            return
        rental_id = tree.item(sel[0])['values'][0]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''SELECT r.*, cu.name, i.name FROM rentals r
                     JOIN customers cu ON r.customer_id=cu.id
                     JOIN items i ON r.item_id=i.id
                     WHERE r.id=?''', (rental_id,))
        rental = c.fetchone()
        conn.close()
        if rental:
            msg = f"""شماره قرارداد: {rental[0]}
مشتری: {rental[14]}
کالا: {rental[15]}
واحد: {rental[3]} - تعداد: {rental[5]}
شروع: {rental[6]}
پایان: {rental[7]}
برگشت: {rental[8]}
اجاره: {rental[10]:,.0f} | جریمه: {rental[11]:,.0f} | نهایی: {rental[12]:,.0f}"""
            messagebox.showinfo("جزئیات قرارداد", msg)

    # ======================== Invoice Tab ========================
    def build_invoice_tab(self, parent):
        btn_frame = tk.Frame(parent)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="بروزرسانی لیست", command=self.refresh_invoices_list).pack(side='left', padx=5)
        tk.Button(btn_frame, text="ثبت پرداخت", command=self.new_payment).pack(side='left', padx=5)
        tk.Button(btn_frame, text="خروجی PDF", command=self.invoice_pdf_export).pack(side='left', padx=5)

        self.inv_tree = ttk.Treeview(parent, columns=("کد","مشتری","تاریخ","مبلغ کل","وضعیت","منبع"), show='headings')
        for col in self.inv_tree["columns"]:
            self.inv_tree.heading(col, text=col)
        self.inv_tree.pack(fill='both', expand=True, padx=10, pady=5)
        self.refresh_invoices_list()

    def refresh_invoices_list(self):
        query = """SELECT i.id, cu.name, i.invoice_date, i.total_amount, i.status, i.origin_type
                   FROM invoices i
                   JOIN customers cu ON i.customer_id = cu.id
                   ORDER BY i.id DESC"""
        refresh_treeview(self.inv_tree, query)

    def new_payment(self):
        win = tk.Toplevel(self)
        win.title("ثبت پرداخت")
        tk.Label(win, text="شماره فاکتور").grid(row=0, column=0)
        inv_id_entry = tk.Entry(win); inv_id_entry.grid(row=0, column=1)
        tk.Label(win, text="مبلغ").grid(row=1, column=0)
        amt_entry = tk.Entry(win); amt_entry.grid(row=1, column=1)
        def save():
            try:
                inv_id = int(inv_id_entry.get())
                amt = float(amt_entry.get())
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO payments (invoice_id, amount, payment_date) VALUES (?,?,?)", (inv_id, amt, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                update_invoice_status_from_payments(inv_id)
                messagebox.showinfo("موفق", "پرداخت ثبت شد")
                self.refresh_invoices_list()
                win.destroy()
            except: messagebox.showerror("خطا", "ورودی نادرست")
        tk.Button(win, text="ذخیره", command=save).grid(row=2, columnspan=2, pady=10)

    def invoice_pdf_export(self):
        sel = self.inv_tree.selection()
        if not sel: return
        inv_id = self.inv_tree.item(sel[0])['values'][0]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT i.*, cu.name FROM invoices i JOIN customers cu ON i.customer_id=cu.id WHERE i.id=?", (inv_id,))
        inv = c.fetchone()
        conn.close()
        data = [[inv[0], inv[10], inv[2], f"{inv[4]:,.0f}", inv[5]]]
        export_to_pdf(data, ["کد فاکتور","مشتری","تاریخ","مبلغ","وضعیت"], title=f"Invoice #{inv_id}")

    # ======================== Pre-invoice Tab ========================
    def build_preinvoice_tab(self, parent):
        tk.Label(parent, text="مدیریت پیش‌فاکتورها (به زودی در آپدیت بعدی تکمیل می‌شود)").pack(pady=20)

    # ======================== Payment Tab ========================
    def build_payment_tab(self, parent):
        self.pay_tree = ttk.Treeview(parent, columns=("کد","فاکتور","مبلغ","تاریخ"), show='headings')
        for col in self.pay_tree["columns"]:
            self.pay_tree.heading(col, text=col)
        self.pay_tree.pack(fill='both', expand=True, padx=10, pady=5)
        tk.Button(parent, text="بروزرسانی", command=lambda: refresh_treeview(self.pay_tree, "SELECT * FROM payments ORDER BY id DESC")).pack()

    # ======================== Report Tab ========================
    def build_report_tab(self, parent):
        tk.Button(parent, text="گزارش کل درآمد (Excel)", command=self.report_income_excel).pack(pady=10)

    def report_income_excel(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, invoice_date, total_amount, status FROM invoices")
        data = c.fetchall()
        conn.close()
        export_to_excel(data, ["کد","تاریخ","مبلغ","وضعیت"], title="Income Report")

if __name__ == "__main__":
    app = App()
    app.mainloop()
