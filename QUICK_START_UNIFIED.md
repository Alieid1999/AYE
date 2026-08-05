# 🚀 Unified Gateway - Quick Start Guide

## ⚡ البدء السريع (5 دقائق)

### 1️⃣ تحضير البيانات (10 دقائق)

**Telegram:**
```
1. اذهب إلى @BotFather
2. اكتب: /newbot
3. اختر اسم البوت
4. احصل على TOKEN
5. إنشئ قناة وأضف البوت
6. احصل على ID (-100...)
```

**WhatsApp (Twilio):**
```
1. اذهب إلى twilio.com
2. إنشئ حساب
3. اختر Messaging → Whatsapp
4. احصل على Account SID و Auth Token
5. أضف رقمك في Sandbox
```

**Firebase:**
```
1. Firebase Console > Project Settings
2. Service Accounts
3. Generate Private Key (JSON)
4. احفظ محتوى الملف كاملاً
```

**Instagram:**
```
استخدم:
Username: ayemarket2
Password: Qwertyuiop1@
```

---

### 2️⃣ Deploy على Render

**الخطوة 1:** اذهب إلى https://render.com/dashboard

**الخطوة 2:** اضغط **New +** → **Cron Job**

**الخطوة 3:** اختر Repository **AYE** واضغط **Connect**

**الخطوة 4:** ملأ:
```
Name: unified-gateway
Runtime: Python 3.11
Build: pip install -r requirements.txt
Start: python unified_gateway.py
Schedule: */10 * * * *
```

**الخطوة 5:** اضغط **Create Cron Job**

**الخطوة 6:** اذهب إلى **Environment** وأضف المتغيرات:

```
✅ FIREBASE_CREDENTIALS_JSON    (Sync: false)
✅ FIREBASE_STORAGE_BUCKET      (aye-commercial-4b871.firebasestorage.app)
✅ TELEGRAM_BOT_TOKEN           (Sync: false)
✅ TELEGRAM_CHANNEL_ID          (Sync: false)
✅ TWILIO_ACCOUNT_SID           (Sync: false)
✅ TWILIO_AUTH_TOKEN            (Sync: false)
✅ WHATSAPP_FROM                (whatsapp:+14155238886)
✅ WHATSAPP_TO                  (whatsapp:+966...)
✅ INSTAGRAM_USERNAME           (ayemarket2)
✅ INSTAGRAM_PASSWORD           (Sync: false)
```

**الخطوة 7:** اضغط **Save**

---

### 3️⃣ اختبر

في Render Dashboard:
1. اختر **unified-gateway**
2. اضغط **Manual Trigger** أو انتظر 10 دقائق
3. اضغط **Logs** وشوف النتائج

### Output المتوقع:

```
============================================================
🚀 UNIFIED GATEWAY STARTED
============================================================
📱 Channels: Instagram + Telegram + WhatsApp
⏰ Checking every 10 minutes...
============================================================

🔍 Checking for new products...
✅ Posted to 3 channels
```

---

## ✅ Checklist

- [ ] أنشأت Telegram Bot
- [ ] أنشأت Twilio Account
- [ ] احصلت على Firebase Credentials
- [ ] إضافة كل المتغيرات في Render
- [ ] Push التغييرات للـ Git

---

## 📊 Firestore Collection

أضف هذه الحقول للمنتج:

```json
{
  "title": "Product Name",
  "description": "Description",
  "price": 99.99,
  "currency": "USD",
  "category": "Category",
  "image": "url",
  "posted": false
}
```

---

## 🎯 النتيجة

✅ كل منتج جديد ينشر تلقائياً على:
- 📸 Instagram
- 📱 Telegram
- 💬 WhatsApp

---

## 🆘 مشاكل شائعة

**❌ "Telegram token not set"**
→ أضف TELEGRAM_BOT_TOKEN في Environment

**❌ "Instagram: Invalid credentials"**
→ تحقق من username و password صحيح

**❌ "Firebase not initialized"**
→ تحقق من FIREBASE_CREDENTIALS_JSON كاملة

**❌ "Twilio error"**
→ تحقق من Account SID و Auth Token

---

**🎉 خلاص! كل شي جاهز!**

كل منتج جديد سينشر تلقائياً على الثلاث قنوات في نفس الوقت!
