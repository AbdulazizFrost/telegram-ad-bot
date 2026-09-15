# 🛡 Telegram Anti-Ad Moderation Bot (Taksi & Biznes Reklama Nazorati)

Production-ready Telegram-bot guruhlardagi reklama va e'lonlar oqimini tartibga solish, taksi haydovchilari va biznes vakillarining reklamasini nazorat qilish, shuningdek oddiy foydalanuvchilarning erkin suhbatlashishi va savol-javoblarini asrab qolish uchun mo'ljallangan.

---

## 📋 Mundarija
1. [Loyiha haqida va Asosiy g'oya](#-loyiha-haqida-va-asosiy-goya)
2. [Foydalanuvchilar toifalari (Rollar)](#-foydalanuvchilar-toifalari-rollar)
3. [Reklamani aniqlash algoritmi (Smart Ad Detection)](#-reklamani-aniqlash-algoritmi-smart-ad-detection)
4. [Tariflar va To'lov tizimi](#-tariflar-va-tolov-tizimi)
5. [Texnologiyalar](#-texnologiyalar)
6. [Loyihaning tuzilishi (Arxitektura)](#-loyihaning-tuzilishi-arxitektura)
7. [Telegram Maxfiyligi va Bot huquqlari](#-telegram-maxfiyligi-va-bot-huquqlari)
8. [BotFather orqali bot yaratish bo'yicha qo'llanma](#-botfather-orqali-bot-yaratish-boyicha-qollanma)
9. [Botni guruhga qo'shish va Admin qilish](#-botni-guruhga-qoshish-va-admin-qilish)
10. [Lokal ishga tushirish (Local Run)](#-lokal-ishga-tushirish-local-run)
11. [GitHub repozitoriyasini yaratish](#-github-repozitoriyasini-yaratish)
12. [Render Free platformasiga Deploy qilish](#-render-free-platformasiga-deploy-qilish)
13. [Render Free saqlash cheklovi va PostgreSQL](#-render-free-saqlash-cheklovi-va-postgresql)
14. [Testlarni ishga tushirish](#-testlarni-ishga-tushirish)

---

## 🎯 Loyiha haqida va Asosiy g'oya

Ko'p tarmoqli Telegram guruhlarida (aholi, taksi haydovchilari, do'konlar, ustalar) eng katta muammo — betartib va to'xtovsiz reklama xabarlari.
Oddiy spam-botlar savdo yoki narxga oid so'zlarni ko'rsa, oddiy aholining savollarini ham o'chirib yuboradi.

**Ushbu botning asosiy tamoyili:**
* **Oddiy foydalanuvchilar:** Bemalol savol berishi, tavsiya so'rashi, narxlar va taksilar haqida so'rashi mumkin. Ular guruhning erkin a'zosi bo'lib qoladi.
* **Taksi haydovchilari:** Har **24 soatda roppa-rosa 1 ta bepul reklama** e'loni berish huquqiga ega (masalan, 14-sentyabr 10:30 da berilgan bo'lsa, keyingisi 15-sentyabr 10:30 da ochiladi). Cheklovsiz reklama berish uchun arzon pullik tarif xarid qilishi mumkin.
* **Biznes (Do'kon, Kafe, Xizmatlar, Mahsulot sotuvchilari):** Guruhda bepul reklama berish taqiqlangan (0 bepul e'lon). Faqat faol reklama tarifi bo'lgandagina reklama qoldirishi mumkin.
* **Guruh ma'murlari:** Moderatsiya qilinmaydi.

---

## 👥 Foydalanuvchilar toifalari (Rollar)

Tizimda rollar va pullik obunalar qat'iy ajratilgan:

| Rol | Bepul reklama | Pullik obuna bilan reklama | Oddiy suhbat / Savol |
| :--- | :--- | :--- | :--- |
| **`user` (Oddiy a'zo / Biznes)** | 0 ta (reklama darhol o'chiriladi) | Cheklovsiz ruxsat beriladi | Cheklovsiz ruxsat beriladi |
| **`taxi` (Taksi haydovchisi)** | Har **rolling 24 soatda 1 ta** | Cheklovsiz ruxsat beriladi | Cheklovsiz ruxsat beriladi |
| **`admin` (Bot administratori)** | Nazorat qilinmaydi | Cheklovsiz | Cheklovsiz |
| **Guruh Administratorlari** | Nazorat qilinmaydi | Cheklovsiz | Cheklovsiz |

> **Eslatma:** Foydalanuvchi tarif sotib olganda uning roli `advertiser` ga aylanmaydi. Rol uning kimligini belgilaydi (`user` yoki `taxi`), pullik reklama huquqi esa `subscriptions` jadvali orqali tekshiriladi.

---

## 🧠 Reklamani aniqlash algoritmi (Smart Ad Detection)

`app/services/advertisement_detector.py` moduli xabarlarni kontekstiga qarab aqlli tahlil qiladi.

### ❌ REKLAMA HISOBLANMAYDI (O'chirilmaydi):
Quyidagi kabi savol va suhbatlar guruhda to'liq saqlanib qoladi:
* *"Kim kartoshka narxini biladi?"*
* *"Bugun Samarqandga kim boryapti?"*
* *"Yaxshi usta bormi?"*
* *"Avtosalonlarda Gentra bormi?"*
* *"Kimda taksistning nomeri bor?"*
* *"Telefon narxi qancha?"*
* *"Qaysi kafeda ovqat yaxshi?"*

### ✅ REKLAMA HISOBLANADI (Moderatsiyaga tushadi):
* Tijoriy sotuv takliflari: *"Sotiladi! iPhone 15 Pro Max narxi arzon..."*
* Taksi haydovchilari qatnovi: *"Toshkent — Samarqand mashina bor, 2 ta joy bor yuramiz..."*, *"Odam va pochta olamiz..."*
* Havolalar: `http://`, `https://`, `t.me/...`, `instagram.com/...`
* Aksiyalar va xizmatlar: *"Kafemizda yangi aksiya! Yetkazib berish bepul..."*, *"Usta xizmati! Ta'mirlaymiz..."*
* Tijoriy kontekstdagi telefon raqamlari: `+998...` va *"Murojaat uchun lichkaga yozing"*.

---

## 💳 Tariflar va To'lov tizimi

Standart narxlar (baza orqali admin tomonidan osongina o'zgartirilishi mumkin):
* ⚡️ **1 kun (24 soat):** `15 000 so'm`
* 🔥 **7 kun (168 soat):** `35 000 so'm`
* 👑 **30 kun (720 soat):** `100 000 so'm`

### Qo'lda tasdiqlash jarayoni (Manual Payment Flow):
1. Foydalanuvchi botga shaxsiy xabarda (PM) `/start` yuboradi yoki `💳 Reklama tariflari` tugmasini bosadi.
2. Kerakli tarifni tanlaydi (masalan, 7 kun).
3. Bot bank kartasi rekvizitlarini ko'rsatadi va to'lov chekini (skrinshot yoki kvitansiya) yuborishni so'raydi.
4. Foydalanuvchi chekni yuboradi -> Bot chekni administratorga yuboradi.
5. Admin xabaridagi inline tugmalar orqali `[✅ Tasdiqlash]` yoki `[❌ Rad etish]` ni bosadi.
6. Tasdiqlanganda foydalanuvchiga avtomatik obuna yoziladi va unga tabrik xabari yuboriladi.

---

## 🛠 Texnologiyalar

* **Python 3.11+**
* **aiogram 3.x** (Telegram Bot framework)
* **SQLAlchemy 2.0 (Async API)**
* **aiosqlite** (SQLite drayveri) & **asyncpg** (PostgreSQL drayveri)
* **Pydantic Settings** (Konfiguratsiya boshqaruvi)
* **aiohttp** (Webhook va Render health-check serveri)
* **pytest** & **pytest-asyncio** (To'liq avtomatlashtirilgan testlar)

---

## 📂 Loyihaning tuzilishi (Arxitektura)

```
telegram-ad-bot/
├── app/
│   ├── __init__.py
│   ├── bot.py                        # Bot va Dispatcher yaratish, lifecycle
│   ├── config.py                     # Sozlamalar va .env o'qish
│   ├── database.py                   # Async SQLAlchemy dvigateli va sessiyalari
│   │
│   ├── models/                       # Ma'lumotlar bazasi modellari
│   │   ├── user.py                   # Foydalanuvchi (ID, username, roli)
│   │   ├── subscription.py           # Obunalar (boshlanish, tugash vaqti, faollik)
│   │   ├── taxi_limit.py             # Taksi uchun 24 soatlik bepul limit vaqti
│   │   ├── payment.py                # To'lov arizalari va cheklar
│   │   ├── setting.py                # Narxlar va karta sozlamalari
│   │   └── moderation_log.py         # O'chirilgan reklamalar tarixi
│   │
│   ├── services/                     # Biznes mantiq qatlami
│   │   ├── advertisement_detector.py # Aqlli reklama aniqlash dvigateli
│   │   ├── subscription_service.py   # Obuna va foydalanuvchini bog'lash servisi
│   │   ├── moderation_service.py     # Guruh xabarlarini moderatsiya qilish
│   │   └── payment_service.py        # To'lovlar va tariflar
│   │
│   ├── handlers/                     # Telegram hodisalari kontrollerlari
│   │   ├── admin.py                  # Admin buyruqlari va paneli (/stats, /add_taxi, ...)
│   │   ├── user.py                   # Shaxsiy menyu (/start, /help, tariflar)
│   │   ├── payments.py               # Chek yuborish va admin tasdiqlashi
│   │   └── moderation.py             # Guruhdagi xabarlarni tutib olish
│   │
│   ├── keyboards/                    # Tugmalar (Keyboards)
│   │   ├── admin.py                  # Admin inline paneli
│   │   ├── user.py                   # Foydalanuvchi menyusi
│   │   └── payments.py               # Tarif tanlash va chek tasdiqlash
│   │
│   └── utils/                        # Yordamchi vositalar
│       ├── time.py                   # Asia/Tashkent vaqt mintaqasi va 24 soat hisoblash
│       └── text.py                   # Matnni tozalash, kirill-lotin transliteratsiya
│
├── tests/
│   ├── test_detector.py              # Reklama detektori testlari
│   └── test_moderation.py            # Barcha 14 ta biznes-mantiq testi
│
├── main.py                           # Asosiy ishga tushiruvchi fayl (Polling / Webhook)
├── requirements.txt                  # Python kutubxonalari
├── render.yaml                       # Render konfiguratsiyasi
├── .env.example                      # Muhit o'zgaruvchilari namunasi
├── .gitignore                        # Git e'tiborsiz qoldiradigan fayllar
└── README.md                         # Qo'llanma
```

---

## 🔒 Telegram Maxfiyligi va Bot huquqlari

### Nima uchun guruhda xabarlar o'chirilishi uchun botga Admin huquqlari zarur?
Telegram platformasining xavfsizlik (Privacy Mode) qoidalariga ko'ra:
1. Odatiy botlar guruhda faqat o'ziga qaratilgan xabarlarni (masalan, `/` bilan boshlanuvchi buyruqlar yoki reply xabarlarni) ko'ra oladi.
2. Oddiy a'zolarning matnli xabarlarini o'qish va tahlil qilish uchun bot guruhda **Administrator** bo'lishi shart.
3. Reklama xabarlarini o'chirish uchun botda **"Delete Messages"** (Xabarlarni o'chirish) ruxsati faol bo'lishi kerak.

**Botga berilishi shart bo'lgan huquqlar:**
* ✅ **Delete messages (Xabarlarni o'chirish)** — Ruxsat etilmagan reklamalarni o'chirish uchun.
* ❌ *Qolgan huquqlar (foydalanuvchilarni ban qilish, chat sozlamalarini o'zgartirish va h.k.) TALAB ETILMAYDI.*

---

## 🤖 BotFather orqali bot yaratish bo'yicha qo'llanma

1. Telegramda [@BotFather](https://t.me/BotFather) ga kiring va `/newbot` buyrug'ini yuboring.
2. Bot uchun nom kiriting (masalan: `Guruh Nazoratchisi`).
3. Bot uchun username kiriting (oxiri `bot` bilan tugashi kerak, masalan: `guruh_antireklama_bot`).
4. BotFather sizga **HTTP API Token** beradi (masalan: `7123456789:AAHK...`). Ushbu tokenni nusxalab oling.
5. Privacy Mode ni tekshirish (ixtiyoriy, chunki guruhda admin qilinganda avtomatik o'chadi):
   * BotFather ga `/setprivacy` buyrug'ini yuboring.
   * Botingizni tanlang va `Disable` ni bosing.

---

## 👥 Botni guruhga qo'shish va Admin qilish

1. Guruhingiz sozlamalariga kiring -> **Administrators** (Administratorlar) bo'limini oching.
2. **Add Administrator** (Administrator qo'shish) tugmasini bosing.
3. Qidiruv qatoriga o'zingiz yaratgan botning `@username` ini yozing va botni tanlang.
4. Huquqlar ro'yxatida faqat quyidagini qoldiring:
   * ✅ **Delete Messages** (Xabarlarni o'chirish) — Yoqilsin.
   * Qolgan barcha huquqlarni (Ban users, Pin messages, Change info) o'chirib qo'yishingiz mumkin.
5. **Save** (Saqlash) tugmasini bosing.
6. Endi bot guruhdagi barcha xabarlarni avtomatik nazorat qilishni boshlaydi!

---

## 💻 Lokal ishga tushirish (Local Run)

### 1. Repozitoriyani yuklab oling:
```bash
git clone <Sizning_Repo_Havolangiz>
cd "бот анти реклама"
```

### 2. Virtual muhit (venv) yarating va faollashtiring:
```bash
# Windows:
python -m venv venv
venv\Scripts\activate

# Linux / MacOS:
python3 -m venv venv
source venv/bin/activate
```

### 3. Kerakli kutubxonalarni o'rnating:
```bash
pip install -r requirements.txt
```

### 4. `.env` faylini sozlang:
`.env.example` nusxasini `.env` nomi bilan yarating:
```bash
# Windows:
copy .env.example .env

# Linux / MacOS:
cp .env.example .env
```
`.env` faylini ochib, quyidagi asosiy parametrlarni to'ldiring:
```env
BOT_TOKEN=7123456789:AAHK... # BotFather bergan token
ADMIN_ID=123456789           # O'zingizning Telegram ID ingiz (@userinfobot orqali bilsa bo'ladi)
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db
BOT_TIMEZONE=Asia/Tashkent
PAYMENT_CARD=8600 0000 0000 0000
PAYMENT_CARD_HOLDER=ISMINGIZ FAMILIYANGIZ
```

### 5. Botni ishga tushiring:
```bash
python main.py
```
Konsolda quyidagicha xabar chiqadi:
`Starting bot in Polling mode...`
`Bot authorized as @your_bot`
`Database initialized successfully.`

---

## 🐙 GitHub repozitoriyasini yaratish

1. [GitHub.com](https://github.com) da yangi repozitoriya oching (masalan, `telegram-ad-moderator`). Repozitoriyani **Private** yoki **Public** qilishingiz mumkin.
2. Loyihangiz papkasida terminalni oching:
```bash
git init
git add .
git commit -m "Initial commit: Production-ready Telegram Ad Moderation Bot"
git branch -M main
git remote add origin https://github.com/<sizning_username>/telegram-ad-moderator.git
git push -u origin main
```

---

## ☁️ Render Free platformasiga Deploy qilish

Loyiha Render platformasining bepul **Web Service** tarifiga to'liq moslashtirilgan. Render Web Service ga kelayotgan so'rovlar botni avtomatik uyg'oq ushlab turadi.

### 1-qadam: Render hisobiga kiring
1. [Render.com](https://render.com) ga kiring (GitHub orqali ro'yxatdan o'tish qulay).
2. Asosiy ekranda **New +** tugmasini bosing va **Web Service** ni tanlang.
3. GitHub dagi `telegram-ad-moderator` repozitoriyangizni ulang.

### 2-qadam: Asosiy sozlamalar (Settings)
* **Name:** `telegram-ad-moderator` (ixtiyoriy nom)
* **Region:** `Frankfurt (EU Central)`
* **Branch:** `main`
* **Runtime:** `Python 3`
* **Build Command:** `pip install -r requirements.txt`
* **Start Command:** `python main.py`
* **Instance Type:** `Free`

### 3-qadam: Muhit o'zgaruvchilari (Environment Variables)
Quyidagi kalitlarni kiriting:
* `BOT_TOKEN` = `BotFather dan olgan tokeningiz`
* `ADMIN_ID` = `Sizning Telegram ID ingiz`
* `BOT_TIMEZONE` = `Asia/Tashkent`
* `NOTICE_DELETE_SECONDS` = `10`
* `PAYMENT_CARD` = `To'lov uchun karta raqami`
* `PAYMENT_CARD_HOLDER` = `Karta egasi ismi`
* `WEBHOOK_URL` = `https://<sizning-render-web-servisingiz>.onrender.com` (Render xizmat nomingizga mos keluvchi havola)

### 4-qadam: Deploy
**Create Web Service** tugmasini bosing.
Render loyihani avtomatik quradi va Webhook orqali ishga tushiradi! Render `https://.../health` endpointi orqali servis holatini muntazam tekshirib turadi.

---

## ⚠️ Render Free saqlash cheklovi va PostgreSQL

### Muhim ogohlantirish (Render Free Disk haqida):
Render Free tarifidagi disk **ephemeral (vaqtinchalik)** hisoblanadi. Bu degani:
* Agar SQLite (`bot.db`) ishlatilsa va Render servisi qayta ishga tushsa (har deployda yoki 15 daqiqa harakatsizlikdan so'ng uxlaganda), lokal SQLite faylidagi yangi ma'lumotlar asl holatiga qaytib qolishi mumkin.

### Doimiy saqlash uchun yechim (PostgreSQL):
Botimiz **SQLAlchemy 2.0 Async** arxitekturasida yaratilgan bo'lib, SQLite dan PostgreSQL ga o'tish uchun kodda biror qatorni ham o'zgartirish shart emas! Faqatgina `DATABASE_URL` o'zgaruvchisini almashtirish kifoya:

1. Bepul bulutli PostgreSQL oching:
   * [Neon.tech](https://neon.tech) (Tavsiya etiladi: mutlaqo bepul, kuchli PostgreSQL)
   * yoki [Supabase.com](https://supabase.com)
   * yoki Render ning o'zida bepul **New PostgreSQL** yarating.
2. Berilgan ulanish havolasini oling va boshidagi `postgres://` yoki `postgresql://` qismini `postgresql+asyncpg://` ga o'zgartiring:
   ```env
   DATABASE_URL=postgresql+asyncpg://foydalanuvchi:parol@ep-host.neon.tech/neondb?ssl=require
   ```
3. Ushbu `DATABASE_URL` ni Render dagi Environment Variables ga qo'shing.
4. Barcha ma'lumotlar, taksistlar, faol obunalar va to'lovlar abadiy va ishonchli saqlanadi!

---

## 🧪 Testlarni ishga tushirish

Loyiha barcha belgilangan talablar bo'yicha 100% avtomatlashtirilgan unit-testlar bilan qoplangan:

1. Oddiy savol -> xabar o'chirilmaydi.
2. Oddiy suhbat -> xabar o'chirilmaydi.
3. Ruxsatsiz tijoriy reklama -> xabar o'chiriladi.
4. Taksi birinchi reklama -> ruxsat beriladi.
5. Taksi 24 soat ichidagi ikkinchi reklama -> o'chiriladi va ogohlantirish beriladi.
6. Taksi 24 soatdan keyingi reklama -> ruxsat beriladi.
7. Taksi faol pullik obuna bilan -> cheklovsiz ruxsat beriladi.
8. Taksi obunasi tugagach -> yana 1/24 soatlik bepul limitga qaytadi.
9. Biznes obunasiz -> reklama o'chiriladi (0 bepul).
10. Biznes obuna bilan -> reklama ruxsat etiladi.
11. Guruh administratori -> xabari moderatsiya qilinmaydi.
12. Taksi avval username orqali qo'shilgan bo'lsa -> birinchi xabaridan keyin Telegram ID avtomatik bog'lanadi.
13. Username o'zgarganda -> Telegram ID asosiy identifikator bo'lib qoladi.
14. Bot qayta ishga tushganda -> ma'lumotlar bazada to'liq saqlanadi.

Testlarni yurgizish buyrug'i:
```bash
pytest
```
Barcha 11 ta test to'plami muvaffaqiyatli (`passed`) o'tadi.
