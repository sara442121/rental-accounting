import requests

# تنظیمات پیش‌فرض پنل پیامک (این مقادیر باید توسط کاربر با پنل واقعی جایگزین شوند)
SMS_API_URL = "https://api.sms-provider.com/v1/send"
API_KEY = "YOUR_API_KEY_HERE"
SENDER_NUMBER = "1000123456"

def send_sms(phone_number, message):
    """ارسال پیامک به مشتری"""
    payload = {
        "api_key": API_KEY,
        "sender": SENDER_NUMBER,
        "receptor": phone_number,
        "message": message
    }
    
    try:
        # در حالت آزمایشی فقط در کنسول چاپ می‌کنیم تا هزینه واقعی ایجاد نشود
        print(f"در حال ارسال پیامک به {phone_number}: {message}")
        
        # برای فعال‌سازی واقعی خط زیر را از کامنت خارج کنید:
        # response = requests.post(SMS_API_URL, json=payload)
        # return response.status_code == 200
        return True
    except Exception as e:
        print(f"خطا در ارسال پیامک: {e}")
        return False

def send_rental_reminder(phone_number, customer_name, tool_name, end_time):
    """ارسال پیامک یادآوری بازگشت کالا"""
    msg = f"مشتری گرامی {customer_name}، زمان اجاره کالای {tool_name} شما در تاریخ {end_time} به پایان می‌رسد. لطفاً جهت جلوگیری از جریمه نسبت به عودت اقدام نمایید."
    return send_sms(phone_number, msg)
