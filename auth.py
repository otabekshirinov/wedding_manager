# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        name = (request.form.get('name') or '').strip()
        password = request.form.get('password') or ''
        if not email or not password:
            flash('Введите email и пароль', 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Такой email уже зарегистрирован', 'error')
            return redirect(url_for('auth.register'))

        u = User(email=email, name=name)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash('Успешная регистрация! Теперь войдите', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth_register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(password):
            flash('Неверный email или пароль', 'error')
            return redirect(url_for('auth.login'))
        login_user(u)
        return redirect(url_for('index'))
    return render_template('auth_login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
