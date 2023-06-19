from django.utils.html import strip_tags

import io
from PIL import Image
from svglib.svglib import svg2rlg, Drawing
from django_countries import countries
from datetime import datetime

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Rect

from main.models import Settings


BACKGROUND = HexColor('#fdf8f2')
#FOOTER_COLOR = HexColor('#70ad47')
FOOTER_COLOR = HexColor('#d2e1bd')
WHITE = HexColor('#ffffff')
BLACK = HexColor('#000000')
GREEN = HexColor('#86b146')
DARK_GREEN = HexColor('#42994a')
WIDTH, HEIGHT = A4
MARGIN = 2 * cm

CONTENT_WIDTH = WIDTH - 2 * MARGIN
CONTENT_HEIGHT = HEIGHT - 2 * MARGIN

DEBUG_MODE = False
SIGNATURE_AT_BOTTOM = False
INSTRUCTIONS_IN_COLUMN = True
DEFAULT_FLAGS = 1

input_width_fraction = 1/2
radio_columns = 2
min_fields_on_page = 1

instruction_style = ParagraphStyle(
    'instructions',
    fontSize=12,
    alignment=TA_CENTER
)

header_style = ParagraphStyle(
    'header',
    fontSize=17,
    leading=22,
    textColor=BACKGROUND,
    alignment=TA_RIGHT,
    backColor=GREEN,
    borderWidth=1 * mm,
    borderColor=DARK_GREEN,
    borderRadius=2 * mm,
    borderPadding=(2 * mm, 5 * mm)
)

def set_background(pdf, color=BACKGROUND):
    pdf.setFillColor(color)
    pdf.rect(0, 0, 900, 900, fill=1)


def get_field_height(field):
    if field['type'] == 'radio':
        return 30 * len(field['options']) // radio_columns
    elif field['type'] == 'textarea':
        return 70
    else:
        return 30


def get_section_height(section):
    return sum(get_field_height(field) for field in section['fields']) + 30


def print_footer(pdf):
    footer_style = ParagraphStyle(
        name='footer',
        fontName='Helvetica',
        fontSize=10,
        textColor=FOOTER_COLOR,
        alignment=TA_CENTER,
    )
    text = '<br />'.join([
        'Central Asia. Middle East. Differently.',
        'Saiga Tours - Almaty Kazakhstan - <a href="https://www.saigatours.com">saigatours.com</a>',
        'WhatsApp: <a href="tel:+77 079 148 146">+77 079 148 146</a> - Email: <a href="mailto:tours@saigatours.com">tours@saigatours.com</a>',
    ])
    footer = Paragraph(text, footer_style)
    footer.wrap(CONTENT_WIDTH, MARGIN)
    footer.drawOn(pdf, MARGIN, MARGIN - footer.height)


def start_new_page(pdf, cursor_pos):
    if DEBUG_MODE:
        pdf.rect(MARGIN, MARGIN, CONTENT_WIDTH, CONTENT_HEIGHT, fill=0)
    pdf.showPage()
    cursor_pos = HEIGHT - MARGIN
    set_background(pdf)
    print_footer(pdf)
    if DEBUG_MODE:
        pdf.rect(MARGIN, MARGIN, CONTENT_WIDTH, CONTENT_HEIGHT, fill=0)
    return cursor_pos


def wrap_field(field, pdf, cursor_pos):
    if cursor_pos - get_field_height(field) < MARGIN:
        cursor_pos = start_new_page(pdf, cursor_pos)
    return cursor_pos


def wrap_section(section, pdf, cursor_pos):
    header = Paragraph(section['title'], header_style)
    header.wrap(CONTENT_WIDTH, CONTENT_HEIGHT)
    if cursor_pos - header.height - get_field_height(section['fields'][0]) < MARGIN:
        cursor_pos = start_new_page(pdf, cursor_pos)
    #if len(section['fields']) < min_fields_on_page:
        #if cursor_pos - get_section_height(section) < MARGIN:
            #cursor_pos = start_new_page(pdf, cursor_pos)
    #elif cursor_pos - get_field_height(section['fields'][min_fields_on_page - 1]) < MARGIN:
        #cursor_pos = start_new_page(pdf, cursor_pos)
    #elif cursor_pos - get_section_height(section) + get_field_height(section['fields'][0 - min_fields_on_page]) < MARGIN:
        #cursor_pos = start_new_page(pdf, cursor_pos)
    return cursor_pos


field_instruction_style = ParagraphStyle(
    name='field_instruction',
    fontName='Helvetica',
    fontSize=10,
    textColor=BLACK,
)

label_style = ParagraphStyle(
    name='label',
    fontName='Helvetica',
    fontSize=12,
    textColor=BLACK,
)


def print_field_label(field, pdf, cursor_pos):
    if field['type'] == 'date':
        label_text = f'{field["title"]} (dd/mm/yyyy):'
    else:
        label_text = f'{field["title"]}:'

    label = Paragraph(label_text, label_style)
    label.wrap(CONTENT_WIDTH * (1 - input_width_fraction) - 10, CONTENT_HEIGHT)
    label.drawOn(pdf, MARGIN, cursor_pos - label.height - 7)
    cursor_pos -= label.height + 10

    return cursor_pos


def print_field_instructions(field, pdf, cursor_pos):
    extra_margin = 10
    width = CONTENT_WIDTH * input_width_fraction - extra_margin * 2 if INSTRUCTIONS_IN_COLUMN else CONTENT_WIDTH - extra_margin * 2
    if field['type'] == 'file' and not field.get('file', None):
        instructions = Paragraph('Please include this file when you submit the form.', field_instruction_style)
        instructions.wrap(width, MARGIN)
        instructions.drawOn(pdf, MARGIN + extra_margin, cursor_pos - instructions.height)
        cursor_pos -= instructions.height + 10
    if field['instructions']:
        instructions = Paragraph(field['instructions'], field_instruction_style)
        instructions.wrap(width, MARGIN)
        instructions.drawOn(pdf, MARGIN + extra_margin, cursor_pos - instructions.height)
        cursor_pos -= instructions.height + 10
    return cursor_pos


def print_date_field(pdf, origin, width, height, name, value=None, date=None):
    slash_width = 10
    print("Full width: ", width)
    print("Slash width: ", slash_width)
    print("Field width - slash width: ", width - slash_width * 2)
    field_width = (width - slash_width * 2) / 3
    print("Field width: ", field_width)
    value = datetime.strptime(value, '%Y-%m-%d').date() if value else None
    pdf.acroForm.textfield(
        name=f'{name}_day',
        tooltip=f'{name}_day',
        x=origin[0],
        y=origin[1] - height,
        borderStyle='inset',
        borderColor=BLACK,
        fillColor=WHITE,
        forceBorder=True,
        width=(width - slash_width * 2) / 3,
        height=height,
        value=str(value.day) if value else '',
        fieldFlags=DEFAULT_FLAGS
    )
    pdf.acroForm.textfield(
        name=f'{name}_month',
        tooltip=f'{name}_month',
        x=origin[0] + field_width + slash_width,
        y=origin[1] - height,
        borderStyle='inset',
        borderColor=BLACK,
        fillColor=WHITE,
        forceBorder=True,
        width=(width - slash_width * 2) / 3,
        height=height,
        value=str(value.month) if value else '',
        fieldFlags=DEFAULT_FLAGS
    )
    pdf.acroForm.textfield(
        name=f'{name}_year',
        tooltip=f'{name}_year',
        x=origin[0] + 2 * (field_width + slash_width),
        y=origin[1] - height,
        borderStyle='inset',
        borderColor=BLACK,
        fillColor=WHITE,
        forceBorder=True,
        width=(width - slash_width * 2) / 3,
        height=height,
        value=str(value.year) if value else '',
        fieldFlags=DEFAULT_FLAGS
    )
    pdf.saveState()
    pdf.setFillColor(BLACK)
    pdf.setFont('Helvetica', height)
    pdf.drawCentredString(origin[0] + field_width + slash_width / 2, origin[1] - height * 9 / 10, '/')
    pdf.drawCentredString(origin[0] + 2 * field_width + slash_width * 3/2, origin[1] - height * 9 / 10, '/')


def print_signature_instructions(instructions, pdf, cursor_pos):
    instructions = Paragraph(instructions, field_instruction_style)
    instructions.wrap(CONTENT_WIDTH, MARGIN)
    instructions.drawOn(pdf, MARGIN, cursor_pos - instructions.height)
    cursor_pos -= instructions.height + 10
    return cursor_pos


def print_signature_box(pdf, cursor_pos):
    pdf.saveState()
    width = CONTENT_WIDTH * 2/3 - 10
    height = width / 2
#    pdf.acroForm.textfield(
#        name='signature',
#        tooltip='Signature',
#        x=MARGIN,
#        y=cursor_pos - height,
#        borderStyle='inset',
#        borderColor=BLACK,
#        fillColor=WHITE,
#        forceBorder=True,
#        width=width,
#        height=width / 2,
#        fieldFlags=DEFAULT_FLAGS
#    )
    pdf.rect(MARGIN, cursor_pos - height, width, height, stroke=1, fill=0)
    pdf.setFillColor(WHITE)
    pdf.rect(MARGIN, cursor_pos - height, width, height, stroke=0, fill=1)
    cursor_pos -= height + 10
    pdf.restoreState()
    return cursor_pos

def print_signature(pdf, cursor_pos, svg):
    pdf.saveState()
    width = CONTENT_WIDTH * 2/3 - 10
    height = width / 2
    image = svg2rlg(svg)
    if image is not None:
        image.scale(width / image.width, height / image.height)
        image.drawOn(pdf, MARGIN, cursor_pos - height)
        cursor_pos -= height + 10
        pdf.restoreState()
        return cursor_pos


def wrap_signature(instructions, pdf, cursor_pos):
    instructions = Paragraph(instructions, field_instruction_style)
    instructions.wrap(CONTENT_WIDTH, MARGIN)
    instruction_height = instructions.height
    box_height = 50
    if cursor_pos - instruction_height - box_height - 10 < MARGIN:
        cursor_pos = start_new_page(pdf, cursor_pos)
    if SIGNATURE_AT_BOTTOM:
        cursor_pos = MARGIN + instruction_height + box_height + 10
    return cursor_pos


def gen_form_pdf(form_data):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf.setTitle(form_data['title'])

    cursor_pos = HEIGHT - MARGIN / 2

    set_background(pdf)

    # Draw header logo
    image_is_svg = Settings.load().logo.path.endswith('.svg')
    if image_is_svg:
        image = svg2rlg(Settings.load().logo.path)
    else:
        image = Image.open(Settings.load().logo.path)

    if image is not None:
        max_width = 250
        max_height = 150
        scale = min(max_width / image.width, max_height / image.height)
        width = int(image.width * scale)
        height = int(image.height * scale)

        x = WIDTH / 2 - width / 2
        y = cursor_pos - height
        cursor_pos -= height + 10

        if type(image) is Drawing:
            image.scale(scale, scale)
            image.drawOn(pdf, x, y)
        else:
            #image.resize((width, height))
            pdf.drawInlineImage(image, x, y, width, height)


    # Draw title
    pdf.setFont('Helvetica-Bold', 20)
    pdf.setFillColor(BLACK)
    pdf.drawCentredString(WIDTH / 2, cursor_pos - 20, form_data['title'])
    cursor_pos -= 40

    # Draw instructions
    instructions = Paragraph(strip_tags(form_data['instructions']), instruction_style)
    instructions.wrap(WIDTH - MARGIN * 2, HEIGHT - MARGIN * 2)
    instructions.drawOn(pdf, MARGIN, cursor_pos - instructions.height)
    cursor_pos -= instructions.height + 20

    print_footer(pdf)

    if DEBUG_MODE:
        pdf.rect(MARGIN, MARGIN, WIDTH - MARGIN * 2, HEIGHT - MARGIN * 2)

    for section in form_data.get('sections'):
        cursor_pos = wrap_section(section, pdf, cursor_pos)

        # Draw header
        header = Paragraph(section['title'], header_style)
        header.wrap(CONTENT_WIDTH, CONTENT_HEIGHT)
        header.drawOn(pdf, MARGIN, cursor_pos - header.height)
        cursor_pos -= header.height + 10

        # Draw fields
        for field in section['fields']:
            cursor_pos = wrap_field(field, pdf, cursor_pos)

            post_label_cursor_pos = print_field_label(field, pdf, cursor_pos)

            if field['type'] == 'textarea':
                height = 60
                pdf.acroForm.textfield(
                    name=field['name'],
                    tooltip=field['title'],
                    x=CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN,
                    y=cursor_pos - height - 4,
                    width=CONTENT_WIDTH * input_width_fraction,
                    height=height,
                    borderStyle='solid',
                    borderColor=BLACK,
                    borderWidth=1,
                    fillColor=WHITE,
                    textColor=BLACK,
                    forceBorder=True,
                    value=field.get('value', '') or '',
                    maxlen=None,
                    fieldFlags=1<<12 | DEFAULT_FLAGS,
                )
                post_input_cursor_pos = 60
            elif field['type'] == 'checkbox':
                pdf.acroForm.checkbox(
                    name=field['name'],
                    tooltip=field['title'],
                    x=CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN,
                    y=cursor_pos - 24,
                    buttonStyle='cross',
                    borderStyle='solid',
                    borderColor=BLACK,
                    borderWidth=1,
                    fillColor=WHITE,
                    textColor=BLACK,
                    forceBorder=True,
                    checked=field.get('value', False),
                    fieldFlags=DEFAULT_FLAGS,
                )
                post_input_cursor_pos = 20
            elif field['type'] in ['select', 'countries']:
                if field['type'] == 'countries':
                    options = list(map(lambda x: x[1], countries))
                    value = dict(countries).get(field.get('value', ''), '')
                else:
                    options = list(map(lambda x: x['value'], field['options']))
                    value = field.get('value', '')

                # Add blank option:
                options.insert(0, '')
                print(options)
                pdf.acroForm.choice(
                    name=field['name'],
                    tooltip=field['title'],
                    x=CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN,
                    y=cursor_pos - 24,
                    width=CONTENT_WIDTH * input_width_fraction,
                    height=20,
                    borderStyle='solid',
                    borderColor=BLACK,
                    borderWidth=1,
                    fillColor=WHITE,
                    textColor=BLACK,
                    forceBorder=True,
                    options=options,
                    value=[value or ''],
                    fieldFlags=DEFAULT_FLAGS,
                )
                post_input_cursor_pos = 20
            elif field['type'] == 'radio':
                initial_cursor_pos = cursor_pos

                for index, option in enumerate(field['options']):
                    x_offset = (CONTENT_WIDTH * input_width_fraction / radio_columns) * (index % radio_columns)
                    size = 20
                    gap = 10
                    pdf.acroForm.radio(
                        name=field['title'],
                        value=option['value'],
                        tooltip=option['value'],
                        x=CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN + x_offset,
                        y=cursor_pos - 24,
                        buttonStyle='circle',
                        borderStyle='solid',
                        borderColor=BLACK,
                        borderWidth=1,
                        fillColor=WHITE,
                        textColor=BLACK,
                        forceBorder=True,
                        size=size,
                        fieldFlags=DEFAULT_FLAGS,
                    )
                    pdf.setFillColor(BLACK)
                    pdf.setFont('Helvetica', 12)
                    pdf.drawString(
                        CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN + size + x_offset + gap,
                        cursor_pos - 20,
                        option['value']
                    )
                    if index % radio_columns == radio_columns - 1:
                        cursor_pos -= size + (gap if index < len(field['options']) - 1 else 0)

                post_input_cursor_pos = initial_cursor_pos - cursor_pos
                cursor_pos = initial_cursor_pos

            elif field['type'] == 'file':
                filename_text = str(field.get('filename', None)) or 'no file uploaded'
                pdf.setFillColor(BLACK)
                pdf.setFont('Helvetica', 12)
                pdf.drawString(
                    CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN,
                    cursor_pos - 20,
                    filename_text
                )
                string_width = pdf.stringWidth(filename_text, 'Helvetica', 12)
                if field.get('file', None):
                    pdf.linkURL(
                        str(field['file'].url),
                        (
                            CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN - 5,
                            cursor_pos - 24,
                            CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN + string_width + 5,
                            cursor_pos - 24 + 20
                        ),
                        thickness=0,
                        relative=0,
                        color=BLACK,
                        border=(0, 0, 0)
                    )

                post_input_cursor_pos = 20
            elif field['type'] == 'date':
                print(field)
                print(field.get('value', '') or '')
                print_date_field(
                    pdf,
                    [
                        CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN,
                        cursor_pos - 4,
                    ],
                    CONTENT_WIDTH * input_width_fraction,
                    20,
                    field.get('title', '') or '',
                    field.get('value', '') or '',
                )
            else:
                pdf.acroForm.textfield(
                    name=field['name'],
                    tooltip=field['title'],
                    x=int(CONTENT_WIDTH * (1 - input_width_fraction) + MARGIN),
                    y=int(cursor_pos - 24),
                    width=int(CONTENT_WIDTH * input_width_fraction),
                    height=20,
                    borderStyle='solid',
                    borderColor=BLACK,
                    borderWidth=1,
                    fillColor=WHITE,
                    textColor=BLACK,
                    forceBorder=True,
                    value=field.get('value', '').replace('\u202f', ' ') or '',
                    #maxlen=None,
                    fieldFlags=DEFAULT_FLAGS,
                )
                post_input_cursor_pos = 20

            cursor_pos = min(post_label_cursor_pos, cursor_pos - post_input_cursor_pos)
            cursor_pos -= 2
            if INSTRUCTIONS_IN_COLUMN:
                cursor_pos = min(print_field_instructions(field, pdf, post_label_cursor_pos), cursor_pos)
            else:
                cursor_pos = print_field_instructions(field, pdf, cursor_pos)
            cursor_pos -= 8
            #cursor_pos = min(print_field_instructions(field, pdf, cursor_pos), post_label_cursor_pos)

        cursor_pos -= 30


    if form_data['signature_instructions']:
        cursor_pos = wrap_signature(form_data['signature_instructions'], pdf, cursor_pos)
        cursor_pos = print_signature_instructions(form_data['signature_instructions'], pdf, cursor_pos)
        print_date_field(
            pdf,
            [
                CONTENT_WIDTH * 2/3 + MARGIN,
                cursor_pos - 30,
            ],
            CONTENT_WIDTH * 1/3,
            20,
            'Date',
            '',
            form_data.get('finalised_date')
        )
        pdf.setFillColor(BLACK)
        pdf.setFont('Helvetica', 12)
        pdf.drawString(
            CONTENT_WIDTH * 2/3 + MARGIN,
            cursor_pos - 25,
            'Signed On'
        )
        pre_box_cursor = cursor_pos
        cursor_pos = print_signature_box(pdf, cursor_pos)

        if form_data.get('svg_signature', None):
            print_signature(pdf, pre_box_cursor, form_data.get('svg_signature', '').path)

    #pdf.setFont('Helvetica', 12)
    #pdf.setFillColor(BLACK)
    #pdf.drawCentredString(WIDTH / 2, cursor_pos - 20, strip_tags(form_data['instructions']))
    #cursor_pos -= 30

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return buffer

