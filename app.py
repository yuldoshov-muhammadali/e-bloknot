"""
app.py — E-Bloknot dasturining asosiy fayli.

Bu yerda:
  - dastur (Flask) sozlanadi,
  - ma'lumotlar bazasi ulanadi,
  - sahifalar (route) yoziladi: /register, /login, /logout, / (bosh sahifa).

Dasturni ishga tushirish uchun terminalda: python app.py
"""

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo  # vaqt zonasi (Asia/Tashkent) uchun

import click
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_migrate import Migrate
from flask_wtf import CSRFProtect

from categories import (
    CATEGORIES,
    classify,
    extract_words,
    get_category,
    is_valid_category,
    split_tasks,
)
import reports
from models import Task, User, UserKeyword, db

# O'zbekiston vaqt zonasi — "bugun" shunga qarab hisoblanadi.
TOSHKENT = ZoneInfo("Asia/Tashkent")

# O'zbekcha nomlar va vaqt matni — reports moduldan (takrorlamaslik uchun).
OYLAR = reports.OYLAR
HAFTA_KUNLARI = reports.HAFTA_KUNLARI
daqiqa_matni = reports.daqiqa_matni

# Bir vaqtda qancha vazifa / kun ko'rsatiladi degan cheklovlar.
KECHIKKAN_KUNLAR = 14   # ko'chirish uchun faqat oxirgi 14 kunga qaraymiz
MAX_DAQIQA = 1440       # bir vazifaga maksimal vaqt (24 soat)


def bugungi_sana():
    """Toshkent vaqti bo'yicha bugungi sanani (Date) qaytaradi."""
    return datetime.now(TOSHKENT).date()


def sanani_chiqar(sana):
    """Sanani o'zbekcha matnga aylantiradi, masalan: 23-noyabr 2026-yil."""
    return f"{sana.day}-{OYLAR[sana.month - 1]} {sana.year}-yil"


def kun_sarlavhasi(sana):
    """Sana + hafta kuni, masalan: 23-noyabr, dushanba."""
    return f"{sana.day}-{OYLAR[sana.month - 1]}, {HAFTA_KUNLARI[sana.weekday()]}"


def sanani_oqi(matn, zaxira):
    """URL dagi 'date' ni (YYYY-MM-DD) Date ga aylantiradi, xato bo'lsa zaxira."""
    if not matn:
        return zaxira
    try:
        return date.fromisoformat(matn)
    except (ValueError, TypeError):
        return zaxira


# =========================================================
#   O'RGANISH BILAN BOG'LIQ YORDAMCHI FUNKSIYALAR
# =========================================================


def foydalanuvchi_sozlari(user_id):
    """Foydalanuvchi o'rgatgan so'zlarni {so'z: guruh} lug'ati qilib qaytaradi.

    Bu lug'at classify() ga beriladi — shunda foydalanuvchining tuzatishlari
    hisobga olinadi.
    """
    yozuvlar = UserKeyword.query.filter_by(user_id=user_id).all()
    return {y.word: y.category for y in yozuvlar}


def vazifadan_organ(user_id, title, yangi_guruh):
    """Foydalanuvchi vazifa guruhini qo'lda o'zgartirganda chaqiriladi.

    Vazifa matnidagi (stopword bo'lmagan, 3 harfdan uzun) so'zlarni oladi va
    har birini UserKeyword jadvaliga yozadi:
      - so'z yo'q bo'lsa — yangi yozuv (hits=1);
      - bor bo'lib, guruhi bir xil bo'lsa — hits +1;
      - bor bo'lib, guruhi boshqa bo'lsa — yangi guruhga almashtiriladi, hits=1.
    """
    for so_z in extract_words(title):
        yozuv = UserKeyword.query.filter_by(user_id=user_id, word=so_z).first()

        if yozuv is None:
            # Bu so'z birinchi marta uchrayapti — yangi yozuv yaratamiz.
            yozuv = UserKeyword(
                user_id=user_id, word=so_z, category=yangi_guruh, hits=1
            )
            db.session.add(yozuv)
        elif yozuv.category == yangi_guruh:
            # Avvalgi o'rganish tasdiqlandi — ishonchni oshiramiz.
            yozuv.hits += 1
            yozuv.updated_at = datetime.utcnow()
        else:
            # Foydalanuvchi fikrini o'zgartirdi — yangi guruhga o'tkazamiz.
            yozuv.category = yangi_guruh
            yozuv.hits = 1
            yozuv.updated_at = datetime.utcnow()

# .env faylidagi maxfiy sozlamalarni (SECRET_KEY va h.k.) o'qib olamiz.
load_dotenv()

# APP_ENV: "production" bo'lsa — internetdagi (jonli) rejim, aks holda lokal.
APP_ENV = os.environ.get("APP_ENV", "development")
IS_PRODUCTION = APP_ENV == "production"
# Testlar paytida APP_ENV=testing bo'ladi (CSRF o'chiriladi).
IS_TESTING = APP_ENV == "testing"

# Flask dasturini yaratamiz.
app = Flask(__name__)

# --- Sozlamalar ---

# SECRET_KEY — sessiyalarni himoyalash uchun maxfiy kalit.
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    if IS_PRODUCTION:
        # Production'da maxfiy kalitsiz ishga tushmaymiz (xavfsizlik).
        raise RuntimeError(
            "SECRET_KEY o'rnatilmagan! Production'da ishlash uchun SECRET_KEY "
            "muhit o'zgaruvchisini o'rnating. Yaratish: "
            "python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    # Lokal ishlab chiqishda vaqtinchalik kalit (xavfsiz emas, faqat sinash uchun).
    secret_key = "vaqtinchalik-maxfiy-kalit-faqat-lokal-uchun"
app.config["SECRET_KEY"] = secret_key

# Ma'lumotlar bazasi manzili.
# DATABASE_URL bo'lsa — o'shani (masalan, Railway PostgreSQL), bo'lmasa — SQLite.
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Railway ba'zan "postgres://" beradi, SQLAlchemy esa "postgresql://" kutadi.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///e_bloknot.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --- Cookie (sessiya) xavfsizligi ---
app.config["SESSION_COOKIE_HTTPONLY"] = True   # JavaScript cookie'ni o'qiy olmaydi
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # boshqa saytdan yuborishni cheklaydi
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)  # "meni eslab qol" 30 kun
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
# Faqat production'da (HTTPS) cookie'ni xavfsiz qilamiz. Lokalda (http) o'chiq,
# aks holda brauzer cookie'ni yubormaydi va kira olmaysiz.
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION
app.config["REMEMBER_COOKIE_SECURE"] = IS_PRODUCTION

# Testlar paytida CSRF ni o'chiramiz (test mijozida token yuborish shart emas).
app.config["WTF_CSRF_ENABLED"] = not IS_TESTING

# Ma'lumotlar bazasini dasturga bog'laymiz.
db.init_app(app)

# Flask-Migrate — ma'lumotlar bazasi jadvallari o'zgarsa, ma'lumot o'chmasligi
# uchun migratsiyalar orqali yangilaymiz.
migrate = Migrate(app, db)

# CSRF himoyasi — forma va fetch so'rovlarini soxtalashtirishdan saqlaydi.
csrf = CSRFProtect(app)

# --- Flask-Login sozlamalari (kirish/chiqish tizimi) ---

login_manager = LoginManager()
login_manager.init_app(app)

# Kirish talab qilinadigan sahifaga kirmagan odam kelsa, uni shu sahifaga yuboradi.
login_manager.login_view = "login"
# Login sahifasiga yuborilganda chiqadigan xabar (o'zbek tilida).
login_manager.login_message = "Bu sahifani ko'rish uchun avval tizimga kiring."


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login foydalanuvchini id orqali topib beradi."""
    return db.session.get(User, int(user_id))


# Guruhlar ro'yxatining soddalashtirilgan (faqat id, emoji, nom) ko'rinishi —
# JavaScript va shablonlar uchun. (Kalit so'zlar bu yerda kerak emas.)
GURUHLAR_PUBLIC = [
    {"id": c["id"], "emoji": c["emoji"], "name": c["name"]} for c in CATEGORIES
]


@app.context_processor
def inject_categories():
    """Barcha shablonlarga guruhlar ro'yxatini (chip tanlash uchun) uzatadi."""
    return {"all_categories": GURUHLAR_PUBLIC}


# =========================================================
#   LOGIN HIMOYASI (oddiy, xotiradagi rate limit)
# =========================================================
# Bitta IP dan 5 daqiqada 10 tadan ortiq NOTO'G'RI urinish bo'lsa, vaqtincha
# bloklaymiz. Oddiy yechim: xotirada saqlanadi (server qayta ishga tushsa
# tozalanadi). Bu ~100 kishilik kichik loyiha uchun yetarli.

LOGIN_OYNA = timedelta(minutes=5)   # necha vaqt ichida sanaymiz
LOGIN_URINISH_CHEGARA = 10          # shunchadan ko'p noto'g'ri urinish — blok

# {ip: [urinish vaqtlari]}
_login_urinishlar = {}


def _login_bloklanganmi(ip):
    """Shu IP hozir bloklanganmi (oxirgi 5 daqiqadagi noto'g'ri urinishlar soni)."""
    hozir = datetime.utcnow()
    urinishlar = [t for t in _login_urinishlar.get(ip, []) if hozir - t < LOGIN_OYNA]
    _login_urinishlar[ip] = urinishlar
    return len(urinishlar) >= LOGIN_URINISH_CHEGARA


def _login_xato_qayd(ip):
    """Noto'g'ri urinishni qayd etadi."""
    _login_urinishlar.setdefault(ip, []).append(datetime.utcnow())


def _login_tozala(ip):
    """Muvaffaqiyatli kirgandan keyin hisobni tozalaymiz."""
    _login_urinishlar.pop(ip, None)


@app.route("/health")
def health():
    """Oddiy "tirikman" tekshiruvi (Railway va monitoring uchun)."""
    return jsonify({"status": "ok"})


@app.route("/sw.js")
def service_worker():
    """Service worker faylini ildizdan beradi (butun sayt bo'yicha ishlashi uchun)."""
    resp = app.send_static_file("sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


# =========================================================
#   KUN KO'RINISHI UCHUN YORDAMCHI FUNKSIYALAR
# =========================================================

# Kunlik ro'yxatda ko'rinadigan statuslar (ko'chirilgan "moved" va voz
# kechilgan "dropped" vazifalar kunlik ro'yxatda ko'rsatilmaydi).
KORINADIGAN_STATUS = ["todo", "done", "failed"]


def _vazifa_korinishi(t, bugun):
    """Bitta vazifani shablon uchun qulay lug'atga aylantiradi."""
    return {
        "id": t.id,
        "title": t.title,
        "category": t.category,
        "status": t.status,
        "reason": t.reason or "",
        "minutes": t.minutes or 0,
        "moved_count": t.moved_count or 0,
        # Vazifa birinchi yozilganidan beri necha kun o'tgani.
        "days_since": (bugun - t.first_date).days if t.first_date else 0,
    }


def kun_konteksti(user_id, tanlangan, bugun):
    """Tanlangan kun uchun shablonga kerakli hamma ma'lumotni tayyorlaydi."""

    vazifalar = (
        Task.query.filter(
            Task.user_id == user_id,
            Task.plan_date == tanlangan,
            Task.status.in_(KORINADIGAN_STATUS),
        )
        .order_by(Task.id)
        .all()
    )

    # Guruhlar bo'yicha ajratamiz (va har guruhda bajarilganini sanaymiz).
    guruhlar = []
    for cat in CATEGORIES:
        shular = [t for t in vazifalar if t.category == cat["id"]]
        if shular:
            guruhlar.append({
                "emoji": cat["emoji"],
                "name": cat["name"],
                "total": len(shular),
                "done": sum(1 for t in shular if t.status == "done"),
                "tasks": [_vazifa_korinishi(t, bugun) for t in shular],
            })

    # Kun xulosasi.
    jami = len(vazifalar)
    bajarildi = sum(1 for t in vazifalar if t.status == "done")
    bajarilmadi = sum(1 for t in vazifalar if t.status == "failed")
    qolgan = sum(1 for t in vazifalar if t.status == "todo")
    daqiqalar = sum((t.minutes or 0) for t in vazifalar)
    foiz = round(bajarildi / jami * 100) if jami else 0

    xulosa = {
        "jami": jami,
        "bajarildi": bajarildi,
        "bajarilmadi": bajarilmadi,
        "qolgan": qolgan,
        "foiz": foiz,
        "vaqt_matni": daqiqa_matni(daqiqalar),
        # Hamma vazifa belgilangan bo'lsa (todo qolmasa) — kun yakunlandi.
        "yakunlandi": jami > 0 and qolgan == 0,
    }

    # Kechikkan (bajarilmay qolgan va hali ko'chirilmagan) vazifalar —
    # faqat bugungi kunda ko'rsatiladi.
    kechikkanlar = []
    if tanlangan == bugun:
        kechikkanlar = kechikkan_vazifalar(user_id, bugun)

    return {
        "tanlangan": tanlangan,
        "tanlangan_iso": tanlangan.isoformat(),
        "kun_sarlavha": kun_sarlavhasi(tanlangan),
        "oldingi_iso": (tanlangan - timedelta(days=1)).isoformat(),
        "keyingi_iso": (tanlangan + timedelta(days=1)).isoformat(),
        "ertaga_iso": (tanlangan + timedelta(days=1)).isoformat(),
        "bugunmi": tanlangan == bugun,
        "bugun_iso": bugun.isoformat(),
        "guruhlar": guruhlar,
        "xulosa": xulosa,
        "kechikkanlar": kechikkanlar,
    }


def kechikkan_vazifalar(user_id, bugun):
    """Oldingi kunlardan bajarilmay, hali ko'chirilmagan vazifalar ro'yxati.

    Shartlar: plan_date < bugun, status "todo" yoki "failed", oxirgi 14 kun
    ichida, va shu root_id da undan keyingi sanada nusxa YO'Q (ya'ni hali
    ko'chirilmagan).
    """
    boshlanish = bugun - timedelta(days=KECHIKKAN_KUNLAR)

    nomzodlar = (
        Task.query.filter(
            Task.user_id == user_id,
            Task.plan_date < bugun,
            Task.plan_date >= boshlanish,
            Task.status.in_(["todo", "failed"]),
        )
        .order_by(Task.plan_date)
        .all()
    )

    natija = []
    for t in nomzodlar:
        # Shu zanjirda (root_id) undan keyingi sanada nusxa bormi?
        keyingi = Task.query.filter(
            Task.user_id == user_id,
            Task.root_id == t.root_id,
            Task.plan_date > t.plan_date,
        ).first()

        if keyingi is None:  # hali ko'chirilmagan
            cat = get_category(t.category)
            natija.append({
                "id": t.id,
                "title": t.title,
                "emoji": cat["emoji"],
                "name": cat["name"],
                "days_ago": (bugun - t.plan_date).days,
            })

    return natija


def vazifani_kochir(task, maqsad_sana):
    """Vazifani boshqa kunga ko'chiradi (yangi nusxa yaratadi).

    Qaytaradi: True — ko'chirildi; False — allaqachon ko'chirilgan edi.
    """
    # Agar shu zanjirda keyingi sanada nusxa bo'lsa — ikki marta ko'chirmaymiz.
    keyingi = Task.query.filter(
        Task.user_id == task.user_id,
        Task.root_id == task.root_id,
        Task.plan_date > task.plan_date,
    ).first()
    if keyingi is not None:
        return False

    # Yangi nusxa: first_date va root_id ASLINIKIDAN olinadi.
    nusxa = Task(
        user_id=task.user_id,
        title=task.title,
        category=task.category,
        plan_date=maqsad_sana,
        status="todo",
        first_date=task.first_date,
        root_id=task.root_id,
        moved_count=(task.moved_count or 0) + 1,
        minutes=0,
    )
    db.session.add(nusxa)

    # Asl vazifa: "todo" bo'lsa → "moved"; "failed" bo'lsa → "failed" qoladi.
    if task.status == "todo":
        task.status = "moved"

    db.session.commit()
    return True


# =========================================================
#                      SAHIFALAR (ROUTES)
# =========================================================


@app.route("/register", methods=["GET", "POST"])
def register():
    """Ro'yxatdan o'tish sahifasi."""

    # Agar foydalanuvchi allaqachon kirgan bo'lsa, bosh sahifaga yuboramiz.
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    # Agar forma yuborilgan bo'lsa (POST), ma'lumotlarni tekshiramiz.
    if request.method == "POST":
        # Formadan kelgan ma'lumotlarni olamiz (bo'sh joylarni tozalaymiz).
        full_name = request.form.get("full_name", "").strip()
        group_name = request.form.get("group_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        # --- Tekshiruvlar ---

        # 1) Hamma maydon to'ldirilganmi?
        if not full_name or not group_name or not username or not password:
            flash("Iltimos, barcha maydonlarni to'ldiring.", "error")
            return render_template("register.html")

        # 2) Parol kamida 6 ta belgidanmi?
        if len(password) < 6:
            flash("Parol kamida 6 ta belgidan iborat bo'lishi kerak.", "error")
            return render_template("register.html")

        # 3) Ikkala parol mos keladimi?
        if password != password2:
            flash("Parollar bir-biriga mos kelmadi.", "error")
            return render_template("register.html")

        # 4) Bu login band emasmi?
        mavjud = User.query.filter_by(username=username).first()
        if mavjud:
            flash("Bu login band. Boshqa login tanlang.", "error")
            return render_template("register.html")

        # --- Hammasi joyida: yangi foydalanuvchi yaratamiz ---
        yangi_user = User(
            full_name=full_name,
            group_name=group_name,
            username=username,
        )
        yangi_user.set_password(password)  # parol xeshlanadi

        db.session.add(yangi_user)
        db.session.commit()

        flash("Ro'yxatdan muvaffaqiyatli o'tdingiz! Endi tizimga kiring.", "success")
        return redirect(url_for("login"))

    # Agar oddiy ochilgan bo'lsa (GET), bo'sh formani ko'rsatamiz.
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Tizimga kirish sahifasi."""

    if current_user.is_authenticated:
        return redirect(url_for("index"))

    ip = request.remote_addr or "nomalum"

    if request.method == "POST":
        # Juda ko'p noto'g'ri urinish bo'lsa — vaqtincha bloklaymiz.
        if _login_bloklanganmi(ip):
            flash(
                "Juda ko'p noto'g'ri urinish. Iltimos, 5 daqiqadan so'ng qayta urinib ko'ring.",
                "error",
            )
            return render_template("login.html"), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Foydalanuvchini login orqali topamiz.
        user = User.query.filter_by(username=username).first()

        # Foydalanuvchi topilmasa YOKI parol xato bo'lsa — bir xil xabar.
        # (Xavfsizlik uchun "login xato" yoki "parol xato" deb aniq aytmaymiz.)
        if user is None or not user.check_password(password):
            _login_xato_qayd(ip)  # noto'g'ri urinishni qayd etamiz
            flash("Login yoki parol xato.", "error")
            return render_template("login.html")

        # Hammasi to'g'ri — bloklash hisobini tozalab, tizimga kiritamiz.
        _login_tozala(ip)
        login_user(user, remember=True)  # "meni eslab qol" (30 kun)
        flash(f"Xush kelibsiz, {user.full_name}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
@login_required  # faqat kirgan odam chiqa oladi
def logout():
    """Tizimdan chiqish."""
    logout_user()
    flash("Tizimdan chiqdingiz.", "success")
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required  # faqat kirgan odam bosh sahifani ko'radi
def index():
    """Bosh sahifa — tanlangan kun. Vazifa qo'shish va ko'rsatish."""

    bugun = bugungi_sana()
    # URL dagi ?date=YYYY-MM-DD ni o'qiymiz, bo'lmasa bugun.
    tanlangan = sanani_oqi(request.args.get("date"), bugun)

    # --- Vazifa qo'shish (forma yuborilganda) ---
    if request.method == "POST":
        matn = request.form.get("kunlik_matn", "")

        # Vazifa TANLANGAN kunga yoziladi (ertangi kunga ham reja mumkin).
        vazifalar = split_tasks(matn)
        organilgan = foydalanuvchi_sozlari(current_user.id)

        qoshildi = 0
        for vazifa_matni in vazifalar:
            guruh = classify(vazifa_matni, organilgan)

            yangi = Task(
                user_id=current_user.id,
                title=vazifa_matni,
                category=guruh,
                plan_date=tanlangan,
                first_date=tanlangan,  # birinchi marta shu kuni yozildi
                status="todo",
            )
            db.session.add(yangi)
            db.session.flush()  # id paydo bo'lishi uchun
            yangi.root_id = yangi.id  # yangi vazifada root_id = o'z id si
            qoshildi += 1

        db.session.commit()

        if qoshildi:
            flash(f"{qoshildi} ta vazifa qo'shildi.", "success")
        else:
            flash("Hech qanday vazifa topilmadi. Qaytadan yozib ko'ring.", "error")

        # PRG: tanlangan kunni saqlab qolgan holda qayta yo'naltiramiz.
        return redirect(url_for("index", date=tanlangan.isoformat()))

    # --- Tanlangan kunni ko'rsatish (GET) ---
    ctx = kun_konteksti(current_user.id, tanlangan, bugun)
    return render_template("index.html", **ctx)


@app.route("/fragment")
@login_required
def fragment():
    """Kun mazmunining HTML bo'lagi (JavaScript sahifani qayta chizishi uchun)."""
    bugun = bugungi_sana()
    tanlangan = sanani_oqi(request.args.get("date"), bugun)
    ctx = kun_konteksti(current_user.id, tanlangan, bugun)
    return render_template("_day_content.html", **ctx)


# =========================================================
#                   API ENDPOINTLAR (JSON)
# =========================================================
# Bular sahifani qayta yuklamasdan ishlaydi (JavaScript fetch orqali chaqiriladi).


def _oz_vazifasi(task_id):
    """Faqat JORIY foydalanuvchining vazifasini qaytaradi, bo'lmasa 404.

    Bu — xavfsizlik: birov boshqa odamning vazifa id sini yuborsa, topilmaydi.
    """
    vazifa = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if vazifa is None:
        abort(404)
    return vazifa


@app.route("/api/task/<int:task_id>/category", methods=["POST"])
@login_required
def api_task_category(task_id):
    """Vazifa guruhini o'zgartiradi va foydalanuvchidan O'RGANADI."""
    vazifa = _oz_vazifasi(task_id)

    data = request.get_json(silent=True) or {}
    yangi_guruh = (data.get("category") or "").strip()

    # Guruh haqiqiy (ro'yxatda bor) bo'lishi kerak.
    if not is_valid_category(yangi_guruh):
        return jsonify({"ok": False, "error": "Noto'g'ri guruh"}), 400

    # Guruh haqiqatan o'zgarayotgan bo'lsagina o'rganamiz.
    if vazifa.category != yangi_guruh:
        vazifadan_organ(current_user.id, vazifa.title, yangi_guruh)
        vazifa.category = yangi_guruh
        db.session.commit()

    return jsonify({"ok": True, "category": yangi_guruh})


@app.route("/api/task/<int:task_id>/edit", methods=["POST"])
@login_required
def api_task_edit(task_id):
    """Vazifa matnini o'zgartiradi. Guruh O'ZGARMAYDI (foydalanuvchi tanlovi muhim)."""
    vazifa = _oz_vazifasi(task_id)

    data = request.get_json(silent=True) or {}
    yangi_matn = (data.get("title") or "").strip()

    if len(yangi_matn) < 2:
        return jsonify({"ok": False, "error": "Matn juda qisqa"}), 400

    vazifa.title = yangi_matn
    db.session.commit()

    return jsonify({"ok": True, "title": vazifa.title})


@app.route("/api/task/<int:task_id>/delete", methods=["POST"])
@login_required
def api_task_delete(task_id):
    """Vazifani o'chiradi."""
    vazifa = _oz_vazifasi(task_id)
    db.session.delete(vazifa)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/task/<int:task_id>/status", methods=["POST"])
@login_required
def api_task_status(task_id):
    """Vazifani belgilash: done (bajarildi), failed (bajarolmadim), todo (bekor)."""
    vazifa = _oz_vazifasi(task_id)

    data = request.get_json(silent=True) or {}
    yangi_status = (data.get("status") or "").strip()

    if yangi_status == "done":
        vazifa.status = "done"
        vazifa.done_at = datetime.utcnow()
        vazifa.reason = None
    elif yangi_status == "failed":
        vazifa.status = "failed"
        vazifa.reason = (data.get("reason") or "").strip() or None
        vazifa.done_at = None
    elif yangi_status == "todo":
        # "Bekor qilish" — hamma belgini tozalaymiz.
        vazifa.status = "todo"
        vazifa.reason = None
        vazifa.done_at = None
    else:
        return jsonify({"ok": False, "error": "Noto'g'ri status"}), 400

    db.session.commit()
    return jsonify({"ok": True, "status": vazifa.status})


@app.route("/api/task/<int:task_id>/minutes", methods=["POST"])
@login_required
def api_task_minutes(task_id):
    """Vazifaga sarflangan vaqtni (daqiqa) qo'shadi yoki o'rnatadi.

    mode="add" — mavjud vaqtga qo'shadi (taymerdan keladi);
    mode="set" — vaqtni to'g'ridan-to'g'ri o'rnatadi (qo'lda kiritish).
    0–1440 oralig'idan tashqari qiymatlar rad etiladi.
    """
    vazifa = _oz_vazifasi(task_id)

    data = request.get_json(silent=True) or {}
    rejim = data.get("mode", "set")

    # Qiymat butun son bo'lishi kerak.
    try:
        qiymat = int(data.get("value"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Noto'g'ri qiymat"}), 400

    if rejim == "add":
        yangi = (vazifa.minutes or 0) + qiymat
    else:  # "set"
        yangi = qiymat

    # 0–1440 oralig'ida bo'lishi shart.
    if yangi < 0 or yangi > MAX_DAQIQA:
        return jsonify({"ok": False, "error": "Vaqt 0–1440 daqiqa oralig'ida bo'lsin"}), 400

    vazifa.minutes = yangi
    db.session.commit()
    return jsonify({"ok": True, "minutes": vazifa.minutes})


@app.route("/api/task/<int:task_id>/move", methods=["POST"])
@login_required
def api_task_move(task_id):
    """Vazifani boshqa kunga ko'chiradi (yangi nusxa yaratadi)."""
    vazifa = _oz_vazifasi(task_id)

    data = request.get_json(silent=True) or {}
    maqsad = sanani_oqi(data.get("date"), None)
    if maqsad is None:
        return jsonify({"ok": False, "error": "Noto'g'ri sana"}), 400

    kochdi = vazifani_kochir(vazifa, maqsad)
    if not kochdi:
        return jsonify({"ok": False, "error": "Bu vazifa allaqachon ko'chirilgan"}), 400

    return jsonify({"ok": True})


@app.route("/api/task/<int:task_id>/drop", methods=["POST"])
@login_required
def api_task_drop(task_id):
    """Vazifadan voz kechish (status = dropped)."""
    vazifa = _oz_vazifasi(task_id)
    vazifa.status = "dropped"
    db.session.commit()
    return jsonify({"ok": True})


# =========================================================
#              SOZLAMALAR — "O'rgangan so'zlarim"
# =========================================================


@app.route("/settings")
@login_required
def settings():
    """Platforma o'rgangan so'zlar ro'yxati sahifasi."""
    sozlar = (
        UserKeyword.query.filter_by(user_id=current_user.id)
        .order_by(UserKeyword.updated_at.desc())
        .all()
    )

    # Har bir so'zga guruh ma'lumotini (emoji + nom) qo'shamiz.
    royxat = []
    for s in sozlar:
        cat = get_category(s.category)
        royxat.append({
            "id": s.id,
            "word": s.word,
            "category": s.category,
            "emoji": cat["emoji"],
            "name": cat["name"],
            "hits": s.hits,
        })

    return render_template("settings.html", sozlar=royxat)


def _oz_sozim(kw_id):
    """Faqat joriy foydalanuvchining o'rgatgan so'zini qaytaradi, bo'lmasa 404."""
    yozuv = UserKeyword.query.filter_by(id=kw_id, user_id=current_user.id).first()
    if yozuv is None:
        abort(404)
    return yozuv


@app.route("/api/keyword/<int:kw_id>/category", methods=["POST"])
@login_required
def api_keyword_category(kw_id):
    """O'rgatilgan so'zning guruhini o'zgartiradi (noto'g'ri o'rganib qolgan bo'lsa)."""
    yozuv = _oz_sozim(kw_id)

    data = request.get_json(silent=True) or {}
    yangi_guruh = (data.get("category") or "").strip()

    if not is_valid_category(yangi_guruh):
        return jsonify({"ok": False, "error": "Noto'g'ri guruh"}), 400

    yozuv.category = yangi_guruh
    yozuv.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"ok": True, "category": yangi_guruh})


@app.route("/api/keyword/<int:kw_id>/delete", methods=["POST"])
@login_required
def api_keyword_delete(kw_id):
    """O'rgatilgan so'zni o'chiradi."""
    yozuv = _oz_sozim(kw_id)
    db.session.delete(yozuv)
    db.session.commit()
    return jsonify({"ok": True})


# =========================================================
#                      HISOBOT SAHIFASI
# =========================================================


def _davr_vazifalari(user_id, boshi, oxiri):
    """Berilgan oraliqdagi vazifalarni bitta so'rov bilan oladi (tezlik)."""
    return (
        Task.query.filter(
            Task.user_id == user_id,
            Task.plan_date >= boshi,
            Task.plan_date <= oxiri,
        )
        .order_by(Task.plan_date, Task.id)
        .all()
    )


@app.route("/report")
@login_required
def report():
    """Hisobot sahifasi — hafta yoki oy bo'yicha statistika."""
    bugun = bugungi_sana()

    # Davr turi (week/month) va sana.
    period = request.args.get("period", "week")
    if period not in ("week", "month"):
        period = "week"
    ref = sanani_oqi(request.args.get("date"), bugun)
    # Kelajakka o'tib bo'lmaydi.
    if ref > bugun:
        ref = bugun

    boshi, oxiri = reports.davr_oraligi(period, ref)

    # Davr vazifalari (bitta so'rov).
    tasks = _davr_vazifalari(current_user.id, boshi, oxiri)

    # Oldingi davr (solishtirish uchun, bitta so'rov).
    old_boshi, old_oxiri = reports.oldingi_davr(period, boshi)
    old_tasks = _davr_vazifalari(current_user.id, old_boshi, old_oxiri)

    # Uzoq kutayotganlar uchun — foydalanuvchining BARCHA vazifalari (bitta so'rov).
    barcha = Task.query.filter_by(user_id=current_user.id).all()

    # --- Hisoblashlar (hammasi reports.py da) ---
    joriy = reports.bajarilish(tasks, bugun)
    oldingi = reports.bajarilish(old_tasks, bugun)
    taqqos = reports.solishtirish(joriy, oldingi)

    grafik = reports.kunlik_grafik(tasks, boshi, oxiri, bugun)
    vaqt_qatorlar, jami_vaqt = reports.vaqt_guruhlar(tasks, bugun)
    kutayotganlar = reports.uzoq_kutayotganlar(barcha, bugun)
    sabab_qatorlar = reports.sabablar(tasks)
    xulosa = reports.xulosa_jumlalari(
        grafik, vaqt_qatorlar, tasks, bugun, taqqos, period
    )

    # Oldingi davrdagi vaqt (jami vaqt kartasi solishtiruvi uchun).
    vaqt_delta = None
    if oldingi["jami"] > 0:
        vaqt_delta = joriy["daqiqa"] - oldingi["daqiqa"]

    # Navigatsiya: oldingi/keyingi davr sanasi.
    oldingi_ref = (boshi - timedelta(days=1)).isoformat()
    keyingi_ref = (oxiri + timedelta(days=1)).isoformat()
    # Keyingi davrga faqat u kelajakda bo'lmasa o'tish mumkin.
    keyingi_mumkin = oxiri < bugun

    return render_template(
        "report.html",
        period=period,
        sarlavha=reports.davr_sarlavhasi(period, boshi, oxiri),
        oldingi_ref=oldingi_ref,
        keyingi_ref=keyingi_ref,
        keyingi_mumkin=keyingi_mumkin,
        joriy=joriy,
        taqqos=taqqos,
        vaqt_delta=vaqt_delta,
        vaqt_delta_matni=(daqiqa_matni(abs(vaqt_delta)) if vaqt_delta else None),
        grafik=grafik,
        vaqt_qatorlar=vaqt_qatorlar,
        jami_vaqt=jami_vaqt,
        kutayotganlar=kutayotganlar,
        sabab_qatorlar=sabab_qatorlar,
        xulosa=xulosa,
        bugun_iso=bugun.isoformat(),
    )


# =========================================================
#              DEMO MA'LUMOT (faqat sinash uchun)
# =========================================================


@app.cli.command("seed-demo")
@click.argument("username")
def seed_demo_command(username):
    """Berilgan foydalanuvchiga oxirgi 30 kun uchun demo vazifalar yaratadi.

    Ishlatish:  flask seed-demo <login>
    Masalan:    flask seed-demo ali
    """
    _seed_demo(username)


def _seed_demo(username):
    """Demo ma'lumot yaratish (CLI va test uchun umumiy)."""
    import random

    # Production'da demo ma'lumot yaratish TAQIQLANADI.
    if IS_PRODUCTION:
        click.echo("Xatolik: 'seed-demo' production rejimida ishlamaydi.")
        return

    user = User.query.filter_by(username=username).first()
    if user is None:
        click.echo(f"Xatolik: '{username}' foydalanuvchi topilmadi.")
        return

    bugun = bugungi_sana()

    # Har guruh uchun real ko'rinadigan vazifa namunalari.
    namunalar = {
        "til": ["Ingliz tilidan writing yozish", "IELTS listening mashqi", "50 ta vocabulary yodlash"],
        "dastur": ["Python loyiha ustida ishlash", "Flask API yozish", "GitHub ga kod yuklash", "Udemy kursini ko'rish"],
        "oqish": ["Kursovoy ishni yozish", "Huquq fanidan konspekt", "Imtihonga tayyorlanish", "Referat tayyorlash"],
        "kitob": ["Kitob o'qish (50 sahifa)", "Audiokitob eshitish"],
        "sport": ["3 km yugurish", "Turnikda mashq", "Zalda trenirovka"],
        "xizmat": ["Naryadga tayyorlanish", "Saf tayyorgarligi"],
        "maishiy": ["Formani dazmollash", "Kir yuvish", "Xonani yig'ishtirish"],
        "oila": ["Onamga qo'ng'iroq qilish", "Oila bilan vaqt"],
        "moliya": ["Stipendiyani rejalashtirish", "Xarajatlarni hisoblash"],
        "dam": ["Namoz o'qish", "Meditatsiya qilish", "Kino ko'rish"],
    }
    sabablar = ["Vaqt yetmadi", "Dangasalik qildim", "Chalg'idim (telefon)", "Kutilmagan ish chiqdi", ""]

    random.seed(42)  # takrorlanadigan demo
    yaratildi = 0

    # Oxirgi 30 kun uchun vazifalar.
    for ofset in range(30, -1, -1):
        kun = bugun - timedelta(days=ofset)
        soni = random.randint(2, 6)
        for _ in range(soni):
            guruh = random.choice(list(namunalar.keys()))
            title = random.choice(namunalar[guruh])

            if ofset == 0:
                # Bugun — asosan todo.
                status = random.choice(["todo", "todo", "done"])
            else:
                status = random.choices(
                    ["done", "failed", "todo", "dropped"],
                    weights=[60, 22, 12, 6],
                )[0]

            minut = 0
            reason = None
            done_at = None
            if status == "done":
                minut = random.choice([0, 15, 25, 30, 45, 60, 90])
                done_at = datetime.utcnow()
            elif status == "failed":
                minut = random.choice([0, 10, 20])
                reason = random.choice(sabablar) or None

            t = Task(
                user_id=user.id, title=title, category=guruh,
                plan_date=kun, first_date=kun, status=status,
                minutes=minut, reason=reason, done_at=done_at,
            )
            db.session.add(t)
            db.session.flush()
            t.root_id = t.id
            yaratildi += 1

    db.session.commit()

    # Bir nechta ko'p marta ko'chirilgan zanjir (uzoq kutayotganlar uchun).
    for i in range(3):
        bosh_kun = bugun - timedelta(days=random.randint(8, 20))
        guruh = random.choice(list(namunalar.keys()))
        title = random.choice(namunalar[guruh])
        root = Task(
            user_id=user.id, title=title, category=guruh,
            plan_date=bosh_kun, first_date=bosh_kun, status="moved",
            minutes=0, moved_count=0,
        )
        db.session.add(root)
        db.session.flush()
        root.root_id = root.id
        root_id = root.id

        # 2–3 marta ko'chirilgan nusxalar.
        nusxa_soni = random.randint(2, 3)
        oxirgi_kun = bosh_kun
        for n in range(1, nusxa_soni + 1):
            oxirgi_kun = oxirgi_kun + timedelta(days=random.randint(1, 3))
            if oxirgi_kun > bugun:
                oxirgi_kun = bugun
            oxirgi = (n == nusxa_soni)
            nusxa = Task(
                user_id=user.id, title=title, category=guruh,
                plan_date=oxirgi_kun, first_date=bosh_kun, status=("todo" if oxirgi else "moved"),
                root_id=root_id, moved_count=n, minutes=0,
            )
            db.session.add(nusxa)
            yaratildi += 1

    db.session.commit()

    click.echo(f"Tayyor! '{username}' uchun {yaratildi} ta demo vazifa yaratildi.")


# Dasturni to'g'ridan-to'g'ri ishga tushirish (python app.py).
if __name__ == "__main__":
    # Dastur birinchi marta ishga tushganda ma'lumotlar bazasi jadvallarini yaratamiz.
    # (Production'da jadvallar migratsiyalar orqali yaratiladi — pastdagi README.)
    with app.app_context():
        db.create_all()

    # debug — faqat lokal (ishlab chiqish) rejimida yoqiladi, production'da O'CHIQ.
    app.run(debug=not IS_PRODUCTION)
