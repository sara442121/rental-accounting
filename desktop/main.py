import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime

# تنظیمات پایه
class Config:
    APP_NAME = "سیستم حسابداری ابزارالات"
    FONT_TITLE = ("Segoe UI", 16, "bold")
    FONT_NORMAL = ("Segoe UI", 10)
    COLOR_PRIMARY = "#2C3E50"
    COLOR_SECONDARY = "#3498DB"
    COLOR_SUCCESS = "#27AE60"
    COLOR_DANGER = "#E74C3C"
    COLOR_LIGHT = "#ECF0F1"
    COLOR_DARK = "#2C3E50"

# داده‌ها در فایل
DATA_FILE = "data.json"

# بلوک ساختار اولیه دیتا (در صورت نبود فایل)
initial_data = {
    "customers": [],
    "tools": [],
    "rentals": [],
}

# load/save data
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=4)
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# برنامه اصلی
class MainApp:
    def __init__(self, root):
        self.root = root
        self.data = load_data()
        self.root.title(Config.APP_NAME)
        self.root.geometry("1200x700")
        self.create_ui()

    def create_ui(self):
        # هدر
        header = tk.Frame(self.root, bg=Config.COLOR_PRIMARY, height=80)
        header.pack(fill=tk.X)
        tk.Label(header, text=Config.APP_NAME, font=Config.FONT_TITLE, bg=Config.COLOR_PRIMARY, fg="white").pack(padx=20, pady=20)

        # منو و محتوا
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # نوار منوی سمت چپ
        sidebar = tk.Frame(main_frame, bg=Config.COLOR_DARK, width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        buttons = [
            ("مشتری‌ها", self.show_customers),
            ("کالاهای اجاره‌ای", self.show_tools),
            ("قراردادهای اجاره", self.show_rentals),
            ("موجودی و انبار", self.show_inventory),
            ("گزارش‌ها", self.show_reports),
            ("خروج", self.root.quit),
        ]
        for txt, cmd in buttons:
            b = tk.Button(sidebar, text=txt, command=cmd, bg=Config.COLOR_DARK, fg="white")
            b.pack(fill=tk.X, pady=2, padx=10)

        # محتوای سمت راست
        self.content = tk.Frame(main_frame, bg=Config.COLOR_LIGHT)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.show_customers()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_inventory(self):
        self.clear_content()
        tk.Label(self.content, text="موجودی و انبار", font=Config.FONT_TITLE, bg=Config.COLOR_LIGHT).pack(pady=10)
        tk.Label(self.content, text="این بخش در حال توسعه است.", bg=Config.COLOR_LIGHT).pack(pady=20)

    # صفحه مشتری‌ها
    def show_customers(self):
        self.clear_content()
        tk.Label(self.content, text="مدیریت مشتریان", font=Config.FONT_TITLE, bg=Config.COLOR_LIGHT).pack(pady=10)
        tk.Button(self.content, text="مشتری جدید", command=self.add_customer).pack(pady=5)
        self.customers_tree = ttk.Treeview(self.content, columns=("کد ملی", "نام", "تلفن", "عکس"), show='headings')
        for col in ("کد ملی", "نام", "تلفن", "عکس"):
            self.customers_tree.heading(col, text=col)
        self.customers_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.refresh_customers()

    def refresh_customers(self):
        for r in self.customers_tree.get_children():
            self.customers_tree.delete(r)
        for c in self.data["customers"]:
            self.customers_tree.insert('', 'end', values=(c["c_code"], c["name"], c["phone"], "مشاهده"))

    def add_customer(self):
        win = tk.Toplevel(self.root)
        win.title("افزودن مشتری")
        win.geometry("400x500")
        c_code_var = tk.StringVar()
        name_var = tk.StringVar()
        phone_var = tk.StringVar()
        photo_path = tk.StringVar()

        tk.Label(win, text="کد ملی:", bg=Config.COLOR_LIGHT).pack(pady=5)
        tk.Entry(win, textvariable=c_code_var).pack(pady=5, fill=tk.X, padx=10)
        tk.Label(win, text="نام و نام خانوادگی:", bg=Config.COLOR_LIGHT).pack(pady=5)
        tk.Entry(win, textvariable=name_var).pack(pady=5, fill=tk.X, padx=10)
        tk.Label(win, text="شماره تلفن:", bg=Config.COLOR_LIGHT).pack(pady=5)
        tk.Entry(win, textvariable=phone_var).pack(pady=5, fill=tk.X, padx=10)
        def select_photo():
            file_path = filedialog.askopenfilename(title='انتخاب عکس', filetypes=[("Image files", "*.jpg;*.png")])
            if file_path:
                photo_path.set(file_path)
        tk.Button(win, text="انتخاب عکس کارت ملی", command=select_photo).pack(pady=5)
        def save():
            if not c_code_var.get() or not name_var.get() or not phone_var.get():
                messagebox.showwarning("هشدار", "لطفاً همه فیلدها پر شود.")
                return
            self.data["customers"].append({
                "c_code": c_code_var.get(),
                "name": name_var.get(),
                "phone": phone_var.get(),
                "photo": photo_path.get()
            })
            save_data(self.data)
            self.refresh_customers()
            messagebox.showinfo("موفقیت", "مشتری ثبت شد")
            win.destroy()
        tk.Button(win, text="ذخیره", bg=Config.COLOR_SUCCESS, fg="white", command=save).pack(pady=10)
        tk.Button(win, text="انصراف", bg=Config.COLOR_DANGER, fg="white", command=win.destroy).pack()

    # صفحه کالاهای اجاره‌ای
    def show_tools(self):
        self.clear_content()
        tk.Label(self.content, text="کالاهای اجاره‌ای", font=Config.FONT_TITLE, bg=Config.COLOR_LIGHT).pack(pady=10)
        tk.Button(self.content, text="کالا جدید", command=self.add_tool).pack(pady=5)
        self.tools_tree = ttk.Treeview(self.content, columns=("کد", "نام", "قیمت ساعتی", "روزانه", "هفتگی", "ماهانه", "وضعیت"), show='headings')
        for col in ("کد", "نام", "قیمت ساعتی", "روزانه", "هفتگی", "ماهانه", "وضعیت"):
            self.tools_tree.heading(col, text=col)
        self.tools_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.refresh_tools()

    def refresh_tools(self):
        for r in self.tools_tree.get_children():
            self.tools_tree.delete(r)
        for t in self.data["tools"]:
            self.tools_tree.insert('', 'end', values=(
                t.get('code',''), t.get('name',''), t.get('hourly_price',''),
                t.get('daily_price',''), t.get('weekly_price',''), t.get('monthly_price',''), t.get('status','در انبار')
            ))

    def add_tool(self):
        win = tk.Toplevel(self.root)
        win.title("کالای جدید")
        win.geometry("400x600")
        fields = {}
        for txt, var in [("کد:", "code"), ("نام:", "name"), ("قیمت ساعتی:", "hourly_price"),
                         ("قیمت روزانه:", "daily_price"), ("قیمت هفتگی:", "weekly_price"),
                         ("قیمت ماهانه:", "monthly_price"),
                         ("وضعیت:", "status")]:
            tk.Label(win, text=txt, bg=Config.COLOR_LIGHT).pack(pady=5)
            entry_var = tk.StringVar()
            if txt=="وضعیت:":
                combo = ttk.Combobox(win, textvariable=entry_var, values=["در انبار","در حال اجاره"])
                combo.pack(pady=5, fill=tk.X, padx=10)
                fields["status"] = combo
            else:
                tk.Entry(win, textvariable=entry_var).pack(pady=5, fill=tk.X, padx=10)
                fields[txt]=entry_var
        def save():
            t = {k: v.get() for k, v in fields.items()}
            self.data["tools"].append(t)
            save_data(self.data)
            self.refresh_tools()
            messagebox.showinfo("موفقیت", "کالا ثبت شد")
            win.destroy()
        tk.Button(win, text="ثبت", bg=Config.COLOR_SUCCESS, fg="white", command=save).pack(pady=10)
        tk.Button(win, text="انصراف", bg=Config.COLOR_DANGER, fg="white", command=win.destroy).pack()

    # صفحه قراردادهای اجاره
    def show_rentals(self):
        self.clear_content()
        tk.Label(self.content, text="قراردادهای اجاره", font=Config.FONT_TITLE, bg=Config.COLOR_LIGHT).pack(pady=10)
        tk.Button(self.content, text="قرارداد جدید", command=self.new_rental).pack(pady=5)
        self.rentals_tree = ttk.Treeview(self.content, columns=("مشتری", "کالا", "مدت", "مبلغ", "وضعیت"), show='headings')
        for col in ("مشتری", "کالا", "مدت", "مبلغ", "وضعیت"):
            self.rentals_tree.heading(col, text=col)
        self.rentals_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.refresh_rentals()

    def refresh_rentals(self):
        for r in self.rentals_tree.get_children():
            self.rentals_tree.delete(r)
        for r in self.data.get("rentals", []):
            self.rentals_tree.insert('', 'end', values=(r['customer_name'], r['tool_name'], r['period'], r['amount'], r['status']))

    def new_rental(self):
        win = tk.Toplevel(self.root)
        win.title("قرارداد جدید")
        win.geometry("500x600")
        # انتخاب مشتری
        tk.Label(win, text="انتخاب مشتری:", bg=Config.COLOR_LIGHT).pack(pady=5)
        cust_var = tk.StringVar()
        cust_combo = ttk.Combobox(win, textvariable=cust_var, values=[c['name'] for c in self.data["customers"]])
        cust_combo.pack(pady=5, fill=tk.X, padx=10)

        # انتخاب کالا
        tk.Label(win, text="انتخاب کالا:", bg=Config.COLOR_LIGHT).pack(pady=5)
        tool_var = tk.StringVar()
        available_tools = [t['name'] for t in self.data["tools"] if t.get('status')=='در انبار']
        tool_combo = ttk.Combobox(win, textvariable=tool_var, values=available_tools)
        tool_combo.pack(pady=5, fill=tk.X, padx=10)

        # نوع دوره
        tk.Label(win, text="نوع دوره:", bg=Config.COLOR_LIGHT).pack(pady=5)
        period_type = ttk.Combobox(win, values=["ساعت", "روز", "هفته", "ماه"])
        period_type.pack(pady=5, fill=tk.X, padx=10)

        # تعداد دوره
        tk.Label(win, text="تعداد دوره:", bg=Config.COLOR_LIGHT).pack(pady=5)
        count_var = tk.StringVar()
        tk.Entry(win, textvariable=count_var).pack(pady=5, fill=tk.X, padx=10)

        # مبلغ
        tk.Label(win, text="مبلغ کل (تومان):", bg=Config.COLOR_LIGHT).pack(pady=5)
        amount_var = tk.StringVar()
        tk.Entry(win, textvariable=amount_var).pack(pady=5, fill=tk.X, padx=10)

        # تاریخ شروع
        tk.Label(win, text="تاریخ شروع (شمسی):", bg=Config.COLOR_LIGHT).pack(pady=5)
        start_date_var = tk.StringVar()
        tk.Entry(win, textvariable=start_date_var).pack(pady=5, fill=tk.X, padx=10)

        # وضعیت پرداخت
        tk.Label(win, text="وضعیت پرداخت:", bg=Config.COLOR_LIGHT).pack(pady=5)
        pay_status = ttk.Combobox(win, values=["پرداخت شده", "در انتظار"])
        pay_status.pack(pady=5, fill=tk.X, padx=10)

        def save():
            if not cust_var.get() or not tool_var.get() or not count_var.get() or not amount_var.get() or not start_date_var.get():
                messagebox.showwarning("هشدار", "تمامی فیلدها پر شود")
                return
            self.data['rentals'].append({
                'customer_name': cust_var.get(),
                'tool_name': tool_var.get(),
                'period': f"{count_var.get()} {period_type.get()}",
                'amount': amount_var.get(),
                'start_date': start_date_var.get(),
                'status': pay_status.get()
            })
            # بروز رسانی وضعیت کالا به در حال اجاره
            for t in self.data["tools"]:
                if t['name'] == tool_var.get():
                    t['status'] = 'در حال اجاره'
                    break
            save_data(self.data)
            self.refresh_rentals()
            messagebox.showinfo("موفقیت", "قرارداد ثبت شد")
            win.destroy()

        tk.Button(win, text="ثبت", bg=Config.COLOR_SUCCESS, fg="white", command=save).pack(pady=10)
        tk.Button(win, text="انصراف", bg=Config.COLOR_DANGER, fg="white", command=win.destroy).pack()

    # صفحه گزارش‌ها
    def show_reports(self):
        self.clear_content()
        tk.Label(self.content, text="گزارش‌ها و تحلیل‌ها", font=Config.FONT_TITLE, bg=Config.COLOR_LIGHT).pack(pady=10)
        # نمونه گزارشات ساده (در نسخه نهایی کامل‌تر)
        tk.Label(self.content, text="در این بخش، گزارش‌های مالی و فعالیت‌های اقتصادی نمایش داده می‌شود.", bg=Config.COLOR_LIGHT).pack(pady=20)

# اجرای برنامه
if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
