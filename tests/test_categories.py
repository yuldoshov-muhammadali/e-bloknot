"""
test_categories.py — Guruhlash modulini (categories.py) tekshirish.

Ishga tushirish (loyiha papkasida, venv yoqilgandan keyin):
    python -m pytest
"""

import os
import sys

# Loyiha papkasini import yo'liga qo'shamiz (categories.py ni topishi uchun).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from categories import classify, normalize, split_tasks  # noqa: E402


# --- classify: har bir vazifa to'g'ri guruhga tushishi ---

def test_ingliz_til():
    assert classify("Ingliz tilidan writing yozish") == "til"


def test_python_dastur():
    # "python" bor — demak dasturlash guruhi.
    assert classify("Python kursidan 2 ta dars ko'rish") == "dastur"


def test_kursovoy_oqish():
    assert classify("Kursovoy ishning 1-bobini yozish") == "oqish"


def test_onamga_oila():
    assert classify("Onamga qo'ng'iroq qilish") == "oila"


def test_forma_maishiy():
    assert classify("Formani dazmollash") == "maishiy"


def test_yugurish_sport():
    assert classify("Ertalab 3 km yugurish") == "sport"


def test_naryad_xizmat():
    assert classify("Naryadga tayyorlanish") == "xizmat"


# --- So'z boshidan qidirish: "zona" → "ona" ga mos kelmasligi kerak ---

def test_zona_oila_emas():
    # "zona" ichida "ona" bor, lekin oldida "z" harfi — mos kelmasligi shart.
    assert classify("Zona haqida o'ylash") != "oila"


# --- Yangi alifbo harflari (ö, ğ) bilan yozilgan matn ham ishlasin ---

def test_yangi_alifbo_normalize():
    # ö → o', ğ → g'
    assert normalize("Ö") == "o'"
    assert normalize("Ğ") == "g'"
    assert normalize("Ş") == "sh"
    assert normalize("Ç") == "ch"


def test_yangi_alifbo_classify():
    # "Onamga" ö/ğ bilan yozilgan bo'lsa ham oila guruhiga tushsin.
    assert classify("Yangi alifboda: Qöñğiroq / Onamga qöñğiroq") == "oila"
    # "dökon" → "do'kon" (maishiy) ga aylanib mos kelsin.
    assert classify("Dökonga borish") == "maishiy"


# --- split_tasks: matnni to'g'ri bo'laklarga bo'lishi ---

def test_split_uchta_vazifa():
    matn = "1) Writing yozish, onamga qo'ng'iroq\n- Formani dazmollash"
    natija = split_tasks(matn)
    assert len(natija) == 3
    assert natija[0] == "Writing yozish"
    assert natija[1] == "Onamga qo'ng'iroq"
    assert natija[2] == "Formani dazmollash"


def test_split_bosh_belgilar_olinadi():
    # Boshidagi "-", "•", "2." kabi belgilar olib tashlanishi kerak.
    natija = split_tasks("• Sport\n2. Kitob o'qish")
    assert natija == ["Sport", "Kitob o'qish"]


def test_split_qisqalar_tashlanadi():
    # 2 belgidan qisqa bo'laklar (masalan "a") tashlab yuboriladi.
    natija = split_tasks("a, Sportga borish")
    assert natija == ["Sportga borish"]
