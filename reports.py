"""
reports.py — Hisobot uchun barcha hisob-kitoblar.

MUHIM: bu modul faqat HISOBLAYDI. Ma'lumotlar bazasiga o'zi murojaat
qilmaydi — unga tayyor vazifalar ro'yxati (Task obyektlari) beriladi.
Shu tufayli test yozish oson (sahifa/route siz ham sinab ko'rsa bo'ladi).

Asosiy tushunchalar (CLAUDE.md dagi qoida):
  - "Bajarildi"   = status "done"
  - "Bajarilmadi" = status "failed", "moved" yoki "dropped"
  - O'tgan kunlarning "todo" si ham bajarilmagan hisoblanadi;
    bugungi/kelajakdagi "todo" foizga KIRMAYDI (kun hali tugamagan).
"""

from calendar import monthrange
from datetime import date, timedelta

from categories import CATEGORIES, get_category

# O'zbekcha nomlar (app.py ham shulardan foydalanadi).
OYLAR = [
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
]
HAFTA_KUNLARI = [
    "dushanba", "seshanba", "chorshanba", "payshanba",
    "juma", "shanba", "yakshanba",
]

# "Bajarilmadi" deb hisoblanadigan statuslar.
BAJARILMADI_STATUS = ("failed", "moved", "dropped")


def daqiqa_matni(daqiqa):
    """Daqiqalarni o'zbekcha matnga: 200 → '3 soat 20 daq'."""
    daqiqa = daqiqa or 0
    soat = daqiqa // 60
    qoldiq = daqiqa % 60
    if soat and qoldiq:
        return f"{soat} soat {qoldiq} daq"
    if soat:
        return f"{soat} soat"
    return f"{qoldiq} daq"


# =========================================================
#   DAVR (hafta / oy) oraliqlari
# =========================================================


def hafta_oraligi(d):
    """d kuni tushgan haftaning (dushanba, yakshanba) oralig'i."""
    boshi = d - timedelta(days=d.weekday())  # dushanba
    oxiri = boshi + timedelta(days=6)         # yakshanba
    return boshi, oxiri


def oy_oraligi(d):
    """d kuni tushgan oyning (1-kun, oxirgi kun) oralig'i."""
    boshi = d.replace(day=1)
    oxirgi_kun = monthrange(d.year, d.month)[1]
    oxiri = d.replace(day=oxirgi_kun)
    return boshi, oxiri


def davr_oraligi(period, d):
    """period ("week"/"month") va sana bo'yicha oraliq qaytaradi."""
    if period == "month":
        return oy_oraligi(d)
    return hafta_oraligi(d)


def oldingi_davr(period, boshi):
    """Oldingi davr oralig'i (solishtirish uchun)."""
    if period == "month":
        # Oldingi oyning istalgan kuni — oldingi oyning oxirgi kunidan olamiz.
        oldingi_oxiri = boshi - timedelta(days=1)
        return oy_oraligi(oldingi_oxiri)
    oldingi_boshi = boshi - timedelta(days=7)
    return oldingi_boshi, oldingi_boshi + timedelta(days=6)


def davr_sarlavhasi(period, boshi, oxiri):
    """Davr nomi: hafta → '17–23-noyabr', oy → 'noyabr 2026'."""
    if period == "month":
        return f"{OYLAR[boshi.month - 1]} {boshi.year}"
    if boshi.month == oxiri.month:
        return f"{boshi.day}–{oxiri.day}-{OYLAR[oxiri.month - 1]}"
    # Ikki oyga cho'zilgan hafta.
    return (
        f"{boshi.day}-{OYLAR[boshi.month - 1]} – "
        f"{oxiri.day}-{OYLAR[oxiri.month - 1]}"
    )


# =========================================================
#   BAJARILISH (foiz) hisobi
# =========================================================


def bajarilish(tasks, bugun):
    """Berilgan vazifalar uchun bajarilish ko'rsatkichlari.

    Qaytaradi: {jami, bajarildi, bajarilmadi, hisobga_olingan, foiz, daqiqa}
      - foiz: 0–100 butun son, yoki None (maxraj 0 bo'lsa — "—").
    """
    jami = len(tasks)
    bajarildi = sum(1 for t in tasks if t.status == "done")
    bajarilmadi = sum(1 for t in tasks if t.status in BAJARILMADI_STATUS)
    # O'tgan kunlarning "todo" si ham bajarilmagan hisoblanadi.
    otgan_todo = sum(
        1 for t in tasks if t.status == "todo" and t.plan_date < bugun
    )

    maxraj = bajarildi + bajarilmadi + otgan_todo
    foiz = round(bajarildi / maxraj * 100) if maxraj > 0 else None

    daqiqa = sum((t.minutes or 0) for t in tasks)

    return {
        "jami": jami,
        "bajarildi": bajarildi,
        "bajarilmadi": bajarilmadi,
        "hisobga_olingan": maxraj,
        "foiz": foiz,
        "daqiqa": daqiqa,
        "vaqt_matni": daqiqa_matni(daqiqa),
    }


# =========================================================
#   KUNLAR BO'YICHA GRAFIK
# =========================================================


def _rang(foiz):
    """Foizga qarab rang nomi (grafik ustuni uchun)."""
    if foiz is None:
        return "grey"
    if foiz >= 80:
        return "green"
    if foiz >= 50:
        return "yellow"
    return "red"


def kunlik_grafik(tasks, boshi, oxiri, bugun):
    """Har bir kun uchun ustun ma'lumoti."""
    # Kun bo'yicha guruhlaymiz.
    kunlar = {}
    kun = boshi
    while kun <= oxiri:
        kunlar[kun] = []
        kun += timedelta(days=1)
    for t in tasks:
        if t.plan_date in kunlar:
            kunlar[t.plan_date].append(t)

    natija = []
    for kun in sorted(kunlar):
        kun_tasks = kunlar[kun]
        st = bajarilish(kun_tasks, bugun)
        natija.append({
            "sana": kun.isoformat(),
            "kun_raqami": kun.day,
            "hafta_kuni": HAFTA_KUNLARI[kun.weekday()],
            "bajarildi": st["bajarildi"],
            "jami": len(kun_tasks),
            "foiz": st["foiz"],
            "balandlik": st["foiz"] if st["foiz"] is not None else 0,
            "rang": _rang(st["foiz"]),
            "vaqt_matni": st["vaqt_matni"],
        })
    return natija


# =========================================================
#   VAQT — GURUHLAR BO'YICHA
# =========================================================


def vaqt_guruhlar(tasks, bugun):
    """Har bir guruh bo'yicha sarflangan vaqt va ulush.

    Qaytaradi: (qatorlar, jami_daqiqa). Qatorlar vaqti ko'pdan kamga tartibli,
    vaqti 0 bo'lgan guruhlar chiqmaydi.
    """
    jami_daqiqa = sum((t.minutes or 0) for t in tasks)

    qatorlar = []
    for cat in CATEGORIES:
        guruh_tasks = [t for t in tasks if t.category == cat["id"]]
        daqiqa = sum((t.minutes or 0) for t in guruh_tasks)
        if daqiqa <= 0:
            continue
        st = bajarilish(guruh_tasks, bugun)
        qatorlar.append({
            "id": cat["id"],
            "emoji": cat["emoji"],
            "name": cat["name"],
            "daqiqa": daqiqa,
            "vaqt_matni": daqiqa_matni(daqiqa),
            "ulush": round(daqiqa / jami_daqiqa * 100) if jami_daqiqa else 0,
            "vazifa_soni": len(guruh_tasks),
            "bajarilish_foizi": st["foiz"],
        })

    qatorlar.sort(key=lambda r: r["daqiqa"], reverse=True)
    return qatorlar, jami_daqiqa


# =========================================================
#   UZOQ VAQTDAN BERI BAJARILMAYOTGANLAR (hozirgi holat)
# =========================================================


def _oxirgi_yozuv(zanjir):
    """Zanjirdagi eng oxirgi (plan_date, id bo'yicha) vazifani qaytaradi."""
    return max(zanjir, key=lambda t: (t.plan_date, t.id))


def uzoq_kutayotganlar(barcha_tasks, bugun):
    """Uzoq vaqtdan beri bajarilmayotgan vazifa zanjirlari.

    Zanjir (root_id bo'yicha) ro'yxatga tushadi, agar:
      - zanjirda birorta ham "done" yo'q,
      - eng oxirgi yozuv "dropped" emas,
      - va (bugun − first_date) ≥ 3 kun YOKI moved_count ≥ 2.
    """
    # root_id bo'yicha guruhlaymiz.
    zanjirlar = {}
    for t in barcha_tasks:
        zanjirlar.setdefault(t.root_id, []).append(t)

    natija = []
    for root_id, zanjir in zanjirlar.items():
        # Zanjirda bajarilgan bo'lsa — tashlaymiz.
        if any(t.status == "done" for t in zanjir):
            continue

        oxirgi = _oxirgi_yozuv(zanjir)
        if oxirgi.status == "dropped":
            continue

        kun_otdi = (bugun - oxirgi.first_date).days if oxirgi.first_date else 0
        moved = oxirgi.moved_count or 0
        if not (kun_otdi >= 3 or moved >= 2):
            continue

        # Oxirgi sababi: avval oxirgi yozuvniki, bo'lmasa zanjirdan eng yangisi.
        sabab = oxirgi.reason or ""
        if not sabab:
            for t in sorted(zanjir, key=lambda x: (x.plan_date, x.id), reverse=True):
                if t.reason:
                    sabab = t.reason
                    break

        cat = get_category(oxirgi.category)
        natija.append({
            "id": oxirgi.id,
            "title": oxirgi.title,
            "emoji": cat["emoji"],
            "name": cat["name"],
            "kun_otdi": kun_otdi,
            "moved_count": moved,
            "sabab": sabab,
            "oxirgi_sana": oxirgi.plan_date.isoformat(),
            "bugunmi": oxirgi.plan_date == bugun,
            "qizil": kun_otdi > 7,
        })

    # Eng eskisi (ko'p kun o'tgani) tepada.
    natija.sort(key=lambda r: r["kun_otdi"], reverse=True)
    return natija


# =========================================================
#   SABABLAR (nega bajarolmadim)
# =========================================================


def sabablar(tasks, limit=5):
    """Davrdagi failed vazifalar sabablarining soni (ko'pdan kamga, top 5)."""
    sanoq = {}
    for t in tasks:
        if t.status != "failed":
            continue
        sabab = (t.reason or "").strip() or "Sabab ko'rsatilmagan"
        sanoq[sabab] = sanoq.get(sabab, 0) + 1

    qatorlar = [{"sabab": k, "soni": v} for k, v in sanoq.items()]
    qatorlar.sort(key=lambda r: r["soni"], reverse=True)
    return qatorlar[:limit]


# =========================================================
#   SOLISHTIRISH (oldingi davr bilan)
# =========================================================


def solishtirish(joriy, oldingi):
    """Joriy va oldingi davr bajarilish foizini solishtiradi.

    Qaytaradi: None (oldingi davrda ma'lumot yo'q) yoki
    {delta, yaxshi} — delta foiz farqi, yaxshi — yaxshilandi(True)/yomon(False).
    """
    if oldingi["hisobga_olingan"] == 0 or oldingi["foiz"] is None:
        return None
    if joriy["foiz"] is None:
        return None
    delta = joriy["foiz"] - oldingi["foiz"]
    return {"delta": delta, "yaxshi": delta >= 0}


# =========================================================
#   QISQA XULOSA (avtomatik, AI siz)
# =========================================================


def xulosa_jumlalari(grafik, vaqt_qatorlar, tasks, bugun, taqqos, period):
    """Oddiy qoidalar asosida 2–4 ta jumla yasaydi."""
    jumlalar = []

    # 1) Eng samarali kun.
    bor_kunlar = [k for k in grafik if k["foiz"] is not None]
    if bor_kunlar:
        eng = max(bor_kunlar, key=lambda k: k["foiz"])
        jumlalar.append(
            f"Eng samarali kuningiz: {eng['hafta_kuni']} ({eng['foiz']}%)."
        )

    # 2) Eng ko'p vaqt ketgan guruh.
    if vaqt_qatorlar:
        eng_vaqt = vaqt_qatorlar[0]
        jumlalar.append(
            f"Eng ko'p vaqt: {eng_vaqt['name']} ({eng_vaqt['ulush']}%)."
        )

    # 3) Eng qiyin guruh (kamida 3 ta vazifasi bor guruhlar orasidan).
    qiyin = None
    for cat in CATEGORIES:
        guruh_tasks = [t for t in tasks if t.category == cat["id"]]
        if len(guruh_tasks) < 3:
            continue
        st = bajarilish(guruh_tasks, bugun)
        if st["foiz"] is None:
            continue
        if qiyin is None or st["foiz"] < qiyin["foiz"]:
            qiyin = {"name": cat["name"], "foiz": st["foiz"]}
    if qiyin is not None:
        jumlalar.append(
            f"Eng qiyin guruh: {qiyin['name']} — atigi {qiyin['foiz']}% bajarildi."
        )

    # 4) Oldingi davr bilan solishtirish.
    if taqqos is not None and taqqos["delta"] != 0:
        davr_soz = "hafta" if period == "week" else "oy"
        yon = "yaxshiroq" if taqqos["yaxshi"] else "yomonroq"
        jumlalar.append(
            f"Bu {davr_soz} o'tgan {davr_soz}dan {abs(taqqos['delta'])}% {yon}."
        )

    return jumlalar
