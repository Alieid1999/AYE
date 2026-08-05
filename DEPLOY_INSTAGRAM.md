# Instagram Gateway Deployment on Render

## 🎯 Overview

Instagram Gateway تلقائياً:
- تراقب قاعدة بيانات Firestore
- تأخذ منتجات جديدة (حيث `instagramPosted = false`)
- تحمل الصور وتعدلها
- تنشرها على Instagram مع وصف وسعر وفئة
- تحدّث Firestore لتعليم المنتج كمنشور

## 🔧 المتطلبات

1. **حساب Instagram**: `ayemarket2` مع كلمة مرور آمنة
2. **Firebase Project**: مع Firestore قاعدة بيانات
3. **Render.com Account**: حساب مجاني أو مدفوع

## 📋 خطوات الـ Deployment

### 1️⃣ تحضير Firebase Credentials

```bash
# من Firebase Console:
# 1. اذهب إلى Project Settings > Service Accounts
# 2. انقر "Generate New Private Key"
# 3. سيحمل ملف JSON يحتوي على credentials
# 4. احفظ محتوى الملف (سنحتاجه قريباً)
```

### 2️⃣ إنشاء Render Service

**الطريقة الأولى - عبر Dashboard (سهلة):**

1. اذهب إلى [render.com](https://render.com)
2. انقر **New +** > **Cron Job**
3. اختر **Connect a repository** أو **Deploy a public repository**
4. ابحث عن `AYE` repository وانقر **Connect**
5. املأ التفاصيل:
   - **Name**: `instagram-gateway`
   - **Runtime**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python instagram_gateway.py`
   - **Schedule**: `*/10 * * * *` (كل 10 دقائق)

### 3️⃣ إضافة Environment Variables على Render

في dashboard Render، اذهب إلى **Environment** وأضف:

```
INSTAGRAM_USERNAME = ayemarket2
INSTAGRAM_PASSWORD = [كلمة المرور]
FIREBASE_CREDENTIALS_JSON = [محتوى ملف JSON كاملاً]
FIREBASE_STORAGE_BUCKET = aye-commercial-4b871.firebasestorage.app
```

**⚠️ مهم - أمان كلمة المرور:**
- لا تشارك كلمة المرور على GitHub
- استخدم Render's **Secret Management** (وليس السعر)
- اختر **Sync** = `false` للـ secrets

### 4️⃣ تحقق من Logs

```bash
# في Render Dashboard:
# 1. اذهب إلى Instagram Gateway service
# 2. انقر على "Logs" tab
# 3. يجب أن ترى:
#    ✅ Firebase initialized successfully
#    ✅ Logged into Instagram as @ayemarket2
#    🔍 Checking for new products...
```

## 📊 Firestore Collection Structure

يجب أن تكون مجموعة `products` بهذا الهيكل:

```json
{
  "id": "product_123",
  "title": "MacBook Pro 14\"",
  "description": "Apple MacBook Pro with M3 chip...",
  "price": 1499.99,
  "currency": "USD",
  "category": "Laptops",
  "image": "https://example.com/image.jpg",
  "images": ["https://example.com/image1.jpg", "..."],
  "instagramPosted": false,
  "instagramMediaId": null,
  "instagramPostTime": null,
  "createdAt": "2026-01-15T10:30:00Z"
}
```

## ⚙️ خطوات إضافية - اختيارية

### تفعيل البريد الإلكتروني للإشعارات

أضف متغير بيئي:
```
ADMIN_EMAIL = your-email@gmail.com
```

### تخصيص وقت الفحص

في `instagram_gateway.py`:
```python
# غيّر من:
schedule.every(10).minutes.do(...)

# إلى:
schedule.every(30).minutes.do(...)  # كل 30 دقيقة
schedule.every().hour.do(...)       # كل ساعة
schedule.every().day.at("09:00").do(...)  # يومياً في 9 صباحاً
```

### تخطي منتجات معينة

في Firestore، أضف:
```json
{
  "instagramSkip": true,
  "instagramReason": "Already posted manually"
}
```

## 🐛 استكشاف الأخطاء

### ❌ "BadPassword" Error
- تحقق من username و password
- جرب تسجيل الدخول يدوياً في Instagram

### ❌ "Firebase not initialized"
- تحقق من FIREBASE_CREDENTIALS_JSON
- تأكد أن ملف JSON كامل (بدون تقطيع)

### ❌ "No image downloaded"
- تحقق من رابط الصورة
- تأكد أن الصورة موجودة وقابلة للتنزيل

### ❌ "Firestore permission denied"
- في Firebase Console، احقق من Security Rules:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /products/{document=**} {
      allow read, write: if true;  // للاختبار فقط
    }
  }
}
```

## 📈 مراقبة الأداء

**متغيرات يمكنك تتبعها:**
- عدد المنتجات المنشورة
- عدد الفشل
- وقت آخر تحديث

هذه تُحفظ في `instagram_state.json`:
```json
{
  "posted_ids": ["prod_1", "prod_2"],
  "last_updated": "2026-01-15T15:30:00"
}
```

## 🚀 البدء السريع

```bash
# 1. اختبار محلياً
pip install -r requirements.txt
python instagram_gateway.py

# 2. Push إلى GitHub
git add -A
git commit -m "Add Instagram Gateway"
git push origin main

# 3. Deploy على Render
# (اتبع الخطوات أعلاه في Render Dashboard)
```

## 📞 الدعم

إذا واجهت مشاكل:
1. تحقق من logs في Render Dashboard
2. تأكد من بيانات اعتماد Firebase و Instagram
3. اختبر تحميل الصورة يدوياً

---

**آخر تحديث:** 2026-01-15
**الإصدار:** 1.0.0
