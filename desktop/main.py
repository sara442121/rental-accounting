import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
from datetime import datetime, timedelta
import sys

# افزودن مسیر اصلی پروژه برای دسترسی به database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, init_db

# تنظیمات پایه
class Config:
    APP_NAME = "سیستم حسابداری ابزارالات (نسخه حرفه‌ای)"
    FONT_TITLE = ("Segoe UI", 14, "bold")
    COLOR_PRIMARY = "#2C3E50"
    COLOR_SUCCESS = "#27AE60"
    COLOR_DANGER = "#E74C3C"
    COLOR_LIGHT = "#ECF0F1"
    IMAGE_DIR = "data/images"

# ایجاد پوشه تصاویر در صورت نبودن
if not os.path.exists(Config.IMAGE_DIR):
    os.makedirs(Config.IMAGE_DIR)

class MainApp:
    def __init__(self, root):
        self.root = root
        init_db()
        self.root.title(Config.APP_NAME)
        self.root.geometry("1100x700")
        self.create_ui()

    def create_ui(self):
        header = tk.Frame(self.root, bg=Config.COLOR_PRIMARY, height=60)
        header.pack(fill=tk.X)
        tk.Label(header, text=Config.APP_NAME, font=Config.FONT_TITLE, bg=Config.COLOR_PRIMARY, fg="white").pack(pady=15)

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(main_frame, bg="#34495E", width=180)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        menu_items = [
            ("مشتریان", self.show_customers),
            ("کالاها", self.show_tools),
            ("اجاره‌های فعال", self.show_rentals),
            ("ثبت بازگشت", self.show_return_tool),
            ("خروج", self.root.quit)
        ]
        for txt, cmd in menu_items:
            tk.Button(sidebar, text=txt, command=cmd, bg="#34495E", fg="white", relief='flat', pady=10).pack(fill=tk.X)

        self.content = tk.Frame(main_frame, bg=Config.COLOR_LIGHT)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.show_rentals()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    # --- بخش مشتریان ---
    def show_customers(self):
        self.clear_content()
        tk.Label(self.content, text="مدیریت مشتریان", font=Config.FONT_TITLE, bg=Config.COLOR_LIGHT).pack(pady=10)
        tk.Button(self.content, text="+ مشتری جدید", command=self.add_customer_dialog, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=5)
        
        tree = ttk.Treeview(self.content, columns=("کد ملی", "نام", "تلفن"), show='headings')
        tree.heading("کد ملی", text="کد ملی")
        tree.heading("نام", text="نام و نام خانوادگی")
        tree.heading("تلفن", text="تلفن")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        conn = get_db_connection()
        customers = conn.execute("SELECT * FROM customers").fetchall()
        conn.close()
        for c in customers:
            tree.insert('', 'end', values=(c['c_code'], c['name'], c['phone']))

    def add_customer_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("افزودن مشتری")
        win.geometry("350x400")
        
        vars = {
            "c_code": tk.StringVar(),
            "name": tk.StringVar(),
            "phone": tk.StringVar(),
            "photo": tk.StringVar()
        }
        
        for i, (label, key) in enumerate([("کد ملی:", "c_code"), ("نام:", "name"), ("تلفن:", "phone")]):
            tk.Label(win, text=label).pack(pady=5)
            tk.Entry(win, textvariable=vars[key]).pack(pady=5, fill=tk.X, padx=20)
        
        def pick_photo():
            path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png")])
            if path: vars["photo"].set(path)
            
        tk.Button(win, text="انتخاب عکس کارت ملی", command=pick_photo).pack(pady=10)
        
        def save():
            if not vars["c_code"].get() or not vars["name"].get():
                messagebox.showerror("خطا", "فیلدها را پر کنید")
                return
            
            final_photo_path = ""
            if vars["photo"].get():
                ext = os.path.splitext(vars["photo"].get())[1]
                final_photo_path = os.path.join(Config.IMAGE_DIR, f"{vars['c_code'].get()}{ext}")
                shutil.copy(vars["photo"].get(), final_photo_path)

            conn = get_db_connection()
            try:
                conn.execute("INSERT INTO customers (c_code, name, phone, photo_path) VALUES (?,?,?,?)",
                             (vars["c_code"].get(), vars["name"].get(), vars["phone"].get(), final_photo_path))
                conn.commit()
                messagebox.showinfo("موفقیت", "مشتری ثبت شد")
                win.destroy()
                self.show_customers()
            except:
                messagebox.showerror("خطا", "کد ملی تکراری است")
            conn.close()

        tk.Button(win, text="ذخیره", command=save, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=10)

    # --- بخش کالاها ---
    def show_tools(self):
        self.clear_content()
        tk.Label(self.content, text="مدیریت کالاها", font=Config.FONT_TITLE, bg=Config.COLOR_LIGHT).pack(pady=10)
        tk.Button(self.content, text="+ کالا جدید", command=self.add_tool_dialog, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=5)
        
        tree = ttk.Treeview(self.content, columns=("کد", "نام", "روزانه", "ساعتی", "وضعیت"), show='headings')
        for col in tree["columns"]: tree.heading(col, text=col)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        conn = get_db_connection()
        tools = conn.execute("SELECT * FROM tools").fetchall()
        conn.close()
        for t in tools:
            tree.insert('', 'end', values=(t['code'], t['name'], t['daily_price'], t['hourly_price'], t['status']))

    def add_tool_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("افزودن کالا")
        win.geometry("350x450")
        
        vars = {k: tk.StringVar() for k in ["code", "name", "h_price", "d_price", "late_fee"]}
        for label, key in [("کد کالا:", "code"), ("نام کالا:", "name"), ("قیمت ساعتی:", "h_price"), ("قیمت روزانه:", "d_price"), ("جریمه دیرکرد (ساعت):", "late_fee")]:
            tk.Label(win, text=label).pack(pady=2)
            tk.Entry(win, textvariable=vars[key]).pack(pady=2, fill=tk.X, padx=20)

        def save():
            conn = get_db_connection()
            try:
                conn.execute("INSERT INTO tools (code, name, hourly_price, daily_price, late_fee_per_hour) VALUES (?,?,?,?,?)",
                             (vars["code"].get(), vars["name"].get(), float(vars["h_price"].get()), float(vars["d_price"].get()), float(vars["late_fee"].get())))
                conn.commit()
                win.destroy()
                self.show_tools()
            except Exception as e:
                messagebox.showerror("خطا", f"خطا در ثبت: {e}")
            conn.close()
        tk.Button(win, text="ذخیره", command=save, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=10)

    # --- بخش اجاره‌ها ---
    def show_rentals(self):
        self.clear_content()
        tk.Label(self.content, text="قراردادهای فعال", font=Config.FONT_TITLE, bg=Config.COLOR_LIGHT).pack(pady=10)
        tk.Button(self.content, text="+ قرارداد جدید", command=self.new_rental_dialog, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=5)
        
        tree = ttk.Treeview(self.content, columns=("ID", "مشتری", "کالا", "شروع", "پایان", "مبلغ"), show='headings')
        for col in tree["columns"]: tree.heading(col, text=col)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        conn = get_db_connection()
        rentals = conn.execute("""SELECT r.id, cu.name as cname, t.name as tname, r.start_time, r.end_time_planned, r.amount 
                                  FROM rentals r JOIN customers cu ON r.customer_id=cu.id 
                                  JOIN tools t ON r.tool_id=t.id WHERE r.status='فعال'""").fetchall()
        conn.close()
        for r in rentals:
            tree.insert('', 'end', values=(r['id'], r['cname'], r['tname'], r['start_time'], r['end_time_planned'], r['amount']))

    def new_rental_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("ثبت اجاره")
        win.geometry("400x500")
        
        conn = get_db_connection()
        customers = conn.execute("SELECT id, name FROM customers").fetchall()
        tools = conn.execute("SELECT id, name FROM tools WHERE status='در انبار'").fetchall()
        conn.close()

        tk.Label(win, text="انتخاب مشتری:").pack()
        c_cb = ttk.Combobox(win, values=[f"{c['id']}-{c['name']}" for c in customers])
        c_cb.pack(pady=5, fill=tk.X, padx=20)

        tk.Label(win, text="انتخاب کالا:").pack()
        t_cb = ttk.Combobox(win, values=[f"{t['id']}-{t['name']}" for t in tools])
        t_cb.pack(pady=5, fill=tk.X, padx=20)

        tk.Label(win, text="مدت (روز):").pack()
        days_e = tk.Entry(win); days_e.insert(0, "1"); days_e.pack()

        def save():
            try:
                c_id = int(c_cb.get().split('-')[0])
                t_id = int(t_cb.get().split('-')[0])
                days = int(days_e.get())
                start = datetime.now().strftime("%Y-%m-%d %H:%M")
                end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
                
                conn = get_db_connection()
                tool = conn.execute("SELECT daily_price FROM tools WHERE id=?", (t_id,)).fetchone()
                amount = tool['daily_price'] * days
                
                conn.execute("INSERT INTO rentals (customer_id, tool_id, start_time, end_time_planned, amount) VALUES (?,?,?,?,?)",
                             (c_id, t_id, start, end, amount))
                conn.execute("UPDATE tools SET status='در حال اجاره' WHERE id=?", (t_id,))
                conn.commit()
                conn.close()
                win.destroy()
                self.show_rentals()
            except: messagebox.showerror("خطا", "ورودی نامعتبر")

        tk.Button(win, text="ثبت نهایی", command=save, bg=Config.COLOR_SUCCESS, fg="white").pack(pady=20)

    # --- بخش بازگشت کالا ---
    def show_return_tool(self):
        self.clear_content()
        tk.Label(self.content, text="ثبت بازگشت کالا و محاسبه تسویه", font=Config.FONT_TITLE, bg=Config.COLOR_LIGHT).pack(pady=10)
        
        tk.Label(self.content, text="شماره قرارداد (ID):", bg=Config.COLOR_LIGHT).pack()
        rid_e = tk.Entry(self.content); rid_e.pack(pady=5)
        
        def calculate():
            rid = rid_e.get()
            conn = get_db_connection()
            rental = conn.execute("""SELECT r.*, t.name, t.late_fee_per_hour FROM rentals r 
                                     JOIN tools t ON r.tool_id=t.id WHERE r.id=? AND r.status='فعال'""", (rid,)).fetchone()
            if not rental:
                messagebox.showerror("خطا", "قرارداد فعال یافت نشد")
                return
            
            now = datetime.now()
            planned = datetime.strptime(rental['end_time_planned'], "%Y-%m-%d %H:%M")
            late_fee = 0
            if now > planned:
                hours_late = (now - planned).total_seconds() / 3600
                late_fee = hours_late * rental['late_fee_per_hour']
            
            total = rental['amount'] + late_fee
            msg = f"کالا: {rental['name']}\nمبلغ اجاره: {rental['amount']}\nجریمه دیرکرد: {late_fee:.0f}\nمبلغ نهایی جهت تسویه: {total:.0f}"
            if messagebox.askyesno("تسویه نهایی", msg + "\n\nآیا تسویه انجام شود؟"):
                conn.execute("UPDATE rentals SET status='تسویه شده', actual_return_time=? WHERE id=?", (now.strftime("%Y-%m-%d %H:%M"), rid))
                conn.execute("UPDATE tools SET status='در انبار' WHERE id=?", (rental['tool_id'],))
                conn.commit()
                messagebox.showinfo("موفقیت", "تسویه با موفقیت انجام شد")
            conn.close()

        tk.Button(self.content, text="محاسبه و تسویه", command=calculate, bg=Config.COLOR_PRIMARY, fg="white").pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
