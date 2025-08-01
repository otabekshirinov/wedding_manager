# finance.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Wedding, Expense, SponsorGift, Guest
from collections import defaultdict

finance_bp = Blueprint('finance_bp', __name__, url_prefix='/finance')

@finance_bp.route('/<int:wedding_id>')
def page_finance(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    total_expenses = sum((e.total or 0) for e in wedding.expenses)

    # Расходы по категориям (для pie chart)
    cat_totals = defaultdict(float)
    for e in wedding.expenses:
        if e.category:
            cat_totals[e.category] += e.total or 0
    expense_categories = list(cat_totals.keys())
    expense_amounts = list(cat_totals.values())

    # Все гости для селекта
    guests = wedding.guests

    # Все подарки/спонсоры
    sponsors = SponsorGift.query.filter_by(wedding_id=wedding.id).all()

    return render_template(
        'finance.html',
        wedding=wedding,
        total_expenses=total_expenses,
        expense_categories=expense_categories,
        expense_amounts=expense_amounts,
        guests=guests,
        sponsors=sponsors,
    )

@finance_bp.route('/<int:wedding_id>/budget', methods=['POST'])
def update_budget(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    try:
        budget = float(request.form.get('budget', 0))
    except ValueError:
        budget = 0
    wedding.budget = budget
    db.session.commit()
    return redirect(url_for('finance_bp.page_finance', wedding_id=wedding_id))

@finance_bp.route('/<int:wedding_id>/sponsor', methods=['POST'])
def add_sponsor(wedding_id):
    guest_id = int(request.form['guest_id'])
    amount = float(request.form['amount'])
    notes = request.form.get('notes', '')
    sponsor = SponsorGift(guest_id=guest_id, amount=amount, notes=notes, wedding_id=wedding_id)
    db.session.add(sponsor)
    db.session.commit()
    return redirect(url_for('finance_bp.page_finance', wedding_id=wedding_id))

@finance_bp.route('/<int:wedding_id>/sponsor/<int:sponsor_id>/delete', methods=['POST'])
def delete_sponsor(wedding_id, sponsor_id):
    sponsor = SponsorGift.query.get_or_404(sponsor_id)
    db.session.delete(sponsor)
    db.session.commit()
    return redirect(url_for('finance_bp.page_finance', wedding_id=wedding_id))
