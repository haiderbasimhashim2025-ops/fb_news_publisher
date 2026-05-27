#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام نشر الأخبار التلقائي على Facebook - النسخة 19
🇮🇶 تركيز على الأخبار العراقية فقط
✅ تصاميم مميزة واحترافية لكل صفحة
✅ صور الخبر مع الإطارات المخصصة
✅ نظام متقدم لمنع التكرار
✅ نشر مستمر 24/7
"""

import os
import sys
import sqlite3
import requests
import feedparser
from datetime import datetime, timedelta
import time
import re
import hashlib
from PIL import Image, ImageDraw, ImageFont
import io
from bs4 import BeautifulSoup

# =====================================================
# إعدادات الصفحات مع الألوان والتصاميم المخصصة
# =====================================================
PAGES_CONFIG = {
    'SALSSAL': {
        'page_id': '1104346172760947',
        'name': 'صلصال',
        'token': os.environ.get('PAGE_SALSSAL', '').split('|')[1] if '|' in os.environ.get('PAGE_SALSSAL', '') else '',
        'primary_color': (212, 165, 116),  # بني ذهبي
        'secondary_color': (139, 115, 85),  # بني غامق
        'accent_color': (255, 215, 0),  # ذهبي
        'bg_color': (245, 240, 235),  # بيج فاتح
        'frame_style': 'rounded',  # إطار مستدير
    },
    'CHAI': {
        'page_id': '1078693568663658',
        'name': 'چاي سادة',
        'token': os.environ.get('PAGE_CHAI', '').split('|')[1] if '|' in os.environ.get('PAGE_CHAI', '') else '',
        'primary_color': (139, 115, 85),  # بني
        'secondary_color': (101, 84, 63),  # بني غامق جداً
        'accent_color': (212, 165, 116),  # بني فاتح
        'bg_color': (230, 220, 210),  # بيج فاتح جداً
        'frame_style': 'rounded',
    },
    'TABOGA': {
        'page_id': '1063874040148711',
        'name': 'طابوگة',
        'token': os.environ.get('PAGE_TABOGA', '').split('|')[1] if '|' in os.environ.get('PAGE_TABOGA', '') else '',
        'primary_color': (78, 205, 196),  # أزرق فيروزي
        'secondary_color': (0, 150, 136),  # أزرق غامق
        'accent_color': (255, 215, 0),  # ذهبي
        'bg_color': (224, 247, 246),  # أزرق فاتح جداً
        'frame_style': 'rounded',
    },
    'TEIN': {
        'page_id': '1094102397116855',
        'name': 'طين',
        'token': os.environ.get('PAGE_TEIN', '').split('|')[1] if '|' in os.environ.get('PAGE_TEIN', '') else '',
        'primary_color': (160, 130, 109),  # بني طيني
        'secondary_color': (120, 100, 85),  # بني غامق
        'accent_color': (200, 170, 140),  # بني فاتح
        'bg_color': (240, 235, 230),  # بيج فاتح جداً
        'frame_style': 'rounded',
    },
}

# مصادر الأخبار العراقية
NEWS_SOURCES = [
    'https://feeds.aljazeera.net/xml/news/iraq.xml',
    'https://feeds.bbc.co.uk/news/world/middle_east/rss.xml',
    'https://feeds.reuters.com/reuters/worldNews',
    'https://feeds.aljazeera.net/xml/news/middleeast.xml',
    'https://www.dw.com/ar/s-100625/rss.xml',
    'https://www.bbc.com/arabic/index.xml',
    'https://feeds.reuters.com/reuters/arabicNews',
    'https://feeds.aljazeera.net/xml/news/business.xml',
    'https://feeds.aljazeera.net/xml/news/sports.xml',
    'https://feeds.aljazeera.net/xml/news/technology.xml',
    'https://feeds.bbc.co.uk/news/health/rss.xml',
    'https://feeds.aljazeera.net/xml/news/entertainment.xml',
    'https://feeds.reuters.com/reuters/entertainment',
    'https://feeds.aljazeera.net/xml/news/arabworld.xml',
]

# كلمات مفتاحية عراقية
IRAQ_KEYWORDS = [
    'العراق', 'بغداد', 'البصرة', 'الموصل', 'أربيل', 'كركوك', 'النجف', 'كربلاء',
    'الحلة', 'الناصرية', 'الديوانية', 'الرمادي', 'تكريت', 'سامراء', 'هيت',
    'عنة', 'الفلوجة', 'الرطبة', 'القائم', 'الحديثة', 'الخالدية',
    'العراقي', 'العراقيين', 'عراقي', 'حكومة العراق', 'البرلمان العراقي',
    'الجيش العراقي', 'الشرطة العراقية', 'الحشد الشعبي', 'البيشمركة',
    'الدينار العراقي', 'النفط العراقي', 'الاقتصاد العراقي',
]

DB_FILE = 'news_database.db'

def init_db():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DROP TABLE IF EXISTS news')
    cursor.execute('DROP TABLE IF EXISTS duplicate_check')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            title_hash TEXT UNIQUE NOT NULL,
            description TEXT,
            description_hash TEXT,
            link TEXT,
            link_hash TEXT,
            image_url TEXT,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            posted_at TIMESTAMP,
            posted_pages TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS duplicate_check (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_hash TEXT UNIQUE NOT NULL,
            description_hash TEXT,
            link_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def calculate_hash(text):
    """حساب hash للنص"""
    if not text:
        return None
    return hashlib.md5(text.encode()).hexdigest()

def is_duplicate(title, description, link):
    """فحص متقدم لمنع التكرار"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    title_hash = calculate_hash(title)
    desc_hash = calculate_hash(description)
    link_hash = calculate_hash(link)
    
    try:
        if title_hash:
            cursor.execute('SELECT id FROM duplicate_check WHERE title_hash = ?', (title_hash,))
            if cursor.fetchone():
                conn.close()
                return True
        
        if desc_hash:
            cursor.execute('SELECT id FROM duplicate_check WHERE description_hash = ?', (desc_hash,))
            if cursor.fetchone():
                conn.close()
                return True
        
        if link_hash:
            cursor.execute('SELECT id FROM duplicate_check WHERE link_hash = ?', (link_hash,))
            if cursor.fetchone():
                conn.close()
                return True
        
        conn.close()
        return False
    except Exception as e:
        print(f"خطأ في فحص التكرار: {e}")
        conn.close()
        return False

def is_arabic(text):
    """التحقق من أن النص يحتوي على أحرف عربية"""
    if not text:
        return False
    
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    arabic_chars = len(arabic_pattern.findall(text))
    total_chars = len(text)
    
    return (arabic_chars / total_chars) > 0.3 if total_chars > 0 else False

def is_iraq_related(text):
    """التحقق من أن الخبر متعلق بالعراق"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    for keyword in IRAQ_KEYWORDS:
        if keyword in text_lower:
            return True
    
    return False

def fetch_news():
    """جلب الأخبار من المصادر"""
    news_list = []
    
    for source_url in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source_url)
            
            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                description = entry.get('summary', '')
                link = entry.get('link', '')
                
                description = BeautifulSoup(description, 'html.parser').get_text()[:200]
                
                if is_arabic(title) or is_arabic(description):
                    if is_iraq_related(title) or is_iraq_related(description):
                        if not is_duplicate(title, description, link):
                            image_url = None
                            if 'media_content' in entry:
                                image_url = entry.media_content[0]['url']
                            elif 'image' in entry:
                                image_url = entry.image.get('href')
                            
                            news_list.append({
                                'title': title,
                                'description': description,
                                'link': link,
                                'image_url': image_url
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
        title_hash = calculate_hash(news['title'])
        desc_hash = calculate_hash(news['description'])
        link_hash = calculate_hash(news['link'])
        
        cursor.execute('''
            INSERT INTO news (title, title_hash, description, description_hash, link, link_hash, image_url, saved_at, posted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL)
        ''', (news['title'], title_hash, news['description'], desc_hash, news['link'], link_hash, news.get('image_url')))
        
        cursor.execute('''
            INSERT INTO duplicate_check (title_hash, description_hash, link_hash)
            VALUES (?, ?, ?)
        ''', (title_hash, desc_hash, link_hash))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_unposted_news():
    """الحصول على الأخبار التي لم تُنشر بعد"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, description, link, image_url FROM news
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
            'link': result[3],
            'image_url': result[4]
        }
    
    return None

def download_image(image_url):
    """تحميل الصورة من الإنترنت"""
    try:
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
    except:
        pass
    return None

def draw_rounded_rectangle(draw, xy, radius=20, **kwargs):
    """رسم مستطيل بزوايا مستديرة"""
    x0, y0, x1, y1 = xy
    
    # رسم الزوايا المستديرة
    draw.ellipse([x0, y0, x0 + radius * 2, y0 + radius * 2], **kwargs)
    draw.ellipse([x1 - radius * 2, y0, x1, y0 + radius * 2], **kwargs)
    draw.ellipse([x0, y1 - radius * 2, x0 + radius * 2, y1], **kwargs)
    draw.ellipse([x1 - radius * 2, y1 - radius * 2, x1, y1], **kwargs)
    
    # رسم المستطيلات الوسيطة
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], **kwargs)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], **kwargs)

def create_post_image(title, description, image_url, page_config):
    """إنشاء صورة المنشور مع تصميم مميز"""
    try:
        # محاولة تحميل صورة الخبر
        news_image = None
        if image_url:
            news_image = download_image(image_url)
        
        # إنشاء الصورة الأساسية
        img = Image.new('RGB', (1200, 800), page_config['bg_color'])
        
        # إضافة صورة الخبر في الأعلى
        if news_image:
            news_image.thumbnail((1200, 400), Image.Resampling.LANCZOS)
            img.paste(news_image, (0, 0))
        else:
            # خلفية بسيطة
            for x in range(0, 1200, 50):
                for y in range(0, 400, 50):
                    img.paste(page_config['primary_color'], (x, y, x + 50, y + 50))
        
        draw = ImageDraw.Draw(img)
        
        # محاولة استخدام خط عربي
        try:
            title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
            desc_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 28)
            footer_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
        except:
            title_font = ImageFont.load_default()
            desc_font = ImageFont.load_default()
            footer_font = ImageFont.load_default()
        
        # رسم خلفية شفافة للنص
        text_bg_color = page_config['bg_color']
        draw.rectangle([(0, 400), (1200, 800)], fill=text_bg_color)
        
        # رسم شريط ملون في الأعلى
        draw.rectangle([(0, 400), (1200, 420)], fill=page_config['primary_color'])
        
        # كتابة العنوان
        title_text = title[:80]
        draw.text((50, 450), title_text, fill=page_config['primary_color'], font=title_font)
        
        # كتابة الوصف
        desc_text = description[:120]
        draw.text((50, 550), desc_text, fill=page_config['secondary_color'], font=desc_font)
        
        # كتابة اسم الصفحة والتاريخ
        footer_text = f"{page_config['name']} • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        draw.text((50, 720), footer_text, fill=page_config['accent_color'], font=footer_font)
        
        # رسم خط فاصل
        draw.line([(50, 710), (1150, 710)], fill=page_config['accent_color'], width=2)
        
        return img
    except Exception as e:
        print(f"خطأ في إنشاء الصورة: {e}")
        return None

def post_to_facebook(news, page_key):
    """نشر الخبر على Facebook"""
    page_config = PAGES_CONFIG[page_key]
    
    if not page_config['token']:
        return False
    
    try:
        page_id = page_config['page_id']
        access_token = page_config['token']
        
        # إنشاء صورة المنشور
        image = create_post_image(news['title'], news['description'], news.get('image_url'), page_config)
        
        if image:
            # نشر مع صورة
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            files = {'source': img_byte_arr}
            data = {
                'caption': f"{news['title']}\n\n{news['description']}",
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
                'message': f"{news['title']}\n\n{news['description']}",
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
    """حذف الأخبار القديمة"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM news
        WHERE saved_at < datetime('now', '-24 hours')
    ''')
    
    cursor.execute('''
        DELETE FROM duplicate_check
        WHERE created_at < datetime('now', '-24 hours')
    ''')
    
    conn.commit()
    conn.close()

def main_loop():
    """الحلقة الرئيسية"""
    print("🚀 بدء نظام نشر الأخبار التلقائي - النسخة 19")
    print("🇮🇶 أخبار عراقية فقط مع تصاميم مميزة واحترافية")
    print("=" * 50)
    
    init_db()
    
    cleanup_counter = 0
    
    while True:
        try:
            print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - جاري جلب الأخبار...")
            news_list = fetch_news()
            print(f"✅ تم جلب {len(news_list)} خبر جديد")
            
            saved_count = 0
            for news in news_list:
                if save_to_db(news):
                    saved_count += 1
            
            if saved_count > 0:
                print(f"💾 تم حفظ {saved_count} أخبار جديدة")
            
            unposted = get_unposted_news()
            if unposted:
                print(f"📝 نشر الخبر: {unposted['title'][:50]}...")
                
                posted_pages = []
                for page_key in PAGES_CONFIG.keys():
                    if PAGES_CONFIG[page_key]['token']:
                        if post_to_facebook(unposted, page_key):
                            posted_pages.append(page_key)
                            print(f"✅ تم النشر على صفحة {page_key}")
                        else:
                            print(f"❌ فشل النشر على صفحة {page_key}")
                
                if posted_pages:
                    mark_as_posted(unposted['id'], posted_pages)
            else:
                print("⏳ لا توجد أخبار جديدة للنشر الآن")
            
            cleanup_counter += 1
            if cleanup_counter >= 900:
                print("🧹 تنظيف الأخبار القديمة...")
                cleanup_old_news()
                cleanup_counter = 0
            
            time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n🛑 تم إيقاف النظام")
            break
        except Exception as e:
            print(f"❌ خطأ: {e}")
            time.sleep(5)
            continue

if __name__ == '__main__':
    main_loop()
