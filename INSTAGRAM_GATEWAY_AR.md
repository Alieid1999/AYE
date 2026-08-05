# 🎬 Instagram Gateway - شرح سريع

## ✅ ما تم إنشاؤه؟

```
📁 AYE/
├── instagram_gateway.py           ⭐ البرنامج الرئيسي
├── test_instagram_gateway.py      🧪 اختبر الاتصالات
├── instagram_gateway_render.yaml  🚀 تكوين Render
├── DEPLOY_INSTAGRAM.md            📋 تعليمات الـ deployment
├── instagram_gateway_README.md    📖 التوثيق الكامل
├── requirements.txt               📦 المكتبات (تم التحديث)
└── .env.example                   🔐 متغيرات البيئة
```

## 🚀 الخطوات للبدء

### 1️⃣ اختبر محلياً (اختياري)

```bash
cd c:\Users\Ali\Desktop\AYE

# ثبت المكتبات
pip install -r requirements.txt

# اختبر الاتصالات
python test_instagram_gateway.py
```

### 2️⃣ احصل على Firebase Credentials

```
1. اذهب إلى: https://firebase.google.com
2. اختر مشروعك: aye-commercial-4b871
3. اذهب إلى: Project Settings > Service Accounts
4. اضغط: Generate New Private Key
5. سيحمل ملف JSON - احفظه
```

### 3️⃣ Deploy على Render

**الطريقة الأولى - الأسهل (عبر Render Dashboard):**

```
1. اذهب إلى: https://dashboard.render.com
2. اضغط: New +
3. اختر: Cron Job
4. اختر: Connect your repository (AYE)
5. اكمل التفاصيل:
   - Name: instagram-gateway
   - Runtime: Python 3.11
   - Build Command: pip install -r requirements.txt
   - Start Command: python instagram_gateway.py
   - Schedule: */10 * * * * (كل 10 دقائق)
```

**الطريقة الثانية - عبر render.yaml:**

```bash
git push origin main
# ثم Render سيقرأ instagram_gateway_render.yaml تلقائياً
```

### 4️⃣ أضف متغيرات البيئة على Render

في Render Dashboard > instagram-gateway > Environment:

```
INSTAGRAM_USERNAME = ayemarket2
INSTAGRAM_PASSWORD = Qwertyuiop1@
FIREBASE_CREDENTIALS_JSON = [محتوى ملف JSON كاملاً]
FIREBASE_STORAGE_BUCKET = aye-commercial-4b871.firebasestorage.app
```

### 5️⃣ تحقق من أن كل شيء يعمل

```
في Render Dashboard > instagram-gateway > Logs:
✅ Firebase initialized successfully
✅ Logged into Instagram as @ayemarket2
🔍 Checking for new products...
```

## 📱 كيفية العمل

```
1. كل 10 دقائق، البرنامج يفحص Firestore
2. يبحث عن منتجات حيث instagramPosted = false
3. يحمل الصورة ويعدلها
4. ينشرها على Instagram مع وصف وسعر
5. يحدّث Firestore: instagramPosted = true
```

## 🔧 ما الذي يحتاج تعديل؟

أضف هذا في Firestore لكل منتج:

```json
{
  "instagramPosted": false,
  "instagramMediaId": null,
  "instagramPostTime": null
}
```

## ⚠️ نقاط مهمة

✅ استخدم **Sync = false** للـ passwords على Render
✅ لا تشارك كلمة المرور مباشرة على GitHub
✅ اختبر locally أولاً قبل الـ deployment
✅ تحقق من logs إذا حصل خطأ

## 📊 الملفات الرئيسية

| الملف | الدور |
|------|-------|
| **instagram_gateway.py** | ينشر للـ Instagram تلقائياً |
| **test_instagram_gateway.py** | اختبر الاتصالات قبل الـ deployment |
| **DEPLOY_INSTAGRAM.md** | تعليمات مفصلة للـ deployment |

## 🆘 إذا حصل خطأ

```
1. شغّل: python test_instagram_gateway.py
2. تحقق من Render Logs
3. تأكد من صحة:
   - كلمة المرور Instagram
   - ملف Firebase JSON
   - بيانات المنتج في Firestore
```

## 📞 الدعم

تفاصيل كاملة في:
- **DEPLOY_INSTAGRAM.md** - deployment شامل
- **instagram_gateway_README.md** - توثيق كامل
- **test_instagram_gateway.py** - اختبر الاتصالات

---

**جاهز؟ ابدأ الآن! 🚀**
