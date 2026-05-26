# -*- coding: utf-8 -*-
"""
نظام نشر الأخبار التلقائي على فيسبوك - النسخة 10
✅ نشر مستمر (كل دقيقة) 24/7 بدون توقف
✅ تنظيف تلقائي لقاعدة البيانات كل 15 دقيقة
✅ صور الأخبار الفعلية في المنشورات
✅ إطار مخصص لكل صفحة
✅ منع تكرار المنشورات بفحص محسّن جداً
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
]

# =====================================================
# قاعدة البيانات
# =====================================================
DB_PATH = os.environ.get("DB_PATH", "/tmp/published.db")
CLEANUP_INTERVAL = 15  # تنظيف كل 15 دقيقة
last_cleanup_time = None

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

def should_cleanup():
    """التحقق من الحاجة للتنظيف (كل 15 دقيقة)"""
    global last_cleanup_time
    
    if last_cleanup_time is None:
        return True
    
    elapsed = (datetime.now() - last_cleanup_time).total_seconds() / 60
    return elapsed >= CLEANUP_INTERVAL

def cleanup_old_records():
    """حذف الأخبار القديمة (أكثر من 24 ساعة) - كل 15 دقيقة"""
    global last_cleanup_time
    
    if not should_cleanup():
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # حذف السجلات الأقدم من 24 ساعة
        cutoff_time = datetime.now() - timedelta(hours=24)
        c.execute(
            "DELETE FROM published WHERE timestamp < ?",
            (cutoff_time.isoformat(),)
        )
        
        deleted_count = c.rowcount
        if deleted_count > 0:
            print(f"🧹 تم حذف {deleted_count} خبر قديم من قاعدة البيانات")
        
        # عرض إحصائيات قاعدة البيانات
        c.execute("SELECT COUNT(*) FROM published")
        total_records = c.fetchone()[0]
        print(f"📊 إجمالي السجلات: {total_records}")
        
        conn.commit()
        conn.close()
        
        last_cleanup_time = datetime.now()
        print(f"✅ تنظيف قاعدة البيانات تم في {last_cleanup_time.strftime('%H:%M:%S')}")
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
        pass

def download_image(image_url):
    """تحميل الصورة من الإنترنت"""
    try:
        if not image_url:
            return None
        
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return img
    except Exception as e:
        pass
    
    return None

def create_post_image_with_news(title, image_url, page_name, color, bg_color):
    """إنشاء صورة المنشور مع صورة الخبر الفعلية"""
    try:
        news_image = download_image(image_url) if image_url else None
        
        if news_image:
            img = news_image.resize((1200, 630))
            overlay = Image.new('RGBA', (1200, 630), color + (180,))
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')
        else:
            img = Image.new("RGB", (1200, 630), bg_color)
        
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            font_footer = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font_title = ImageFont.load_default()
            font_footer = ImageFont.load_default()
        
        draw.rectangle([(10, 10), (1190, 620)], outline=color, width=5)
        title_text = title[:100]
        draw.text((50, 100), title_text, fill=color, font=font_title)
        footer_text = f"{page_name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        draw.text((50, 550), footer_text, fill=color, font=font_footer)
        
        return img
    except Exception as e:
        return None

def get_news():
    """جلب الأخبار من جميع المصادر"""
    news_list = []
    
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            
            for entry in feed.entries[:3]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                
                summary = BeautifulSoup(summary, "html.parser").get_text()[:200]
                
                if title and not is_duplicate(title, link, summary):
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
                    
                    mark_as_published(title, link, summary)
        
        except Exception as e:
            pass
    
    return news_list

def post_to_facebook(page_id, page_config, title, image_url=None):
    """نشر الخبر على فيسبوك مع الصورة الفعلية"""
    try:
        if not page_config["token"]:
            return False
        
        url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
        
        post_image = create_post_image_with_news(title, image_url, page_config["name"], page_config["color"], page_config["bg_color"])
        
        if post_image:
            img_path = f"/tmp/post_{page_id}.jpg"
            post_image.save(img_path, quality=95)
            
            with open(img_path, "rb") as f:
                files = {"source": f}
                params = {"access_token": page_config["token"]}
                response = requests.post(url, files=files, params=params, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ {page_config['name']}: {title[:40]}")
                return True
            else:
                return False
        else:
            return False
    
    except Exception as e:
        return False

def main():
    """البرنامج الرئيسي - نشر مستمر مع تنظيف كل 15 دقيقة"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 دورة نشر مستمرة...")
    
    # إنشاء قاعدة البيانات
    init_db()
    
    # تنظيف كل 15 دقيقة
    cleanup_old_records()
    
    # جلب الأخبار
    news = get_news()
    
    if news:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📰 وجدت {len(news)} خبر جديد")
        
        published_count = 0
        for news_item in news:
            for page_id, page_config in PAGES_CONFIG.items():
                if post_to_facebook(page_id, page_config, news_item["title"], news_item.get("image_url")):
                    published_count += 1
                time.sleep(1)
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ تم نشر {published_count} منشور")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ℹ️ لا توجد أخبار جديدة")

if __name__ == "__main__":
    main()
