# E-Bloknot

Kursantlar uchun oddiy elektron kunlik bloknot. Maqsad — kunni tartibli
o'tkazish: bugungi ishlarni yozib, guruhlarga bo'lib, bajarilishini kuzatish.

Hozircha **1-bosqich** tayyor: ro'yxatdan o'tish, tizimga kirish va chiqish.

## Texnologiyalar

- Python 3 + Flask
- Flask-SQLAlchemy (lokalda SQLite, keyinchalik Railway'da PostgreSQL)
- Flask-Login (kirish/chiqish)
- Jinja shablonlari + oddiy CSS

## Ishga tushirish (Windows / PowerShell)

Quyidagi buyruqlarni loyiha papkasida, PowerShell terminalida bajaring.

### 1. Virtual muhit (venv) yaratish

Virtual muhit — loyiha kutubxonalarini alohida saqlaydigan "qutichak".

```powershell
python -m venv venv
```

### 2. Virtual muhitni yoqish

```powershell
.\venv\Scripts\Activate.ps1
```

Yoqilgach, satr boshida `(venv)` yozuvi paydo bo'ladi.

> Agar xatolik chiqsa ("скрипты отключены" / "running scripts is disabled"),
> bir marta quyidagini bajaring, so'ng 2-qadamni qaytaring:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### 3. Kutubxonalarni o'rnatish

```powershell
pip install -r requirements.txt
```

### 4. .env faylini sozlash

`.env.example` faylidan nusxa olib, `.env` deb nomlang:

```powershell
Copy-Item .env.example .env
```

So'ng `.env` faylini ochib, `SECRET_KEY` qiymatini o'zingizning uzun,
tasodifiy matningizga almashtiring.

### 5. Serverni ishga tushirish

```powershell
python app.py
```

Terminalda `http://127.0.0.1:5000` manzili chiqadi. Uni brauzerda oching.

Serverni to'xtatish uchun terminalda **Ctrl + C** bosing.

## Sahifalar

| Manzil      | Vazifasi                                            |
|-------------|-----------------------------------------------------|
| `/register` | Ro'yxatdan o'tish                                   |
| `/login`    | Tizimga kirish                                      |
| `/logout`   | Tizimdan chiqish                                    |
| `/`         | Bosh sahifa ("Bugun") — faqat kirgan foydalanuvchi |
| `/report`   | Hisobot (hafta/oy statistikasi)                     |
| `/settings` | O'rgangan so'zlar                                   |

## Demo ma'lumot (faqat sinash uchun)

Hisobotni to'ldirib ko'rish uchun oxirgi 30 kunga tasodifiy, real
ko'rinadigan vazifalar yaratish mumkin. Avval ro'yxatdan o'ting, so'ng:

```powershell
$env:FLASK_APP = "app"
python -m flask seed-demo SIZNING_LOGINGIZ
```

> **Diqqat:** bu buyruq **faqat sinash uchun**. U haqiqiy vazifalaringiz
> ustiga qo'shimcha soxta ma'lumotlar yozadi — shaxsiy hisobingizda
> ishlatmang, alohida sinov foydalanuvchisi oching.

> **Eslatma:** bu kompyuterda Windows "Smart App Control" yoqilgani uchun
> `flask` buyrug'i to'g'ridan-to'g'ri ishlamasligi mumkin. Shuning uchun
> hamma joyda `python -m flask ...` ko'rinishida yozilgan.

## Telefonga o'rnatish (PWA)

E-Bloknot — Progressive Web App. Telefonda saytni ochib, brauzer menyusidan
**"Bosh ekranga qo'shish"** (Add to Home Screen) ni tanlasangiz, u oddiy
ilovadek ishlaydi. Internet yo'q bo'lsa oddiy oflayn sahifa ko'rsatiladi.

## Railway'ga joylash (internetga chiqarish)

Loyiha Railway (yoki shunga o'xshash xizmat) uchun tayyor:
`Procfile`, `requirements.txt`, `runtime.txt` va migratsiyalar bor.

### 1. Kerakli muhit o'zgaruvchilari (Railway → Variables)

| O'zgaruvchi    | Qiymati                                               |
|----------------|-------------------------------------------------------|
| `APP_ENV`      | `production`                                          |
| `SECRET_KEY`   | uzun tasodifiy matn (pastda yaratish usuli)           |
| `DATABASE_URL` | Railway PostgreSQL qo'shsangiz avtomatik to'ldiriladi |

> `APP_ENV=production` bo'lsa va `SECRET_KEY` o'rnatilmagan bo'lsa, ilova
> **ataylab ishga tushmaydi** (xavfsizlik).

### 2. SECRET_KEY yaratish

Terminalda quyidagini ishga tushiring va chiqqan qiymatni `SECRET_KEY` ga
yozing (bu kalitni hech kimga bermang, GitHubga ham yuklamang):

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Baza va migratsiyalar

- Railway'da **PostgreSQL** xizmatini qo'shing — `DATABASE_URL` avtomatik
  paydo bo'ladi.
- Har safar deploy bo'lganda `Procfile` dagi `release:` qatori
  `flask db upgrade` ni ishga tushiradi va jadvallarni yaratadi/yangilaydi.
  Shuning uchun model o'zgarsa ham ma'lumotlar o'chib ketmaydi.

### 4. Ishga tushirish

Railway `web:` qatori bo'yicha `gunicorn` bilan serverni ko'taradi.
Holatni tekshirish uchun `/health` manzili `{"status": "ok"}` qaytaradi.

## Fayllar

- `app.py` — asosiy dastur, sahifalar va API
- `models.py` — ma'lumotlar bazasi modellari (User, Task, UserKeyword)
- `categories.py` — vazifalarni avtomatik guruhlash (kalit so'zlar)
- `reports.py` — hisobot hisob-kitoblari
- `templates/` — HTML sahifalar
- `static/css/`, `static/js/` — dizayn va JavaScript
- `static/manifest.json`, `static/sw.js`, `static/icons/` — PWA (telefonga o'rnatish)
- `migrations/` — ma'lumotlar bazasi migratsiyalari (Flask-Migrate)
- `tests/` — avtomatik testlar (pytest)
- `Procfile`, `runtime.txt`, `.python-version` — Railway (deploy) sozlamalari
- `requirements.txt` — kerakli kutubxonalar ro'yxati
- `.env.example` — muhit o'zgaruvchilari namunasi
- `CLAUDE.md` — loyiha rejasi va bosqichlar
