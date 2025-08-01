# invitations.py

from flask import Blueprint, send_file, url_for
from models import Wedding, Guest
from fpdf import FPDF
import qrcode
import tempfile
import os
from io import BytesIO

invitations_bp = Blueprint('invitations_bp', __name__, url_prefix='/invitations')

BASE_DIR = os.path.dirname(__file__)
FONT_DIR = os.path.join(BASE_DIR, 'fonts')
BG_PATH   = os.path.join(BASE_DIR, 'static', 'invite_bg.jpg')

def gen_invitation_pdf(wedding: Wedding, guest: Guest) -> BytesIO:
    pdf = FPDF(format='A5', orientation='P', unit='mm')
    pdf.add_page()

    # 1) фон
    if os.path.exists(BG_PATH):
        pdf.image(BG_PATH, x=0, y=0, w=148, h=210)

    # 2) шрифты
    pdf.add_font("Playfair",    "", os.path.join(FONT_DIR, "PlayfairDisplay-Regular.ttf"),    uni=True)
    pdf.add_font("Playfair",   "I", os.path.join(FONT_DIR, "PlayfairDisplay-Italic.ttf"),     uni=True)
    pdf.add_font("Montserrat",  "", os.path.join(FONT_DIR, "Montserrat-Regular.ttf"),       uni=True)
    pdf.add_font("Montserrat", "B", os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),          uni=True)

    # стартовая Y-координата (чуть ниже цветка)
    y = 65

    # 3) заголовок
    pdf.set_xy(0, y)
    pdf.set_font("Montserrat", "", 14)
    pdf.set_text_color(70,70,90)
    pdf.cell(0, 8, "ПРИГЛАШЕНИЕ НА СВАДЬБУ", ln=1, align='C')
    y += 12

    # 4) имена пары (курсивом Playfair)
    pdf.set_xy(0, y)
    pdf.set_font("Playfair", "I", 30)
    pdf.set_text_color(75,53,40)
    pdf.cell(0, 14, wedding.name, ln=1, align='C')
    y += 18

    # 5) дата и место
    pdf.set_xy(0, y)
    pdf.set_font("Montserrat", "", 14)
    pdf.set_text_color(75,75,75)
    pdf.cell(0, 8, f"{wedding.date.strftime('%d.%m.%Y')}, ресторан «Мумтоз»", ln=1, align='C')
    y += 14

    # 6) обращение к гостю (жирным Montserrat)
    pdf.set_xy(0, y)
    pdf.set_font("Montserrat", "B", 22)
    pdf.set_text_color(180,138,30)
    pdf.cell(0, 12, f"Дорогой(ая) {guest.name}!", ln=1, align='C')
    y += 16

    # 7) основной текст приглашения
    pdf.set_xy(10, y)
    pdf.set_font("Montserrat", "", 12)
    pdf.set_text_color(85,85,85)
    pdf.multi_cell(128, 7, "Мы будем очень рады видеть Вас среди почётных гостей на нашем торжестве!", align='C')
    y = pdf.get_y() + 6

    # 8) время и адрес
    pdf.set_xy(0, y)
    pdf.set_font("Montserrat", "", 12)
    pdf.set_text_color(75,75,75)
    pdf.cell(0, 7, "Начало: 17:00", ln=1, align='C')
    y += 8
    pdf.set_xy(0, y)
    pdf.cell(0, 7, "Адрес: г. Навои, ул. Любая, 123", ln=1, align='C')

    # 9) QR-код через временный файл
    #    — в коде закладываем ссылку на страницу свадьбы + приветствие
    invite_url = url_for('view_wedding', wedding_id=wedding.id, _external=True)
    qr_payload = f"Приглашение на свадьбу «{wedding.name}»\nДля: {guest.name}\n\nПерейти: {invite_url}"
    qr_img = qrcode.make(qr_payload)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        qr_path = tmp.name
        qr_img.save(qr_path)

    pdf.image(qr_path, x=105, y=170, w=32, h=32)

    # удаляем временный файл
    os.remove(qr_path)

    # 10) отдаём PDF в байтах
    out = BytesIO()
    pdf.output(out)
    out.seek(0)
    return out

@invitations_bp.route('/<int:wedding_id>/<int:guest_id>/pdf')
def invitation_pdf(wedding_id, guest_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    guest   = Guest.query.get_or_404(guest_id)
    pdf_buf = gen_invitation_pdf(wedding, guest)
    return send_file(
        pdf_buf,
        as_attachment=False,
        download_name=f"Приглашение_{guest.name}.pdf",
        mimetype="application/pdf"
    )
