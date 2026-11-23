"""
test_stage4.py — 4-bosqich: belgilash, vaqt va ko'chirish testlari.

Ishga tushirish (loyiha papkasida, venv yoqilgandan keyin):
    python -m pytest
"""

import os
import sys
from datetime import timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret"

import app as A  # noqa: E402


@pytest.fixture(autouse=True)
def toza_baza():
    with A.app.app_context():
        A.db.drop_all()
        A.db.create_all()
    yield


def foydalanuvchi_yarat(username):
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


def vazifa_qosh(client, matn, sana_iso=None):
    url = "/" if sana_iso is None else "/?date=" + sana_iso
    client.post(url, data={"kunlik_matn": matn})


def oxirgi_vazifa(username):
    with A.app.app_context():
        u = A.User.query.filter_by(username=username).first()
        return (
            A.Task.query.filter_by(user_id=u.id)
            .order_by(A.Task.id.desc())
            .first()
        )


def vazifani_ol(task_id):
    with A.app.app_context():
        return A.db.session.get(A.Task, task_id)


# --- Belgilash: done → bekor → todo ---

def test_done_va_bekor():
    c = foydalanuvchi_yarat("ali")
    vazifa_qosh(c, "Formani dazmollash")
    t = oxirgi_vazifa("ali")

    # Bajarildi
    r = c.post(f"/api/task/{t.id}/status", json={"status": "done"})
    assert r.status_code == 200
    t2 = vazifani_ol(t.id)
    assert t2.status == "done"
    assert t2.done_at is not None

    # Bekor qilish — yana todo, done_at va reason tozalanadi
    c.post(f"/api/task/{t.id}/status", json={"status": "todo"})
    t3 = vazifani_ol(t.id)
    assert t3.status == "todo"
    assert t3.done_at is None
    assert t3.reason is None


def test_failed_sabab():
    c = foydalanuvchi_yarat("vali")
    vazifa_qosh(c, "Kitob o'qish")
    t = oxirgi_vazifa("vali")

    c.post(f"/api/task/{t.id}/status", json={"status": "failed", "reason": "Vaqt yetmadi"})
    t2 = vazifani_ol(t.id)
    assert t2.status == "failed"
    assert t2.reason == "Vaqt yetmadi"


# --- Vaqt (minutes) ---

def test_minutes_qosh_va_ornat():
    c = foydalanuvchi_yarat("time")
    vazifa_qosh(c, "Sport zaliga borish")
    t = oxirgi_vazifa("time")

    # O'rnatish
    r = c.post(f"/api/task/{t.id}/minutes", json={"mode": "set", "value": 30})
    assert r.status_code == 200
    assert r.get_json()["minutes"] == 30

    # Qo'shish
    r = c.post(f"/api/task/{t.id}/minutes", json={"mode": "add", "value": 15})
    assert r.get_json()["minutes"] == 45


def test_minutes_notogri_rad():
    c = foydalanuvchi_yarat("time2")
    vazifa_qosh(c, "Sport")
    t = oxirgi_vazifa("time2")

    assert c.post(f"/api/task/{t.id}/minutes", json={"mode": "set", "value": -5}).status_code == 400
    assert c.post(f"/api/task/{t.id}/minutes", json={"mode": "set", "value": 2000}).status_code == 400
    # Harf ham rad etilsin
    assert c.post(f"/api/task/{t.id}/minutes", json={"mode": "set", "value": "abc"}).status_code == 400


# --- Ko'chirish ---

def test_kochirish_mantiqi():
    c = foydalanuvchi_yarat("move")
    bugun = A.bugungi_sana()
    kecha = (bugun - timedelta(days=1)).isoformat()

    vazifa_qosh(c, "Formani dazmollash", kecha)
    asl = oxirgi_vazifa("move")
    asl_id = asl.id
    asl_root = asl.root_id
    asl_first = asl.first_date

    # Bugunga ko'chiramiz
    r = c.post(f"/api/task/{asl_id}/move", json={"date": bugun.isoformat()})
    assert r.status_code == 200

    # Asl vazifa (todo edi) → moved
    asl2 = vazifani_ol(asl_id)
    assert asl2.status == "moved"

    # Yangi nusxa: bugungi, todo, first_date va root_id asliniki, moved_count +1
    nusxa = oxirgi_vazifa("move")
    assert nusxa.id != asl_id
    assert nusxa.plan_date == bugun
    assert nusxa.status == "todo"
    assert nusxa.first_date == asl_first
    assert nusxa.root_id == asl_root
    assert nusxa.moved_count == 1


def test_ikki_marta_kochirib_bolmaydi():
    c = foydalanuvchi_yarat("move2")
    bugun = A.bugungi_sana()
    kecha = (bugun - timedelta(days=1)).isoformat()

    vazifa_qosh(c, "Kitob o'qish", kecha)
    asl = oxirgi_vazifa("move2")

    # Birinchi ko'chirish — OK
    assert c.post(f"/api/task/{asl.id}/move", json={"date": bugun.isoformat()}).status_code == 200
    # Ikkinchi marta o'sha asl vazifani ko'chirish — rad etiladi
    assert c.post(f"/api/task/{asl.id}/move", json={"date": bugun.isoformat()}).status_code == 400


def test_failed_kochirilsa_failed_qoladi():
    c = foydalanuvchi_yarat("movef")
    bugun = A.bugungi_sana()
    kecha = (bugun - timedelta(days=1)).isoformat()

    vazifa_qosh(c, "Sport", kecha)
    asl = oxirgi_vazifa("movef")
    c.post(f"/api/task/{asl.id}/status", json={"status": "failed", "reason": "Dangasalik"})

    c.post(f"/api/task/{asl.id}/move", json={"date": bugun.isoformat()})
    asl2 = vazifani_ol(asl.id)
    assert asl2.status == "failed"  # failed bo'lib qoladi
    assert asl2.reason == "Dangasalik"


# --- Kechikkanlar ro'yxati ---

def test_kechikkanlar_royxati():
    c = foydalanuvchi_yarat("over")
    bugun = A.bugungi_sana()
    kecha = (bugun - timedelta(days=1)).isoformat()

    vazifa_qosh(c, "Formani dazmollash", kecha)  # todo, kecha
    with A.app.app_context():
        u = A.User.query.filter_by(username="over").first()
        kech = A.kechikkan_vazifalar(u.id, bugun)
    assert len(kech) == 1


def test_dropped_kechikkanlarda_chiqmaydi():
    c = foydalanuvchi_yarat("drop")
    bugun = A.bugungi_sana()
    kecha = (bugun - timedelta(days=1)).isoformat()

    vazifa_qosh(c, "Kitob o'qish", kecha)
    t = oxirgi_vazifa("drop")
    c.post(f"/api/task/{t.id}/drop", json={})

    with A.app.app_context():
        u = A.User.query.filter_by(username="drop").first()
        kech = A.kechikkan_vazifalar(u.id, bugun)
    assert len(kech) == 0


def test_kochirilgan_kechikkanlarda_chiqmaydi():
    c = foydalanuvchi_yarat("over2")
    bugun = A.bugungi_sana()
    kecha = (bugun - timedelta(days=1)).isoformat()

    vazifa_qosh(c, "Sport", kecha)
    t = oxirgi_vazifa("over2")
    c.post(f"/api/task/{t.id}/move", json={"date": bugun.isoformat()})

    with A.app.app_context():
        u = A.User.query.filter_by(username="over2").first()
        kech = A.kechikkan_vazifalar(u.id, bugun)
    # Asl "moved" bo'ldi, nusxa esa bugungi — kechikkanlarda hech biri chiqmaydi
    assert len(kech) == 0


# --- Xavfsizlik: birovning vazifasi ---

def test_birovni_belgilash_404():
    a = foydalanuvchi_yarat("u1")
    b = foydalanuvchi_yarat("u2")
    vazifa_qosh(a, "Formani dazmollash")
    ta = oxirgi_vazifa("u1")

    assert b.post(f"/api/task/{ta.id}/status", json={"status": "done"}).status_code == 404
    assert b.post(f"/api/task/{ta.id}/move", json={"date": A.bugungi_sana().isoformat()}).status_code == 404
    assert b.post(f"/api/task/{ta.id}/minutes", json={"mode": "set", "value": 10}).status_code == 404


# --- Kun sahifasi va fragment ishlaydi ---

def test_fragment_ishlaydi():
    c = foydalanuvchi_yarat("frag")
    vazifa_qosh(c, "Kitob o'qish")
    r = c.get("/fragment")
    assert r.status_code == 200
    # (Apostrof HTML'da &#39; ga aylanadi, shuning uchun "Kitob" ni qidiramiz.)
    assert "Kitob" in r.get_data(as_text=True)
