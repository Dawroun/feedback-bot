# 📋 O'quv Markazi Feedback Bot

Ota-onalardan ovozli va matnli feedback yig'ib, AI yordamida tahlil qiluvchi Telegram bot.

---

## 🎯 Imkoniyatlari

- ✅ Ovozli habar → avtomatik tekstga aylantirish (bepul)
- ✅ AI feedback tahlili (ijobiy / salbiy / neytral)
- ✅ Kurslar bo'yicha kategoriya
- ✅ Anonim yoki ismli feedback tanlash
- ✅ So'kinish / haqorat filtri (lokal + AI)
- ✅ Ogohlantirish tizimi (3 marta → ban)
- ✅ Rate limiting (kuniga 5 ta)
- ✅ Salbiy feedback kelganda adminlarga darhol xabar
- ✅ Kunlik avtomatik hisobot
- ✅ Web dashboard (grafiklar bilan)
- ✅ Anonim foydalanuvchini `/unmask` bilan aniqlash
- ✅ CSV export

---

## 📦 O'rnatish (qadam-baqadam)

### 1-qadam: Kompyuterga kerakli narsalarni o'rnatish

**Python o'rnatish** (agar yo'q bo'lsa):
- https://python.org saytidan Python 3.10+ yuklab oling
- O'rnatishda "Add Python to PATH" ni ✅ belgilang

**ffmpeg o'rnatish** (ovozli habarlar uchun kerak):
- Windows: https://ffmpeg.org/download.html dan yuklab, PATH ga qo'shing
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### 2-qadam: Telegram bot yaratish

1. Telegram'da **@BotFather** ni oching
2. `/newbot` yozing
3. Bot nomini kiriting (masalan: "My Center Feedback")
4. Bot username'ni kiriting (masalan: `mycenter_feedback_bot`)
5. BotFather sizga **token** beradi — uni saqlang!

### 3-qadam: O'z Telegram ID ni bilish

1. Telegram'da **@userinfobot** ni oching
2. `/start` bosing
3. U sizning **ID** raqamingizni ko'rsatadi — saqlang!

### 4-qadam: Groq API kalitini olish (BEPUL)

1. https://console.groq.com saytiga kiring
2. Google/GitHub bilan ro'yxatdan o'ting
3. "API Keys" bo'limidan yangi kalit yarating
4. Kalitni saqlang (masalan: `gsk_abc123...`)

### 5-qadam: Loyihani sozlash

```bash
# Loyihani yuklang (yoki papkani kompyuterga ko'chiring)
cd feedback-bot

# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# Sozlamalar faylini tayyorlash
cp .env.example .env
```

Endi `.env` faylni ochib, o'z ma'lumotlaringizni kiriting:

```env
BOT_TOKEN=7123456789:AAH...   # BotFather'dan olgan token
ADMIN_IDS=123456789            # O'z Telegram ID raqamingiz
GROQ_API_KEY=gsk_abc123...     # Groq'dan olgan kalit
CENTER_NAME=My Learning Center # O'quv markazingiz nomi
COURSES=Ingliz tili,Matematika,Dasturlash  # Kurslar ro'yxati
```

### 6-qadam: Ishga tushirish!

```bash
python run.py
```

Agar hammasi to'g'ri bo'lsa, ko'rasiz:
```
🚀 My Learning Center Feedback Bot ishga tushdi!
🌐 Dashboard ishga tushdi: http://0.0.0.0:5050
```

---

## 📱 Foydalanish

### Ota-onalar uchun:
1. Bot linkini ulashing: `https://t.me/your_bot_username`
2. Ota-ona `/start` bosadi
3. Anonim yoki ismli tanlaydi
4. Kurs tanlaydi
5. Ovozli yoki matnli feedback yuboradi
6. Bot "Rahmat!" deb javob beradi

### Admin uchun (Telegram):
| Buyruq | Vazifasi |
|--------|----------|
| `/admin` | Admin panel (tugmalar) |
| `/stats` | Umumiy statistika |
| `/report` | Kunlik AI hisobot |
| `/export` | CSV formatda yuklash |
| `/unmask 45` | #45 feedbackning haqiqiy egasini ko'rish |

### Web Dashboard:
Brauzerda oching: `http://localhost:5050`
- Grafiklar: sentiment, kurslar, dinamika
- Filtrlar: kurs va sentiment bo'yicha
- Jadval: barcha feedbacklar ro'yxati

---

## 🛡 Himoya tizimi

### So'kinish filtri
Bot so'kinish va haqoratni ikki bosqichda tekshiradi:
1. **Lokal filtr** — o'zbek, rus, ingliz so'kinish so'zlari
2. **AI filtr** — nozik haqoratlarni ham ushlaydi (Groq API)

### Ogohlantirish tizimi
- 1-chi marta: ⚠️ Ogohlantirish
- 2-chi marta: ⚠️ Ikkinchi ogohlantirish
- 3-chi marta: ⛔ Doimiy ban

### Rate Limiting
- Har bir foydalanuvchi kuniga max 5 ta feedback yuborishi mumkin
- `.env` da `MAX_DAILY_FEEDBACKS` ni o'zgartirsa bo'ladi

### Anonim foydalanuvchini topish
Admin `/unmask <id>` buyrug'i bilan anonim feedback egasini ko'ra oladi.
Bu yerda Telegram user ID, ism va username ko'rsatiladi.

---

## 🌐 Bepul hostingga joylashtirish (Render.com)

### 1. GitHub'ga yuklash

```bash
git init
git add .
git commit -m "Feedback bot"
# GitHub'da yangi repo yarating, keyin:
git remote add origin https://github.com/SIZNING_USERNAME/feedback-bot.git
git push -u origin main
```

### 2. Render.com da deploy

1. https://render.com ga kiring (GitHub bilan)
2. "New +" → "Web Service" bosing
3. GitHub repo'ni tanlang
4. Sozlamalar:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python run.py`
5. "Environment" bo'limiga `.env` dagi barcha o'zgaruvchilarni qo'shing
6. "Create Web Service" bosing

**Muhim:** Render free tier da bot 15 daqiqa ishlamasdan tursa uxlab qoladi.
Buni hal qilish uchun https://cron-job.org dan har 14 daqiqada 
dashboard URL ga ping yuboradigan cron job yarating.

---

## 📁 Loyiha tuzilmasi

```
feedback-bot/
├── bot.py              # Asosiy Telegram bot
├── analyzer.py         # AI feedback tahlili (Groq)
├── moderation.py       # So'kinish filtri + ban tizimi
├── speech_to_text.py   # Ovoz → tekst (Google STT)
├── database.py         # SQLite baza
├── dashboard.py        # Flask web dashboard
├── run.py              # Hammani ishga tushirish
├── requirements.txt    # Python kutubxonalari
├── .env.example        # Sozlamalar namunasi
├── .env                # Sizning sozlamalaringiz (MAXFIY!)
└── templates/
    └── dashboard.html  # Dashboard UI
```

---

## ❓ Tez-tez so'raladigan savollar

**S: Ovozli habar ishlamayapti?**
J: `ffmpeg` o'rnatilganligini tekshiring: `ffmpeg -version`

**S: AI tahlil ishlamayapti?**
J: Groq API kalitini tekshiring. https://console.groq.com da kalit faolligini ko'ring.

**S: Dashboard ochilmayapti?**
J: `http://localhost:5050` manzilini tekshiring. Port band bo'lsa `.env` da o'zgartiring.

**S: Bot javob bermayapti?**
J: Token to'g'riligini tekshiring. BotFather'da `/token` bilan yangilash mumkin.

**S: So'kinish filtri ko'p narsani bloklamoqda?**
J: `moderation.py` dagi `TOXIC_PATTERNS_UZ` ro'yxatdan kerak bo'lmagan so'zlarni olib tashlang.

---

## 📞 Yordam

Muammo bo'lsa, GitHub Issues'da yozing yoki Telegram orqali bog'laning.
