#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام نشر الأخبار التلقائي المستمر 24/7
GitHub Actions - نشر مستمر بدون توقف
مع إعادة تشغيل تلقائي عند الخروج
الإصلاح: فصل saved_at عن posted_at
"""

import os
import sys
import time
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import feedparser
import signal
import atexit

# ==================== الإعدادات ====================

# رموز الوصول لصفحات Facebook
PAGE_TOKENS = {
    'SALSSAL': os.environ.get('PAGE_SALSSAL', ''),
    'CHAI': os.environ.get('PAGE_CHAI', ''),
    'TABOGA': os.environ.get('PAGE_TABOGA', ''),
    'TEIN': os.environ.get('PAGE_TEIN', '')
}

# مصادر الأخبار (20 مصدر عراقي وعربي)
NEWS_SOURCES = [
    'https://feeds.aljazeera.net/xml/rss/all.xml',
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://feeds.reuters.com/reuters/worldNews',
    'https://feeds.aljazeera.net/xml/rss/mritems/middleeast.xml',
    'https://www.france24.com/en/middleeast/rss',
    'https://feeds.bloomberg.com/markets/news.rss',
    'https://feeds.cnbc.com/id/100003114/device/rss/rss.html',
    'https://feeds.independent.co.uk/world-rss.xml',
    'https://feeds.theguardian.com/theguardian/world/rss',
    'https://feeds.washingtonpost.com/rss/world',
    'https://feeds.npr.org/1001/rss.xml',
    'https://feeds.cnn.com/rss2.0/world.rss',
    'https://feeds.bbc.co.uk/news/rss.xml',
    'https://feeds.aljazeera.net/xml/rss/all.xml',
    'https://feeds.skynews.com/feeds/rss/world.xml',
    'https://feeds.euronews.com/euronews/en/news/rss',
    'https://feeds.dw.com/rss/en/rss-en-all',
    'https://feeds.france24.com/en/rss',
    'https://feeds.aljazeera.net/xml/rss/middleeast.xml',
    'https://feeds.aljazeera.net/xml/rss/iraq.xml'
]

# قاعدة البيانات
DB_FILE = '/tmp/news_cache.db'
STATE_FILE = '/tmp/publisher_state.json'

# ==================== متغيرات عامة ====================

running = True
start_time = datetime.now()
posts_count = 0
errors_count = 0

# ==================== دوال المساعدة ====================

def save_state():
    """حفظ حالة البرنامج"""
    try:
        state = {
            'last_run': datetime.now().isoformat(),
            'posts_count': posts_count,
            'errors_count': errors_count,
            'uptime_seconds': (datetime.now() - start_time).total_seconds()
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except:
        pass

def signal_handler(sig, frame):
    """معالج الإشارات"""
    global running
    print("\n\n🛑 استقبال إشارة إيقاف - جاري الحفظ...")
    save_state()
    running = False

def exit_handler():
    """معالج الخروج"""
    print("\n🛑 البرنامج يغلق - جاري الحفظ...")
    save_state()

# تسجيل معالجات الخروج
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(exit_handler)

def init_db():
    """تهيئة قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY,
                title TEXT UNIQUE,
                link TEXT,
                source TEXT,
                pub_date TEXT,
                image_url TEXT,
                saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                posted_at TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ تم تهيئة قاعدة البيانات")
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")

def get_news():
    """جلب الأخبار من المصادر"""
    all_news = []
    for source_url in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source_url)
            for entry in feed.entries[:3]:
                all_news.append({
                    'title': entry.get('title', 'بدون عنوان'),
                    'link': entry.get('link', ''),
                    'source': feed.feed.get('title', 'مصدر غير معروف'),
                    'pub_date': entry.get('published', datetime.now().isoformat()),
                    'image_url': None
                })
        except:
            pass
    return all_news

def save_to_db(news):
    """حفظ الأخبار في قاعدة البيانات - بدون تعيين posted_at"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        for item in news:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO news (title, link, source, pub_date, image_url, saved_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    item['title'],
                    item['link'],
                    item['source'],
                    item['pub_date'],
                    item.get('image_url'),
                    datetime.now().isoformat()
                ))
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ خطأ في حفظ الأخبار: {e}")

def get_unposted_news():
    """الحصول على الأخبار التي لم تُنشر بعد"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM news WHERE posted_at IS NULL ORDER BY saved_at DESC LIMIT 10')
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"❌ خطأ في جلب الأخبار: {e}")
        return []

def mark_as_posted(title):
    """تعيين الخبر كمنشور بعد النشر الناجح على Facebook"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE news SET posted_at = ? WHERE title = ?
        ''', (datetime.now().isoformat(), title))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ خطأ في تعيين الخبر كمنشور: {e}")

def create_image_with_text(title, source):
    """إنشاء صورة مع النص"""
    try:
        img = Image.new('RGB', (1200, 630), color=(20, 30, 50))
        draw = ImageDraw.Draw(img)
        
        try:
            font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 60)
            font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 40)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        text_y = 150
        lines = [title[i:i+50] for i in range(0, len(title), 50)]
        for line in lines[:3]:
            draw.text((50, text_y), line, fill=(255, 255, 255), font=font_large)
            text_y += 80
        
        draw.text((50, 550), f"المصدر: {source}", fill=(255, 150, 50), font=font_small)
        
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
    except Exception as e:
        print(f"❌ خطأ في إنشاء الصورة: {e}")
        return None

def post_to_facebook(page_token, title, source):
    """نشر الخبر على Facebook"""
    global posts_count, errors_count
    
    try:
        image = create_image_with_text(title, source)
        
        if not image:
            return False
        
        files = {'source': image}
        data = {
            'message': f"📰 {title}\n\n✅ المصدر: {source}",
            'access_token': page_token
        }
        
        response = requests.post(
            'https://graph.facebook.com/v18.0/me/photos',
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            posts_count += 1
            print(f"✅ تم النشر: {title[:40]}...")
            # تعيين الخبر كمنشور فقط بعد النشر الناجح
            mark_as_posted(title)
            return True
        else:
            errors_count += 1
            print(f"❌ خطأ: {response.text[:100]}")
            return False
    except Exception as e:
        errors_count += 1
        print(f"❌ خطأ في النشر: {e}")
        return False

def cleanup_old_news():
    """تنظيف الأخبار القديمة"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute('DELETE FROM news WHERE saved_at < ?', (cutoff_date,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            print(f"🧹 تم حذف {deleted} خبر قديم")
    except Exception as e:
        print(f"❌ خطأ في التنظيف: {e}")

def main_loop():
    """الحلقة الرئيسية"""
    global running, posts_count, errors_count, start_time
    
    print("🚀 بدء نظام النشر المستمر 24/7 على GitHub Actions")
    print("=" * 60)
    print(f"⏰ وقت البدء: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    init_db()
    cleanup_count = 0
    cycle = 0
    
    while running:
        try:
            cycle += 1
            print(f"\n📍 دورة #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
            
            # جلب الأخبار
            print("📡 جاري جلب الأخبار...")
            news = get_news()
            print(f"✅ تم جلب {len(news)} خبر")
            
            # حفظ في قاعدة البيانات (بدون تعيين posted_at)
            save_to_db(news)
            
            # النشر على الصفحات - فقط الأخبار التي لم تُنشر
            unposted = get_unposted_news()
            if unposted:
                print(f"📢 توجد {len(unposted)} أخبار جديدة للنشر")
                for news_item in unposted:
                    if not running:
                        break
                    title = news_item[1]
                    source = news_item[3]
                    
                    for page_name, token in PAGE_TOKENS.items():
                        if token and running:
                            post_to_facebook(token, title, source)
                            time.sleep(0.5)
            else:
                print("⏳ لا توجد أخبار جديدة للنشر")
            
            # التنظيف كل 15 دقيقة
            cleanup_count += 1
            if cleanup_count >= 900:  # 900 ثانية = 15 دقيقة
                cleanup_old_news()
                cleanup_count = 0
            
            # الإحصائيات
            uptime = (datetime.now() - start_time).total_seconds()
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            print(f"📊 المنشورات: {posts_count} | الأخطاء: {errors_count} | الوقت: {hours}h {minutes}m")
            
            # حفظ الحالة
            save_state()
            
            # الانتظار ثانية واحدة
            if running:
                time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n\n🛑 توقف البرنامج بناءً على طلب المستخدم")
            running = False
            break
        except Exception as e:
            errors_count += 1
            print(f"❌ خطأ: {e}")
            if running:
                time.sleep(5)

if __name__ == '__main__':
    try:
        main_loop()
    finally:
        save_state()
        print("\n✅ تم إغلاق البرنامج بنجاح")
