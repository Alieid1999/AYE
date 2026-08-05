# 🎬 Instagram Gateway

**ينشر تلقائياً جميع المنتجات الجديدة من Firestore إلى Instagram!**

## ✨ المميزات

✅ **مراقبة تلقائية** - يفحص Firestore كل 10 دقائق للمنتجات الجديدة
✅ **تحرير الصور** - يضبط حجم الصور تلقائياً بصيغة Instagram
✅ **وصف ذكي** - ينشئ captions احترافية مع الهاشتاجات
✅ **تتبع النشر** - يحفظ معرّف الـ post في Firestore
✅ **معالجة الأخطاء** - يتعامل مع الأخطاء بشكل آمن

## 🚀 البدء السريع

### الخطوة 1: اختبر محلياً

```bash
# ثبت المتطلبات
pip install -r requirements.txt

# اختبر الاتصالات
python test_instagram_gateway.py

# إذا كل شيء OK، شغّل البرنامج
python instagram_gateway.py
```

### الخطوة 2: Deploy على Render

اتبع التعليمات في [DEPLOY_INSTAGRAM.md](./DEPLOY_INSTAGRAM.md)

## 📊 كيفية العمل

```
┌─────────────────┐
│   Firestore DB  │ (المنتجات)
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Instagram Gateway       │ (يفحص كل 10 دقائق)
│ - Download Images       │
│ - Process & Resize      │
│ - Create Caption        │
│ - Post to Instagram     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────┐
│   Instagram     │ (منشور على الحساب)
│  @ayemarket2    │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   Firestore DB  │ (تحديث instagramPosted = true)
└─────────────────┘
```

## 🔧 المتغيرات البيئية المطلوبة

```bash
# حساب Instagram
INSTAGRAM_USERNAME=ayemarket2
INSTAGRAM_PASSWORD=Qwertyuiop1@

# Firebase (مفتاح الخدمة كـ JSON)
FIREBASE_CREDENTIALS_JSON='{"type":"service_account",...}'

# Bucket Storage
FIREBASE_STORAGE_BUCKET=aye-commercial-4b871.firebasestorage.app
```

## 📝 هيكل البيانات في Firestore

```json
{
  "title": "MacBook Pro 14\"",
  "description": "Apple MacBook Pro...",
  "price": 1499.99,
  "currency": "USD",
  "category": "Laptops",
  "image": "https://example.com/image.jpg",
  "instagramPosted": false
}
```

## 📱 تنسيق الـ Post

```
✨ MacBook Pro 14" ✨

📝 Apple MacBook Pro with M3 chip...

💰 Price: 1499.99 USD
🏷️ Category: Laptops

🛒 Shop now via our store!

#AYEMarket #TechProducts #Laptops #NewProduct #MacBookPro14
```

## 🛠️ التخصيص

### تغيير تكرار الفحص

في `instagram_gateway.py`:

```python
# من كل 10 دقائق:
schedule.every(10).minutes.do(self.check_new_products)

# إلى كل 30 دقيقة:
schedule.every(30).minutes.do(self.check_new_products)

# أو يومياً في الصباح:
schedule.every().day.at("09:00").do(self.check_new_products)
```

### تخطي منتجات معينة

أضف في Firestore:

```json
{
  "instagramSkip": true,
  "instagramReason": "Posted manually"
}
```

## 📊 الملفات المهمة

| الملف | الوصف |
|------|-------|
| `instagram_gateway.py` | البرنامج الرئيسي |
| `test_instagram_gateway.py` | اختبر الاتصالات |
| `DEPLOY_INSTAGRAM.md` | تعليمات الـ deployment |
| `instagram_gateway_render.yaml` | تكوين Render |
| `instagram_state.json` | قائمة المنتجات المنشورة |

## 📈 المراقبة

تحقق من الـ logs على Render:

```
✅ Firebase initialized successfully
✅ Logged into Instagram as @ayemarket2
🔍 Checking for new products...
📤 Posting product: MacBook Pro 14"
✅ Successfully posted to Instagram! Media ID: 123456
```

## ⚠️ الأخطاء الشائعة

| الخطأ | الحل |
|------|------|
| `BadPassword` | تحقق من كلمة المرور |
| `Firebase not initialized` | تحقق من FIREBASE_CREDENTIALS_JSON |
| `Image download failed` | تحقق من رابط الصورة |
| `No new products` | تحقق أن `instagramPosted = false` |

## 🔒 الأمان

- ✅ استخدم **Secret Variables** على Render للكلمات المرورية
- ✅ لا تشارك credentials على GitHub
- ✅ حدّث كلمة مرور Instagram دورياً
- ✅ استخدم App Password أو 2FA إذا أمكن

## 📞 الدعم

في حالة المشاكل:

1. شغّل `test_instagram_gateway.py`
2. تحقق من logs على Render
3. تأكد من صحة البيانات في Firestore
4. تحقق من تفعيل حسابك على Instagram

---

**آخر تحديث:** 2026-01-15 | **الإصدار:** 1.0.0
