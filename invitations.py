# invitations.py

from flask import Blueprint, send_file, url_for
from models import Wedding, Guest
from fpdf import FPDF
import qrcode, tempfile, os
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

    # 2) регистрируем шрифты
    pdf.add_font("Playfair",    "", os.path.join(FONT_DIR, "PlayfairDisplay-Regular.ttf"),    uni=True)
    pdf.add_font("Playfair",   "I", os.path.join(FONT_DIR, "PlayfairDisplay-Italic.ttf"),     uni=True)
    pdf.add_font("Montserrat",  "", os.path.join(FONT_DIR, "Montserrat-Regular.ttf"),       uni=True)
    pdf.add_font("Montserrat", "B", os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),          uni=True)

    # стартовый Y-отступ
    y = 65

    # 3) заголовок
    pdf.set_xy(0, y)
    pdf.set_font("Montserrat", "", 14)
    pdf.set_text_color(70,70,90)
    pdf.cell(0, 8, "ПРИГЛАШЕНИЕ НА СВАДЬБУ", ln=1, align='C')
    y += 12

    # 4) имена пары (курсив)
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

    # 6) обращение к гостю (жирным)
    pdf.set_xy(0, y)
    pdf.set_font("Montserrat", "B", 22)
    pdf.set_text_color(180,138,30)
    pdf.cell(0, 12, f"Дорогой(ая) {guest.name}!", ln=1, align='C')
    y += 16

    # 7) основной текст
    pdf.set_xy(10, y)
    pdf.set_font("Montserrat", "", 12)
    pdf.set_text_color(85,85,85)
    pdf.multi_cell(128, 7,
        "Мы будем очень рады видеть Вас среди почётных гостей на нашем торжестве!",
        align='C'
    )
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
    invite_url = url_for('view_wedding', wedding_id=wedding.id, _external=True)
    qr_payload = (
        f"Приглашение на свадьбу «{wedding.name}»\n"
        f"Гость: {guest.name}\n\n"
        f"Перейти на страницу: {invite_url}"
    )
    qr_img = qrcode.make(qr_payload)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        qr_img.save(tmp_path)
    pdf.image(tmp_path, x=105, y=170, w=32, h=32)
    os.remove(tmp_path)

    # 10) собираем PDF в память
    pdf_str = pdf.output(dest='S')        # получаем PDF как строку
    pdf_bytes = pdf_str.encode('latin1')  # конвертируем в байты
    bio = BytesIO(pdf_bytes)
    bio.seek(0)
    return bio

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
