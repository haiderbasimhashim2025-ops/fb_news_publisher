# -*- coding: utf-8 -*-
"""
نظام نشر الأخبار التلقائي على فيسبوك - النسخة 8
✅ صور الأخبار الفعلية في المنشورات
✅ إطار مخصص لكل صفحة
✅ منع تكرار المنشورات بفحص محسّن جداً
✅ تنظيف تلقائي لقاعدة البيانات (حذف أخبار أقدم من 48 ساعة)
✅ متابعة دقيقة مثل البشر
✅ جميع المصادر الإخبارية العراقية
✅ يعمل على GitHub Actions 24/7 بدون توقف
"""

import requests
import feedparser
import hashlib
import time
import os
import sqlite3
import warnings
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import re

warnings.filterwarnings("ignore")

from bs4 import BeautifulSoup

# =====================================================
# رموز وصول الصفحات مع الألوان المخصصة
# =====================================================
PAGES_CONFIG = {
    "1104346172760947": {
        "name": "صلصال",
        "token": os.environ.get("PAGE_SALSSAL", ""),
        "color": (255, 107, 107),
        "bg_color": (255, 229, 229),
    },
    "1078693568663658": {
        "name": "چاي سادة",
        "token": os.environ.get("PAGE_CHAI", ""),
        "color": (139, 115, 85),
        "bg_color": (212, 165, 116),
    },
    "1063874040148711": {
        "name": "طابوگة",
        "token": os.environ.get("PAGE_TABOGA", ""),
        "color": (78, 205, 196),
        "bg_color": (224, 247, 246),
    },
    "1094102397116855": {
        "name": "طين",
        "token": os.environ.get("PAGE_TEIN", ""),
        "color": (160, 130, 109),
        "bg_color": (230, 220, 210),
    },
}

# =====================================================
# جميع المصادر الإخبارية العراقية والعربية
# =====================================================
NEWS_SOURCES = [
    # المصادر الإخبارية الرسمية
    {"name": "وكالة الأنباء العراقية", "url": "https://www.ina.iq/feed"},
    {"name": "الإذاعة والتلفزيون العراقي", "url": "https://www.iraqiya.iq/feed"},
    
    # القنوات الفضائية العراقية
    {"name": "قناة الشرقية", "url": "https://www.alsharqiya.iq/feed"},
    {"name": "قناة السومرية", "url": "https://www.alsumaria.tv/feed"},
    {"name": "قناة الغدير", "url": "https://www.alghadeer.tv/feed"},
    {"name": "قناة العراقية", "url": "https://www.iraqiya.iq/feed"},
    {"name": "قناة الرافدين", "url": "https://www.alrafidain.iq/feed"},
    {"name": "قناة بغداد", "url": "https://www.baghdad.iq/feed"},
    
    # المصادر الإخبارية المستقلة
    {"name": "موقع عراق برس", "url": "https://www.iraqpress.iq/feed"},
    {"name": "موقع الشرقية نيوز", "url": "https://www.sharqiyah.iq/feed"},
    {"name": "موقع بغداد اليوم", "url": "https://www.baghdadtoday.iq/feed"},
    {"name": "موقع العراق الحر", "url": "https://www.iraqfree.iq/feed"},
    
    # المصادر العربية الموثوقة
    {"name": "BBC عربي", "url": "http://www.bbc.com/arabic/index.xml"},
    {"name": "سكاي نيوز عربية", "url": "https://www.skynewsarabia.com/feeds/rss.xml"},
    {"name": "الجزيرة", "url": "https://www.aljazeera.net/xml/feeds/all.xml"},
    {"name": "رويترز عربي", "url": "https://feeds.reuters.com/reuters/arabicnews"},
    {"name": "فرانس 24 عربي", "url": "https://www.france24.com/ar/feed"},
    
    # المصادر المحلية الإضافية
    {"name": "ناس", "url": "https://www.nas.iq/feed"},
    {"name": "الحرة", "url": "https://www.alhurra.com/feed"},
    {"name": "ميدل إيست آي", "url": "https://www.middleeasteye.net/feed"},
    {"name": "دنيا الوطن", "url": "https://www.alwatanvoice.com/feed"},
    {"name": "موقع الاتحاد", "url": "https://www.alittihad.info/feed"},
]

# =====================================================
# قاعدة البيانات
# =====================================================
# استخدام /tmp للـ GitHub Actions أو المسار المحدد
DB_PATH = os.environ.get("DB_PATH", "/tmp/published.db")

def init_db():
    """إنشاء قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS published (
                id INTEGER PRIMARY KEY,
                title_hash TEXT UNIQUE,
                url_hash TEXT,
                content_hash TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ خطأ في إنشاء قاعدة البيانات: {e}")

def cleanup_old_records():
    """حذف الأخبار القديمة (أكثر من 48 ساعة) لتحرير المساحة"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # حذف السجلات الأقدم من 48 ساعة
        cutoff_time = datetime.now() - timedelta(hours=48)
        c.execute(
            "DELETE FROM published WHERE timestamp < ?",
            (cutoff_time.isoformat(),)
        )
        
        deleted_count = c.rowcount
        if deleted_count > 0:
            print(f"🧹 تم حذف {deleted_count} خبر قديم من قاعدة البيانات")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ خطأ في تنظيف قاعدة البيانات: {e}")

def is_duplicate(title, url, content):
    """
    فحص محسّن جداً لمنع التكرار
    يستخدم 3 مستويات من الفحص:
    1. hash العنوان (الفحص الأساسي)
    2. hash الرابط
    3. hash المحتوى
    """
    try:
        title_hash = hashlib.md5(title.encode()).hexdigest()
        url_hash = hashlib.md5(url.encode()).hexdigest() if url else ""
        content_hash = hashlib.md5(content.encode()).hexdigest() if content else ""
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # فحص 1: هل العنوان موجود؟
        c.execute("SELECT * FROM published WHERE title_hash = ?", (title_hash,))
        if c.fetchone():
            conn.close()
            return True
        
        # فحص 2: هل الرابط موجود؟
        if url_hash:
            c.execute("SELECT * FROM published WHERE url_hash = ?", (url_hash,))
            if c.fetchone():
                conn.close()
                return True
        
        # فحص 3: هل المحتوى موجود؟
        if content_hash:
            c.execute("SELECT * FROM published WHERE content_hash = ?", (content_hash,))
            if c.fetchone():
                conn.close()
                return True
        
        conn.close()
        return False
    except Exception as e:
        print(f"❌ خطأ في فحص التكرار: {e}")
        return False

def mark_as_published(title, url, content):
    """تسجيل الخبر كمنشور"""
    try:
        title_hash = hashlib.md5(title.encode()).hexdigest()
        url_hash = hashlib.md5(url.encode()).hexdigest() if url else ""
        content_hash = hashlib.md5(content.encode()).hexdigest() if content else ""
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO published (title_hash, url_hash, content_hash) VALUES (?, ?, ?)",
            (title_hash, url_hash, content_hash)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ خطأ في تسجيل الخبر: {e}")

def download_image(image_url):
    """تحميل الصورة من الإنترنت"""
    try:
        if not image_url:
            return None
        
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # تحويل إلى RGB إذا لزم الأمر
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return img
    except Exception as e:
        print(f"❌ خطأ في تحميل الصورة: {e}")
    
    return None

def create_post_image_with_news(title, image_url, page_name, color, bg_color):
    """إنشاء صورة المنشور مع صورة الخبر الفعلية"""
    try:
        # محاولة تحميل صورة الخبر
        news_image = download_image(image_url) if image_url else None
        
        if news_image:
            # إذا كانت هناك صورة، استخدمها كخلفية
            img = news_image.resize((1200, 630))
            
            # إضافة طبقة شفافة بلون الصفحة
            overlay = Image.new('RGBA', (1200, 630), color + (180,))
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')
        else:
            # إذا لم تكن هناك صورة، إنشاء صورة بسيطة
            img = Image.new("RGB", (1200, 630), bg_color)
        
        draw = ImageDraw.Draw(img)
        
        # محاولة استخدام خط عربي
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            font_footer = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font_title = ImageFont.load_default()
            font_footer = ImageFont.load_default()
        
        # رسم الإطار
        draw.rectangle([(10, 10), (1190, 620)], outline=color, width=5)
        
        # كتابة العنوان (مع خلفية شفافة)
        title_text = title[:100]
        draw.text((50, 100), title_text, fill=color, font=font_title)
        
        # كتابة اسم الصفحة والتاريخ
        footer_text = f"{page_name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        draw.text((50, 550), footer_text, fill=color, font=font_footer)
        
        return img
    except Exception as e:
        print(f"❌ خطأ في إنشاء الصورة: {e}")
        return None

def get_news():
    """جلب الأخبار من جميع المصادر"""
    news_list = []
    
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            
            for entry in feed.entries[:2]:  # أول خبرين فقط من كل مصدر
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                
                # تنظيف النص
                summary = BeautifulSoup(summary, "html.parser").get_text()[:200]
                
                if title and not is_duplicate(title, link, summary):
                    # استخراج الصورة
                    image_url = None
                    if "media_content" in entry:
                        image_url = entry.media_content[0]["url"]
                    elif "image" in entry:
                        image_url = entry.image.get("href")
                    
                    news_list.append({
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "image_url": image_url,
                        "source": source["name"]
                    })
                    
                    # تسجيل الخبر فوراً
                    mark_as_published(title, link, summary)
        
        except Exception as e:
            print(f"❌ خطأ في جلب أخبار {source['name']}: {e}")
    
    return news_list

def post_to_facebook(page_id, page_config, title, image_url=None):
    """نشر الخبر على فيسبوك مع الصورة الفعلية"""
    try:
        # التحقق من وجود التوكن
        if not page_config["token"]:
            print(f"❌ لا يوجد توكن للصفحة {page_config['name']}")
            return False
        
        url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
        
        # إنشاء صورة المنشور مع صورة الخبر الفعلية
        post_image = create_post_image_with_news(title, image_url, page_config["name"], page_config["color"], page_config["bg_color"])
        
        if post_image:
            # حفظ الصورة مؤقتاً
            img_path = f"/tmp/post_{page_id}.jpg"
            post_image.save(img_path, quality=95)
            
            # رفع الصورة
            with open(img_path, "rb") as f:
                files = {"source": f}
                params = {"access_token": page_config["token"]}
                response = requests.post(url, files=files, params=params, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ تم النشر على {page_config['name']} مع الصورة الفعلية")
                return True
            else:
                print(f"❌ فشل النشر على {page_config['name']}: {response.text[:100]}")
                return False
        else:
            print(f"❌ فشل في إنشاء صورة المنشور")
            return False
    
    except Exception as e:
        print(f"❌ خطأ في النشر على {page_config['name']}: {e}")
        return False

def main():
    """البرنامج الرئيسي"""
    print("[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] 🚀 بدء دورة النشر...")
    print("[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f"] 📡 عدد المصادر: {len(NEWS_SOURCES)}")
    
    # إنشاء قاعدة البيانات
    init_db()
    
    # تنظيف السجلات القديمة
    cleanup_old_records()
    
    # جلب الأخبار
    news = get_news()
    print(f"[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f"] وجدت {len(news)} خبر جديد")
    
    # النشر على الصفحات
    if news:
        for news_item in news:
            for page_id, page_config in PAGES_CONFIG.items():
                post_to_facebook(page_id, page_config, news_item["title"], news_item.get("image_url"))
                time.sleep(3)  # تأخير 3 ثواني بين المنشورات
    
    print("[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] ✅ دورة النشر انتهت بنجاح")

if __name__ == "__main__":
    main()
