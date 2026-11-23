"""
test_learning.py — 3-bosqich: qo'lda tuzatish, o'rganish va xavfsizlik testlari.

Ishga tushirish (loyiha papkasida, venv yoqilgandan keyin):
    python -m pytest
"""

import os
import sys

import pytest

# Loyiha papkasini import yo'liga qo'shamiz.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test uchun xotiradagi (fayl emas) bazadan foydalanamiz — import oldidan beramiz.
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret"

import app as A  # noqa: E402
from categories import extract_words  # noqa: E402


@pytest.fixture(autouse=True)
def toza_baza():
    """Har bir testdan oldin bazani tozalab, qaytadan yaratamiz."""
    with A.app.app_context():
        A.db.drop_all()
        A.db.create_all()
    yield


def foydalanuvchi_yarat(username):
    """Yangi foydalanuvchi yaratib, unga kirgan test mijozini qaytaradi."""
    c = A.app.test_client()
    c.post("/register", data={
        "full_name": "Test " + username,
        "group_name": "BI-525",
        "username": username,
        "password": "parol123",
        "password2": "parol123",
    })
    c.post("/login", data={"username": username, "password": "parol123"})
    return c


def oxirgi_vazifa(username):
    """Berilgan foydalanuvchining eng oxirgi vazifasini (DB dan) qaytaradi."""
    with A.app.app_context():
        u = A.User.query.filter_by(username=username).first()
        return (
            A.Task.query.filter_by(user_id=u.id)
            .order_by(A.Task.id.desc())
            .first()
        )


# --- O'RGANISH: qo'lda o'zgartirish keyingi vazifaga ta'sir qiladi ---

def test_organish_ishlaydi():
    c = foydalanuvchi_yarat("ali")

    # 1) "Kursovoy 1-bob" qo'shamiz (dastlab boshqa guruhga tushadi).
    c.post("/", data={"kunlik_matn": "Kursovoy 1-bob"})
    t1 = oxirgi_vazifa("ali")

    # 2) Foydalanuvchi uni qo'lda "dam" guruhiga o'zgartiradi.
    r = c.post(f"/api/task/{t1.id}/category", json={"category": "dam"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True

    # 3) Endi "Kursovoy 2-bob" qo'shamiz — u endi "dam" ga tushishi kerak.
    c.post("/", data={"kunlik_matn": "Kursovoy 2-bob"})
    t2 = oxirgi_vazifa("ali")
    assert t2.category == "dam"


# --- To'xtash so'zlari o'rganilmaydi ---

def test_stopword_organilmaydi():
    sozlar = extract_words("Bugun kitob o'qish")
    assert "bugun" not in sozlar   # to'xtash so'zi
    assert "o'qish" not in sozlar  # to'xtash so'zi (yozish/o'qish)
    assert "kitob" in sozlar       # bu o'rganiladi


def test_stopword_bazaga_yozilmaydi():
    c = foydalanuvchi_yarat("vali")
    c.post("/", data={"kunlik_matn": "Bugun kitob o'qish"})
    t = oxirgi_vazifa("vali")
    c.post(f"/api/task/{t.id}/category", json={"category": "sport"})

    with A.app.app_context():
        u = A.User.query.filter_by(username="vali").first()
        sozlar = [k.word for k in A.UserKeyword.query.filter_by(user_id=u.id).all()]
    assert "bugun" not in sozlar
    assert "kitob" in sozlar


# --- Bir foydalanuvchining o'rganishi boshqasiga ta'sir qilmaydi ---

def test_organish_shaxsiy():
    a = foydalanuvchi_yarat("aaa")
    b = foydalanuvchi_yarat("bbb")

    # A "kursovoy" ni "dam" ga o'rgatadi.
    a.post("/", data={"kunlik_matn": "Kursovoy 1-bob"})
    ta = oxirgi_vazifa("aaa")
    a.post(f"/api/task/{ta.id}/category", json={"category": "dam"})

    # B "Kursovoy 2-bob" qo'shadi — B ga A ning o'rganishi ta'sir qilmasligi kerak.
    b.post("/", data={"kunlik_matn": "Kursovoy 2-bob"})
    tb = oxirgi_vazifa("bbb")
    assert tb.category != "dam"   # standart lug'at bo'yicha "oqish" bo'ladi
    assert tb.category == "oqish"


# --- XAVFSIZLIK: birovning vazifasini o'zgartirish/o'chirish 404 ---

def test_birovning_vazifasi_404():
    a = foydalanuvchi_yarat("x1")
    b = foydalanuvchi_yarat("x2")

    a.post("/", data={"kunlik_matn": "Formani dazmollash"})
    ta = oxirgi_vazifa("x1")

    # B boshqa odamning vazifasini o'zgartirmoqchi — 404.
    r1 = b.post(f"/api/task/{ta.id}/category", json={"category": "sport"})
    assert r1.status_code == 404

    # B uni o'chirmoqchi — 404.
    r2 = b.post(f"/api/task/{ta.id}/delete", json={})
    assert r2.status_code == 404

    # B uni tahrirlamoqchi — 404.
    r3 = b.post(f"/api/task/{ta.id}/edit", json={"title": "O'zgargan"})
    assert r3.status_code == 404


# --- Matnni tahrirlash guruhni o'zgartirmaydi ---

def test_tahrir_guruhni_ozgartirmaydi():
    c = foydalanuvchi_yarat("edit")
    c.post("/", data={"kunlik_matn": "Formani dazmollash"})  # -> maishiy
    t = oxirgi_vazifa("edit")
    eski_guruh = t.category

    # Matnni sport so'zli matnga o'zgartiramiz, lekin guruh o'zgarmasligi kerak.
    r = c.post(f"/api/task/{t.id}/edit", json={"title": "Sport zaliga borish"})
    assert r.status_code == 200

    t2 = oxirgi_vazifa("edit")
    assert t2.title == "Sport zaliga borish"
    assert t2.category == eski_guruh  # guruh o'zgarmadi
