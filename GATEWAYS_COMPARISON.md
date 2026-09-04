# 📦 Gateway Files Overview

## الملفات الأساسية

### 🌐 **Unified Gateway** (الخيار الأفضل)

```
unified_gateway.py          ← ملف واحد يجمع كل شي ✨
UNIFIED_GATEWAY_GUIDE.md    ← توثيق شامل
QUICK_START_UNIFIED.md      ← البدء السريع
.env.unified.example        ← متغيرات البيئة
render_unified.yaml         ← تكوين Render
```

**الاستخدام:**
```bash
python unified_gateway.py
```

**المخرجات:**
- ✅ Instagram

---

### 📸 **Instagram Gateway** (منفصل)

```
instagram_gateway.py        ← للـ Instagram فقط
DEPLOY_INSTAGRAM.md         ← توثيق
instagram_gateway_render.yaml
test_instagram_gateway.py
```

**الاستخدام:**
```bash
python instagram_gateway.py
```

---

## 🎯 الخيارات

### ✨ **Unified (موصى به)**

**الملف:** `unified_gateway.py`

**المميزات:**
- ✅ ملف Python واحد
- ✅ يدعم النشر على Instagram
- ✅ سهل للـ Deploy
- ✅ تحديث موحد

**المتطلبات:**
```
Python 3.11+
firebase-admin
instagrapi
```

**Deploy:**
```
Render Cron Job (Python)
```

---

## 🚀 البدء

### للـ Unified Gateway:

```bash
# 1. اختبر محلياً
python unified_gateway.py

# 2. Push للـ GitHub
git add unified_gateway.py requirements.txt render_unified.yaml UNIFIED_GATEWAY_GUIDE.md
git commit -m "Add unified gateway"
git push origin main

# 3. Deploy على Render
# - اذهب إلى Render Dashboard
# - أنشئ Cron Job جديد
# - استخدم: python unified_gateway.py
# - أضف Environment Variables
# - Done! ✨
```

---

## 📝 الملفات المحتاجة

```
✅ unified_gateway.py         (ملف البرنامج)
✅ requirements.txt            (المكتبات - محدثة)
✅ render_unified.yaml         (تكوين Render)
✅ UNIFIED_GATEWAY_GUIDE.md    (التوثيق الكامل)
✅ QUICK_START_UNIFIED.md      (البدء السريع)
✅ .env.unified.example        (متغيرات البيئة)
```

---

## ⚙️ الإعدادات المطلوبة

قبل الـ Deploy، تأكد من:

### Firebase:
- [ ] لديك Firebase Project
- [ ] لديك Service Account JSON
- [ ] لديك Firestore Database

### Instagram:
- [ ] لديك حساب `ayemarket2`
- [ ] تعرف كلمة المرور
- [ ] فعّلت "Apps and Websites"

---

## 🎯 الخطوات النهائية

1. **اختبر محلياً** (اختياري)
2. **أضف المتغيرات في Render**
3. **Deploy الـ Code**
4. **انتظر أول تشغيل (10 دقائق)**
5. **تفقد الـ Logs**
6. **كل شي جاهز!** ✨
