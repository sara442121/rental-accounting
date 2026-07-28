import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
from datetime import datetime
import sys
import pandas as pd
import hashlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# افزودن مسیر اصلی پروژه برای دسترسی به ماژول‌ها
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, init_db
from backup_manager import start_auto_backup, create_local_backup
from sms_service import send_rental_reminder

class Config:
    APP_NAME = "نرم‌افزار جامع حسابداری و انبارداری (تجاری)"
    COLOR_PRIMARY = "#2C3E50"
    COLOR_SUCCESS = "#27AE60"
    COLOR_DANGER = "#E74C3C"
    COLOR_DARK = "#34495E"
    COLOR_LIGHT = "#ECF0F1"

class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("ورود ایمن")
        self.root.geometry("350x450")
        self.root.configure(bg=Config.COLOR_DARK)
        
        tk.Label(self.root, text="سیستم مدیریت ابزارآلات", font=("Segoe UI", 14, "bold"), bg=Config.COLOR_DARK, fg="white").pack(pady=30)
        
        tk.Label(self.root, text="نام کاربری:", bg=Config.COLOR_DARK, fg="white").pack()
        self.user_e = tk.Entry(self.root, justify='center'); self.user_e.pack(pady=10)
        
        tk.Label(self.root, text="رمز عبور:", bg=Config.COLOR_DARK, fg="white").pack()
        self.pass_e = tk.Entry(self.root, show="*", justify='center'); self.pass_e.pack(pady=10)
        
        tk.Button(self.root, text="ورود به سیستم", command=self.login, bg=Config.COLOR_SUCCESS, fg="white", width=15).pack(pady=20)

    def login(self):
        user = self.user_e.get()
        pw = hashlib.sha256(self.pass_e.get().encode()).hexdigest()
        conn = get_db_connection()
        res = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pw)).fetchone()
        conn.close()
        if res:
            self.root.destroy()
            main_root = tk.Tk()
            MainApp(main_root, res['role'])
            main_root.mainloop()
        else:
            messagebox.showerror("خطا", "اطلاعات ورود اشتباه است")

class MainApp:
    def __init__(self, root, role):
        self.root = root
        self.role = role
        init_db()
        start_auto_backup() # فعال‌سازی بک‌آپ خودکار در شروع برنامه
        self.root.title(f"{Config.APP_NAME} - ({role})")
        self.root.geometry("1200x800")
        self.create_ui()

    def create_ui(self):
        sidebar = tk.Frame(self.root, bg=Config.COLOR_DARK, width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        menu = [
            ("📊 داشبورد مدیریتی", self.show_dashboard),
            ("📦 انبار و بارکدخوان", self.show_inventory),
            ("📄 مدیریت اجاره", self.show_rentals),
            ("💸 مالی و هزینه‌ها", self.show_finance),
            ("👥 مشتریان", self.show_customers),
            ("⚙️ تنظیمات و بک‌آپ", self.show_settings)
        ]
        for txt, cmd in menu:
            tk.Button(sidebar, text=txt, command=cmd, bg=Config.COLOR_DARK, fg="white", relief='flat', pady=15, font=("Segoe UI", 10)).pack(fill=tk.X)

        self.content = tk.Frame(self.root, bg=Config.COLOR_LIGHT)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.show_dashboard()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    # --- داشبورد تحلیلی ---
    def show_dashboard(self):
        self.clear_content()
        tk.Label(self.content, text="داشبورد تحلیلی و سود خالص", font=("Segoe UI", 16, "bold"), bg=Config.COLOR_LIGHT).pack(pady=10)
        
        conn = get_db_connection()
        income = conn.execute("SELECT SUM(total_amount) FROM rentals WHERE status='تسویه شده'").fetchone()[0] or 0
        expenses = conn.execute("SELECT SUM(amount) FROM expenses").fetchone()[0] or 0
        profit = income - expenses
        conn.close()

        stats_frame = tk.Frame(self.content, bg=Config.COLOR_LIGHT)
        stats_frame.pack(pady=20)
        for t, v, c in [("درآمد کل", f"{income:,.0f}", "green"), ("هزینه کل", f"{expenses:,.0f}", "red"), ("سود خالص", f"{profit:,.0f}", "blue")]:
            f = tk.Frame(stats_frame, bg="white", padx=40, pady=15, bd=1, relief='solid')
            f.pack(side=tk.LEFT, padx=10)
            tk.Label(f, text=t, bg="white").pack()
            tk.Label(f, text=v, bg="white", font=("Segoe UI", 14, "bold"), fg=c).pack()

        # نمودار مالی
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.pie([income, expenses], labels=['Income', 'Expenses'], autopct='%1.1f%%', colors=['#27AE60', '#E74C3C'])
        ax.set_title("Income vs Expenses Distribution")
        
        canvas = FigureCanvasTkAgg(fig, master=self.content)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=10, fill=tk.BOTH, expand=True)

    # --- انبار و بارکد ---
    def show_inventory(self):
        self.clear_content()
        tk.Label(self.content, text="مدیریت هوشمند انبار و بارکد", font=("Segoe UI", 16, "bold"), bg=Config.COLOR_LIGHT).pack(pady=10)
        
        search_frame = tk.Frame(self.content, bg="white", pady=10)
        search_frame.pack(fill=tk.X, padx=20)
        tk.Label(search_frame, text="🔍 اسکن بارکد کالا:", bg="white").pack(side=tk.LEFT, padx=10)
        barcode_e = tk.Entry(search_frame, width=30); barcode_e.pack(side=tk.LEFT, padx=10)
        barcode_e.focus() # تمرکز خودکار برای استفاده از اسکنر

        def handle_scan():
            conn = get_db_connection()
            tool = conn.execute("SELECT * FROM tools WHERE barcode=?", (barcode_e.get(),)).fetchone()
            conn.close()
            if tool: messagebox.showinfo("بارکد یافت شد", f"نام کالا: {tool['name']}\nموجودی فعلی: {tool['current_stock']}")
            else: messagebox.showwarning("خطا", "بارکد در سیستم تعریف نشده است.")
            barcode_e.delete(0, tk.END)

        tk.Button(search_frame, text="بررسی بارکد", command=handle_scan, bg=Config.COLOR_PRIMARY, fg="white").pack(side=tk.LEFT)

        # جدول کالاها
        tree = ttk.Treeview(self.content, columns=("کد", "نام", "موجودی", "بارکد"), show='headings')
        for col in tree["columns"]: tree.heading(col, text=col)
        tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        conn = get_db_connection()
        for t in conn.execute("SELECT * FROM tools").fetchall():
            tree.insert('', 'end', values=(t['code'], t['name'], t['current_stock'], t['barcode']))
        conn.close()

    # --- تنظیمات و پشتیبان‌گیری ---
    def show_settings(self):
        self.clear_content()
        tk.Label(self.content, text="تنظیمات سیستم و امنیت داده‌ها", font=("Segoe UI", 16, "bold"), bg=Config.COLOR_LIGHT).pack(pady=10)
        
        backup_frame = tk.Frame(self.content, bg="white", pdy=20, padx=20)
        backup_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(backup_frame, text="🛡️ وضعیت پشتیبان‌گیری:", bg="white", font=("Segoe UI", 11)).pack(side=tk.LEFT)
        
        def manual_backup():
            path = create_local_backup()
            if path: messagebox.showinfo("موفقیت", f"فایل پشتیبان با موفقیت در مسیر زیر ذخیره شد:\n{path}")
        
        tk.Button(backup_frame, text="ایجاد پشتیبان دستی (فوری)", command=manual_backup, bg=Config.COLOR_SUCCESS, fg="white").pack(side=tk.RIGHT)

        # مدیریت کاربران
        tk.Label(self.content, text="مدیریت دسترسی کاربران", font=("Segoe UI", 12, "bold"), bg=Config.COLOR_LIGHT).pack(pady=20)
        user_tree = ttk.Treeview(self.content, columns=("ID", "نام کاربری", "نقش"), show='headings')
        user_tree.heading("ID", text="ID"); user_tree.heading("نام کاربری", text="نام کاربری"); user_tree.heading("نقش", text="نقش")
        user_tree.pack(fill=tk.X, padx=20)
        
        conn = get_db_connection()
        for u in conn.execute("SELECT id, username, role FROM users").fetchall():
            user_tree.insert('', 'end', values=(u['id'], u['username'], u['role']))
        conn.close()

    # --- متدهای کمکی (اجاره، مشتری، مالی) ---
    def show_rentals(self): self.clear_content(); tk.Label(self.content, text="مدیریت اجاره").pack()
    def show_finance(self): self.clear_content(); tk.Label(self.content, text="مدیریت مالی").pack()
    def show_customers(self): self.clear_content(); tk.Label(self.content, text="مدیریت مشتریان").pack()

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()
