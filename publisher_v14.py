# -*- coding: utf-8 -*-
"""
نظام نشر الأخبار التلقائي المستمر 24/7
GitHub Actions - نشر مستمر بدون توقف
مع إعادة تشغيل تلقائي عند الخروج
الإصلاح: استخدام الـ endpoint الصحيح لنشر على صفحات Facebook
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

# رموز الوصول لصفحات Facebook (تحتوي على page_id)
# الصيغة: page_id|access_token
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
cleanup_counter = 0

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
        # حذف قاعدة البيانات القديمة إذا كانت غير متوافقة
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('PRAGMA table_info(news)')
            columns = [row[1] for row in cursor.fetchall()]
            if 'saved_at' not in columns or 'posted_at' not in columns:
                conn.close()
                os.remove(DB_FILE)
                print("🔄 تم حذف قاعدة البيانات القديمة - إعادة الإنشاء...")
            else:
                conn.close()
        except:
            pass
        
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
                saved_at TEXT,
                posted_at TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ تم تهيئة قاعدة البيانات")
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")

def fetch_news():
    """جلب الأخبار من المصادر"""
    all_news = []
    
    for source_url in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source_url)
            
            for entry in feed.entries[:2]:  # آخر خبرين من كل مصدر
                try:
                    title = entry.get('title', 'بدون عنوان')
                    link = entry.get('link', '')
                    source = feed.feed.get('title', 'مصدر غير معروف')
                    pub_date = entry.get('published', datetime.now().isoformat())
                    image_url = None
                    
                    # محاولة استخراج الصورة
                    if 'media_content' in entry:
                        image_url = entry.media_content[0]['url']
                    elif 'links' in entry:
                        for link_item in entry.links:
                            if link_item.get('type', '').startswith('image'):
                                image_url = link_item.get('href')
                                break
                    
                    all_news.append({
                        'title': title,
                        'link': link,
                        'source': source,
                        'pub_date': pub_date,
                        'image_url': image_url
                    })
                except:
                    continue
        except Exception as e:
            print(f"⚠️ خطأ في جلب من {source_url}: {str(e)[:50]}")
            continue
    
    return all_news

def save_to_db(news):
    """حفظ الأخبار في قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        for item in news:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO news 
                    (title, link, source, pub_date, image_url, saved_at, posted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item['title'],
                    item['link'],
                    item['source'],
                    item['pub_date'],
                    item['image_url'],
                    datetime.now().isoformat(),
                    None  # posted_at = NULL في البداية
                ))
            except sqlite3.IntegrityError:
                pass  # الخبر موجود بالفعل
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ خطأ في حفظ الأخبار: {e}")

def get_unposted_news():
    """الحصول على أخبار لم تُنشر بعد"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT title, source FROM news 
            WHERE posted_at IS NULL
            ORDER BY saved_at DESC
            LIMIT 10
        ''')
        news = cursor.fetchall()
        conn.close()
        return news
    except Exception as e:
        print(f"❌ خطأ في جلب الأخبار: {e}")
        return []

def mark_as_posted(title):
    """تعيين الخبر كمنشور"""
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
    """نشر الخبر على صفحة Facebook - الإصلاح: استخدام الـ endpoint الصحيح"""
    global posts_count, errors_count
    
    try:
        # استخراج page_id من الـ token (الصيغة: page_id|access_token)
        if '|' in page_token:
            page_id, access_token = page_token.split('|')
        else:
            # إذا كان الـ token بدون page_id، استخدمه كما هو
            access_token = page_token
            page_id = 'me'
        
        image = create_image_with_text(title, source)
        
        if not image:
            return False
        
        files = {'source': image}
        data = {
            'message': f"📰 {title}\n\n✅ المصدر: {source}",
            'access_token': access_token
        }
        
        # ✅ الإصلاح: استخدام الـ endpoint الصحيح
        # بدلاً من: /me/photos (ينشر على الملف الشخصي)
        # استخدام: /{page_id}/feed (ينشر على صفحة Facebook)
        response = requests.post(
            f'https://graph.facebook.com/v18.0/{page_id}/feed',
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
        
        # حذف الأخبار أقدم من 24 ساعة
        cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute('DELETE FROM news WHERE saved_at < ?', (cutoff_time,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            print(f"🧹 تم حذف {deleted} خبر قديم")
    except Exception as e:
        print(f"❌ خطأ في تنظيف الأخبار: {e}")

def main_loop():
    """الحلقة الرئيسية للنشر المستمر"""
    global running, cleanup_counter
    
    print("🚀 بدء النشر المستمر والمفتوح 24/7 - بدون توقف")
    print(f"⏰ الوقت: {datetime.now()}")
    print(f"📊 الصفحات: {len([t for t in PAGE_TOKENS.values() if t])}")
    print("=" * 50)
    
    init_db()
    
    while running:
        try:
            # جلب الأخبار الجديدة
            news = fetch_news()
            if news:
                print(f"\n📰 تم جلب {len(news)} خبر جديد")
                save_to_db(news)
            
            # الحصول على أخبار لم تُنشر بعد
            unposted = get_unposted_news()
            
            if unposted:
                print(f"\n📤 عدد الأخبار المنتظرة: {len(unposted)}")
                
                for title, source in unposted:
                    # النشر على جميع الصفحات
                    for page_name, page_token in PAGE_TOKENS.items():
                        if page_token:
                            print(f"\n📍 النشر على صفحة {page_name}...")
                            post_to_facebook(page_token, title, source)
                            time.sleep(1)  # تأخير 1 ثانية بين المنشورات
            
            # التنظيف التلقائي كل 15 دقيقة
            cleanup_counter += 1
            if cleanup_counter >= 900:  # 900 ثانية = 15 دقيقة
                print("\n🧹 جاري التنظيف التلقائي...")
                cleanup_old_news()
                cleanup_counter = 0
            
            # الانتظار قبل الدورة التالية
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n\n🛑 تم إيقاف البرنامج من قبل المستخدم")
            running = False
            break
        except Exception as e:
            print(f"❌ خطأ في الحلقة الرئيسية: {e}")
            errors_count += 1
            time.sleep(5)

if __name__ == '__main__':
    try:
        main_loop()
    except Exception as e:
        print(f"❌ خطأ حرج: {e}")
    finally:
        save_state()
        print("\n✅ انتهى البرنامج")
