# 🌐 Unified Gateway - Telegram + WhatsApp + Instagram

**ملف واحد ينشر على ثلاث قنوات في نفس الوقت!**

## ✨ المميزات

✅ **Instagram** - ينشر الصور والأوصاف  
✅ **Telegram** - ينشر في القناة  
✅ **WhatsApp** - ينشر رسائل (عبر Twilio)  
✅ **موحد** - ملف Python واحد يجمع كل شي  
✅ **ذكي** - لا ينشر نفس المنتج مرتين  

---

## 🚀 الـ Deployment على Render

### 1️⃣ اذهب إلى Render Dashboard

```
https://dashboard.render.com
```

### 2️⃣ أنشئ Cron Job جديد

- اضغط **New +** → **Cron Job**
- اختر Repository **AYE**
- اضغط **Connect**

### 3️⃣ ملأ التفاصيل

| الحقل | القيمة |
|------|--------|
| **Name** | unified-gateway |
| **Runtime** | Python 3.11 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python unified_gateway.py` |
| **Schedule** | `*/10 * * * *` (كل 10 دقائق) |

### 4️⃣ أضف Environment Variables

في **Environment** اضغط **Add Environment Variable**:

```
FIREBASE_CREDENTIALS_JSON = [ملف JSON الكامل]
FIREBASE_STORAGE_BUCKET = aye-commercial-4b871.firebasestorage.app

TELEGRAM_BOT_TOKEN = [token من BotFather]
TELEGRAM_CHANNEL_ID = [معرف القناة]

TWILIO_ACCOUNT_SID = [من Twilio]
TWILIO_AUTH_TOKEN = [من Twilio]
WHATSAPP_TO = whatsapp:+966501234567

INSTAGRAM_USERNAME = ayemarket2
INSTAGRAM_PASSWORD = Qwertyuiop1@
```

**⚠️ هام**: وضّع `Sync = false` لكل الـ passwords و tokens!

---

## 🔧 كيفية العمل

```
1. كل 10 دقائق يفحص Firestore
2. يبحث عن منتجات حيث posted = false
3. ينشرها على:
   ✅ Instagram (صورة + وصف)
   ✅ Telegram (رسالة نصية + صورة)
   ✅ WhatsApp (رسالة نصية)
4. يحدّث Firestore: posted = true
```

---

## 📋 بيانات المنتج المطلوبة في Firestore

```json
{
  "title": "MacBook Pro 14\"",
  "description": "Apple MacBook Pro with M3 chip...",
  "price": 1499.99,
  "currency": "USD",
  "category": "Laptops",
  "image": "https://example.com/image.jpg",
  "images": ["image1.jpg", "image2.jpg"],
  "posted": false,
  "postedTime": null,
  "postedChannels": []
}
```

---

## 📱 إعداد كل قناة

### Telegram

1. تكلم مع [@BotFather](https://t.me/botfather)
2. اطلب: `/newbot`
3. اختر اسم البوت (مثلاً `AYE_Market_Bot`)
4. سيعطيك **token** (احفظه)
5. إنشئ قناة خاصة (أو استخدم موجودة)
6. أضف البوت للقناة كـ admin
7. احصل على معرف القناة:
   ```
   https://t.me/c/123456789 → ID = -100123456789
   ```

### WhatsApp (Twilio)

1. اذهب إلى [Twilio Console](https://www.twilio.com/console)
2. اضغط **Messaging** → **Programmable Messaging**
3. إنشئ WhatsApp Sandbox
4. احصل على:
   - **Account SID**
   - **Auth Token**
   - **Whatsapp FROM** (رقم Twilio)
5. أضف رقمك كـ **TO**

### Instagram

1. استخدم حسابك `ayemarket2`
2. تأكد من كلمة المرور صحيحة
3. قد تحتاج تفعيل "Apps and Websites" في الإعدادات

---

## 🧪 اختبر محلياً

```bash
# ثبت المكتبات
pip install -r requirements.txt

# اختبر البرنامج
python unified_gateway.py
```

### الـ Output المتوقع

```
============================================================
🚀 UNIFIED GATEWAY STARTED
============================================================
📱 Channels: Instagram + Telegram + WhatsApp
⏰ Checking every 10 minutes...
============================================================

🔍 Checking for new products...
🚀 Posting product: MacBook Pro 14"
============================================================
📸 Posting to Instagram: MacBook Pro 14"
✅ Instagram posted! Media ID: 123456
📱 Posting to Telegram: MacBook Pro 14"
✅ Telegram posted!
📲 Posting to WhatsApp: MacBook Pro 14"
✅ WhatsApp sent! Message ID: SM123456
✅ Posted to 3 channels
============================================================
```

---

## 📊 الملفات

| الملف | الوصف |
|------|-------|
| `unified_gateway.py` | **البرنامج الرئيسي** |
| `render_unified.yaml` | تكوين Render |
| `requirements.txt` | المكتبات (محدثة) |
| `gateway_state.json` | تتبع المنتجات المنشورة |

---

## 🐛 الأخطاء الشائعة

| الخطأ | الحل |
|------|------|
| `Telegram token not set` | أضف TELEGRAM_BOT_TOKEN |
| `Instagram: Invalid credentials` | تحقق من username و password |
| `Firebase not initialized` | تحقق من FIREBASE_CREDENTIALS_JSON |
| `Twilio error` | تأكد من TWILIO_ACCOUNT_SID و AUTH_TOKEN |

---

## 📈 المراقبة

في Render Dashboard:

1. اختر **unified-gateway**
2. اضغط **Logs** tab
3. شوف الـ status من البرنامج

---

## 🚀 ابدأ الآن!

```bash
# 1. Push التغييرات
git add unified_gateway.py render_unified.yaml requirements.txt
git commit -m "Add unified gateway for all channels"
git push origin main

# 2. Deploy على Render (من Dashboard)
# 3. ابدأ النشر الأوتوماتيكي! 🎉
```

---

**آخر تحديث:** 2026-01-15  
**الإصدار:** 1.0.0
