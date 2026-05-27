# -*- coding: utf-8 -*-
"""
نظام نشر الأخبار المستمر - النسخة 23
✅ حلقة لا نهائية حقيقية - لا توقف أبداً
✅ معالجة شاملة لكل الأخطاء
✅ إعادة محاولة تلقائية عند أي فشل
✅ تصاميم احترافية لكل صفحة
✅ بدون ذكر المصدر
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
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
from bs4 import BeautifulSoup
from arabic_reshaper import ArabicReshaper
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import traceback

# =====================================================
# إعداد arabic_reshaper
# =====================================================
try:
    reshaper = ArabicReshaper()
    def ar(text):
        if not text:
            return ""
        try:
            return reshaper.reshape(str(text))
        except:
            return str(text)
except:
    def ar(text):
        return str(text) if text else ""

# =====================================================
# إعداد الخطوط
# =====================================================
FONT_PATHS = [
    "/usr/share/fonts/opentype/fonts-hosny-amiri/Amiri-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

def get_font(size):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

# =====================================================
# إعدادات الصفحات مع الألوان الاحترافية
# =====================================================
PAGES_CONFIG = {
    'salssal': {
        'page_id': '1104346172760947',
        'name': 'صلصال',
        'token': os.environ.get('PAGE_SALSSAL', '').split('|')[1] if '|' in os.environ.get('PAGE_SALSSAL', '') else '',
        'bar_grad_start': (210, 175, 100),
        'bar_grad_end':   (140, 100, 45),
        'bar_text':       (255, 255, 255),
        'border1':        (220, 185, 110),
        'border2':        (160, 120, 55),
        'glow':           (255, 240, 180),
        'overlay_color':  (20, 10, 0),
        'deco_color':     (255, 220, 120),
    },
    'chai': {
        'page_id': '1078693568663658',
        'name': 'چاي سادة',
        'token': os.environ.get('PAGE_CHAI', '').split('|')[1] if '|' in os.environ.get('PAGE_CHAI', '') else '',
        'bar_grad_start': (35, 22, 8),
        'bar_grad_end':   (15, 8, 2),
        'bar_text':       (212, 175, 55),
        'border1':        (212, 175, 55),
        'border2':        (140, 105, 25),
        'glow':           (255, 215, 80),
        'overlay_color':  (10, 5, 0),
        'deco_color':     (212, 175, 55),
    },
    'taboga': {
        'page_id': '1063874040148711',
        'name': 'طابوگة',
        'token': os.environ.get('PAGE_TABOGA', '').split('|')[1] if '|' in os.environ.get('PAGE_TABOGA', '') else '',
        'bar_grad_start': (5, 5, 5),
        'bar_grad_end':   (0, 0, 0),
        'bar_text':       (212, 175, 55),
        'border1':        (212, 175, 55),
        'border2':        (140, 105, 25),
        'glow':           (255, 215, 80),
        'overlay_color':  (0, 0, 0),
        'deco_color':     (212, 175, 55),
    },
    'tein': {
        'page_id': '1094102397116855',
        'name': 'طين',
        'token': os.environ.get('PAGE_TEIN', '').split('|')[1] if '|' in os.environ.get('PAGE_TEIN', '') else '',
        'bar_grad_start': (230, 215, 185),
        'bar_grad_end':   (200, 180, 145),
        'bar_text':       (90, 55, 20),
        'border1':        (180, 145, 90),
        'border2':        (120, 90, 45),
        'glow':           (200, 160, 80),
        'overlay_color':  (60, 35, 10),
        'deco_color':     (150, 110, 55),
    },
}

# =====================================================
# مصادر الأخبار العراقية
# =====================================================
NEWS_SOURCES = [
    'https://www.alsumaria.tv/rss',
    'https://www.shafaq.com/ar/rss.xml',
    'https://www.rudaw.net/arabic/rss',
    'https://www.ina.iq/rss.xml',
    'https://www.mawazin.net/rss',
    'https://www.aljazeera.net/rss/all.xml',
    'https://feeds.bbci.co.uk/arabic/rss.xml',
    'https://arabic.rt.com/rss/',
]

IRAQ_KEYWORDS = [
    'العراق', 'عراق', 'بغداد', 'البصرة', 'الموصل', 'أربيل', 'كركوك',
    'السليمانية', 'النجف', 'كربلاء', 'الكاظمي', 'السوداني', 'الحكومة العراقية',
    'البرلمان العراقي', 'الجيش العراقي', 'الحشد الشعبي', 'الكرد', 'العراقي',
    'العراقية', 'العراقيين', 'دينار', 'نفط العراق',
]

# =====================================================
# قاعدة البيانات
# =====================================================
DB_PATH = '/tmp/news_cache.db'

def init_db():
    """تهيئة قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            url TEXT,
            image_url TEXT,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            posted INTEGER DEFAULT 0,
            posted_at TIMESTAMP
        )''')
        conn.commit()
        conn.close()
        print("✅ قاعدة البيانات جاهزة")
    except Exception as e:
        print(f"⚠️ خطأ في قاعدة البيانات: {e}")

def save_news(title, url, image_url=''):
    """حفظ خبر في قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO news (title, url, image_url) VALUES (?, ?, ?)',
                  (title, url, image_url))
        conn.commit()
        conn.close()
    except:
        pass

def get_unposted():
    """جلب أول خبر لم يُنشر بعد"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, title, url, image_url FROM news WHERE posted=0 ORDER BY id ASC LIMIT 1')
        row = c.fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'title': row[1], 'url': row[2], 'image_url': row[3]}
    except:
        pass
    return None

def mark_posted(news_id):
    """تعليم الخبر كمنشور"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE news SET posted=1, posted_at=CURRENT_TIMESTAMP WHERE id=?', (news_id,))
        conn.commit()
        conn.close()
    except:
        pass

def cleanup_old():
    """حذف الأخبار القديمة (أكثر من 3 أيام)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM news WHERE saved_at < datetime('now', '-3 days')")
        conn.commit()
        conn.close()
    except:
        pass

# =====================================================
# جلب الأخبار
# =====================================================
def is_iraq_news(text):
    """التحقق من أن الخبر عراقي"""
    if not text:
        return False
    return any(kw in text for kw in IRAQ_KEYWORDS)

def extract_image(entry):
    """استخراج صورة من الخبر"""
    try:
        # من media_content
        if hasattr(entry, 'media_content') and entry.media_content:
            for m in entry.media_content:
                if m.get('url'):
                    return m['url']
        # من media_thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url', '')
        # من enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if 'image' in enc.get('type', ''):
                    return enc.get('href', '')
        # من summary
        if hasattr(entry, 'summary'):
            soup = BeautifulSoup(entry.summary, 'html.parser')
            img = soup.find('img')
            if img and img.get('src'):
                return img['src']
    except:
        pass
    return ''

def fetch_news():
    """جلب الأخبار من جميع المصادر"""
    all_news = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    for source in NEWS_SOURCES:
        try:
            resp = requests.get(source, timeout=8, headers=headers)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:15]:
                title = entry.get('title', '').strip()
                url = entry.get('link', '')
                if not title or len(title) < 10:
                    continue
                if not is_iraq_news(title + entry.get('summary', '')):
                    continue
                image_url = extract_image(entry)
                all_news.append({'title': title, 'url': url, 'image_url': image_url})
        except Exception as e:
            pass  # تجاهل أخطاء المصادر

    return all_news

# =====================================================
# إنشاء الصورة الاحترافية
# =====================================================
def download_image(url):
    """تحميل صورة من URL"""
    if not url:
        return None
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': 'https://www.google.com/',
        }
        resp = requests.get(url, timeout=8, headers=headers, stream=True)
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content)).convert('RGB')
    except:
        pass
    return None

def wrap_text(text, font, max_width, draw):
    """تقسيم النص إلى أسطر"""
    words = text.split()
    lines = []
    current = []
    for word in words:
        test = ' '.join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(' '.join(current))
            current = [word]
    if current:
        lines.append(' '.join(current))
    return lines

def draw_gradient_rect(draw, x1, y1, x2, y2, color_start, color_end, vertical=True):
    """رسم مستطيل بتدرج لوني"""
    if vertical:
        height = y2 - y1
        for i in range(height):
            t = i / max(height - 1, 1)
            r = int(color_start[0] * (1 - t) + color_end[0] * t)
            g = int(color_start[1] * (1 - t) + color_end[1] * t)
            b = int(color_start[2] * (1 - t) + color_end[2] * t)
            draw.line([(x1, y1 + i), (x2, y1 + i)], fill=(r, g, b))
    else:
        width = x2 - x1
        for i in range(width):
            t = i / max(width - 1, 1)
            r = int(color_start[0] * (1 - t) + color_end[0] * t)
            g = int(color_start[1] * (1 - t) + color_end[1] * t)
            b = int(color_start[2] * (1 - t) + color_end[2] * t)
            draw.line([(x1 + i, y1), (x1 + i, y2)], fill=(r, g, b))

def create_post_image(title, image_url, page_config):
    """إنشاء صورة المنشور بالتصميم الاحترافي"""
    try:
        p = page_config
        W, H = 1200, 850
        BAR = 90
        PAD = 20
        IH = H - BAR * 2

        canvas = Image.new('RGB', (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # ===== الشريط العلوي بتدرج لوني =====
        draw_gradient_rect(draw, 0, 0, W, BAR, p['bar_grad_start'], p['bar_grad_end'])

        # ===== الشريط السفلي بتدرج لوني =====
        draw_gradient_rect(draw, 0, H - BAR, W, H, p['bar_grad_end'], p['bar_grad_start'])

        # ===== الحدود الخارجية السميكة =====
        border_w = 5
        draw.rectangle([0, 0, W - 1, H - 1], outline=p['border1'], width=border_w)

        # ===== الحدود الداخلية الرفيعة =====
        inner = 12
        draw.rectangle([inner, inner, W - inner, H - inner], outline=p['border2'], width=2)

        # ===== صورة الخبر =====
        ix = PAD
        iy = BAR + PAD // 2
        iw = W - PAD * 2
        ih = IH - PAD

        news_image = download_image(image_url)
        if news_image:
            news_resized = news_image.resize((iw, ih), Image.LANCZOS)
            enhancer = ImageEnhance.Contrast(news_resized)
            news_resized = enhancer.enhance(1.1)
        else:
            # خلفية احترافية جميلة عند غياب الصورة
            news_resized = Image.new("RGB", (iw, ih), p['bar_grad_end'])
            bg_draw = ImageDraw.Draw(news_resized)
            for i in range(ih):
                t = i / max(ih - 1, 1)
                r = int(p['bar_grad_end'][0] * (1 - t) + p['overlay_color'][0] * t)
                g = int(p['bar_grad_end'][1] * (1 - t) + p['overlay_color'][1] * t)
                b = int(p['bar_grad_end'][2] * (1 - t) + p['overlay_color'][2] * t)
                bg_draw.line([(0, i), (iw, i)], fill=(max(0, r), max(0, g), max(0, b)))
            # نمط هندسي زخرفي
            dc = p['deco_color']
            for xi in range(0, iw, 80):
                for yi in range(0, ih, 80):
                    bg_draw.ellipse([xi - 2, yi - 2, xi + 2, yi + 2], fill=dc)
            lc = tuple(max(0, c - 20) for c in p['bar_grad_start'])
            for xi in range(-ih, iw, 60):
                bg_draw.line([(xi, 0), (xi + ih, ih)], fill=lc, width=1)
            for xi in range(0, iw + ih, 60):
                bg_draw.line([(xi, 0), (xi - ih, ih)], fill=lc, width=1)

        canvas.paste(news_resized, (ix, iy))

        # ===== حدود داخلية حول الصورة =====
        draw.rectangle([ix - 2, iy - 2, ix + iw + 2, iy + ih + 2],
                       outline=p['border2'], width=2)

        # ===== تعتيم تدريجي على الصورة للنص =====
        overlay = Image.new('RGBA', (iw, ih), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        overlay_h = ih // 2
        for i in range(overlay_h):
            alpha = int(200 * (i / overlay_h))
            ov_draw.line([(0, ih - overlay_h + i), (iw, ih - overlay_h + i)],
                         fill=(*p['overlay_color'], alpha))
        canvas_rgba = canvas.convert('RGBA')
        overlay_full = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        overlay_full.paste(overlay, (ix, iy))
        canvas_rgba = Image.alpha_composite(canvas_rgba, overlay_full)
        canvas = canvas_rgba.convert('RGB')
        draw = ImageDraw.Draw(canvas)

        # ===== زخارف الزوايا =====
        corner_size = 18
        dc = p['deco_color']
        corners = [(inner + 3, inner + 3), (W - inner - 3 - corner_size, inner + 3),
                   (inner + 3, H - inner - 3 - corner_size), (W - inner - 3 - corner_size, H - inner - 3 - corner_size)]
        for cx, cy in corners:
            draw.rectangle([cx, cy, cx + corner_size, cy + corner_size], outline=dc, width=2)
            draw.line([(cx + corner_size // 2, cy), (cx + corner_size // 2, cy + corner_size)], fill=dc, width=1)
            draw.line([(cx, cy + corner_size // 2), (cx + corner_size, cy + corner_size // 2)], fill=dc, width=1)

        # ===== اسم الصفحة في الشريطين =====
        page_name_ar = ar(p['name'])
        font_page = get_font(42)
        font_small = get_font(20)

        for bar_y_center in [BAR // 2, H - BAR // 2]:
            # توهج خلف النص
            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, -3), (0, 3), (-3, 0), (3, 0)]:
                bbox = draw.textbbox((0, 0), page_name_ar, font=font_page)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                draw.text((W // 2 - tw // 2 + dx, bar_y_center - th // 2 + dy),
                          page_name_ar, font=font_page, fill=p['glow'])
            # النص الرئيسي
            bbox = draw.textbbox((0, 0), page_name_ar, font=font_page)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((W // 2 - tw // 2, bar_y_center - th // 2),
                      page_name_ar, font=font_page, fill=p['bar_text'])

            # خط زخرفي بجانب الاسم
            line_y = bar_y_center
            draw.line([(W // 2 - tw // 2 - 60, line_y), (W // 2 - tw // 2 - 15, line_y)],
                      fill=p['deco_color'], width=2)
            draw.line([(W // 2 + tw // 2 + 15, line_y), (W // 2 + tw // 2 + 60, line_y)],
                      fill=p['deco_color'], width=2)

            # معين زخرفي
            mid_x = W // 2
            deco_size = 5
            draw.polygon([
                (mid_x - deco_size, line_y),
                (mid_x, line_y - deco_size),
                (mid_x + deco_size, line_y),
                (mid_x, line_y + deco_size)
            ], fill=p['deco_color'])

        # ===== عنوان الخبر على الصورة =====
        font_title = get_font(38)
        title_ar = ar(title)
        max_title_w = W - PAD * 4
        title_lines = wrap_text(title_ar, font_title, max_title_w, draw)
        if len(title_lines) > 3:
            title_lines = title_lines[:3]
            title_lines[-1] = title_lines[-1][:30] + '...'

        line_height = 50
        total_h = len(title_lines) * line_height
        title_y = H - BAR - PAD - total_h - 10

        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=font_title)
            tw = bbox[2] - bbox[0]
            tx = W // 2 - tw // 2
            # ظل النص
            for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                draw.text((tx + dx, title_y + dy), line, font=font_title, fill=(0, 0, 0))
            # النص الرئيسي
            draw.text((tx, title_y), line, font=font_title, fill=(255, 255, 255))
            title_y += line_height

        return canvas

    except Exception as e:
        print(f"⚠️ خطأ في إنشاء الصورة: {e}")
        traceback.print_exc()
        return None

# =====================================================
# النشر على فيسبوك
# =====================================================
def post_to_facebook(news, page_key):
    """نشر خبر على صفحة فيسبوك"""
    try:
        p = PAGES_CONFIG[page_key]
        token = p['token']
        page_id = p['page_id']

        if not token:
            return False

        image = create_post_image(news['title'], news.get('image_url', ''), p)

        if image:
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG', optimize=True)
            img_bytes.seek(0)

            resp = requests.post(
                f'https://graph.facebook.com/v18.0/{page_id}/photos',
                files={'source': img_bytes},
                data={
                    'caption': news['title'],
                    'access_token': token
                },
                timeout=30
            )
        else:
            resp = requests.post(
                f'https://graph.facebook.com/v18.0/{page_id}/feed',
                data={
                    'message': news['title'],
                    'access_token': token
                },
                timeout=30
            )

        if resp.status_code in [200, 201]:
            return True
        else:
            print(f"⚠️ فيسبوك رفض النشر على {page_key}: {resp.status_code} - {resp.text[:100]}")
            return False

    except Exception as e:
        print(f"⚠️ خطأ في النشر على {page_key}: {e}")
        return False

def post_to_all_pages(news):
    """نشر على جميع الصفحات بالتوازي"""
    posted = []

    def post_page(key):
        try:
            if post_to_facebook(news, key):
                return key
        except:
            pass
        return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(post_page, k): k for k in PAGES_CONFIG}
        for future in as_completed(futures, timeout=60):
            try:
                result = future.result()
                if result:
                    posted.append(result)
            except:
                pass

    return posted

# =====================================================
# الحلقة الرئيسية - لا توقف أبداً
# =====================================================
def main():
    print("=" * 60)
    print("🚀 نظام النشر المستمر - النسخة 23")
    print("✅ حلقة لا نهائية | معالجة شاملة للأخطاء")
    print("🎨 تصاميم احترافية | بدون ذكر المصدر")
    print("=" * 60)

    # تهيئة قاعدة البيانات
    while True:
        try:
            init_db()
            break
        except Exception as e:
            print(f"⚠️ إعادة محاولة تهيئة قاعدة البيانات: {e}")
            time.sleep(3)

    fetch_counter = 0
    cleanup_counter = 0
    post_count = 0
    start_time = time.time()

    print(f"⏰ بدء التشغيل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    while True:  # حلقة لا نهائية حقيقية
        try:
            loop_start = time.time()

            # ===== جلب الأخبار كل 3 دورات (30 ثانية) =====
            fetch_counter += 1
            if fetch_counter >= 3:
                fetch_counter = 0
                try:
                    news_list = fetch_news()
                    new_count = 0
                    for news in news_list:
                        try:
                            save_news(news['title'], news['url'], news.get('image_url', ''))
                            new_count += 1
                        except:
                            pass
                    if new_count > 0:
                        print(f"📰 {datetime.now().strftime('%H:%M:%S')} - جلب {new_count} خبر جديد")
                except Exception as e:
                    print(f"⚠️ خطأ في جلب الأخبار: {e}")

            # ===== نشر الأخبار المعلقة =====
            try:
                unposted = get_unposted()
                if unposted:
                    title_short = unposted['title'][:50]
                    print(f"📝 {datetime.now().strftime('%H:%M:%S')} - نشر: {title_short}...")

                    posted_pages = post_to_all_pages(unposted)

                    if posted_pages:
                        mark_posted(unposted['id'])
                        post_count += 1
                        print(f"✅ تم النشر على {len(posted_pages)} صفحات | إجمالي: {post_count}")
                    else:
                        # علّم الخبر كمنشور لتجنب التكرار اللانهائي
                        mark_posted(unposted['id'])
                        print(f"❌ فشل النشر - تخطي هذا الخبر")
                else:
                    print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - لا توجد أخبار جديدة")
            except Exception as e:
                print(f"⚠️ خطأ في دورة النشر: {e}")

            # ===== تنظيف دوري =====
            cleanup_counter += 1
            if cleanup_counter >= 120:  # كل 20 دقيقة
                cleanup_counter = 0
                try:
                    cleanup_old()
                    elapsed = (time.time() - start_time) / 60
                    print(f"🧹 تنظيف | وقت التشغيل: {elapsed:.0f} دقيقة | منشورات: {post_count}")
                except:
                    pass

            # ===== انتظار 10 ثواني =====
            elapsed = time.time() - loop_start
            wait = max(0, 10 - elapsed)
            if wait > 0:
                time.sleep(wait)

        except KeyboardInterrupt:
            print("\n⛔ توقف يدوي")
            break
        except Exception as e:
            # معالجة أي خطأ غير متوقع - الاستمرار دائماً
            print(f"⚠️ خطأ غير متوقع: {e}")
            traceback.print_exc()
            time.sleep(5)
            continue  # استمر في الحلقة

if __name__ == '__main__':
    main()
