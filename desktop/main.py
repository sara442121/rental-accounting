import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
from datetime import datetime, timedelta
import sys
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# افزودن مسیر اصلی پروژه برای دسترسی به database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, init_db

class Config:
    APP_NAME = "سیستم مدیریت اجاره و انبارداری ابزار"
    COLOR_PRIMARY = "#2C3E50"
    COLOR_SUCCESS = "#27AE60"
    COLOR_INFO = "#3498DB"
    COLOR_DANGER = "#E74C3C"
    COLOR_LIGHT = "#ECF0F1"

class MainApp:
    def __init__(self, root):
        self.root = root
        init_db()
        self.root.title(Config.APP_NAME)
        self.root.geometry("1200x800")
        self.create_ui()

    def create_ui(self):
        # Header
        header = tk.Frame(self.root, bg=Config.COLOR_PRIMARY, height=70)
        header.pack(fill=tk.X)
        tk.Label(header, text=Config.APP_NAME, font=("Segoe UI", 16, "bold"), bg=Config.COLOR_PRIMARY, fg="white").pack(pady=20)

        # Sidebar
        sidebar = tk.Frame(self.root, bg="#34495E", width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        buttons = [
            ("📦 مدیریت انبار", self.show_inventory),
            ("👥 مشتریان", self.show_customers),
            ("📄 ثبت اجاره (دقیقه‌ای)", self.show_rentals),
            ("💰 پیش‌فاکتور", self.show_pre_invoice),
            ("📊 گزارشات و خروجی", self.show_reports),
            ("❌ خروج", self.root.quit)
        ]
        for txt, cmd in buttons:
            tk.Button(sidebar, text=txt, command=cmd, bg="#34495E", fg="white", relief='flat', pady=15, font=("Segoe UI", 10)).pack(fill=tk.X)

        # Content Area
        self.content = tk.Frame(self.root, bg=Config.COLOR_LIGHT)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.show_inventory()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    # --- انبارداری و مدیریت کالا ---
    def show_inventory(self):
        self.clear_content()
        tk.Label(self.content, text="مدیریت موجودی انبار", font=("Segoe UI", 14, "bold"), bg=Config.COLOR_LIGHT).pack(pady=10)
        
        btn_frame = tk.Frame(self.content, bg=Config.COLOR_LIGHT)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="+ کالا جدید", command=self.add_tool_dialog, bg=Config.COLOR_SUCCESS, fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📥 خروجی اکسل انبار", command=self.export_inventory_excel, bg=Config.COLOR_INFO, fg="white").pack(side=tk.LEFT, padx=5)

        tree = ttk.Treeview(self.content, columns=("کد", "نام", "کل", "موجود", "اجاره‌ای", "قیمت/دقیقه"), show='headings')
        for col in tree["columns"]: tree.heading(col, text=col)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        conn = get_db_connection()
        tools = conn.execute("SELECT * FROM tools").fetchall()
        conn.close()
        for t in tools:
            rented = t['total_stock'] - t['current_stock']
            tree.insert('', 'end', values=(t['code'], t['name'], t['total_stock'], t['current_stock'], rented, t['price_per_minute']))

    def add_tool_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("افزودن کالا به انبار")
        win.geometry("400x500")
        
        fields = [("کد کالا:", "code"), ("نام کالا:", "name"), ("تعداد کل:", "stock"), ("قیمت هر دقیقه:", "p_min"), ("قیمت روزانه:", "p_day"), ("جریمه دیرکرد (دقیقه):", "late")]
        vars = {k: tk.StringVar() for _, k in fields}
        
        for label, key in fields:
            tk.Label(win, text=label).pack(pady=2)
            tk.Entry(win, textvariable=vars[key]).pack(pady=2, fill=tk.X, padx=30)

        def save():
            conn = get_db_connection()
            try:
                stock = int(vars["stock"].get())
                conn.execute("""INSERT INTO tools (code, name, total_stock, current_stock, price_per_minute, daily_price, late_fee_per_minute) 
                                VALUES (?,?,?,?,?,?,?)""", 
                             (vars["code"].get(), vars["name"].get(), stock, stock, float(vars["p_min"].get()), float(vars["p_day"].get()), float(vars["late"].get())))
                conn.commit()
                win.destroy()
                self.show_inventory()
            except Exception as e: messagebox.showerror("خطا", f"خطا: {e}")
            conn.close()
        tk.Button(win, text="ثبت در انبار", command=save, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=20)

    # --- مدیریت اجاره (دقیقه‌ای و کسری) ---
    def show_rentals(self):
        self.clear_content()
        tk.Label(self.content, text="ثبت اجاره و خروج از انبار", font=("Segoe UI", 14, "bold"), bg=Config.COLOR_LIGHT).pack(pady=10)
        
        tk.Button(self.content, text="+ ثبت خروج کالا", command=self.new_rental_dialog, bg=Config.COLOR_PRIMARY, fg="white").pack(pady=5)
        
        tree = ttk.Treeview(self.content, columns=("ID", "مشتری", "کالا", "تعداد خروج", "شروع", "وضعیت"), show='headings')
        for col in tree["columns"]: tree.heading(col, text=col)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        conn = get_db_connection()
        rentals = conn.execute("""SELECT r.id, cu.name as cname, t.name as tname, r.quantity_out, r.start_time, r.status 
                                  FROM rentals r JOIN customers cu ON r.customer_id=cu.id 
                                  JOIN tools t ON r.tool_id=t.id WHERE r.status='فعال'""").fetchall()
        conn.close()
        for r in rentals:
            tree.insert('', 'end', values=(r['id'], r['cname'], r['tname'], r['quantity_out'], r['start_time'], r['status']))

        tk.Button(self.content, text="✅ ثبت بازگشت و محاسبه کسری", command=self.return_tool_dialog, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=10)

    def new_rental_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("ثبت خروج کالا")
        win.geometry("400x400")
        
        conn = get_db_connection()
        customers = conn.execute("SELECT id, name FROM customers").fetchall()
        tools = conn.execute("SELECT id, name, current_stock FROM tools WHERE current_stock > 0").fetchall()
        conn.close()

        tk.Label(win, text="مشتری:").pack()
        c_cb = ttk.Combobox(win, values=[f"{c['id']}-{c['name']}" for c in customers])
        c_cb.pack(pady=5, fill=tk.X, padx=30)

        tk.Label(win, text="کالا:").pack()
        t_cb = ttk.Combobox(win, values=[f"{t['id']}-{t['name']} (موجود: {t['current_stock']})" for t in tools])
        t_cb.pack(pady=5, fill=tk.X, padx=30)

        tk.Label(win, text="تعداد خروجی:").pack()
        qty_e = tk.Entry(win); qty_e.insert(0, "1"); qty_e.pack()

        def save():
            try:
                c_id = int(c_cb.get().split('-')[0])
                t_id = int(t_cb.get().split('-')[0])
                qty = int(qty_e.get())
                start = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                conn = get_db_connection()
                tool = conn.execute("SELECT current_stock FROM tools WHERE id=?", (t_id,)).fetchone()
                if tool['current_stock'] < qty:
                    messagebox.showerror("خطا", "موجودی کافی نیست")
                    return
                
                conn.execute("INSERT INTO rentals (customer_id, tool_id, quantity_out, start_time) VALUES (?,?,?,?)",
                             (c_id, t_id, qty, start))
                conn.execute("UPDATE tools SET current_stock = current_stock - ? WHERE id=?", (qty, t_id))
                conn.commit()
                conn.close()
                win.destroy()
                self.show_rentals()
            except: messagebox.showerror("خطا", "ورودی نامعتبر")

        tk.Button(win, text="تایید خروج", command=save, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=20)

    def return_tool_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("ثبت بازگشت و محاسبه")
        win.geometry("400x450")
        
        tk.Label(win, text="شماره قرارداد (ID):").pack(pady=5)
        rid_e = tk.Entry(win); rid_e.pack()

        tk.Label(win, text="تعداد سالم برگشتی:").pack(pady=5)
        qty_in_e = tk.Entry(win); qty_in_e.pack()

        def process():
            rid = rid_e.get()
            qty_in = int(qty_in_e.get())
            conn = get_db_connection()
            r = conn.execute("""SELECT r.*, t.price_per_minute, t.late_fee_per_minute, t.name 
                                FROM rentals r JOIN tools t ON r.tool_id=t.id 
                                WHERE r.id=? AND r.status='فعال'""", (rid,)).fetchone()
            if not r:
                messagebox.showerror("خطا", "یافت نشد")
                return
            
            # محاسبه زمان و مبلغ
            start = datetime.strptime(r['start_time'], "%Y-%m-%d %H:%M")
            now = datetime.now()
            diff_min = (now - start).total_seconds() / 60
            amount = diff_min * r['price_per_minute']
            
            # محاسبه کسری
            shortage = r['quantity_out'] - qty_in
            
            msg = f"کالا: {r['name']}\nمدت اجاره: {diff_min:.1f} دقیقه\nمبلغ اجاره: {amount:.0f}\nتعداد کسری: {shortage}"
            if messagebox.askyesno("تایید تسویه", msg + "\n\nآیا تسویه انجام شود؟"):
                conn.execute("""UPDATE rentals SET quantity_in=?, shortage=?, actual_return_time=?, 
                                total_amount=?, status='تسویه شده' WHERE id=?""", 
                             (qty_in, shortage, now.strftime("%Y-%m-%d %H:%M"), amount, rid))
                conn.execute("UPDATE tools SET current_stock = current_stock + ? WHERE id=?", (qty_in, r['tool_id']))
                conn.commit()
                messagebox.showinfo("موفقیت", "تسویه ثبت شد")
                win.destroy()
                self.show_rentals()
            conn.close()

        tk.Button(win, text="محاسبه نهایی", command=process, bg=Config.COLOR_PRIMARY, fg="white").pack(pady=20)

    # --- پیش‌فاکتور با تاریخ اختیاری ---
    def show_pre_invoice(self):
        self.clear_content()
        tk.Label(self.content, text="صدور پیش‌فاکتور", font=("Segoe UI", 14, "bold"), bg=Config.COLOR_LIGHT).pack(pady=10)
        
        fields = [("مشتری (ID):", "cid"), ("کالا (ID):", "tid"), ("تاریخ اختیاری:", "date"), ("مبلغ تخمینی:", "amt"), ("توضیحات:", "note")]
        vars = {k: tk.StringVar() for _, k in fields}
        vars["date"].set(datetime.now().strftime("%Y-%m-%d"))

        for label, key in fields:
            tk.Label(self.content, text=label, bg=Config.COLOR_LIGHT).pack()
            tk.Entry(self.content, textvariable=vars[key]).pack(pady=2)

        def save_pre():
            conn = get_db_connection()
            conn.execute("INSERT INTO pre_invoices (customer_id, tool_id, date, amount, notes) VALUES (?,?,?,?,?)",
                         (vars["cid"].get(), vars["tid"].get(), vars["date"].get(), vars["amt"].get(), vars["note"].get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("موفقیت", "پیش‌فاکتور صادر شد")
            self.export_pre_invoice_pdf(vars)

        tk.Button(self.content, text="💾 صدور و چاپ PDF", command=save_pre, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=10)

    # --- گزارشات و خروجی‌ها ---
    def show_reports(self):
        self.clear_content()
        tk.Label(self.content, text="گزارشات و چاپ", font=("Segoe UI", 14, "bold"), bg=Config.COLOR_LIGHT).pack(pady=10)
        
        tk.Button(self.content, text="📥 خروجی اکسل تمامی اجاره‌ها", command=self.export_rentals_excel, bg=Config.COLOR_INFO, fg="white", width=30).pack(pady=10)
        tk.Button(self.content, text="📄 گزارش PDF وضعیت انبار", command=self.export_inventory_pdf, bg="#9B59B6", fg="white", width=30).pack(pady=10)

    def export_inventory_excel(self):
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM tools", conn)
        conn.close()
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if path:
            df.to_excel(path, index=False)
            messagebox.showinfo("موفقیت", "فایل اکسل ذخیره شد")

    def export_rentals_excel(self):
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM rentals", conn)
        conn.close()
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if path:
            df.to_excel(path, index=False)
            messagebox.showinfo("موفقیت", "گزارش اکسل ساخته شد")

    def export_pre_invoice_pdf(self, vars):
        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if not path: return
        c = canvas.Canvas(path, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(300, 800, "PRE-INVOICE / پیش‌فاکتور")
        c.setFont("Helvetica", 12)
        c.drawString(50, 750, f"Date: {vars['date'].get()}")
        c.drawString(50, 730, f"Customer ID: {vars['cid'].get()}")
        c.drawString(50, 710, f"Tool ID: {vars['tid'].get()}")
        c.drawString(50, 690, f"Estimated Amount: {vars['amt'].get()}")
        c.drawString(50, 670, f"Notes: {vars['note'].get()}")
        c.save()
        messagebox.showinfo("PDF", "پیش‌فاکتور PDF ساخته شد. آماده چاپ.")

    def export_inventory_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if not path: return
        c = canvas.Canvas(path, pagesize=A4)
        c.drawString(100, 800, "Inventory Status Report")
        conn = get_db_connection()
        tools = conn.execute("SELECT name, total_stock, current_stock FROM tools").fetchall()
        y = 780
        for t in tools:
            c.drawString(100, y, f"{t['name']} - Total: {t['total_stock']} - Available: {t['current_stock']}")
            y -= 20
        c.save()
        conn.close()
        messagebox.showinfo("PDF", "گزارش انبار ساخته شد")

    # --- متدهای کمکی مشتریان (قبلی) ---
    def show_customers(self):
        self.clear_content()
        tk.Label(self.content, text="مدیریت مشتریان", font=("Segoe UI", 14, "bold"), bg=Config.COLOR_LIGHT).pack(pady=10)
        tree = ttk.Treeview(self.content, columns=("کد ملی", "نام", "تلفن"), show='headings')
        for col in tree["columns"]: tree.heading(col, text=col)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        conn = get_db_connection()
        for c in conn.execute("SELECT * FROM customers").fetchall():
            tree.insert('', 'end', values=(c['c_code'], c['name'], c['phone']))
        conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
