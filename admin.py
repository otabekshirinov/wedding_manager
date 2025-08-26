# admin.py
from functools import wraps
from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required
from models import User, Wedding

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            abort(403)
        return f(*args, **kwargs)
    return wrap

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    # Пользователи + количество свадеб
    rows = (
        User.query
        .order_by(User.id.asc())
        .all()
    )
    # В шаблоне посчитаем weddings|length
    return render_template('admin_users.html', users=rows)
