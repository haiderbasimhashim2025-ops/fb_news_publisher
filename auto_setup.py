#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت إعداد تلقائي شامل لـ PythonAnywhere
يقوم بـ:
1. إنشاء virtual environment
2. تثبيت المكتبات
3. اختبار النظام
4. إضافة cron job
"""

import subprocess
import os
import sys
import time

def run_cmd(cmd, description="", show_output=False):
    """تنفيذ أمر وطباعة النتيجة"""
    if description:
        print(f"\n📝 {description}")
        print("=" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        if show_output and result.stdout:
            print(result.stdout)
        
        if result.returncode == 0:
            print(f"✅ تم بنجاح")
            return True
        else:
            if result.stderr:
                print(f"⚠️  {result.stderr[:300]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ انتهت مهلة الوقت")
        return False
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("🚀 جاري إعداد نظام النشر على PythonAnywhere")
    print("=" * 60)
    
    home = os.path.expanduser("~")
    venv_path = os.path.join(home, "myenv")
    
    # الخطوة 1: إنشاء virtual environment
    if not os.path.exists(venv_path):
        run_cmd(
            f"python3 -m venv {venv_path}",
            "الخطوة 1: إنشاء Virtual Environment"
        )
    else:
        print("\n✅ Virtual Environment موجود بالفعل")
    
    # الخطوة 2: تثبيت المكتبات
    pip_path = os.path.join(venv_path, "bin", "pip")
    packages = [
        "requests",
        "feedparser",
        "beautifulsoup4",
        "Pillow",
        "python-bidi",
        "arabic_reshaper"
    ]
    
    run_cmd(
        f"{pip_path} install --upgrade pip",
        "الخطوة 2: تحديث pip"
    )
    
    for pkg in packages:
        run_cmd(
            f"{pip_path} install {pkg} -q",
            f"تثبيت {pkg}"
        )
    
    # الخطوة 3: اختبار النظام
    python_path = os.path.join(venv_path, "bin", "python3")
    publisher_path = os.path.join(home, "publisher.py")
    
    if os.path.exists(publisher_path):
        print("\n" + "=" * 60)
        print("الخطوة 3: اختبار النظام")
        print("=" * 60)
        print("\n🧪 تشغيل النظام للاختبار...")
        print("-" * 60)
        
        result = subprocess.run(
            f"{python_path} {publisher_path}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        print("-" * 60)
        print("✅ اختبار النظام انتهى")
    else:
        print(f"\n❌ ملف publisher.py غير موجود في {home}")
    
    # الخطوة 4: إضافة cron job
    print("\n" + "=" * 60)
    print("الخطوة 4: إضافة Cron Job")
    print("=" * 60)
    
    cron_cmd = f"*/5 * * * * source {venv_path}/bin/activate && cd {home} && {python_path} {publisher_path} >> {home}/publisher.log 2>&1"
    
    # قراءة crontab الحالي
    result = subprocess.run("crontab -l 2>/dev/null", shell=True, capture_output=True, text=True)
    current_crontab = result.stdout if result.returncode == 0 else ""
    
    # التحقق من عدم وجود الأمر بالفعل
    if cron_cmd not in current_crontab:
        # إضافة الأمر الجديد
        new_crontab = current_crontab + "\n" + cron_cmd + "\n"
        
        # كتابة crontab الجديد
        result = subprocess.run(
            f"echo '{new_crontab}' | crontab -",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ تم إضافة cron job بنجاح")
        else:
            print(f"❌ خطأ في إضافة cron job: {result.stderr}")
    else:
        print("✅ cron job موجود بالفعل")
    
    # التحقق من crontab
    print("\n📋 التحقق من crontab:")
    print("-" * 60)
    result = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("❌ لا توجد crontab")
    print("-" * 60)
    
    # الخطوة 5: ملخص النتائج
    print("\n" + "=" * 60)
    print("✅ تم الإعداد بنجاح!")
    print("=" * 60)
    print("\n📊 ملخص الإعداد:")
    print(f"  • Virtual Environment: {venv_path}")
    print(f"  • Python: {python_path}")
    print(f"  • Publisher: {publisher_path}")
    print(f"  • Log: {home}/publisher.log")
    print(f"  • Cron: كل 5 دقائق")
    print("\n📝 المكتبات المثبتة:")
    for pkg in packages:
        print(f"  ✓ {pkg}")
    print("\n🎯 النظام جاهز للعمل 24/7!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ تم إيقاف الإعداد من قبل المستخدم")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ خطأ: {e}")
        sys.exit(1)
