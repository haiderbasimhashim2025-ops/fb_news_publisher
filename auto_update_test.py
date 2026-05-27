#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام التحديث والاختبار التلقائي
يتحقق من التصاميم والبرنامج بشكل مستمر
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path

# =====================================================
# الإعدادات
# =====================================================
PROJECT_DIR = Path(__file__).parent
PUBLISHER_V21 = PROJECT_DIR / "publisher_v21.py"
GIT_REPO = PROJECT_DIR
LOG_FILE = PROJECT_DIR / "auto_update.log"
TEST_RESULTS = PROJECT_DIR / "test_results.json"

# =====================================================
# دوال السجل
# =====================================================
def log_message(message, level="INFO"):
    """تسجيل الرسالة في السجل والشاشة"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def log_error(message):
    """تسجيل خطأ"""
    log_message(message, "ERROR")

def log_success(message):
    """تسجيل نجاح"""
    log_message(message, "SUCCESS")

def log_warning(message):
    """تسجيل تحذير"""
    log_message(message, "WARNING")

# =====================================================
# اختبار الكود
# =====================================================
def test_syntax():
    """اختبار صحة بناء الكود"""
    try:
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(PUBLISHER_V21)],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            log_success("✅ اختبار الصيغة: نجح")
            return True
        else:
            log_error(f"❌ اختبار الصيغة: فشل - {result.stderr.decode()}")
            return False
    except Exception as e:
        log_error(f"❌ خطأ في اختبار الصيغة: {e}")
        return False

def test_import():
    """اختبار استيراد البرنامج"""
    try:
        sys.path.insert(0, str(PROJECT_DIR))
        import publisher_v21
        log_success("✅ اختبار الاستيراد: نجح")
        return True
    except Exception as e:
        log_error(f"❌ اختبار الاستيراد: فشل - {e}")
        return False

def test_functions():
    """اختبار الدوال الأساسية"""
    try:
        sys.path.insert(0, str(PROJECT_DIR))
        import publisher_v21
        
        # التحقق من وجود الدوال المهمة
        required_functions = [
            'create_post_image_fast',
            'draw_gradient_rect_fast',
            'draw_text_with_glow_fast',
            'draw_ornament_fast',
            'draw_corner_ornament_fast',
            'post_to_facebook_fast',
            'post_to_all_pages_fast',
            'main_loop_fast'
        ]
        
        missing = []
        for func_name in required_functions:
            if not hasattr(publisher_v21, func_name):
                missing.append(func_name)
        
        if missing:
            log_error(f"❌ دوال مفقودة: {', '.join(missing)}")
            return False
        
        log_success(f"✅ اختبار الدوال: جميع {len(required_functions)} دالة موجودة")
        return True
    except Exception as e:
        log_error(f"❌ خطأ في اختبار الدوال: {e}")
        return False

def test_design_functions():
    """اختبار دوال التصميم"""
    try:
        sys.path.insert(0, str(PROJECT_DIR))
        import publisher_v21
        from PIL import Image, ImageDraw
        
        # إنشاء صورة اختبار
        test_img = Image.new("RGB", (1200, 850), (50, 50, 50))
        draw = ImageDraw.Draw(test_img)
        
        # اختبار التدرج
        publisher_v21.draw_gradient_rect_fast(test_img, 0, 0, 1200, 110, (0, 0, 0), (255, 215, 0))
        log_success("✅ اختبار التدرج: نجح")
        
        # اختبار الزخارف
        publisher_v21.draw_ornament_fast(draw, 600, 55, (255, 215, 0))
        log_success("✅ اختبار الزخارف: نجح")
        
        # اختبار زخارف الزوايا
        publisher_v21.draw_corner_ornament_fast(draw, 20, 20, 30, (255, 215, 0), "tl")
        log_success("✅ اختبار زخارف الزوايا: نجح")
        
        return True
    except Exception as e:
        log_error(f"❌ خطأ في اختبار دوال التصميم: {e}")
        return False

def test_config():
    """اختبار الإعدادات"""
    try:
        sys.path.insert(0, str(PROJECT_DIR))
        import publisher_v21
        
        # التحقق من وجود الإعدادات
        if not hasattr(publisher_v21, 'PAGES_CONFIG'):
            log_error("❌ PAGES_CONFIG غير موجود")
            return False
        
        config = publisher_v21.PAGES_CONFIG
        required_pages = ['salssal', 'chai', 'taboga', 'tein']
        
        missing_pages = [p for p in required_pages if p not in config]
        if missing_pages:
            log_error(f"❌ صفحات مفقودة: {', '.join(missing_pages)}")
            return False
        
        # التحقق من الألوان
        for page_key, page_config in config.items():
            required_keys = ['name', 'bar_grad_start', 'bar_grad_end', 'border1', 'border2', 'glow', 'deco_color', 'overlay_color', 'bar_text']
            missing_keys = [k for k in required_keys if k not in page_config]
            if missing_keys:
                log_error(f"❌ مفاتيح مفقودة في {page_key}: {', '.join(missing_keys)}")
                return False
        
        log_success(f"✅ اختبار الإعدادات: جميع {len(required_pages)} صفحات موجودة بالألوان الصحيحة")
        return True
    except Exception as e:
        log_error(f"❌ خطأ في اختبار الإعدادات: {e}")
        return False

# =====================================================
# تحديث GitHub
# =====================================================
def git_push():
    """دفع التحديثات إلى GitHub"""
    try:
        os.chdir(GIT_REPO)
        
        # إضافة الملفات
        subprocess.run(["git", "add", "publisher_v21.py"], check=True, capture_output=True)
        
        # التحقق من وجود تغييرات
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not result.stdout.strip():
            log_message("لا توجد تغييرات جديدة للدفع")
            return True
        
        # الـ commit
        subprocess.run(
            ["git", "commit", "-m", f"🔄 تحديث تلقائي - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
            check=True,
            capture_output=True
        )
        
        # الـ push
        subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True, timeout=30)
        log_success("✅ تم دفع التحديثات إلى GitHub")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"❌ خطأ في دفع التحديثات: {e}")
        return False
    except Exception as e:
        log_error(f"❌ خطأ غير متوقع: {e}")
        return False

# =====================================================
# حفظ النتائج
# =====================================================
def save_results(results):
    """حفظ نتائج الاختبار"""
    try:
        with open(TEST_RESULTS, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log_success("✅ تم حفظ نتائج الاختبار")
    except Exception as e:
        log_error(f"❌ خطأ في حفظ النتائج: {e}")

# =====================================================
# الحلقة الرئيسية
# =====================================================
def main():
    """الحلقة الرئيسية للتحديث والاختبار"""
    log_message("=" * 60)
    log_message("🤖 بدء نظام التحديث والاختبار التلقائي")
    log_message("=" * 60)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # الاختبارات
    tests = [
        ("الصيغة", test_syntax),
        ("الاستيراد", test_import),
        ("الدوال", test_functions),
        ("دوال التصميم", test_design_functions),
        ("الإعدادات", test_config),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results["tests"][test_name] = "✅ نجح" if passed else "❌ فشل"
            if not passed:
                all_passed = False
        except Exception as e:
            log_error(f"❌ خطأ في {test_name}: {e}")
            results["tests"][test_name] = f"❌ خطأ: {str(e)}"
            all_passed = False
    
    # النتيجة النهائية
    log_message("=" * 60)
    if all_passed:
        log_success("✅ جميع الاختبارات نجحت!")
        results["status"] = "success"
        
        # دفع التحديثات
        if git_push():
            log_success("✅ تم التحديث والدفع بنجاح")
        else:
            log_warning("⚠️ الاختبارات نجحت لكن فشل الدفع")
    else:
        log_error("❌ بعض الاختبارات فشلت")
        results["status"] = "failed"
    
    log_message("=" * 60)
    
    # حفظ النتائج
    save_results(results)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
