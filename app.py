from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from models import db, Wedding, Expense, Guest
from svodnaya import svodnaya_bp
from tasks import tasks_bp
from finance import finance_bp
from flask_migrate import Migrate
from invitations import invitations_bp











app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wedding.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)


app.register_blueprint(svodnaya_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(finance_bp)
app.register_blueprint(invitations_bp)

@app.route('/')
def index():
    weddings = Wedding.query.order_by(Wedding.date.desc()).all()
    return render_template('index.html', weddings=weddings)

@app.route('/wedding/create', methods=['POST'])
def create_wedding():
    name = request.form['name']
    date = request.form['date']
    wedding = Wedding(name=name, date=datetime.strptime(date, '%Y-%m-%d') if date else None)
    db.session.add(wedding)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/wedding/<int:wedding_id>')
def view_wedding(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    return render_template('wedding_detail.html', wedding=wedding)

@app.route('/wedding/<int:wedding_id>/add_expense', methods=['POST'])
def add_expense(wedding_id):
    # Получаем значения (или 0, если не указано)
    quantity = request.form.get('quantity')
    unit_price = request.form.get('unit_price')
    try:
        quantity = float(quantity) if quantity else 0
    except ValueError:
        quantity = 0
    try:
        unit_price = float(unit_price) if unit_price else 0
    except ValueError:
        unit_price = 0
    total = quantity * unit_price if quantity and unit_price else unit_price or 0
    expense = Expense(
        category=request.form['category'],
        item=request.form['item'],
        quantity=quantity if quantity else None,
        unit_price=unit_price if unit_price else None,
        total=total,
        notes=request.form.get('notes'),
        wedding_id=wedding_id
    )
    db.session.add(expense)
    db.session.commit()
    return redirect(url_for('view_wedding', wedding_id=wedding_id))


@app.route('/wedding/<int:wedding_id>/add_guest', methods=['POST'])
def add_guest(wedding_id):
    guest = Guest(
        name=request.form['name'],
        phone=request.form.get('phone'),
        status=request.form.get('status', 'invited'),
        notes=request.form.get('notes'),
        wedding_id=wedding_id
    )
    db.session.add(guest)
    db.session.commit()
    return redirect(url_for('view_wedding', wedding_id=wedding_id))

# Удаление расхода
@app.route('/expense/<int:expense_id>/delete', methods=['POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    wedding_id = expense.wedding_id
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('view_wedding', wedding_id=wedding_id))

# Удаление гостя
@app.route('/guest/<int:guest_id>/delete', methods=['POST'])
def delete_guest(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    wedding_id = guest.wedding_id
    db.session.delete(guest)
    db.session.commit()
    return redirect(url_for('view_wedding', wedding_id=wedding_id))

# Редактирование расхода
@app.route('/expense/<int:expense_id>/edit', methods=['POST'])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    expense.category = request.form['category']
    expense.item = request.form['item']
    quantity = request.form.get('quantity')
    unit_price = request.form.get('unit_price')
    try:
        quantity = float(quantity) if quantity else 0
    except ValueError:
        quantity = 0
    try:
        unit_price = float(unit_price) if unit_price else 0
    except ValueError:
        unit_price = 0
    expense.quantity = quantity if quantity else None
    expense.unit_price = unit_price if unit_price else None
    expense.total = quantity * unit_price if quantity and unit_price else unit_price or 0
    expense.notes = request.form.get('notes')
    db.session.commit()
    return redirect(url_for('view_wedding', wedding_id=expense.wedding_id))

# Редактирование гостя
@app.route('/guest/<int:guest_id>/edit', methods=['POST'])
def edit_guest(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    guest.name = request.form['name']
    guest.phone = request.form.get('phone')
    guest.status = request.form.get('status')
    guest.notes = request.form.get('notes')
    db.session.commit()
    return redirect(url_for('view_wedding', wedding_id=guest.wedding_id))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=80, debug=True)
