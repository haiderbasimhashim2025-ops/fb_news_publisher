# 📤 تعليمات رفع الملفات إلى GitHub

## 🎯 الهدف
تفعيل نظام النشر التلقائي 24/7 على GitHub Actions

---

## 📋 الخطوات

### 1️⃣ إذا كان لديك مستودع GitHub بالفعل

```bash
cd /home/ubuntu/fb_news_publisher

# تحديث الملفات الموجودة
git add publisher_v8.py .github/workflows/publish.yml AUTOMATION_GUIDE.md GITHUB_SETUP.md

# إنشاء commit
git commit -m "🚀 تحديث النظام للعمل 24/7 على GitHub Actions - إضافة publisher_v8.py مع تنظيف قاعدة البيانات التلقائي"

# رفع التحديثات
git push origin main
```

### 2️⃣ إذا لم يكن لديك مستودع GitHub بعد

```bash
# إنشاء مستودع جديد
cd /home/ubuntu/fb_news_publisher
git init
git add .
git commit -m "🚀 نظام نشر الأخبار التلقائي 24/7 على GitHub Actions"

# إضافة المستودع البعيد
git remote add origin https://github.com/YOUR_USERNAME/fb_news_publisher.git
git branch -M main
git push -u origin main
```

---

## 🔐 إضافة GitHub Secrets

اذهب إلى: `https://github.com/YOUR_USERNAME/fb_news_publisher/settings/secrets/actions`

أضف 4 secrets بالضبط:

| Secret Name | القيمة |
|---|---|
| `PAGE_SALSSAL` | رمز الوصول لصفحة صلصال |
| `PAGE_CHAI` | رمز الوصول لصفحة چاي سادة |
| `PAGE_TABOGA` | رمز الوصول لصفحة طابوگة |
| `PAGE_TEIN` | رمز الوصول لصفحة طين |

---

## ✅ التحقق من التفعيل

1. اذهب إلى: `https://github.com/YOUR_USERNAME/fb_news_publisher/actions`
2. يجب أن ترى workflow باسم "نشر الأخبار التلقائي 24/7"
3. الـ workflow سيبدأ تلقائياً كل 5 دقائق
4. يمكنك مراقبة التشغيل في الـ Actions tab

---

## 🧪 اختبار يدوي

1. اذهب إلى Actions tab
2. اختر "نشر الأخبار التلقائي 24/7"
3. اضغط "Run workflow" > "Run workflow"
4. شاهد السجلات الحية

---

## 📊 المراقبة

يمكنك مراقبة:
- ✅ عدد الأخبار الجديدة في كل دورة
- ✅ عدد الأخبار المحذوفة من قاعدة البيانات
- ✅ نجاح/فشل النشر على كل صفحة
- ✅ الأخطاء والتحذيرات

---

## 🛑 إيقاف النظام (إذا لزم الأمر)

لإيقاف النشر التلقائي:
1. اذهب إلى Settings > Actions > General
2. اختر "Disable actions"

---

## 🚀 النتيجة النهائية

بعد اتباع هذه الخطوات:
- ✅ النشر التلقائي كل 5 دقائق
- ✅ 24/7 بدون توقف
- ✅ بدون أي تدخل يدوي
- ✅ تنظيف تلقائي لقاعدة البيانات
- ✅ منع تكرار الأخبار

**كل شيء يعمل بشكل تلقائي الآن! 🎉**
