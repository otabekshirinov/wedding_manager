# app.py
from __future__ import annotations

import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, abort
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user

from models import db, Wedding, Expense, Guest, User

# блюпринты
from auth import auth_bp            # должен быть Blueprint('auth', __name__, url_prefix='/auth')
from admin import admin_bp          # например Blueprint('admin', __name__, url_prefix='/admin')
from svodnaya import svodnaya_bp
from tasks import tasks_bp
from finance import finance_bp
from invitations import invitations_bp
from wedding_pages import wedding_pages


# ----------------------------
# Инициализация приложения
# ----------------------------
app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///wedding.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.getenv("SECRET_KEY", "change-me-secret"),
)

db.init_app(app)
migrate = Migrate(app, db)

# ----------------------------
# Flask-Login
# ----------------------------
login_manager = LoginManager(app)
# NB: endpoint из блюпринта auth → 'auth.login', НЕ 'auth_bp.login'
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(uid: str):
    try:
        return User.query.get(int(uid))
    except Exception:
        return None


# ----------------------------
# Регистрация блюпринтов
# ----------------------------
# важно: сначала auth/admin, чтобы login_view/админ-страницы были доступны
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

app.register_blueprint(svodnaya_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(finance_bp)
app.register_blueprint(invitations_bp)
app.register_blueprint(wedding_pages)


# ----------------------------
# Хелперы и маршруты
# ----------------------------
def get_wedding_or_403(wedding_id: int) -> Wedding:
    """Проверка доступа: админ видит всё, пользователь — только свои свадьбы."""
    w = Wedding.query.get_or_404(wedding_id)
    if not current_user.is_authenticated:
        abort(401)
    if not current_user.is_admin and w.user_id != current_user.id:
        abort(403)
    return w


@app.route("/")
@login_required
def index():
    # админ — все свадьбы, пользователь — только свои
    q = Wedding.query
    if not current_user.is_admin:
        q = q.filter_by(user_id=current_user.id)
    # .nullslast() ок; для SQLite SQLAlchemy эмитит совместимый ORDER BY
    weddings = q.order_by(Wedding.date.desc().nullslast()).all()
    return render_template("index.html", weddings=weddings)


@app.route("/wedding/create", methods=["POST"])
@login_required
def create_wedding():
    name = request.form.get("name", "").strip()
    date_raw = request.form.get("date") or ""
    dt = None
    if date_raw:
        try:
            dt = datetime.strptime(date_raw, "%Y-%m-%d")
        except ValueError:
            dt = None

    wedding = Wedding(name=name, date=dt, user_id=current_user.id)
    db.session.add(wedding)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/wedding/<int:wedding_id>")
@login_required
def view_wedding(wedding_id: int):
    wedding = get_wedding_or_403(wedding_id)
    # если у тебя есть специальный шаблон-хаб, оставь его
    # иначе временно используем overview
    return render_template("wedding_overview.html", wedding=wedding)


# ----------------------------
# Инициализация БД и сид-админа
# ----------------------------
def ensure_db_and_seed_admin():
    """Создаёт таблицы и пользователя-админа, если ещё нет."""
    db.create_all()  # создаст отсутствующие таблицы; существующие не тронет

    admin_email = os.getenv("ADMIN_EMAIL", "admin@weddings.local")
    admin_pass  = os.getenv("ADMIN_PASSWORD", "admin123")

    u = User.query.filter_by(email=admin_email).first()
    if not u:
        u = User(email=admin_email, name="Админ", is_admin=True)
        u.set_password(admin_pass)
        db.session.add(u)
        db.session.commit()
        print(f"[init] Создан админ: {admin_email} / {admin_pass}")
    else:
        # на всякий случай можно обновить пароль, если надо
        # u.set_password(admin_pass); db.session.commit()
        pass


# ----------------------------
# Точка входа
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        ensure_db_and_seed_admin()

    # порт по умолчанию 5000, debug по желанию
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
