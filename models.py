# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Float, Date, event, Index
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# =========================
# Users / Auth
# =========================
class User(db.Model, UserMixin):
    """Пользователь приложения."""
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(120))
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)

    weddings = relationship('Wedding', back_populates='user', cascade="all, delete-orphan")

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def __repr__(self):
        return f"<User {self.id} {self.email} admin={self.is_admin}>"

# =========================
# Core
# =========================
class Wedding(db.Model):
    """Свадьба + агрегаты/связи."""
    id   = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=True)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    user    = relationship('User', back_populates='weddings')

    budget = Column(Float)

    tasks    = relationship('Task',    back_populates='wedding', cascade="all, delete-orphan")
    expenses = relationship('Expense', backref='wedding',       cascade="all, delete-orphan")
    guests   = relationship('Guest',   backref='wedding',       cascade="all, delete-orphan")

    tables   = relationship(
        'Table',
        backref='wedding',
        cascade="all, delete-orphan",
        order_by="Table.order"
    )

    # БЫЛО: sponsors = relationship('SponsorGift', backref='wedding', ...)
    sponsors = relationship('SponsorGift', back_populates='wedding', cascade="all, delete-orphan")


    # ===== агрегаты по расходам =====
    @hybrid_property
    def total_expenses(self) -> float:
        """Итог по расходам: берём fact если задан, иначе total."""
        s = 0.0
        for e in self.expenses:
            if e.fact is not None:
                s += e.fact or 0
            else:
                s += e.total or 0
        return s

    @hybrid_property
    def plan_sum(self) -> float:
        return sum((e.plan or 0) for e in self.expenses)

    @hybrid_property
    def fact_sum(self) -> float:
        return sum(((e.fact if e.fact is not None else (e.total or 0)) or 0) for e in self.expenses)

    @hybrid_property
    def prepayment_sum(self) -> float:
        return sum((e.prepayment or 0) for e in self.expenses)

    @hybrid_property
    def difference_sum(self) -> float:
        return sum((e.difference or 0) for e in self.expenses)

    @hybrid_property
    def persons_sum(self) -> int:
        """Сколько персон приглашено (семьи учитываются по количеству)."""
        return sum(g.persons for g in self.guests)

    def __repr__(self):
        return f"<Wedding {self.id}: {self.name}>"

# =========================
# Seating (Рассадка)
# =========================
class Table(db.Model):
    """
    Стол на свадьбе (по умолчанию 12 мест).
    """
    __tablename__ = "table"  # OK для SQLite/PostgreSQL
    id         = Column(Integer, primary_key=True)
    wedding_id = Column(Integer, ForeignKey("wedding.id"), nullable=False, index=True)

    name  = Column(String(50), default="Стол")
    seats = Column(Integer, nullable=False, default=12)
    order = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<Table {self.id} {self.name}({self.seats})>"

Index("ix_table_wedding_order", Table.wedding_id, Table.order)

# =========================
# Finance
# =========================
class Expense(db.Model):
    id         = Column(Integer, primary_key=True)
    wedding_id = Column(Integer, ForeignKey('wedding.id'), nullable=False, index=True)

    category   = Column(String(100), nullable=False)
    item       = Column(String(100), nullable=False)
    quantity   = Column(Float)   # количество
    unit_price = Column(Float)   # цена за единицу
    total      = Column(Float)   # quantity * unit_price (может быть пустым)

    notes      = Column(String(200))

    # расширенная финмодель
    plan       = Column(Float)        # план
    fact       = Column(Float)        # факт (если None, используем total)
    prepayment = Column(Float)        # предоплата
    difference = Column(Float)        # (fact - plan), заполняется listener’ом

    def __repr__(self):
        return f"<Expense {self.id} {self.category}/{self.item}>"

# автоподсчёт total и difference перед сохранением
@event.listens_for(Expense, "before_insert")
@event.listens_for(Expense, "before_update")
def expense_autocalc(_mapper, _connection, target: Expense):
    # total = quantity * unit_price
    if (target.quantity is not None) and (target.unit_price is not None):
        try:
            target.total = (target.quantity or 0) * (target.unit_price or 0)
        except Exception:
            pass

    # difference = fact - plan (если fact не задан, берём total)
    p = target.plan or 0
    f = target.fact if target.fact is not None else (target.total or 0)
    target.difference = (f or 0) - (p or 0)

# =========================
# Guests
# =========================
class Guest(db.Model):
    id         = Column(Integer, primary_key=True)
    wedding_id = Column(Integer, ForeignKey('wedding.id'), nullable=False, index=True)

    # имя и/или семья
    name         = Column(String(120))      # может быть пустым, если указана семья
    family_name  = Column(String(120))      # "Шириновы"
    family_count = Column(Integer)          # если None -> считать 1

    phone  = Column(String(50))
    status = Column(String(20))             # invited / confirmed / declined
    notes  = Column(String)                 # Text -> String ок для SQLite, при желании верни Text

    # группы/теги
    side     = Column(String(20))           # 'groom' | 'bride' | 'other'
    is_vip   = Column(Boolean, default=False)
    is_child = Column(Boolean, default=False)

    # старая схема (оставлена для совместимости)
    table_no = Column(Integer)

    # новая схема рассадки
    table_id   = Column(Integer, ForeignKey("table.id"), nullable=True, index=True)
    table_seat = Column(Integer)            # позиция за столом (опционально)

    table = relationship("Table", backref=backref("guests", lazy="dynamic"))

    @hybrid_property
    def persons(self) -> int:
        return self.family_count or 1

    def display_name(self) -> str:
        return self.family_name or self.name or "Без имени"

    def __repr__(self):
        return f"<Guest {self.id} {self.display_name()} ({self.persons}p)>"

Index("ix_guest_wedding_status", Guest.wedding_id, Guest.status)
Index("ix_guest_table", Guest.table_id)

# =========================
# Tasks
# =========================
class Task(db.Model):
    id           = Column(Integer, primary_key=True)
    description  = Column(String(200), nullable=False)
    is_done      = Column(Boolean, default=False)

    wedding_id   = Column(Integer, ForeignKey('wedding.id'), nullable=False, index=True)
    wedding      = relationship("Wedding", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.id} done={self.is_done}>"

# =========================
# Sponsors / Gifts
# =========================
# models.py — класс SponsorGift
class SponsorGift(db.Model):
    id         = Column(Integer, primary_key=True)
    guest_id   = Column(Integer, ForeignKey('guest.id'), nullable=False, index=True)
    amount     = Column(Float, nullable=True)
    notes      = Column(String(255))
    wedding_id = Column(Integer, ForeignKey('wedding.id'), nullable=False, index=True)

    guest   = relationship('Guest')
    # БЫЛО: wedding = relationship('Wedding', backref='sponsors')
    wedding = relationship('Wedding', back_populates='sponsors')

    def __repr__(self):
        return f"<SponsorGift {self.id} +{self.amount or 0} from guest {self.guest_id}>"
