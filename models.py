"""
models.py — Ma'lumotlar bazasi modellari.

Bu faylda ma'lumotlar bazasidagi jadvallar "model" ko'rinishida yoziladi.
Hozircha faqat bitta model bor: User (foydalanuvchi).
Keyingi bosqichlarda bu yerga Task (vazifa) kabi yangi modellar qo'shiladi.
"""

from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

# db — bu ma'lumotlar bazasi bilan ishlash uchun asosiy obyekt.
# Uni shu yerda yaratamiz, lekin dasturga (app) bog'lashni app.py da qilamiz.
db = SQLAlchemy()


# UserMixin — Flask-Login talab qiladigan tayyor xususiyatlarni beradi
# (masalan: foydalanuvchi tizimga kirganmi yoki yo'qligini bilish).
class User(db.Model, UserMixin):
    """Foydalanuvchi jadvali."""

    # Har bir foydalanuvchining takrorlanmas raqami (avtomatik).
    id = db.Column(db.Integer, primary_key=True)

    # Ism familiya, masalan: "Ali Valiyev"
    full_name = db.Column(db.String(120), nullable=False)

    # Guruh nomi, masalan: "BI-525"
    group_name = db.Column(db.String(50), nullable=False)

    # Login (tizimga kirish uchun) — takrorlanmas bo'lishi shart.
    username = db.Column(db.String(80), unique=True, nullable=False)

    # Parol ochiq saqlanmaydi! Faqat uning xeshi (shifrlangan ko'rinishi) saqlanadi.
    password_hash = db.Column(db.String(255), nullable=False)

    # Ro'yxatdan o'tgan vaqti — avtomatik joriy vaqt yoziladi.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Parolni xeshlab (shifrlab) saqlaydi."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Kiritilgan parol to'g'ri yoki yo'qligini tekshiradi."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        # Bu faqat dasturchiga qulaylik uchun (konsolda chiroyli ko'rinish).
        return f"<User {self.username}>"


class Task(db.Model):
    """Vazifa jadvali.

    Har bir vazifa bitta foydalanuvchiga tegishli. Kelajakdagi bosqichlarni
    (belgilash, vaqt, ertaga ko'chirish) hisobga olib, maydonlar hozirdan
    to'liq qilib yaratildi. Hozir ularning hammasi ishlatilmaydi.
    """

    id = db.Column(db.Integer, primary_key=True)

    # Qaysi foydalanuvchiga tegishli (User.id ga bog'langan).
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Vazifa matni, masalan: "Ingliz tilidan writing yozish"
    title = db.Column(db.String(500), nullable=False)

    # Guruh ID si, masalan: "dastur", "oqish" (categories.py dan).
    category = db.Column(db.String(30), nullable=False, default="boshqa")

    # Vazifa qaysi kun uchun rejalashtirilgan (sana).
    plan_date = db.Column(db.Date, nullable=False)

    # Holati:
    #   "todo"    — hali belgilanmagan
    #   "done"    — bajarildi
    #   "failed"  — bajarolmadim (reason da sababi)
    #   "moved"   — boshqa kunga ko'chirildi (yangi kunda nusxasi bor)
    #   "dropped" — voz kechildi (endi kerak emas)
    # Hisobotda "failed", "moved", "dropped" — bajarilmagan deb hisoblanadi.
    status = db.Column(db.String(10), nullable=False, default="todo")

    # --- Quyidagilar 4-5 bosqichda ishlatiladi ---

    # Bajarolmagan bo'lsa sababi (bo'sh bo'lishi mumkin).
    reason = db.Column(db.String(500))

    # Vazifaga sarflangan vaqt (daqiqada).
    minutes = db.Column(db.Integer, default=0)

    # Vazifa BIRINCHI marta qaysi kuni yozilgani (ertaga ko'chsa ham o'zgarmaydi).
    first_date = db.Column(db.Date, nullable=False)

    # Vazifa ko'chirilganda nusxalarni bog'lash uchun (yangi vazifada = o'z id si).
    root_id = db.Column(db.Integer)

    # Necha marta keyingi kunga ko'chirilgani.
    moved_count = db.Column(db.Integer, default=0)

    # Yaratilgan va bajarilgan vaqtlar.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    done_at = db.Column(db.DateTime)

    # Hisobotlar tez ishlashi uchun indekslar
    # (user_id + sana, va user_id + zanjir bo'yicha qidirish).
    __table_args__ = (
        db.Index("ix_task_user_plan", "user_id", "plan_date"),
        db.Index("ix_task_user_root", "user_id", "root_id"),
    )

    def __repr__(self):
        return f"<Task {self.id} {self.title[:20]!r} ({self.category})>"


class UserKeyword(db.Model):
    """Foydalanuvchi o'rgatgan so'zlar jadvali.

    Foydalanuvchi vazifa guruhini QO'LDA o'zgartirganda, platforma vazifa
    matnidagi so'zlarni shu jadvalga yozib qo'yadi. Keyingi safar o'sha so'z
    uchraydigan vazifa to'g'ri guruhga tushadi.

    Har bir yozuv faqat bitta foydalanuvchiga ta'sir qiladi.
    """

    id = db.Column(db.Integer, primary_key=True)

    # Qaysi foydalanuvchiga tegishli.
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # O'rgatilgan so'z (normalize qilingan ko'rinishda saqlanadi).
    word = db.Column(db.String(60), nullable=False)

    # Shu so'z qaysi guruhga tegishli ekani.
    category = db.Column(db.String(30), nullable=False)

    # Necha marta tasdiqlangani (ko'p bo'lsa — ishonch kuchliroq).
    hits = db.Column(db.Integer, nullable=False, default=1)

    # Oxirgi marta yangilangan vaqti.
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Bir foydalanuvchida bitta so'z faqat bir marta bo'lsin.
    __table_args__ = (
        db.UniqueConstraint("user_id", "word", name="uq_user_word"),
    )

    def __repr__(self):
        return f"<UserKeyword {self.word!r} -> {self.category} (x{self.hits})>"
