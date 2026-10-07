# 📚 Kitobxonlar Quiz V29

V29 — Telegram ichidagi kitob viktorina platformasi, nested UX va admin-only configuration bilan. **Web/HTML admin panel yo‘q.** Asosiy navigatsiya pastdagi Telegram Reply Keyboard bilan, ichki bo‘limlar Inline Keyboard bilan ishlaydi.

## 🧭 User arxitekturasi

Pastki menyu atigi 6 ta asosiy bo‘limdan iborat:

- 📚 KITOBLAR
- 🧠 TESTLAR
- 🏆 REYTING
- 👤 PROFIL
- 🎁 BONUSLAR
- ℹ️ YORDAM

### 📚 KITOBLAR

Ichida:

- 🔎 Kitob qidirish
- 📖 Barcha kitoblar
- 🔥 Mashhur kitoblar
- 🆕 Yangi kitoblar
- 📂 Janrlar
- ❤️ Sevimlilarim

Kitob ichida:

- 🧠 Testni boshlash
- 🎯 Qiyin savollar
- 📊 Mening natijam
- ❤️ Sevimliga qo‘shish

### 🧠 TESTLAR

- 📖 Kitob bo‘yicha
- 🎲 Tasodifiy test
- ⚡ Tezkor 5 ta
- 🎯 10 ta savol
- 🔥 Qiyin savollar
- 📅 Bugungi challenge
- ❌ Xato savollarim

### 🏆 REYTING

V29 da **faqat ikkita ochiq reyting** bor:

- 👑 TOP KITOBXONLAR
- 🔥 TOP REFERALLAR

Haftalik, oylik va mavsumiy TOPlar yo‘q. Admin TOP hisoblagichlarini kerak bo‘lsa alohida reset qiladi; umumiy foydalanuvchi tarixi o‘chirilmaydi.

### 👤 PROFIL

- 📊 Mening statistikam
- 🧠 Test tarixim
- ❌ Xato savollarim
- 🔥 Streakim
- 🏅 Yutuqlarim
- 🔗 Referral markazi
- ❤️ Sevimli kitoblarim

Referral markazida foydalanuvchi o‘zining jami tasdiqlangan referallari va TOP referral reytingidagi o‘rnini ko‘radi. Referral sozlamalarini faqat admin boshqaradi.

## 🔗 Referral qoidasi

`ref link → yangi user → majburiy kanal obunasi → tekshiruv → referral tasdiqlanadi`

O‘zini o‘zi referral qilish bloklangan. Bir foydalanuvchi faqat bir marta referral bilan bog‘lanadi.

## 👑 Admin arxitekturasi

Admin panel 7 ta markazga bo‘lingan:

- 📊 BOSHQARUV — dashboard, faol userlar, umumiy statistikalar, audit log
- 📚 KONTENT — kitoblar, savollar, TXT import, kategoriyalar, daily challenge, reportlar
- 👥 FOYDALANUVCHILAR — qidirish, individual boshqaruv, referral markazi, broadcast
- 🏆 REYTINGLAR — faqat TOP user/TOP referral parametrlar va resetlar
- 🎁 BONUSLAR — referral, streak, daily, achievement va manual bonus
- 📢 KANAL — majburiy kanallar, target kanal, post va reaction
- 🛠 TIZIM — umumiy sozlamalar, adminlar, xavfsizlik, cleanup, backup, audit, maintenance

### ❓ Savollar markazi

Admin:

- ➕ Bitta savol qo‘shishi mumkin
- 📋 Kitob bo‘yicha savollarni ko‘rishi mumkin
- 🟢/🔴 Savolni ON/OFF qilishi mumkin
- 🗃 Savolni arxivlashi mumkin
- 📥 100 tagacha savolni TXT bilan import qilishi mumkin
- 🔁 Duplicate savollarni aniqlaydi
- ⚠️ Format xatolarini importdan oldin ko‘rsatadi
- 📝 Foydalanuvchi reportlarini ko‘rishi mumkin

Qo‘lda savol qo‘shishda variantlar 4 qatorda beriladi:

```text
A) Variant A
B) Variant B
C) Variant C
D) Variant D
```

So‘ng:

```text
B medium
```

Bu yerda birinchi token javob, ikkinchi token `easy`, `medium` yoki `hard` bo‘lishi mumkin.

### 📥 TXT import formati

```text
1. Savol matni?
A) Variant A
B) Variant B
C) Variant C
D) Variant D
ANSWER: B
DIFFICULTY: medium
EXPLANATION: Ixtiyoriy izoh.
```

Maksimum 100 ta savol.

## ❤️ Reaction

Reaction parametrlari userga ochilmaydi. Faqat admin:

- ON/OFF
- emoji ro‘yxati
- big reaction ON/OFF

V29 reaction ro‘yxatidan tasodifiy bitta emoji tanlab, target kanalga yuborilgan postga qo‘yadi.

## 🛡 Xavfsizlik

- Admin filter
- Redis rate limit
- Maintenance mode
- Referral self-invite himoyasi
- Import validation
- Duplicate detection
- Destructive resetlarda confirmation
- Admin audit log
- Telegram ID lar `BIGINT`

## 🗄 Stack

- Python 3.13.5
- aiogram 3.31
- FastAPI
- SQLAlchemy 2.x async
- PostgreSQL / asyncpg
- Redis/Render Key Value
- Pydantic Settings
- Alembic

## 🚀 Render

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render Blueprint `render.yaml` orqali PostgreSQL va Key Value service birga yaratiladi. `PYTHON_VERSION=3.13.5` va `.python-version` orqali Python versiyasi pin qilingan. Web service `0.0.0.0:$PORT` ga bind qiladi.

### Environment Variables

```text
BOT_TOKEN=
ADMIN_IDS=123456789
DATABASE_URL=
REDIS_URL=
TARGET_CHANNEL_ID=-100xxxxxxxxxx
WEBHOOK_URL=https://your-service.onrender.com
WEBHOOK_SECRET=
APP_NAME=Kitobxonlar Quiz V29
LOG_LEVEL=INFO
```

`WEBHOOK_URL` berilsa webhook rejimi ishlaydi. Bo‘sh bo‘lsa lokal polling ishlaydi.

## 🧪 Lokal tekshiruv

```bash
python -m compileall app
pytest -q
```

Container muhitida Telegram/Render runtime uchun barcha tashqi paketlarni internetdan qayta o‘rnatish imkoni bo‘lmagani sabab real Telegram API smoke-test bajarilmadi. Syntax, AST, callback route va TXT parser testlari bajarildi.
