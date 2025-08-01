from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Date
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class Wedding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(Date, nullable=True)
    tasks = relationship('Task', back_populates='wedding', cascade="all, delete-orphan")
    expenses = db.relationship('Expense', backref='wedding', cascade='all, delete-orphan')
    guests = db.relationship('Guest', backref='wedding', cascade='all, delete-orphan')
    budget = db.Column(db.Float)  # Новый бюджет!+

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    item = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Float)  # Кол-во
    unit_price = db.Column(db.Float)  # Цена за единицу
    total = db.Column(db.Float)  # Итого
    notes = db.Column(db.String(500))
    wedding_id = db.Column(db.Integer, db.ForeignKey('wedding.id'), nullable=False)

class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20))  # invited, confirmed, declined
    notes = db.Column(db.String(255))
    wedding_id = db.Column(db.Integer, db.ForeignKey('wedding.id'), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    is_done = db.Column(db.Boolean, default=False)
    wedding_id = db.Column(db.Integer, db.ForeignKey('wedding.id'), nullable=False)

    wedding = db.relationship("Wedding", back_populates="tasks")

class SponsorGift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    amount = db.Column(db.Float, nullable=True)
    notes = db.Column(db.String(255))
    wedding_id = db.Column(db.Integer, db.ForeignKey('wedding.id'), nullable=False)

    guest = db.relationship('Guest')
    wedding = db.relationship('Wedding', backref='sponsors')
