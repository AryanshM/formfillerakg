# app.py
import streamlit as st
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
import io
import random
import math

# ------- CONFIG -------
coords = {
    "name": (227, 646),
    "email": (227, 626),
    "dob": (227, 586)
}
FONT_NAME = "Helvetica"
FONT_SIZE = 9

# Fixed strips for each text field
MASK_W = 150
MASK_H = 15
RECT_X_OFFSET = 3
RECT_Y_ADJUST = MASK_H * 0.25

# Hours coordinate and style (large text)
hours_coords = (414, 606)   # x, y in points
hours_font = "Helvetica"
hours_font_size = 26        # large so it looks like the certificate's big time

# Colors
DEFAULT_TEXT_COLOR = "#1d355c"
DEFAULT_BG_COLOR = "#f3f6f7"

# ------- Helpers -------
def hex_to_rgb01(hexstr: str):
    h = hexstr.lstrip("#")
    return (int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0)

def random_hours_string(min_hours=60.0, max_hours=65.0):
    """
    Return a random H:MM:SS string where hours is in [min_hours, max_hours).
    We pick a random float in the range and break into H/M/S.
    """
    val = random.uniform(min_hours, max_hours)  # e.g., 62.374
    hours_int = int(math.floor(val))            # 62
    frac = val - hours_int                      # 0.374...
    minutes = int(frac * 60)                    # e.g., 22
    seconds = int((frac * 60 - minutes) * 60)   # remainder seconds
    # Format as HH:MM:SS (pad minutes/seconds)
    return f"{hours_int:02d}:{minutes:02d}:{seconds:02d}"

def create_overlay(page_width, page_height, name, email, dob,
                   text_color=DEFAULT_TEXT_COLOR, background_color=DEFAULT_BG_COLOR,
                   font_name=FONT_NAME, font_size=FONT_SIZE,
                   hours_text=None):
    """
    Create a one-page overlay PDF with:
      - per-field fixed strips + new text (name/email/dob)
      - the big hours_text at hours_coords
    Returns a PdfReader for the overlay.
    """
    values = {"name": name or "", "email": email or "", "dob": dob or ""}
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    bg_rgb = hex_to_rgb01(background_color)
    txt_rgb = hex_to_rgb01(text_color)

    # Small fields: draw their mask strips and text
    c.setFont(font_name, font_size)
    for key, (x, y) in coords.items():
        text = values.get(key, "")
        if not text:
            continue

        rect_x = x - RECT_X_OFFSET
        rect_y = y - RECT_Y_ADJUST

        # Draw background strip
        c.setFillColorRGB(*bg_rgb)
        c.rect(rect_x, rect_y, MASK_W, MASK_H, fill=True, stroke=False)

        # Draw small text
        c.setFillColorRGB(*txt_rgb)
        c.setFont(font_name, font_size)
        c.drawString(x, y, text)

    # Draw the big hours text (on the right)
    if hours_text:
        hx, hy = hours_coords
        # Draw a small background behind hours so it hides original time cleanly
        # We will draw a rectangle slightly bigger than the hours text.
        # Since width of big text varies, draw a reasonably wide strip to guarantee cover.
        hours_bg_w = 105
        hours_bg_h = hours_font_size + 8
        hours_rect_x = hx - 10
        hours_rect_y = hy - (hours_bg_h * 0.25)

        c.setFillColorRGB(*bg_rgb)
        c.rect(hours_rect_x, hours_rect_y, hours_bg_w, hours_bg_h, fill=True, stroke=False)

        # Now draw the hours in big font and chosen text color
        c.setFillColorRGB(*txt_rgb)
        c.setFont(hours_font, hours_font_size)
        c.drawString(hx, hy, hours_text)

    c.save()
    packet.seek(0)
    return PdfReader(packet)

def fill_pdf(template_bytes, name, email, dob,
             text_color=DEFAULT_TEXT_COLOR, background_color=DEFAULT_BG_COLOR):
    """
    Merge the overlay onto page 1 of the uploaded PDF and return result bytes.
    The overlay includes a random hours value between 60 and 65 hours.
    """
    reader = PdfReader('certificate.pdf')
    writer = PdfWriter()

    # get page size
    page = reader.pages[0]
    w = float(page.mediabox.width)
    h = float(page.mediabox.height)

    # generate random hours string
    hours_text = random_hours_string(60.0, 65.0)

    overlay_pdf = create_overlay(w, h, name, email, dob,
                                 text_color=text_color,
                                 background_color=background_color,
                                 font_name=FONT_NAME, font_size=FONT_SIZE,
                                 hours_text=hours_text)
    overlay_page = overlay_pdf.pages[0]

    # merge overlay on page 1 only
    for i, p in enumerate(reader.pages):
        if i == 0:
            p.merge_page(overlay_page)
        writer.add_page(p)

    out_buffer = io.BytesIO()
    writer.write(out_buffer)

    # Return both PDF bytes and the generated hours string so the UI can show it
    return out_buffer.getvalue(), hours_text

# ------- Streamlit UI -------
st.set_page_config(page_title="PDF Auto-Fill + Random Hours", layout="wide")
st.title("PDF Auto-Fill — assigns random Total Study Time (60–65 hours)")



col1, col2, col3 = st.columns(3)
with col1:
    name = st.text_input("Name")
with col2:
    email = st.text_input("Email")
with col3:
    dob = st.text_input("Date of Birth")



if st.button("Generate PDF with Random Hours"):
    try:
        pdf_bytes, hours_str = fill_pdf(
            None,
            name, email, dob
        )
        st.success(f"PDF generated — Total Study Time placed as **{hours_str}**")
        st.download_button(
            label="Download Filled PDF",
            data=pdf_bytes,
            file_name="filled_with_hours.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Failed to generate PDF: {e}")
