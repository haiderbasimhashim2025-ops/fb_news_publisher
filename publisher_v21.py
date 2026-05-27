#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام نشر الأخبار السريع جداً - النسخة 21
🚀 تحسينات السرعة:
   - معالجة متوازية للأخبار
   - تخزين مؤقت ذكي للصور
   - حذف الأخبار القديمة بسرعة
   - نشر متزامن على جميع الصفحات
   - تحسينات في استخدام الذاكرة
✅ نشر كل 10 ثواني (بدلاً من كل دقيقة)
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

# =====================================================
# إعداد arabic_reshaper
# =====================================================
reshaper = ArabicReshaper()

def ar(text):
    """تحويل النص العربي للعرض الصحيح"""
    if not text:
        return ""
    return reshaper.reshape(str(text))

FONT_PATH = "/usr/share/fonts/opentype/fonts-hosny-amiri/Amiri-Bold.ttf"

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf", size)
        except:
            return ImageFont.load_default()

# =====================================================
# إعدادات الصفحات مع الألوان الاحترافية المعتمدة
# =====================================================
PAGES_CONFIG = {
    'SALSSAL': {
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
    'CHAI': {
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
    'TABOGA': {
        'page_id': '1063874040148711',
        'name': 'طابوگة',
        'token': os.environ.get('PAGE_TABOGA', '').split('|')[1] if '|' in os.environ.get('PAGE_TABOGA', '') else '',
        'bar_grad_start': (18, 14, 8),
        'bar_grad_end':   (5, 3, 1),
        'bar_text':       (212, 175, 55),
        'border1':        (212, 175, 55),
        'border2':        (140, 105, 25),
        'glow':           (255, 215, 80),
        'overlay_color':  (5, 3, 0),
        'deco_color':     (212, 175, 55),
    },
    'TEIN': {
        'page_id': '1094102397116855',
        'name': 'طين',
        'token': os.environ.get('PAGE_TEIN', '').split('|')[1] if '|' in os.environ.get('PAGE_TEIN', '') else '',
        'bar_grad_start': (245, 235, 215),
        'bar_grad_end':   (210, 195, 170),
        'bar_text':       (120, 60, 10),
        'border1':        (190, 150, 65),
        'border2':        (100, 75, 30),
        'glow':           (220, 180, 80),
        'overlay_color':  (15, 8, 0),
        'deco_color':     (190, 150, 65),
    },
}

# مصادر الأخبار
NEWS_SOURCES = [
    'https://www.aljazeera.net/xml/feeds/all-news-stories.xml',
    'https://www.bbc.com/arabic/index.xml',
    'https://feeds.almasryalyoum.com/feeds/latest',
    'https://www.alarabiya.net/rss/latest/',
    'https://www.skynewsarabia.com/web/rss.xml',
    'https://www.france24.com/ar/feed',
    'https://www.dw.com/ar/feed',
    'https://www.alahram.org.eg/rss/',
    'https://www.alyaum.com/rss/',
    'https://www.almustaqbal.info/rss/',
]

# كلمات مفتاحية عراقية
IRAQ_KEYWORDS = ['العراق', 'بغداد', 'الموصل', 'البصرة', 'كركوك', 'أربيل', 'النجف', 'كربلاء', 'الحلة', 'الديوانية', 'الناصرية', 'ذي قار', 'ميسان', 'واسط', 'بابل', 'صلاح الدين', 'الأنبار', 'نينوى', 'دهوك', 'السليمانية', 'حلبجة', 'إقليم كردستان', 'الحكومة العراقية', 'البرلمان العراقي', 'الجيش العراقي', 'الشرطة العراقية']

DB_FILE = '/tmp/news_cache.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
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
    if not text:
        return None
    return hashlib.md5(text.encode()).hexdigest()

def is_duplicate(title, description, link):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    title_hash = calculate_hash(title)
    desc_hash  = calculate_hash(description)
    link_hash  = calculate_hash(link)
    try:
        for col, val in [('title_hash', title_hash), ('description_hash', desc_hash), ('link_hash', link_hash)]:
            if val:
                cursor.execute(f'SELECT id FROM duplicate_check WHERE {col} = ?', (val,))
                if cursor.fetchone():
                    return True
        return False
    except:
        return False
    finally:
        conn.close()

def is_arabic(text):
    if not text:
        return False
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    arabic_chars = len(arabic_pattern.findall(text))
    total_chars  = len(text)
    return (arabic_chars / total_chars) > 0.3 if total_chars > 0 else False

def is_iraq_related(text):
    if not text:
        return False
    for keyword in IRAQ_KEYWORDS:
        if keyword in text:
            return True
    return False

def fetch_news_fast():
    """جلب الأخبار بسرعة باستخدام معالجة متوازية"""
    news_list = []
    
    def fetch_source(source_url):
        try:
            feed = feedparser.parse(source_url)
            for entry in feed.entries[:5]:  # تقليل عدد الأخبار من كل مصدر
                title       = entry.get('title', '')
                description = entry.get('summary', '')
                link        = entry.get('link', '')
                description = BeautifulSoup(description, 'html.parser').get_text()[:150]
                if is_arabic(title) or is_arabic(description):
                    if is_iraq_related(title) or is_iraq_related(description):
                        if not is_duplicate(title, description, link):
                            image_url = None
                            if 'media_content' in entry:
                                image_url = entry.media_content[0]['url']
                            elif 'image' in entry:
                                image_url = entry.image.get('href')
                            return {
                                'title': title,
                                'description': description,
                                'link': link,
                                'image_url': image_url
                            }
        except:
            pass
        return None
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_source, url) for url in NEWS_SOURCES]
        for future in as_completed(futures):
            result = future.result()
            if result:
                news_list.append(result)
    
    return news_list

def save_to_db_fast(news):
    """حفظ سريع في قاعدة البيانات"""
    conn   = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        title_hash = calculate_hash(news['title'])
        desc_hash  = calculate_hash(news['description'])
        link_hash  = calculate_hash(news['link'])
        cursor.execute('''
            INSERT INTO news (title, title_hash, description, description_hash, link, link_hash, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (news['title'], title_hash, news['description'], desc_hash, news['link'], link_hash, news.get('image_url')))
        cursor.execute('''
            INSERT INTO duplicate_check (title_hash, description_hash, link_hash)
            VALUES (?, ?, ?)
        ''', (title_hash, desc_hash, link_hash))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_unposted_news_fast():
    """الحصول على أول خبر لم يتم نشره"""
    conn   = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, description, link, image_url FROM news
        WHERE posted_at IS NULL
        ORDER BY saved_at DESC LIMIT 1
    ''')
    result = cursor.fetchone()
    conn.close()
    if result:
        return {'id': result[0], 'title': result[1], 'description': result[2],
                'link': result[3], 'image_url': result[4]}
    return None

def mark_as_posted_fast(news_id, pages):
    """تحديث حالة الخبر بسرعة"""
    conn   = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE news SET posted_at = CURRENT_TIMESTAMP, posted_pages = ? WHERE id = ?
    ''', (','.join(pages), news_id))
    conn.commit()
    conn.close()

def cleanup_old_news_fast():
    """حذف سريع للأخبار القديمة"""
    conn   = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM news WHERE saved_at < datetime('now', '-12 hours')")
    cursor.execute("DELETE FROM duplicate_check WHERE created_at < datetime('now', '-12 hours')")
    conn.commit()
    conn.close()

def download_image_fast(image_url):
    """تحميل الصورة بسرعة مع تقليل الحجم"""
    try:
        response = requests.get(image_url, timeout=3)
        if response.status_code == 200:
            img = Image.open(io.BytesIO(response.content)).convert("RGB")
            return img
    except:
        pass
    return None

# =====================================================
# دوال التصميم المحسّنة للسرعة
# =====================================================
def draw_gradient_rect_fast(img, x1, y1, x2, y2, color_start, color_end):
    """رسم مستطيل بتدرج لوني عمودي"""
    draw  = ImageDraw.Draw(img)
    steps = max(y2 - y1, 1)
    for i in range(steps):
        t = i / (steps - 1) if steps > 1 else 0
        r = int(color_start[0] + (color_end[0] - color_start[0]) * t)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * t)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * t)
        draw.line([(x1, y1 + i), (x2, y1 + i)], fill=(r, g, b))

def draw_ornament_fast(draw, cx, y, color):
    """رسم زخرفة معينية مركزية مع خطوط جانبية"""
    lw = 180
    draw.rectangle([cx - lw - 25, y+3, cx - 25, y+5], fill=color)
    draw.rectangle([cx + 25, y+3, cx + lw + 25, y+5], fill=color)
    pts = [(cx, y-4), (cx+10, y+4), (cx, y+12), (cx-10, y+4)]
    draw.polygon(pts, fill=color)

def draw_corner_ornament_fast(draw, x, y, size, color, corner="tl"):
    """رسم زخرفة زاوية احترافية"""
    s = size
    if corner == "tl":
        draw.line([(x, y), (x+s, y)], fill=color, width=3)
        draw.line([(x, y), (x, y+s)], fill=color, width=3)
    elif corner == "tr":
        draw.line([(x-s, y), (x, y)], fill=color, width=3)
        draw.line([(x, y), (x, y+s)], fill=color, width=3)
    elif corner == "bl":
        draw.line([(x, y-s), (x, y)], fill=color, width=3)
        draw.line([(x, y), (x+s, y)], fill=color, width=3)
    elif corner == "br":
        draw.line([(x, y-s), (x, y)], fill=color, width=3)
        draw.line([(x-s, y), (x, y)], fill=color, width=3)

def draw_text_with_glow_fast(img, text, font, cx, y, text_color, glow_color, glow_radius=4):
    """رسم نص مع تأثير توهج احترافي"""
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow_layer)
    bbox = gd.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    tx   = cx - tw // 2
    for dx in range(-glow_radius, glow_radius + 1):
        for dy in range(-glow_radius, glow_radius + 1):
            if dx*dx + dy*dy <= glow_radius*glow_radius:
                gd.text((tx+dx, y+dy), text, font=font, fill=(*glow_color, 80))
    glow_blur = glow_layer.filter(ImageFilter.GaussianBlur(glow_radius))
    img_rgba  = img.convert("RGBA")
    img_rgba  = Image.alpha_composite(img_rgba, glow_blur)
    img       = img_rgba.convert("RGB")
    draw      = ImageDraw.Draw(img)
    draw.text((tx+1, y+1), text, font=font, fill=(0, 0, 0))
    draw.text((tx, y),     text, font=font, fill=text_color)
    return img

def wrap_text(draw, text, font, max_width):
    """تقسيم النص إلى أسطر"""
    words   = text.split()
    lines   = []
    current = []
    for word in words:
        current.append(word)
        test = ar(" ".join(current))
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if len(current) > 1:
                current.pop()
                lines.append(ar(" ".join(current)))
                current = [word]
            else:
                lines.append(ar(word))
                current = []
    if current:
        lines.append(ar(" ".join(current)))
    return lines

def create_post_image_fast(title, description, image_url, page_config):
    """إنشاء صورة المنشور بالتصميم الاحترافي المعتمد"""
    try:
        p = page_config

        # ===== الأبعاد =====
        W   = 1200
        BAR = 110
        OB1 = 10
        OB2 = 3
        GAP = 5
        PAD = OB1 + OB2 + GAP + 8
        IH  = 630
        H   = BAR * 2 + IH

        # ===== تحميل صورة الخبر =====
        news_image = None
        if image_url:
            news_image = download_image_fast(image_url)

        # ===== الخلفية =====
        canvas = Image.new("RGB", (W, H), p['bar_grad_start'])

        # ===== تدرج الشريطين =====
        draw_gradient_rect_fast(canvas, 0, 0, W, BAR,
                           p['bar_grad_start'], p['bar_grad_end'])
        draw_gradient_rect_fast(canvas, 0, BAR + IH, W, H,
                           p['bar_grad_end'], p['bar_grad_start'])

        draw = ImageDraw.Draw(canvas)

        # ===== الحدود المزدوجة =====
        draw.rectangle([0, 0, W-1, H-1], outline=p['border1'], width=OB1)
        m = OB1 + GAP
        draw.rectangle([m, m, W-1-m, H-1-m], outline=p['border2'], width=OB2)

        # ===== خطوط الفصل =====
        sep_y = BAR
        draw.rectangle([0, sep_y - OB1, W, sep_y], fill=p['border1'])
        draw.rectangle([m, sep_y - OB1 - GAP - OB2, W-m, sep_y - OB1 - GAP],
                       fill=p['border2'])
        sep_y2 = BAR + IH
        draw.rectangle([0, sep_y2, W, sep_y2 + OB1], fill=p['border1'])
        draw.rectangle([m, sep_y2 + OB1 + GAP, W-m, sep_y2 + OB1 + GAP + OB2],
                       fill=p['border2'])

        # ===== صورة الخبر =====
        ix = PAD
        iy = BAR + PAD // 2
        iw = W - PAD * 2
        ih = IH - PAD

        if news_image:
            news_resized = news_image.resize((iw, ih), Image.LANCZOS)
            enhancer     = ImageEnhance.Contrast(news_resized)
            news_resized = enhancer.enhance(1.1)
        else:
            # خلفية رمادية داكنة عند غياب الصورة
            news_resized = Image.new("RGB", (iw, ih), (40, 40, 40))

        canvas.paste(news_resized, (ix, iy))

        # ===== حدود داخلية حول الصورة =====
        draw.rectangle([ix-OB2-2, iy-OB2-2, ix+iw+OB2+1, iy+ih+OB2+1],
                       outline=p['border2'], width=OB2)

        # ===== تعتيم تدريجي ناعم =====
        ov_h = ih * 52 // 100
        for i in range(ov_h):
            t     = i / ov_h
            alpha = int(30 + 160 * (t ** 0.7))
            r, g, b = p['overlay_color']
            overlay_line = Image.new("RGBA", (iw, 1), (r, g, b, alpha))
            c_rgba = canvas.convert("RGBA")
            c_rgba.paste(overlay_line, (ix, iy + ih - ov_h + i), overlay_line)
            canvas = c_rgba.convert("RGB")

        draw = ImageDraw.Draw(canvas)

        # ===== عنوان الخبر على الصورة =====
        title_font = get_font(50)
        lines      = wrap_text(draw, title, title_font, iw - 100)
        line_h     = 65
        total_h    = len(lines) * line_h
        ty         = iy + ih - total_h - 28
        cx         = W // 2

        for line in lines:
            canvas = draw_text_with_glow_fast(canvas, line, title_font, cx, ty,
                                         (255, 255, 255), p['glow'], glow_radius=4)
            draw   = ImageDraw.Draw(canvas)
            ty    += line_h

        # ===== اسم الصفحة في الشريطين =====
        name_font = get_font(64)
        name_ar   = ar(p['name'])
        bbox      = draw.textbbox((0, 0), name_ar, font=name_font)
        nh        = bbox[3] - bbox[1]

        # شريط علوي
        ny1    = (BAR - nh) // 2 - 5
        canvas = draw_text_with_glow_fast(canvas, name_ar, name_font, W//2, ny1,
                                      p['bar_text'], p['glow'], glow_radius=5)
        draw   = ImageDraw.Draw(canvas)

        # شريط سفلي
        bot_top = BAR + IH + OB1
        ny2     = bot_top + (BAR - OB1 - nh) // 2 - 5
        canvas  = draw_text_with_glow_fast(canvas, name_ar, name_font, W//2, ny2,
                                       p['bar_text'], p['glow'], glow_radius=5)
        draw    = ImageDraw.Draw(canvas)

        # ===== زخارف معينية =====
        draw_ornament_fast(draw, W//2, (BAR - 10) // 2, p['deco_color'])
        draw_ornament_fast(draw, W//2, bot_top + (BAR - OB1) // 2 - 5, p['deco_color'])

        # ===== زخارف الزوايا =====
        corner_s = 30
        margin   = OB1 + GAP + 8
        for cx_c, cy_c, pos in [
            (margin, margin, "tl"),
            (W - margin, margin, "tr"),
            (margin, H - margin, "bl"),
            (W - margin, H - margin, "br"),
        ]:
            draw_corner_ornament_fast(draw, cx_c, cy_c, corner_s, p['deco_color'], pos)

        return canvas

    except Exception as e:
        print(f"خطأ في إنشاء الصورة: {e}")
        return None

def post_to_facebook_fast(news, page_key):
    """نشر سريع على فيسبوك"""
    page_config = PAGES_CONFIG[page_key]
    if not page_config['token']:
        return False
    try:
        page_id = page_config['page_id']
        access_token = page_config['token']

        image = create_post_image_fast(
            news['title'],
            news.get('description', ''),
            news.get('image_url'),
            page_config
        )

        if image:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG', optimize=True)
            img_byte_arr.seek(0)

            response = requests.post(
                f'https://graph.facebook.com/v18.0/{page_id}/photos',
                files={'source': img_byte_arr},
                data={
                    'caption': f"{news['title']}\n\n{news.get('description', '')}",
                    'access_token': access_token
                },
                timeout=10
            )
        else:
            response = requests.post(
                f'https://graph.facebook.com/v18.0/{page_id}/feed',
                data={
                    'message': f"{news['title']}\n\n{news.get('description', '')}",
                    'access_token': access_token
                },
                timeout=10
            )

        return response.status_code in [200, 201]
    except Exception as e:
        print(f"خطأ في النشر على {page_key}: {e}")
        return False

def post_to_all_pages_fast(news):
    """نشر متزامن على جميع الصفحات"""
    posted_pages = []
    
    def post_page(page_key):
        if PAGES_CONFIG[page_key]['token']:
            if post_to_facebook_fast(news, page_key):
                return page_key
        return None
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(post_page, key) for key in PAGES_CONFIG.keys()]
        for future in as_completed(futures):
            result = future.result()
            if result:
                posted_pages.append(result)
    
    return posted_pages

# =====================================================
# الحلقة الرئيسية السريعة
# =====================================================
def main_loop_fast():
    print("🚀 بدء نظام النشر السريع جداً - النسخة 21")
    print("⚡ نشر كل 10 ثواني | معالجة متوازية | تصاميم احترافية")
    print("=" * 60)

    init_db()
    cleanup_counter = 0

    while True:
        try:
            start_time = time.time()
            
            # جلب الأخبار بسرعة
            news_list = fetch_news_fast()
            
            # حفظ الأخبار الجديدة
            for news in news_list:
                save_to_db_fast(news)
            
            # نشر الأخبار المعلقة
            unposted = get_unposted_news_fast()
            if unposted:
                print(f"📝 {datetime.now().strftime('%H:%M:%S')} - نشر: {unposted['title'][:50]}...")
                posted_pages = post_to_all_pages_fast(unposted)
                if posted_pages:
                    mark_as_posted_fast(unposted['id'], posted_pages)
                    print(f"✅ تم النشر على {len(posted_pages)} صفحات")
                else:
                    print(f"❌ فشل النشر")
            
            # تنظيف دوري
            cleanup_counter += 1
            if cleanup_counter >= 60:  # كل 10 دقائق
                cleanup_old_news_fast()
                cleanup_counter = 0
            
            # الانتظار حتى 10 ثواني
            elapsed = time.time() - start_time
            wait_time = max(0, 10 - elapsed)
            if wait_time > 0:
                time.sleep(wait_time)
                
        except Exception as e:
            print(f"❌ خطأ: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main_loop_fast()
