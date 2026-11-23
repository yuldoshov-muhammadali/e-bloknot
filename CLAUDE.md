# E-Bloknot — loyiha hujjati (CLAUDE.md)

Bu fayl loyihaning maqsadi, rejasi va texnologiyalarini saqlaydi.
Har bir yangi bosqichda shu faylga tayaniladi va oxirida qaysi bosqich
tugaganini yangilab boriladi.

## Loyiha maqsadi

E-Bloknot — kursantlar (Bojxona instituti, 2-kurs, ~100 kishi) uchun oddiy
elektron kunlik bloknot. Maqsad: kunni tartibli o'tkazish.

Asosiy g'oya (kelajakda to'liq amalga oshiriladi):
- Foydalanuvchi bugungi ishlarini bitta matn qilib yozadi, platforma ularni
  alohida vazifalarga bo'lib, **kalit so'zlar** orqali avtomatik guruhlaydi.
  **AI ishlatilmaydi.**
- Guruhlar: Dars, Chet tili, Dasturlash, Sport, Xizmat, Maishiy, Oila,
  Moliya, Dam olish, Boshqa.
- Foydalanuvchi guruhni qo'lda o'zgartira oladi, platforma tuzatishlardan
  o'rganadi.
- Vazifani "Bajarildi" / "Bajarolmadim" (sababi bilan) deb belgilash,
  sarflangan vaqtni yozish, bajarilmaganini ertaga ko'chirish.
- Haftalik/oylik hisobotlar: bajarilish foizi, guruhlar bo'yicha vaqt,
  uzoq vaqt bajarilmayotgan vazifalar.
- Har bir foydalanuvchi ma'lumoti **shaxsiy**. Reyting yoki guruh
  funksiyalari **yo'q**.

## Texnologiyalar

- Python 3 + Flask
- Flask-SQLAlchemy — lokalda SQLite, keyinchalik Railway'da PostgreSQL.
  Baza manzili `DATABASE_URL` muhit o'zgaruvchisidan olinadi, bo'lmasa
  SQLite fayl (`e_bloknot.db`) ishlatiladi.
- Flask-Login — kirish/chiqish. Parollar `werkzeug.security` bilan xeshlanadi.
- Frontend: Jinja shablonlari + oddiy CSS + kerak bo'lsa vanilla JavaScript.
  **React ishlatilmaydi.**
- `SECRET_KEY` muhit o'zgaruvchisidan olinadi (`.env` + python-dotenv).
- Dizayn: mobile-first, toza va zamonaviy. Matnlar o'zbek tilida (lotin).

## 6 bosqichlik reja

1. **Asos** — ro'yxatdan o'tish va kirish. ✅ **TUGADI**
2. **Vazifalarni kiritish va avtomatik guruhlash** — kunlik matnni
   vazifalarga bo'lish, kalit so'zlar orqali guruhlash. ✅ **TUGADI**
3. **Qo'lda tuzatish va o'rganish** — guruhni qo'lda o'zgartirish,
   tuzatishlardan o'rganish. ✅ **TUGADI**
4. **Belgilash va vaqt** — bajarildi/bajarolmadim, sarflangan vaqt,
   ertaga ko'chirish. ✅ **TUGADI**
5. **Hisobotlar** — haftalik/oylik statistika. ✅ **TUGADI**
6. **Railway'ga joylash** — PostgreSQL, deploy, PWA, xavfsizlik. ✅ **TUGADI**

## Joriy holat

- **Tugagan bosqich:** 6 (Railway'ga joylash — oxirgi bosqich) 🎉
- **Holat:** Loyiha to'liq tayyor. Barcha 6 bosqich bajarildi.

### Hisobot hisoblash qoidalari (5-bosqichdan)

- Davrga `plan_date` si shu davr (hafta: dushanba–yakshanba, yoki oy) ichida
  bo'lgan barcha `Task` kiradi.
- Bajarildi = `done`. Bajarilmadi = `failed` / `moved` / `dropped`.
- O'tgan kunlarning `todo` si ham bajarilmagan hisoblanadi; bugungi va
  kelajakdagi `todo` foizga **kirmaydi**.
- Foiz = bajarildi / (bajarildi + bajarilmadi + o'tgan_todo) × 100. Maxraj 0
  bo'lsa — "—".
- Kunlik grafik rangi: ≥80% yashil, 50–79% sariq, <50% qizil, vazifasiz kun
  kulrang.
- "Uzoq kutayotganlar" tanlangan davrga emas, HOZIRGI holatga qaraydi:
  `root_id` zanjirida `done` yo'q, oxirgi yozuv `dropped` emas, va
  (bugun − `first_date`) ≥ 3 kun YOKI `moved_count` ≥ 2.
- Barcha hisob-kitob `reports.py` da (toza funksiyalar), `/report` route faqat
  natijani shablonga beradi.

### Vazifa statuslari (4-bosqichdan)

- `todo` — hali belgilanmagan
- `done` — bajarildi (`done_at` to'ldiriladi)
- `failed` — bajarolmadim (`reason` da sababi)
- `moved` — boshqa kunga ko'chirildi (asl vazifa shu statusni oladi)
- `dropped` — voz kechildi

Hisobotda (5-bosqich) `failed`, `moved`, `dropped` — bajarilmagan deb
hisoblanadi.

### Ko'chirish mantiqi (5-bosqich shunga tayanadi)

- Yangi `Task` nusxasi yaratiladi: o'sha `title`, `category`; `plan_date` =
  maqsad kun; `status` = `todo`; `first_date` va `root_id` ASL vazifanikidan;
  `moved_count` = asl + 1; `minutes` = 0.
- Asl vazifa: `todo` bo'lsa → `moved`; `failed` bo'lsa → `failed` qoladi.
- Bir vazifani ikki marta ko'chirib bo'lmaydi: shu `root_id` da keyingi sanada
  nusxa bo'lsa, ko'chirish rad etiladi.
- Kechikkanlar bloki: `plan_date < bugun`, status `todo`/`failed`, oxirgi 14
  kun, va shu `root_id` da keyingi sanada nusxa yo'q.

### 1-bosqichda yaratilgan fayllar

- `app.py` — Flask dasturi, sahifalar: `/register`, `/login`, `/logout`, `/`
- `models.py` — `User` modeli (id, full_name, group_name, username,
  password_hash, created_at)
- `templates/base.html` — umumiy shablon (header, navigatsiya, flash xabarlar)
- `templates/register.html`, `login.html`, `index.html`
- `static/css/style.css` — dizayn (mobile-first, indigo rang)
- `requirements.txt`, `.env.example`, `.gitignore`, `README.md`

### 2-bosqichda qo'shilgan/o'zgargan fayllar

- `categories.py` (YANGI) — guruhlash moduli. AI yo'q, faqat kalit so'zlar.
  Funksiyalar: `normalize`, `classify`, `split_tasks`, `get_category`.
  11 ta guruh: til, dastur, oqish, kitob, sport, xizmat, maishiy, oila,
  moliya, dam, boshqa.
- `models.py` — `Task` modeli qo'shildi (id, user_id, title, category,
  plan_date, status, reason, minutes, first_date, root_id, moved_count,
  created_at, done_at). Hozir: id, user_id, title, category, plan_date,
  status, first_date, root_id, created_at ishlatiladi.
- `app.py` — `/` sahifasi GET+POST bo'ldi: matn kiritish, vazifalarga bo'lish,
  guruhlash va bugungi sana (Asia/Tashkent) bilan saqlash; vazifalarni
  guruhlar bo'yicha ko'rsatish.
- `templates/index.html` — textarea + "Qo'shish" + guruhlangan ro'yxat.
- `static/css/style.css` — textarea, guruh kartochkalari, vazifa ro'yxati.
- `tests/test_categories.py` (YANGI) — pytest testlari (13 ta, hammasi o'tadi).
- `requirements.txt` — `tzdata` (Windows vaqt zonasi) va `pytest` qo'shildi.

**Guruhlash qanday ishlaydi:** foydalanuvchi matnini `split_tasks` yangi
qator/vergul/";" bo'yicha vazifalarga bo'ladi; har birini `classify` kalit
so'zlar orqali guruhga ajratadi. Kalit so'z faqat SO'Z BOSHIDAN qidiriladi
(regex `(?<![a-z'])`), shuning uchun "ona" → "onam" ga mos keladi, lekin
"zona" ga mos kelmaydi. Ko'proq kalit so'z mos kelgan guruh yutadi; teng
bo'lsa ro'yxatda oldinroq turgani yutadi; hech biri bo'lmasa — "boshqa".

### 3-bosqichda qo'shilgan/o'zgargan fayllar

- `models.py` — `UserKeyword` modeli qo'shildi (id, user_id, word, category,
  hits, updated_at; `(user_id, word)` unikal).
- `categories.py` — `classify(title, user_keywords)` endi o'rgatilgan so'zlarni
  ham hisobga oladi (standart so'z +1 ball, o'rgatilgan so'z +3 ball). Yangi:
  `extract_words` (o'rganish uchun so'z ajratish), `STOPWORDS`,
  `is_valid_category`, `_word_match`.
- `app.py` — yangi: `foydalanuvchi_sozlari`, `vazifadan_organ`, context
  processor (`all_categories`). JSON API endpointlar: `GET /api/today`,
  `POST /api/task/<id>/category|edit|delete`, `GET /settings`,
  `POST /api/keyword/<id>/category|delete`. Hamma API faqat O'Z yozuvini
  o'zgartiradi, aks holda 404.
- `templates/base.html` — "Sozlamalar" havolasi, toast konteyneri,
  `window.CATEGORIES` va `app.js`.
- `templates/index.html` — har vazifada guruh "chip"i va "⋯" menyusi.
- `templates/settings.html` (YANGI) — "O'rgangan so'zlarim" sahifasi.
- `static/js/app.js` (YANGI) — fetch+JSON, guruh tanlash paneli (bottom sheet),
  joyida tahrirlash, o'chirish, toast, sahifani qayta chizish.
- `static/css/style.css` — chip, menyu, panel, toast, tahrirlash uslublari
  (tugmalar kamida 44px — barmoq bilan bosishga qulay).
- `tests/test_learning.py` (YANGI) — 6 ta test (o'rganish, stopword, shaxsiylik,
  404 xavfsizlik, tahrir guruhni o'zgartirmasligi). Jami testlar: 19 ta.

**O'rganish qanday ishlaydi:** foydalanuvchi vazifa guruhini qo'lda
o'zgartirganda (`/api/task/<id>/category`), `vazifadan_organ` vazifa
matnidagi so'zlarni (stopword bo'lmagan, 3 harfdan uzun) `UserKeyword` ga
yozadi. Keyingi vazifa qo'shilganda `classify` shu so'zlarga +3 ball beradi,
shuning uchun foydalanuvchi tuzatishi standart lug'atdan ustun keladi. Har
bir foydalanuvchining o'rganishi faqat o'ziga ta'sir qiladi.

### 4-bosqichda qo'shilgan/o'zgargan fayllar

- `models.py` — `Task.status` izohi yangilandi (5 ta status).
- `app.py` — kunlar bo'yicha yurish (`?date=`), `kun_konteksti`,
  `kechikkan_vazifalar`, `vazifani_kochir`, o'zbekcha hafta kunlari. Yangi
  endpointlar: `GET /fragment`, `POST /api/task/<id>/status|minutes|move|drop`.
  Eski `/api/today` olib tashlandi (o'rniga `/fragment`).
- `templates/index.html` — kun navigatsiyasi (◀ sana ▶, "Bugun") + `#day-content`.
- `templates/_day_content.html` (YANGI) — kechikkanlar bloki, kun xulosasi
  (progress bar), guruhlar. `/fragment` ham shuni qaytaradi.
- `templates/_task.html` (YANGI) — vazifa kartochkasi: belgilash tugmalari,
  taymer, vaqt, sabab maydoni, ko'chirish belgisi.
- `static/js/app.js` — `refreshDay()` (/fragment orqali qayta chizish),
  belgilash, taymer (localStorage, bitta ishlaydi, sahifa yangilansa ham
  davom etadi), vaqtni qo'lda kiritish, ko'chirish.
- `static/css/style.css` — kun navigatsiyasi, kechikkanlar, xulosa, progress
  bar, belgilash/taymer/sabab uslublari.
- `tests/test_stage4.py` (YANGI) — 12 ta test. Jami testlar: **31 ta**.

**Eslatma (frontend arxitekturasi):** belgilash/taymer/ko'chirish amallari
JSON API ga `fetch` qiladi, so'ng JavaScript `/fragment` dan kun HTML
bo'lagini olib `#day-content` ni qayta chizadi (sahifa to'liq yuklanmaydi).
Shunday qilib HTML faqat Jinja shablonlarida yoziladi (JS da takrorlanmaydi).

### 5-bosqichda qo'shilgan/o'zgargan fayllar

- `reports.py` (YANGI) — barcha hisob-kitob (toza funksiyalar, DB siz):
  `hafta_oraligi`, `oy_oraligi`, `bajarilish`, `kunlik_grafik`,
  `vaqt_guruhlar`, `uzoq_kutayotganlar`, `sabablar`, `solishtirish`,
  `xulosa_jumlalari`.
- `app.py` — `/report` route (hafta/oy, davr navigatsiyasi, kelajak o'chiq),
  `flask seed-demo <login>` buyrug'i. `OYLAR`/`HAFTA_KUNLARI`/`daqiqa_matni`
  endi `reports.py` dan olinadi.
- `models.py` — Task ga indekslar (`user_id+plan_date`, `user_id+root_id`).
- `templates/report.html` (YANGI) — 4 KPI karta, kunlik grafik (SVG/CSS,
  kutubxonasiz), guruhlar bo'yicha vaqt, uzoq kutayotganlar, sabablar,
  avtomatik xulosa.
- `templates/base.html` — "📊 Hisobot" havolasi.
- `static/js/app.js` — hisobotdagi ko'chirish/voz kechish tugmalari.
- `static/css/style.css` — hisobot uslublari.
- `tests/test_reports.py` (YANGI) — 14 ta test. Jami testlar: **44 ta**.
- `README.md` — demo ma'lumot va `python -m flask` eslatmasi.

**Demo:** `python -m flask seed-demo <login>` — sinash uchun oxirgi 30 kunga
tasodifiy vazifalar (turli guruh, status, sabab, vaqt va ko'p marta
ko'chirilgan zanjirlar). Faqat sinov uchun.

### 6-bosqichda qo'shilgan/o'zgargan fayllar

- `requirements.txt` — `gunicorn`, `psycopg2-binary`, `Flask-WTF`,
  `Flask-Migrate` qo'shildi.
- `app.py` — `APP_ENV` (production/development/testing); production'da
  `SECRET_KEY` majburiy (bo'lmasa ishga tushmaydi); xavfsiz cookie
  (`SECURE`/`HTTPONLY`/`SAMESITE=Lax`, "meni eslab qol" 30 kun); **CSRF**
  (Flask-WTF); **Flask-Migrate**; login **rate limit** (IP: 5 daq / 10
  urinish); `/health`; `/sw.js` (scope "/"); `seed-demo` production'da
  ishlamaydi; debug production'da o'chiq.
- `Procfile` — `web: gunicorn ...`, `release: flask db upgrade`.
- `runtime.txt`, `.python-version` — Python 3.12.7.
- `migrations/` (YANGI) — barcha jadvallar uchun birinchi migratsiya.
- `templates/base.html` — PWA teglari (manifest, theme-color, ikonka),
  CSRF `<meta>`, service worker ro'yxatga olish.
- `templates/{register,login,index}.html` — formalarga CSRF token; login'da
  o'rnatish ko'rsatmasi.
- `static/manifest.json`, `static/sw.js`, `static/offline.html`,
  `static/icons/icon-{192,512}.png` (YANGI) — PWA.
- `static/js/app.js` — fetch so'rovlariga `X-CSRFToken` header.
- `tests/test_stage6.py` (YANGI) — 5 ta test (health, CSRF forma+API, rate
  limit, SECRET_KEY majburligi). Jami testlar: **49 ta**.

**Deploy qoidasi:** Railway'da `APP_ENV=production`, `SECRET_KEY` va
PostgreSQL `DATABASE_URL` o'rnatiladi. Har deployda `release: flask db
upgrade` jadvallarni yangilaydi (ma'lumot o'chmaydi). Server `gunicorn`
bilan ko'tariladi, `/health` monitoring uchun.

**PWA:** `sw.js` faqat statik fayllarni keshlaydi; sahifa/API keshlanmaydi
(ma'lumot doim yangi). Internet yo'q bo'lsa `offline.html` ko'rsatiladi.
