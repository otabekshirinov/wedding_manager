# svodnaya.py
from flask import Blueprint, render_template
from models import Wedding, Expense  # Импортируй из своей модели!
from sqlalchemy import func

svodnaya_bp = Blueprint('svodnaya_bp', __name__, url_prefix='/svodnaya')

@svodnaya_bp.route('/')
def svodnaya():
    # Для каждой свадьбы посчитать сумму расходов
    weddings = Wedding.query.all()
    wedding_data = []
    for w in weddings:
        total = sum(e.total or 0 for e in w.expenses)
        wedding_data.append({
            'id': w.id,
            'name': w.name,
            'date': w.date,
            'total': total
        })
    return render_template('svodnaya.html', weddings=wedding_data)
