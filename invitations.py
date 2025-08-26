# invitations.py
from flask import Blueprint, send_file, url_for
from models import Wedding, Guest
from fpdf import FPDF
import qrcode, tempfile, os, zipfile, re
from io import BytesIO

invitations_bp = Blueprint("invitations_bp", __name__, url_prefix="/invitations")

BASE_DIR = os.path.dirname(__file__)
FONT_DIR = os.path.join(BASE_DIR, "fonts")
BG_PATH  = os.path.join(BASE_DIR, "static", "invite_bg.jpg")


# --------- утилиты ---------

def _safe_filename(s: str, ext: str = ".pdf") -> str:
    s = (s or "гость").strip()
    s = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "_", s)
    return (s or "file") + ext

def _add_font(pdf: FPDF, family: str, style: str, path: str, uni=True):
    if os.path.exists(path):
        pdf.add_font(family, style, path, uni=uni)

def _guess_gender_by_name(name: str) -> str:
    n = (name or "").strip().lower()
    if not n:
        return "n"
    return "f" if n.endswith(("а", "я")) else "m"

# RU: «Ташевы» -> «Ташевых», «Ильины» -> «Ильиных» и т.п.
def _ru_family_gen_pl_genitive(fam: str) -> str:
    if not fam:
        return ""
    parts, out = fam.split("-"), []
    for p in parts:
        w = p.strip()
        lw = w.lower()
        if lw.endswith("ы"):
            out.append(w[:-1] + "ых")
        elif lw.endswith("и"):
            out.append(w[:-1] + "х") if not (lw.endswith("ины") or lw.endswith("ыны")) else out.append(w[:-1] + "х")  # «Ильиных»
            if lw.endswith("ины") or lw.endswith("ыны"):
                out[-1] = w[:-1] + "х".replace("х", "ных")  # корректируем на «-ных»
        elif lw.endswith(("ов", "ев", "ёв")):
            out.append(w + "ых")
        else:
            out.append(w)
    return "-".join(out)

# UZ (кириллица): фамилия -> «...лар»
# Если введено во мн. числе по-русски («Ташевы») — убираем финальную «ы/и» и добавляем «лар».
def _uz_family_plural(fam: str) -> str:
    if not fam:
        return ""
    parts, out = fam.split("-"), []
    for p in parts:
        w = p.strip()
        lw = w.lower()
        stem = w
        for suf in ("ые", "ие"):
            if lw.endswith(suf):
                stem = w[:-2]
                break
        else:
            if lw.endswith(("ы", "и")):
                stem = w[:-1]
        out.append(stem + "лар")
    return "-".join(out)

def _ru_greeting(guest: Guest) -> str:
    if getattr(guest, "family_name", None):
        fam = _ru_family_gen_pl_genitive(guest.family_name)
        return f"Дорогая семья {fam}!"
    name = (guest.name or "").strip()
    if not name:
        return "Дорогие гости!"
    return f"Дорогая {name}!" if _guess_gender_by_name(name) == "f" else f"Дорогой {name}!"

def _uz_greeting(guest: Guest) -> str:
    if getattr(guest, "family_name", None):
        fam = _uz_family_plural(guest.family_name)
        return f"Қадрли {fam} оиласи!"
    name = (guest.name or "").strip()
    return f"Қадрли {name}!" if name else "Қадрли меҳмонлар!"


# --------- рисуем страницу (RU / UZ) ---------

def _draw_page(pdf: FPDF, wedding: Wedding, guest: Guest, lang: str):
    """
    lang: 'ru' | 'uz'
    """
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # фон
    if os.path.exists(BG_PATH):
        pdf.image(BG_PATH, x=0, y=0, w=148, h=210)

    # шрифты (поддержка кириллицы/узбек. кириллицы)
    _add_font(pdf, "Playfair", "", os.path.join(FONT_DIR, "PlayfairDisplay-Regular.ttf"))
    _add_font(pdf, "Playfair", "I", os.path.join(FONT_DIR, "PlayfairDisplay-Italic.ttf"))
    _add_font(pdf, "Montserrat", "", os.path.join(FONT_DIR, "Montserrat-Regular.ttf"))
    _add_font(pdf, "Montserrat", "B", os.path.join(FONT_DIR, "Montserrat-Bold.ttf"))

    MARGIN_X = 12
    WIDTH = 148 - 2 * MARGIN_X
    y = 58

    # заголовки
    pdf.set_xy(MARGIN_X, y)
    pdf.set_font("Montserrat", "", 13)
    pdf.set_text_color(70, 70, 90)
    pdf.cell(WIDTH, 7,
             "ПРИГЛАШЕНИЕ НА СВАДЬБУ" if lang == "ru" else "ТЎЙГА ТАКЛИФНОМА",
             align="C")
    y += 11

    # название свадьбы
    pdf.set_xy(MARGIN_X, y)
    pdf.set_font("Playfair", "I", 28)
    pdf.set_text_color(60, 45, 35)
    pdf.cell(WIDTH, 12, wedding.name, align="C")
    y += 16

    # дата/место
    pdf.set_xy(MARGIN_X, y)
    pdf.set_font("Montserrat", "", 12)
    pdf.set_text_color(85, 85, 85)
    if wedding.date:
        if lang == "ru":
            pdf.cell(WIDTH, 6, f"{wedding.date.strftime('%d.%m.%Y')}, ресторан «Мумтоз»", align="C")
        else:
            pdf.cell(WIDTH, 6, f"{wedding.date.strftime('%d.%m.%Y')}, ресторан «Мумтоз»", align="C")
    else:
        pdf.cell(WIDTH, 6, "Ресторан «Мумтоз»" if lang == "ru" else "Ресторан «Мумтоз»", align="C")
    y += 12

    # приветствие
    greeting = _ru_greeting(guest) if lang == "ru" else _uz_greeting(guest)
    pdf.set_xy(MARGIN_X, y)
    pdf.set_font("Montserrat", "B", 20)
    pdf.set_text_color(182, 140, 36)
    pdf.cell(WIDTH, 10, greeting, align="C")
    y += 14

    # основной текст
    pdf.set_xy(MARGIN_X, y)
    pdf.set_font("Montserrat", "", 12)
    pdf.set_text_color(75, 75, 75)
    pdf.multi_cell(
        WIDTH, 6,
        "Мы будем очень рады видеть Вас на нашем торжестве!" if lang == "ru"
        else "Бизнинг тантанамизда сизларни кўришдан жуда мамнун бўламиз!",
        align="C"
    )
    y = pdf.get_y() + 6

    # детали
    pdf.set_xy(MARGIN_X, y)
    pdf.cell(WIDTH, 6, "Начало: 17:00" if lang == "ru" else "Бошланиши: 17:00", align="C")
    y += 7
    pdf.set_xy(MARGIN_X, y)
    pdf.cell(WIDTH, 6,
             "Адрес: г. Навои, ул. Любая, 123" if lang == "ru" else "Манзил: Навоий ш., Любая кўч., 123",
             align="C")
    y += 7

    if getattr(guest, "family_name", None):
        persons = guest.family_count or 1
        pdf.set_xy(MARGIN_X, y)
        pdf.cell(WIDTH, 6,
                 f"Количество персон: {persons}" if lang == "ru" else f"Кишилар сони: {persons}",
                 align="C")
        y += 7

    # QR (внизу справа)
    invite_url = url_for("wedding_pages.view_wedding", wedding_id=wedding.id, _external=True)
    qr_payload = (
        (f"Приглашение на свадьбу «{wedding.name}»\n" if lang == "ru" else f"«{wedding.name}» тўйига таклифнома\n") +
        (f"Семья: {guest.family_name} (персон: {guest.family_count or 1})\n"
         if guest.family_name else
         (f"Гость: {guest.name}\n" if lang == "ru" else f"Меҳмон: {guest.name}\n")) +
        (f"Страница: {invite_url}" if lang == "ru" else f"Саҳифа: {invite_url}")
    )
    qr_img = qrcode.make(qr_payload)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        qr_path = tmp.name
        qr_img.save(qr_path)
    try:
        pdf.image(qr_path, x=148 - MARGIN_X - 34, y=210 - 34 - 12, w=34, h=34)
    finally:
        os.remove(qr_path)


# --------- генерация PDF (2 страницы: RU + UZ) ---------

def gen_invitation_pdf(wedding: Wedding, guest: Guest) -> BytesIO:
    pdf = FPDF(format="A5", orientation="P", unit="mm")
    # рисуем 2 страницы
    _draw_page(pdf, wedding, guest, "ru")
    _draw_page(pdf, wedding, guest, "uz")

    out = pdf.output(dest="S")
    pdf_bytes = bytes(out)
    bio = BytesIO(pdf_bytes)
    bio.seek(0)
    return bio


# --------- endpoints ---------

@invitations_bp.route("/<int:wedding_id>/<int:guest_id>/pdf")
def invitation_pdf(wedding_id, guest_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    guest = Guest.query.get_or_404(guest_id)
    pdf_buf = gen_invitation_pdf(wedding, guest)
    filename = _safe_filename(guest.family_name or guest.name)
    return send_file(pdf_buf, as_attachment=False, download_name=filename, mimetype="application/pdf")


@invitations_bp.route("/<int:wedding_id>/all_pdfs.zip")
def invitations_zip(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    guests = Guest.query.filter_by(wedding_id=wedding_id).all()

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for g in guests:
            pdf_bytes = gen_invitation_pdf(wedding, g).getvalue()
            name = _safe_filename(g.family_name or g.name)
            zf.writestr(name, pdf_bytes)
    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=_safe_filename(f"Приглашения_{wedding.name}", ext=".zip"),
        mimetype="application/zip",
    )
