"""
test_reports.py — 5-bosqich: hisobot hisob-kitoblari (reports.py) testlari.

reports.py toza funksiyalar bo'lgani uchun ko'p test bazasiz, oddiy
"soxta" (SimpleNamespace) vazifalar bilan yoziladi.

Ishga tushirish:  python -m pytest
"""

import os
import sys
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reports  # noqa: E402

BUGUN = date(2026, 11, 23)  # dushanba


def mk(status="todo", plan=BUGUN, minutes=0, category="dastur",
       first=None, root=1, moved=0, reason=None, tid=1, title="Vazifa"):
    """Soxta Task obyekti yasaydi (reports funksiyalari uchun yetarli)."""
    return SimpleNamespace(
        id=tid, title=title, status=status, plan_date=plan, minutes=minutes,
        category=category, first_date=(first or plan), root_id=root,
        moved_count=moved, reason=reason, done_at=None,
    )


# --- Bajarilish foizi ---

def test_foiz_60():
    kecha = BUGUN - timedelta(days=1)
    tasks = [
        mk("done", kecha), mk("done", kecha), mk("done", kecha),
        mk("failed", kecha), mk("moved", kecha),
    ]
    st = reports.bajarilish(tasks, BUGUN)
    assert st["foiz"] == 60  # 3 / (3 + 2)


def test_todo_qoida():
    kecha = BUGUN - timedelta(days=1)
    tasks = [
        mk("done", kecha),        # bajarildi
        mk("todo", kecha),        # o'tgan kun todo → bajarilmagan
        mk("todo", BUGUN),        # bugungi todo → foizga kirmaydi
    ]
    st = reports.bajarilish(tasks, BUGUN)
    # maxraj = 1 (done) + 1 (kechagi todo) = 2 → 50%
    assert st["foiz"] == 50


def test_todo_bugungi_kirmaydi():
    tasks = [mk("done", BUGUN), mk("todo", BUGUN)]
    st = reports.bajarilish(tasks, BUGUN)
    assert st["foiz"] == 100  # bugungi todo hisobga olinmaydi


def test_maxraj_nol():
    tasks = [mk("todo", BUGUN)]  # faqat bugungi todo
    st = reports.bajarilish(tasks, BUGUN)
    assert st["foiz"] is None  # "—"


# --- Hafta dushanbadan ---

def test_hafta_dushanbadan():
    boshi, oxiri = reports.hafta_oraligi(date(2026, 11, 23))
    assert boshi == date(2026, 11, 23)
    assert oxiri == date(2026, 11, 29)
    assert boshi.weekday() == 0  # dushanba


def test_oy_oraligi():
    boshi, oxiri = reports.oy_oraligi(date(2026, 11, 15))
    assert boshi == date(2026, 11, 1)
    assert oxiri == date(2026, 11, 30)


# --- Vaqt guruhlar bo'yicha ---

def test_vaqt_guruhlar():
    kecha = BUGUN - timedelta(days=1)
    tasks = [
        mk("done", kecha, minutes=30, category="dastur"),
        mk("done", kecha, minutes=30, category="dastur"),
        mk("done", kecha, minutes=40, category="oqish"),
        mk("done", kecha, minutes=0, category="sport"),  # 0 — chiqmasligi kerak
    ]
    qatorlar, jami = reports.vaqt_guruhlar(tasks, BUGUN)
    assert jami == 100
    assert len(qatorlar) == 2  # sport (0 daq) chiqmaydi
    # Ko'pdan kamga tartiblangan
    assert qatorlar[0]["id"] == "dastur"
    assert qatorlar[0]["ulush"] == 60
    assert qatorlar[1]["id"] == "oqish"
    assert qatorlar[1]["ulush"] == 40
    # Ulushlar yig'indisi 100
    assert sum(r["ulush"] for r in qatorlar) == 100


# --- Uzoq kutayotganlar ---

def test_uzoq_kutayotganlar():
    t5 = BUGUN - timedelta(days=5)
    t4 = BUGUN - timedelta(days=4)
    t2 = BUGUN - timedelta(days=2)

    tasks = [
        # A: 4 kun oldingi, bajarilmagan → CHIQADI
        mk("failed", t4, root=1, first=t4, tid=1, title="A"),
        # B: zanjirda done bor → CHIQMAYDI
        mk("done", t4, root=2, first=t4, tid=2, title="B"),
        # C: oxirgisi dropped → CHIQMAYDI
        mk("moved", t5, root=3, first=t5, tid=3, title="C1"),
        mk("dropped", t2, root=3, first=t5, tid=4, title="C2"),
        # D: yangi (bugungi), lekin moved_count=2 → CHIQADI
        mk("todo", BUGUN, root=5, first=BUGUN, moved=2, tid=5, title="D"),
    ]
    natija = reports.uzoq_kutayotganlar(tasks, BUGUN)
    idlar = {p["id"] for p in natija}
    assert idlar == {1, 5}  # A va D


def test_uzoq_eng_eski_tepada():
    t10 = BUGUN - timedelta(days=10)
    t3 = BUGUN - timedelta(days=3)
    tasks = [
        mk("failed", t3, root=1, first=t3, tid=1),
        mk("failed", t10, root=2, first=t10, tid=2),
    ]
    natija = reports.uzoq_kutayotganlar(tasks, BUGUN)
    assert natija[0]["id"] == 2  # 10 kunlik birinchi
    assert natija[0]["qizil"] is True  # 7 dan oshgan


# --- Sabablar ---

def test_sabablar():
    kecha = BUGUN - timedelta(days=1)
    tasks = [
        mk("failed", kecha, reason="Vaqt yetmadi"),
        mk("failed", kecha, reason="Vaqt yetmadi"),
        mk("failed", kecha, reason="Chalg'idim (telefon)"),
        mk("failed", kecha, reason=None),  # bo'sh
        mk("done", kecha, reason=None),     # failed emas — hisobga kirmaydi
    ]
    s = reports.sabablar(tasks)
    d = {r["sabab"]: r["soni"] for r in s}
    assert d["Vaqt yetmadi"] == 2
    assert d["Chalg'idim (telefon)"] == 1
    assert d["Sabab ko'rsatilmagan"] == 1


# --- Solishtirish ---

def test_solishtirish():
    joriy = {"foiz": 60, "hisobga_olingan": 5}
    oldingi = {"foiz": 50, "hisobga_olingan": 4}
    t = reports.solishtirish(joriy, oldingi)
    assert t["delta"] == 10
    assert t["yaxshi"] is True


def test_solishtirish_oldingi_bosh():
    joriy = {"foiz": 60, "hisobga_olingan": 5}
    oldingi = {"foiz": None, "hisobga_olingan": 0}
    assert reports.solishtirish(joriy, oldingi) is None


# =========================================================
#   Integratsiya: A ning hisobotiga B ning ma'lumoti tushmaydi
# =========================================================

os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret"
import app as A  # noqa: E402


@pytest.fixture
def toza_baza():
    with A.app.app_context():
        A.db.drop_all()
        A.db.create_all()
    yield


def _reg_login(username):
    c = A.app.test_client()
    c.post("/register", data={
        "full_name": "T", "group_name": "BI", "username": username,
        "password": "parol123", "password2": "parol123",
    })
    c.post("/login", data={"username": username, "password": "parol123"})
    return c


def test_hisobot_shaxsiy(toza_baza):
    a = _reg_login("aaa")
    b = _reg_login("bbb")

    # A ga vazifa qo'shamiz
    a.post("/", data={"kunlik_matn": "Python kod yozish, Kitob o'qish"})

    # A ning hisobotida vazifa bor
    ra = a.get("/report")
    assert ra.status_code == 200
    assert "Jami vazifalar" in ra.get_data(as_text=True)

    # B ning hisobotida vazifa yo'q
    rb = b.get("/report")
    assert rb.status_code == 200
    assert "Bu davrda vazifa yo'q" in rb.get_data(as_text=True)
