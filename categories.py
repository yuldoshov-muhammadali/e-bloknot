"""
categories.py — Vazifalarni avtomatik guruhlash moduli.

MUHIM: Bu yerda AI ISHLATILMAYDI. Guruhlash faqat oldindan belgilangan
KALIT SO'ZLAR orqali amalga oshiriladi.

3 ta asosiy funksiya bor:
  - normalize(text)   : matnni bir xil ko'rinishga keltiradi (kichik harf, apostroflar)
  - classify(title)   : bitta vazifa matnini guruhga ajratadi
  - split_tasks(text) : katta matnni alohida vazifalarga bo'ladi
"""

import re

# =========================================================
#   GURUHLAR RO'YXATI (tartib muhim — tenglik bo'lsa yuqoridagi yutadi)
# =========================================================
# Har bir guruh: id, nom, emoji va kalit so'zlar ro'yxati.
CATEGORIES = [
    {
        "id": "til",
        "name": "Chet tili",
        "emoji": "🌐",
        "keywords": [
            "ingliz", "english", "ielts", "cefr", "writing", "reading",
            "listening", "speaking", "rus til", "nemis", "arab til", "koreys",
            "turk til", "grammatika", "grammar", "vocabulary", "essay",
        ],
    },
    {
        "id": "dastur",
        "name": "Dasturlash va loyihalar",
        "emoji": "💻",
        "keywords": [
            "python", "kod", "dastur", "loyiha", "github", "sayt", "bot",
            "e-naryad", "e-bloknot", "javascript", "html", "css", "django",
            "flask", "sql", "api", "frontend", "backend", "deploy", "udemy",
            "xakaton", "hackathon",
        ],
    },
    {
        "id": "oqish",
        "name": "Dars va o'qish",
        "emoji": "📚",
        "keywords": [
            "dars", "seminar", "ma'ruza", "maruza", "imtihon", "nazorat",
            "kursovoy", "kurs ish", "referat", "mustaqil", "konspekt", "test",
            "uy vazifa", "fan", "huquq", "bojxona", "kodeks", "matematika",
            "tarix", "otrabotka", "zachet", "sessiya", "o'qituvchi", "domla",
            "taqdimot", "prezentatsiya", "mavzu", "yodla",
        ],
    },
    {
        "id": "kitob",
        "name": "Kitob",
        "emoji": "📖",
        "keywords": ["kitob", "o'qib chiq", "sahifa", "audiokitob", "roman"],
    },
    {
        "id": "sport",
        "name": "Sport",
        "emoji": "🏃",
        "keywords": [
            "sport", "yugur", "mashq", "turnik", "brus", "zal", "otjimaniya",
            "futbol", "basketbol", "voleybol", "suzish", "fizo", "jismoniy",
            "press", "kross", "trenirovka", "shtanga", "boks", "kurash",
        ],
    },
    {
        "id": "xizmat",
        "name": "Xizmat va naryad",
        "emoji": "🎖",
        "keywords": [
            "naryad", "dejur", "navbatchi", "stroy", "saf", "post", "karaul",
            "xizmat", "rota", "komandir", "starshina", "uvalneniya", "kazarma",
            "raport", "smotr", "vzvod",
        ],
    },
    {
        "id": "maishiy",
        "name": "Maishiy ishlar",
        "emoji": "👕",
        "keywords": [
            "dazmol", "kir yuv", "yuv", "tozala", "uborka", "tik", "poyabzal",
            "etik", "tufli", "forma", "kiyim", "sartarosh", "soch", "do'kon",
            "xarid", "bozor", "sotib ol", "yig'ishtir",
        ],
    },
    {
        "id": "oila",
        "name": "Oila va do'stlar",
        "emoji": "📞",
        "keywords": [
            "ona", "ota", "aka", "uka", "opa", "singil", "oila", "buvi",
            "bobo", "qo'ng'iroq", "telefon qil", "xabar yoz", "do'st",
            "tabrikla", "tug'ilgan kun", "mehmon",
        ],
    },
    {
        "id": "moliya",
        "name": "Moliya",
        "emoji": "💰",
        "keywords": [
            "pul", "to'lov", "qarz", "xarajat", "chiqim", "kirim", "hisob",
            "karta", "stipendiya", "oylik", "byudjet", "so'm", "dollar",
        ],
    },
    {
        "id": "dam",
        "name": "Ma'naviyat va dam olish",
        "emoji": "🧘",
        "keywords": [
            "namoz", "qur'on", "duo", "meditatsiya", "nafas", "dam ol",
            "uxla", "kundalik", "sayr", "kino", "film",
        ],
    },
    {
        # Hech bir guruhga mos kelmasa — shu guruh (kalit so'z yo'q).
        "id": "boshqa",
        "name": "Boshqa",
        "emoji": "📌",
        "keywords": [],
    },
]


# =========================================================
#   normalize — matnni bir xil ko'rinishga keltirish
# =========================================================
def normalize(text):
    """Matnni solishtirish uchun qulay ko'rinishga keltiradi.

    - hamma harfni kichik qiladi;
    - barcha apostrof turlarini oddiy ' ga almashtiradi;
    - yangi alifbo harflarini tushunadi: ğ→g', ö→o', ş→sh, ç→ch.
    """
    if not text:
        return ""

    text = text.lower()

    # Turli apostrof belgilarini bitta oddiy apostrofga keltiramiz.
    for belgi in ["ʻ", "ʼ", "’", "‘", "`", "´"]:
        text = text.replace(belgi, "'")

    # Yangi (lotin) alifboning maxsus harflari.
    text = text.replace("ğ", "g'")
    text = text.replace("ö", "o'")
    text = text.replace("ş", "sh")
    text = text.replace("ç", "ch")

    return text


# Har bir guruhning kalit so'zlarini oldindan normalize qilib qo'yamiz
# (tezroq ishlashi va bir xil ko'rinishda bo'lishi uchun).
for _cat in CATEGORIES:
    _cat["_kw_norm"] = [normalize(k) for k in _cat["keywords"]]


def _word_match(text, kalit):
    """Kalit so'z matnda SO'Z BOSHIDAN uchraydimi — True/False.

    (?<![a-z']) — kalit so'zdan oldin harf yoki apostrof BO'LMASIN.
    Shunda "ona" → "onam" ga mos keladi, lekin "zona" ga MOS KELMAYDI.
    """
    naqsh = r"(?<![a-z'])" + re.escape(kalit)
    return re.search(naqsh, text) is not None


# Standart kalit so'z va foydalanuvchi o'rgatgan so'z uchun ball (vazn).
# O'rgatilgan so'z kuchliroq, shuning uchun uning bali kattaroq.
STANDART_BALL = 1
ORGANILGAN_BALL = 3


# =========================================================
#   classify — bitta vazifani guruhga ajratish
# =========================================================
def classify(title, user_keywords=None):
    """Vazifa matniga qarab unga mos guruh ID sini qaytaradi.

    Qoida: kalit so'z SO'Z BOSHIDAN qidiriladi (yuqoridagi _word_match).

    Ball tizimi:
      - standart lug'atdagi har bir mos kalit so'z: +1 ball;
      - foydalanuvchi o'rgatgan har bir mos so'z: +3 ball (kuchliroq).
    Shunday qilib, foydalanuvchining qo'lda tuzatishi standart lug'atdan
    ustun keladi.

    `user_keywords` — {so'z: guruh_id} ko'rinishidagi lug'at (foydalanuvchiga
    xos). Berilmasa, faqat standart lug'at ishlatiladi.

    Qaysi guruhda ball ko'p bo'lsa — o'sha yutadi. Teng bo'lsa — ro'yxatda
    oldinroq turgani. Hech biri 0 dan oshmasa — "boshqa".
    """
    text = normalize(title)

    # Har bir guruh uchun ballni hisoblaymiz.
    ballar = {cat["id"]: 0 for cat in CATEGORIES}

    # 1) Standart lug'at.
    for cat in CATEGORIES:
        for kw in cat["_kw_norm"]:
            if _word_match(text, kw):
                ballar[cat["id"]] += STANDART_BALL

    # 2) Foydalanuvchi o'rgatgan so'zlar.
    if user_keywords:
        for so_z, guruh_id in user_keywords.items():
            if guruh_id in ballar and _word_match(text, normalize(so_z)):
                ballar[guruh_id] += ORGANILGAN_BALL

    # Eng ko'p balli guruhni tanlaymiz (tenglikda ro'yxatda oldingisi yutadi).
    yutgan_id = "boshqa"
    eng_ko_p = 0
    for cat in CATEGORIES:
        if ballar[cat["id"]] > eng_ko_p:
            eng_ko_p = ballar[cat["id"]]
            yutgan_id = cat["id"]

    return yutgan_id


# =========================================================
#   split_tasks — katta matnni alohida vazifalarga bo'lish
# =========================================================

# Vazifa boshidagi belgilar: "-", "•", "*" yoki "1)", "2." kabi raqamlar.
_BOSH_BELGI = re.compile(r"^\s*(?:[-•*]\s*)?(?:\d+[.)]\s*)?")


def split_tasks(text):
    """Katta matnni alohida vazifalar ro'yxatiga bo'ladi.

    - matn yangi qator, vergul (,) yoki nuqta-vergul (;) bo'yicha bo'linadi;
    - har bir bo'lakning boshidagi "-", "•", "*", "1)", "2." belgilari olinadi;
    - ortiqcha bo'sh joylar tozalanadi, birinchi harf katta qilinadi;
    - 2 belgidan qisqa bo'laklar tashlab yuboriladi;
    - bir martada eng ko'pi 50 ta vazifa qaytariladi.
    """
    if not text:
        return []

    # Yangi qator, vergul yoki ";" bo'yicha bo'lamiz.
    bo_laklar = re.split(r"[,\n;]+", text)

    natija = []
    for bolak in bo_laklar:
        # Boshidagi belgilarni (- • * 1) 2.) olib tashlaymiz.
        bolak = _BOSH_BELGI.sub("", bolak)
        # Ortiqcha bo'sh joylarni bitta probelga keltiramiz va chetlarini tozalaymiz.
        bolak = re.sub(r"\s+", " ", bolak).strip()

        # Juda qisqalarini (2 belgidan kam) tashlaymiz.
        if len(bolak) < 2:
            continue

        # Birinchi harfni katta qilamiz.
        bolak = bolak[0].upper() + bolak[1:]
        natija.append(bolak)

        # Bir martada maksimum 50 ta.
        if len(natija) >= 50:
            break

    return natija


def get_category(cat_id):
    """Guruh ID si bo'yicha uning ma'lumotini (nom, emoji) qaytaradi."""
    for cat in CATEGORIES:
        if cat["id"] == cat_id:
            return cat
    # Topilmasa — "boshqa".
    return CATEGORIES[-1]


def is_valid_category(cat_id):
    """Berilgan guruh ID si haqiqiy guruhmi (ro'yxatda bormi)."""
    return any(cat["id"] == cat_id for cat in CATEGORIES)


# =========================================================
#   O'RGANISH UCHUN SO'Z AJRATISH
# =========================================================

# To'xtash so'zlari (stopwords) — bular umumiy so'zlar, o'rganilmaydi.
# (Masalan "bugun kitob o'qish" dan faqat "kitob" o'rganiladi.)
STOPWORDS = {
    # vaqt va umumiy so'zlar
    "bugun", "ertaga", "kecha", "hozir", "keyin", "oldin", "kun", "kuni",
    "soat", "daqiqa", "minut", "vaqt", "ertalab", "kechqurun", "tushdan",
    # "qilish" va shunga o'xshash fe'llar
    "kerak", "qilish", "qilaman", "qilib", "qildim", "qildim", "qilgan",
    "yozish", "yozaman", "yozib", "borish", "boraman", "ko'rish",
    "ko'raman", "olish", "olaman", "tayyorlanish", "tayyorlash",
    "o'qish", "o'qib", "o'qiyman", "qarash", "qilmoq", "bajarish",
    # bog'lovchilar va olmoshlar
    "uchun", "bilan", "yana", "hamma", "barcha", "bir", "ikki", "uch",
    "to'rt", "besh", "men", "sen", "biz", "siz", "ular", "o'z", "o'zim",
    "shu", "bu", "ushbu", "ham", "yoki", "lekin", "ammo", "va",
    # miqdor / birlik
    "ta", "tasi", "dona", "marta", "nechta", "ozgina", "biroz",
    # boshqa keng tarqalganlar
    "ishni", "ishlarni", "ish", "narsa", "joy", "yangi", "eski",
}
# Stopwordlarni ham normalize qilib qo'yamiz (apostrof va h.k. bir xil bo'lsin).
STOPWORDS = {normalize(w) for w in STOPWORDS}


def extract_words(title):
    """Vazifa matnidan O'RGANISH uchun so'zlarni ajratib beradi.

    Qoidalar:
      - matn normalize qilinadi;
      - faqat harflardan iborat so'zlar olinadi (raqamlar tashlanadi);
      - uzunligi 3 harfdan ORTIQ bo'lgan so'zlar (ya'ni 4 va undan uzun);
      - to'xtash so'zlari (STOPWORDS) olinmaydi.

    Masalan: "Kursovoy 1-bobini yozish" → ["kursovoy", "bobini"]
    ("yozish" — stopword, "1" — raqam, "bob" bo'lsa qisqa bo'lardi).
    """
    text = normalize(title)

    # Harf va apostrofdan iborat bo'laklarni olamiz (raqamlar tushib qoladi).
    tokenlar = re.findall(r"[a-z']+", text)

    sozlar = []
    for token in tokenlar:
        so_z = token.strip("'")  # chetidagi apostroflarni olib tashlaymiz
        if len(so_z) > 3 and so_z not in STOPWORDS and so_z not in sozlar:
            sozlar.append(so_z)

    return sozlar
