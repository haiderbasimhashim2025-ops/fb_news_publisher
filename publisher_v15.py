#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام نشر الأخبار التلقائي على Facebook - النسخة 15
تفلتر الأخبار بالعربية فقط
"""

import os
import sys
import sqlite3
import requests
import feedparser
from datetime import datetime, timedelta
import time
import re
from PIL import Image, ImageDraw, ImageFont
import io

# إعدادات الصفحات
PAGES = {
    'SALSSAL': os.environ.get('PAGE_SALSSAL', ''),
    'CHAI': os.environ.get('PAGE_CHAI', ''),
    'TABOGA': os.environ.get('PAGE_TABOGA', ''),
    'TEIN': os.environ.get('PAGE_TEIN', '')
}

# مصادر الأخبار العراقية والعربية
NEWS_SOURCES = [
    'https://feeds.aljazeera.net/xml/news/middleeast.xml',
    'https://feeds.aljazeera.net/xml/news/arabworld.xml',
    'https://www.bbc.com/arabic/index.xml',
    'https://feeds.reuters.com/reuters/arabicNews',
    'https://www.dw.com/ar/s-100625/rss.xml',
    'https://feeds.france24.com/fr/afrique/rss',
    'https://feeds.skynews.com/feeds/rss/news.xml',
    'https://feeds.bloomberg.com/markets/news.rss',
    'https://feeds.cnbc.com/id/100003114/rss.xml',
    'https://feeds.reuters.com/reuters/businessNews',
    'https://feeds.aljazeera.net/xml/news/iraq.xml',
    'https://feeds.bbc.co.uk/news/world/middle_east/rss.xml',
    'https://feeds.reuters.com/reuters/worldNews',
    'https://feeds.aljazeera.net/xml/news/sports.xml',
    'https://feeds.aljazeera.net/xml/news/technology.xml',
    'https://feeds.bbc.co.uk/news/technology/rss.xml',
    'https://feeds.aljazeera.net/xml/news/business.xml',
    'https://feeds.reuters.com/reuters/entertainment',
    'https://feeds.aljazeera.net/xml/news/entertainment.xml',
    'https://feeds.bbc.co.uk/news/health/rss.xml'
]

# إعدادات قاعدة البيانات
DB_FILE = 'news_database.db'

def init_db():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # حذف الجدول القديم إذا كان موجوداً
    cursor.execute('DROP TABLE IF EXISTS news')
    
    # إنشاء جدول جديد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            description TEXT,
            link TEXT,
            source TEXT,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            posted_at TIMESTAMP,
            posted_pages TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def is_arabic(text):
    """التحقق من أن النص يحتوي على أحرف عربية"""
    if not text:
        return False
    
    # نمط الأحرف العربية
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    
    # عد الأحرف العربية
    arabic_chars = len(arabic_pattern.findall(text))
    total_chars = len(text)
    
    # إذا كان أكثر من 30% من النص عربي، اعتبره عربي
    return (arabic_chars / total_chars) > 0.3 if total_chars > 0 else False

def fetch_news():
    """جلب الأخبار من المصادر"""
    news_list = []
    
    for source_url in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source_url)
            
            for entry in feed.entries[:5]:  # أول 5 أخبار من كل مصدر
                title = entry.get('title', '')
                description = entry.get('summary', '')
                link = entry.get('link', '')
                
                # التحقق من أن العنوان والوصف بالعربية
                if is_arabic(title) or is_arabic(description):
                    news_list.append({
                        'title': title,
                        'description': description[:200],
                        'link': link,
                        'source': source_url
                    })
        except Exception as e:
            print(f"خطأ في جلب الأخبار من {source_url}: {e}")
            continue
    
    return news_list

def save_to_db(news):
    """حفظ الأخبار في قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO news (title, description, link, source, saved_at, posted_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, NULL)
        ''', (news['title'], news['description'], news['link'], news['source']))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # الخبر موجود بالفعل
        return False
    finally:
        conn.close()

def get_unposted_news():
    """الحصول على الأخبار التي لم تُنشر بعد"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, description, link FROM news
        WHERE posted_at IS NULL
        ORDER BY saved_at DESC
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'title': result[1],
            'description': result[2],
            'link': result[3]
        }
    
    return None

def create_news_image(title, description):
    """إنشاء صورة للخبر"""
    try:
        # إنشاء صورة بحجم 1200x630 (حجم Facebook المثالي)
        img = Image.new('RGB', (1200, 630), color=(13, 71, 161))  # أزرق داكن
        draw = ImageDraw.Draw(img)
        
        # محاولة استخدام خط عربي
        try:
            title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
            desc_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
        except:
            title_font = ImageFont.load_default()
            desc_font = ImageFont.load_default()
        
        # كتابة العنوان
        title_y = 100
        draw.multiline_text((50, title_y), title[:60], fill=(255, 255, 255), font=title_font)
        
        # كتابة الوصف
        desc_y = 300
        draw.multiline_text((50, desc_y), description[:100], fill=(200, 200, 200), font=desc_font)
        
        # كتابة التاريخ
        date_text = datetime.now().strftime('%Y-%m-%d %H:%M')
        draw.text((50, 550), date_text, fill=(150, 150, 150), font=desc_font)
        
        # حفظ الصورة في الذاكرة
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
    except Exception as e:
        print(f"خطأ في إنشاء الصورة: {e}")
        return None

def post_to_facebook(news, page_key):
    """نشر الخبر على Facebook"""
    if not PAGES[page_key]:
        return False
    
    try:
        page_data = PAGES[page_key].split('|')
        if len(page_data) != 2:
            return False
        
        page_id, access_token = page_data
        
        # إنشاء صورة للخبر
        image = create_news_image(news['title'], news['description'])
        
        if image:
            # نشر مع صورة
            files = {'source': image}
            data = {
                'caption': f"{news['title']}\n\n{news['description']}\n\nالمصدر: {news['link']}",
                'access_token': access_token
            }
            
            response = requests.post(
                f'https://graph.facebook.com/v18.0/{page_id}/photos',
                files=files,
                data=data,
                timeout=10
            )
        else:
            # نشر بدون صورة
            data = {
                'message': f"{news['title']}\n\n{news['description']}\n\nالمصدر: {news['link']}",
                'access_token': access_token
            }
            
            response = requests.post(
                f'https://graph.facebook.com/v18.0/{page_id}/feed',
                data=data,
                timeout=10
            )
        
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"خطأ في النشر على {page_key}: {e}")
        return False

def mark_as_posted(news_id, pages):
    """تعيين الخبر كمنشور"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE news
        SET posted_at = CURRENT_TIMESTAMP, posted_pages = ?
        WHERE id = ?
    ''', (','.join(pages), news_id))
    
    conn.commit()
    conn.close()

def cleanup_old_news():
    """حذف الأخبار القديمة (أكثر من 24 ساعة)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM news
        WHERE saved_at < datetime('now', '-24 hours')
    ''')
    
    conn.commit()
    conn.close()

def main_loop():
    """الحلقة الرئيسية"""
    print("🚀 بدء نظام نشر الأخبار التلقائي - النسخة 15")
    print("📰 تفلتر الأخبار بالعربية فقط")
    print("=" * 50)
    
    init_db()
    
    cleanup_counter = 0
    
    while True:
        try:
            # جلب الأخبار الجديدة
            print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - جاري جلب الأخبار...")
            news_list = fetch_news()
            print(f"✅ تم جلب {len(news_list)} خبر")
            
            # حفظ الأخبار الجديدة
            saved_count = 0
            for news in news_list:
                if save_to_db(news):
                    saved_count += 1
            
            if saved_count > 0:
                print(f"💾 تم حفظ {saved_count} أخبار جديدة")
            
            # نشر الأخبار
            unposted = get_unposted_news()
            if unposted:
                print(f"📝 نشر الخبر: {unposted['title'][:50]}...")
                
                posted_pages = []
                for page_key in PAGES.keys():
                    if PAGES[page_key]:
                        if post_to_facebook(unposted, page_key):
                            posted_pages.append(page_key)
                            print(f"✅ تم النشر على صفحة {page_key}")
                        else:
                            print(f"❌ فشل النشر على صفحة {page_key}")
                
                if posted_pages:
                    mark_as_posted(unposted['id'], posted_pages)
            else:
                print("⏳ لا توجد أخبار جديدة للنشر الآن")
            
            # تنظيف الأخبار القديمة كل 15 دقيقة (900 ثانية)
            cleanup_counter += 1
            if cleanup_counter >= 900:
                print("🧹 تنظيف الأخبار القديمة...")
                cleanup_old_news()
                cleanup_counter = 0
            
            # الانتظار ثانية واحدة قبل الدورة التالية
            time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n🛑 تم إيقاف النظام بواسطة المستخدم")
            break
        except Exception as e:
            print(f"❌ خطأ في الحلقة الرئيسية: {e}")
            time.sleep(5)
            continue

if __name__ == '__main__':
    main_loop()
