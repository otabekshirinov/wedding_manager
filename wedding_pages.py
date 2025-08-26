# wedding_pages.py
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from models import db, Wedding, Expense, Guest, Table
from math import ceil

wedding_pages = Blueprint(
    "wedding_pages",
    __name__,
    url_prefix="/wedding"
)

# ----------------- утилиты -----------------
def _to_float(val):
    """Пробуем привести значение к float. Пустое / некорректное -> None."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None

def _calc_total(quantity, unit_price):
    """Старое правило total: qty*price если оба есть, иначе unit_price или 0."""
    q = _to_float(quantity)
    p = _to_float(unit_price)
    if q is not None and p is not None:
        return q * p
    return p or 0.0

# ======= ХАБ =======
@wedding_pages.route("/<int:wedding_id>")
def view_wedding(wedding_id):
    """
    Хаб-страница: две большие карточки — Расходы и Гости + мини-статистика.
    """
    wedding = Wedding.query.get_or_404(wedding_id)
    total_expenses = sum((e.total or 0) for e in wedding.expenses)
    done_tasks = sum(1 for t in wedding.tasks if getattr(t, "is_done", False))
    return render_template(
        "wedding_overview.html",
        wedding=wedding,
        total_expenses=total_expenses,
        done_tasks=done_tasks,
    )

# ======= РАСХОДЫ =======
@wedding_pages.route("/<int:wedding_id>/expenses")
def wedding_expenses(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    return render_template("wedding_expenses.html", wedding=wedding)

@wedding_pages.route("/<int:wedding_id>/expenses/add", methods=["POST"])
def add_expense(wedding_id):
    # базовые поля
    category   = request.form.get("category", "").strip()
    item       = request.form.get("item", "").strip()
    quantity   = _to_float(request.form.get("quantity"))
    unit_price = _to_float(request.form.get("unit_price"))
    notes      = request.form.get("notes")

    # новые поля
    plan        = _to_float(request.form.get("plan"))
    fact        = _to_float(request.form.get("fact"))
    prepayment  = _to_float(request.form.get("prepayment"))

    exp = Expense(
        category=category,
        item=item,
        quantity=quantity,
        unit_price=unit_price,
        total=_calc_total(quantity, unit_price),
        notes=notes,
        wedding_id=wedding_id,
    )

    # если в модели есть эти колонки — запишем
    if hasattr(Expense, "plan"):
        exp.plan = plan
    if hasattr(Expense, "fact"):
        exp.fact = fact
    if hasattr(Expense, "prepayment"):
        exp.prepayment = prepayment

    db.session.add(exp)
    db.session.commit()
    return redirect(url_for("wedding_pages.wedding_expenses", wedding_id=wedding_id))

@wedding_pages.route("/expenses/<int:expense_id>/edit", methods=["POST"])
def edit_expense(expense_id):
    exp = Expense.query.get_or_404(expense_id)

    # базовые поля
    exp.category   = request.form.get("category", "").strip()
    exp.item       = request.form.get("item", "").strip()
    quantity       = _to_float(request.form.get("quantity"))
    unit_price     = _to_float(request.form.get("unit_price"))
    exp.quantity   = quantity
    exp.unit_price = unit_price
    exp.total      = _calc_total(quantity, unit_price)
    exp.notes      = request.form.get("notes")

    # новые поля
    plan        = _to_float(request.form.get("plan"))
    fact        = _to_float(request.form.get("fact"))
    prepayment  = _to_float(request.form.get("prepayment"))

    if hasattr(Expense, "plan"):
        exp.plan = plan
    if hasattr(Expense, "fact"):
        exp.fact = fact
    if hasattr(Expense, "prepayment"):
        exp.prepayment = prepayment

    db.session.commit()
    return redirect(url_for("wedding_pages.wedding_expenses", wedding_id=exp.wedding_id))

@wedding_pages.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def delete_expense(expense_id):
    exp = Expense.query.get_or_404(expense_id)
    wid = exp.wedding_id
    db.session.delete(exp)
    db.session.commit()
    return redirect(url_for("wedding_pages.wedding_expenses", wedding_id=wid))

# ======= ГОСТИ =======
@wedding_pages.route("/<int:wedding_id>/guests")
def wedding_guests(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    return render_template("wedding_guests.html", wedding=wedding)

@wedding_pages.route("/<int:wedding_id>/guests/add", methods=["POST"])
def add_guest(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)

    name = (request.form.get("name") or "").strip()
    family_name = (request.form.get("family_name") or "").strip()
    family_count = request.form.get("family_count")
    phone = (request.form.get("phone") or "").strip()
    status = request.form.get("status") or "invited"
    notes = request.form.get("notes")

    side = request.form.get("side") or None  # groom/bride/other/None
    is_vip = bool(request.form.get("is_vip"))
    is_child = bool(request.form.get("is_child"))
    table_no = request.form.get("table_no")

    # имя можно не указывать, если есть семья
    if not name and not family_name:
        # можно вернуть 400, но для UX — просто зафиксируем пустым
        name = None

    try:
        family_count = int(family_count) if family_count else None
    except ValueError:
        family_count = None

    try:
        table_no = int(table_no) if table_no else None
    except ValueError:
        table_no = None

    g = Guest(
        wedding_id=wedding.id,
        name=name,
        phone=phone,
        status=status,
        notes=notes,
        family_name=family_name or None,
        family_count=family_count,
        side=side,
        is_vip=is_vip,
        is_child=is_child,
        table_no=table_no,
    )
    db.session.add(g)
    db.session.commit()
    return redirect(url_for("wedding_pages.wedding_guests", wedding_id=wedding.id))

# === edit_guest: тоже поддерживаем новые поля ===
@wedding_pages.route("/guests/<int:guest_id>/edit", methods=["POST"])
def edit_guest(guest_id):
    g = Guest.query.get_or_404(guest_id)

    g.name = (request.form.get("name") or "").strip() or None
    g.phone = (request.form.get("phone") or "").strip()
    g.status = request.form.get("status") or g.status
    g.notes = request.form.get("notes")

    g.family_name = (request.form.get("family_name") or "").strip() or None
    fc = request.form.get("family_count")
    try:
        g.family_count = int(fc) if fc else None
    except ValueError:
        g.family_count = None

    g.side = request.form.get("side") or None
    g.is_vip = bool(request.form.get("is_vip"))
    g.is_child = bool(request.form.get("is_child"))

    tno = request.form.get("table_no")
    try:
        g.table_no = int(tno) if tno else None
    except ValueError:
        g.table_no = None

    db.session.commit()
    return redirect(url_for("wedding_pages.wedding_guests", wedding_id=g.wedding_id))

# === ручная установка стола для одной записи ===
@wedding_pages.route("/guests/<int:guest_id>/set_table", methods=["POST"])
def set_table(guest_id):
    g = Guest.query.get_or_404(guest_id)
    tno = request.form.get("table_no")
    try:
        g.table_no = int(tno) if tno else None
    except ValueError:
        g.table_no = None
    db.session.commit()
    return redirect(url_for("wedding_pages.wedding_guests", wedding_id=g.wedding_id))

# === автосборка рассадки по 12 мест ===
@wedding_pages.route("/<int:wedding_id>/guests/auto_seat", methods=["POST"])
def auto_seat(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    TABLE = 12

    guests = list(wedding.guests)

    # Сначала семьи (с наибольшим количеством), потом одиночки
    def size(g):
        return g.family_count if (g.family_count and g.family_count > 0) else 1

    families = [g for g in guests if g.family_name or (g.family_count and g.family_count > 1)]
    singles  = [g for g in guests if g not in families]

    families.sort(key=lambda g: size(g), reverse=True)

    table_no = 1
    used = 0

    for grp in families + singles:
        need = size(grp)
        # если не помещается — переходим на следующий стол
        if used + need > TABLE:
            table_no += 1
            used = 0
        grp.table_no = table_no
        used += need
        # если ровно 12 — следующий стол
        if used == TABLE:
            table_no += 1
            used = 0

    db.session.commit()
    return redirect(url_for("wedding_pages.wedding_guests", wedding_id=wedding.id))


@wedding_pages.route("/guests/<int:guest_id>/delete", methods=["POST"])
def delete_guest(guest_id):
    g = Guest.query.get_or_404(guest_id)
    wid = g.wedding_id
    db.session.delete(g)
    db.session.commit()
    return redirect(url_for("wedding_pages.wedding_guests", wedding_id=wid))


# ======= РАССАДКА =======
# --- Рассадка: страница ---
@wedding_pages.route("/<int:wedding_id>/seating")
def seating_page(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)

    # сколько мест за столом хотим считать по умолчанию
    seats_per_table = 12

    # общее число персон = суммы family_count (или 1 для одиночных)
    total_persons = sum((g.family_count or 1) for g in wedding.guests)

    # список столов
    # Если модель называется иначе (например SeatingTable), просто поменяй Table -> SeatingTable
    tables = Table.query.filter_by(wedding_id=wedding_id).order_by(Table.id.asc()).all()

    # «минимально нужно столов»
    tables_needed = (total_persons + seats_per_table - 1) // seats_per_table if total_persons else 0

    # гости без стола
    unassigned = Guest.query.filter_by(wedding_id=wedding_id, table_id=None).order_by(Guest.id.asc()).all()

    # словарь: {table_id: [гости за этим столом в нужном порядке]}
    tables_guests = {
        t.id: Guest.query.filter_by(wedding_id=wedding_id, table_id=t.id).order_by(Guest.id.asc()).all()
        for t in tables
    }

    return render_template(
        "wedding_seating.html",
        wedding=wedding,
        seats_per_table=seats_per_table,
        total_persons=total_persons,
        tables_needed=tables_needed,
        tables=tables,
        unassigned=unassigned,
        tables_guests=tables_guests,
    )


@wedding_pages.post("/<int:wedding_id>/seating/new_table")
def seating_new_table(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    n = (Table.query.filter_by(wedding_id=wedding_id).count() or 0) + 1
    t = Table(wedding_id=wedding.id, name=f"Стол {n}", seats=int(request.form.get("seats", 12)), order=n-1)
    db.session.add(t)
    db.session.commit()
    return redirect(url_for("wedding_pages.seating_page", wedding_id=wedding_id))

@wedding_pages.post("/<int:wedding_id>/seating/rename_table/<int:table_id>")
def seating_rename_table(wedding_id, table_id):
    t = Table.query.get_or_404(table_id)
    t.name = request.form.get("name", t.name).strip() or t.name
    db.session.commit()
    return redirect(url_for("wedding_pages.seating_page", wedding_id=wedding_id))

@wedding_pages.post("/<int:wedding_id>/seating/delete_table/<int:table_id>")
def seating_delete_table(wedding_id, table_id):
    t = Table.query.get_or_404(table_id)
    # освобождаем гостей
    for g in t.guests.all():
        g.table_id = None
        g.table_seat = None
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for("wedding_pages.seating_page", wedding_id=wedding_id))

@wedding_pages.post("/<int:wedding_id>/seating/clear")
def seating_clear(wedding_id):
    Guest.query.filter_by(wedding_id=wedding_id).update({Guest.table_id: None, Guest.table_seat: None})
    db.session.commit()
    return redirect(url_for("wedding_pages.seating_page", wedding_id=wedding_id))

# Ajax: назначить гостя столу (table_id может быть null)
@wedding_pages.post("/seating/assign")
def seating_assign():
    data = request.get_json(force=True)
    guest_id = int(data.get("guest_id"))
    table_id = data.get("table_id")  # может быть None
    seat = data.get("seat")

    g = Guest.query.get_or_404(guest_id)
    old_table_id = g.table_id
    g.table_id = int(table_id) if table_id not in (None, "null", "") else None
    g.table_seat = int(seat) if seat not in (None, "null", "") else None
    db.session.commit()

    def table_payload(tid):
        if not tid:
            return {"table_id": None, "persons": 0, "seats": 0}
        t = Table.query.get(tid)
        persons = sum((x.family_count or 1) for x in t.guests)
        return {"table_id": t.id, "current_persons": persons, "seats": t.seats}

    return jsonify({
        "ok": True,
        "updated": [table_payload(old_table_id), table_payload(g.table_id)]
    })

# Авторассадка (жадный алгоритм по убыванию группы)
@wedding_pages.post("/<int:wedding_id>/seating/auto")
def seating_auto(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    tables = Table.query.filter_by(wedding_id=wedding_id).order_by(Table.order, Table.id).all()
    if not tables:
        t = Table(wedding_id=wedding.id, name="Стол 1", seats=12, order=0)
        db.session.add(t)
        db.session.commit()
        tables = [t]

    seats = tables[0].seats
    # очистим
    for g in wedding.guests:
        g.table_id = None
        g.table_seat = None

    # семьи/гости по размеру
    groups = sorted(list(wedding.guests), key=lambda g: (g.family_count or 1), reverse=True)

    # считаем сколько столов нужно минимум
    total_persons = sum((g.family_count or 1) for g in groups)
    need = ceil(max(1, total_persons) / seats)
    while len(tables) < need:
        t = Table(wedding_id=wedding.id, name=f"Стол {len(tables)+1}", seats=seats, order=len(tables))
        db.session.add(t)
        db.session.flush()
        tables.append(t)

    # заполняем
    capacity = {t.id: 0 for t in tables}
    for g in groups:
        p = g.family_count or 1
        # выбираем стол с наименьшей заполненностью, где поместится
        target = None
        for t in sorted(tables, key=lambda x: capacity[x.id]):
            if capacity[t.id] + p <= t.seats:
                target = t
                break
        if not target:
            # нет места — создаём новый стол
            new = Table(wedding_id=wedding.id, name=f"Стол {len(tables)+1}", seats=seats, order=len(tables))
            db.session.add(new)
            db.session.flush()
            tables.append(new)
            capacity[new.id] = 0
            target = new
        g.table_id = target.id
        capacity[target.id] += p

    db.session.commit()
    return redirect(url_for("wedding_pages.seating_page", wedding_id=wedding_id))
