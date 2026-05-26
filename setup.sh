#!/bin/bash

# سكريبت إعداد PythonAnywhere
# يقوم بـ:
# 1. إنشاء virtual environment
# 2. تثبيت المكتبات
# 3. إنشاء cron job

echo "🚀 جاري إعداد نظام النشر على PythonAnywhere..."

# 1. إنشاء virtual environment
echo "📦 إنشاء virtual environment..."
python3 -m venv ~/myenv
source ~/myenv/bin/activate

# 2. تثبيت المكتبات
echo "📦 تثبيت المكتبات..."
pip install requests feedparser beautifulsoup4 Pillow python-bidi arabic_reshaper

# 3. اختبار النظام
echo "🧪 اختبار النظام..."
python3 ~/publisher.py

# 4. إضافة cron job
echo "📝 إضافة cron job..."
CRON_CMD="*/5 * * * * source ~/myenv/bin/activate && cd ~ && python3 publisher.py >> publisher.log 2>&1"
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ تم الإعداد بنجاح!"
echo "📋 النظام سيعمل تلقائياً كل 5 دقائق"
