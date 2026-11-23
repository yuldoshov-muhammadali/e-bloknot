"""
test_stage6.py — 6-bosqich: production xavfsizligi testlari.
  - /health endpoint
  - CSRF himoyasi (forma va API)
  - login rate limit (ko'p noto'g'ri urinish bloklanadi)
  - production'da SECRET_KEY bo'lmasa ishga tushmaydi

Ishga tushirish:  python -m pytest
"""

import os
import re
import subprocess
import sys

import pytest

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)

os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret"

import app as A  # noqa: E402


@pytest.fixture
def toza():
    with A.app.app_context():
        A.db.drop_all()
        A.db.create_all()
    A._login_urinishlar.clear()
    yield


def _meta_token(client, path="/register"):
    """Sahifadagi <meta name="csrf-token"> dan tokenni oladi."""
    html = client.get(path).get_data(as_text=True)
    m = re.search(r'name="csrf-token" content="([^"]+)"', html)
    return m.group(1) if m else ""


# --- /health ---

def test_health(toza):
    r = A.app.test_client().get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


# --- CSRF: forma ---

def test_csrf_forma(toza):
    A.app.config["WTF_CSRF_ENABLED"] = True
    try:
        c = A.app.test_client()
        tok = _meta_token(c, "/register")
        # Token bilan — ishlaydi (login sahifasiga yo'naltiradi)
        r = c.post("/register", data={
            "full_name": "Ali", "group_name": "BI", "username": "ali",
            "password": "parol123", "password2": "parol123", "csrf_token": tok,
        })
        assert r.status_code == 302

        # Tokensiz — rad etiladi (400)
        c2 = A.app.test_client()
        r2 = c2.post("/register", data={
            "full_name": "Vali", "group_name": "BI", "username": "vali",
            "password": "parol123", "password2": "parol123",
        })
        assert r2.status_code == 400
    finally:
        A.app.config["WTF_CSRF_ENABLED"] = False


# --- CSRF: API (fetch header orqali) ---

def test_csrf_api(toza):
    A.app.config["WTF_CSRF_ENABLED"] = True
    try:
        c = A.app.test_client()
        tok = _meta_token(c, "/register")
        c.post("/register", data={
            "full_name": "Ali", "group_name": "BI", "username": "ali",
            "password": "parol123", "password2": "parol123", "csrf_token": tok,
        })
        c.post("/login", data={"username": "ali", "password": "parol123", "csrf_token": tok})
        c.post("/", data={"kunlik_matn": "Kitob o'qish", "csrf_token": tok})

        with A.app.app_context():
            u = A.User.query.filter_by(username="ali").first()
            t = A.Task.query.filter_by(user_id=u.id).first()
            tid = t.id

        # Tokensiz API — rad etiladi
        r = c.post(f"/api/task/{tid}/status", json={"status": "done"})
        assert r.status_code == 400

        # X-CSRFToken header bilan — ishlaydi
        r = c.post(f"/api/task/{tid}/status", json={"status": "done"},
                   headers={"X-CSRFToken": tok})
        assert r.status_code == 200
    finally:
        A.app.config["WTF_CSRF_ENABLED"] = False


# --- Login rate limit ---

def test_login_rate_limit(toza):
    c = A.app.test_client()
    # 10 ta noto'g'ri urinish
    for _ in range(10):
        r = c.post("/login", data={"username": "yoq", "password": "notogri"})
        assert r.status_code == 200  # oddiy "xato" sahifasi
    # 11-chisi — bloklanadi
    r = c.post("/login", data={"username": "yoq", "password": "notogri"})
    assert r.status_code == 429


# --- Production'da SECRET_KEY bo'lmasa ishga tushmaydi ---

def test_production_secret_key_majburiy():
    env = dict(os.environ)
    env.pop("SECRET_KEY", None)
    env["APP_ENV"] = "production"
    env["DATABASE_URL"] = "sqlite://"
    r = subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=PROJECT, env=env, capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "SECRET_KEY" in (r.stderr + r.stdout)
