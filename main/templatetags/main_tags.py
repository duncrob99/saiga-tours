import calendar
import math
from os import path

from PIL import Image
from bs4 import BeautifulSoup as bs
from io import BytesIO
import base64

from django import template
from django.conf import settings
from django.core.paginator import Page
from django.db.models import ImageField
from django.http import Http404
from django.utils.safestring import mark_safe

from main.models import Settings
from main.images import get_image_format, autorotate, crop_to_dims

register = template.Library()


@register.inclusion_tag('main/pagination_buttons.html')
def pagination_middle_buttons(page: Page):
    settings = Settings.load()
    middle_buttons = list(range(max(page.number - settings.pagination_middle_size, 1),
                                min(page.number + settings.pagination_middle_size + 1,
                                    page.paginator.num_pages + 1)))
    start_buttons = list(range(1, min(settings.pagination_outer_size + 1, middle_buttons[0])))
    end_buttons = list(range(max(page.paginator.num_pages - settings.pagination_outer_size, middle_buttons[-1]) + 1,
                             page.paginator.num_pages + 1))
    if len(start_buttons) > 0 and len(middle_buttons) > 0 and abs(start_buttons[-1] - middle_buttons[0]) == 1:
        start_buttons.append(start_buttons[-1] + 1)
    if len(end_buttons) > 0 and len(middle_buttons) > 0 and abs(middle_buttons[-1] - end_buttons[0]) > 1:
        middle_buttons.append(middle_buttons[-1] + 1)
    return {'middle_buttons': middle_buttons,
            'start_buttons': start_buttons,
            'end_buttons': end_buttons,
            'start_sep': len(start_buttons) > 0 and len(middle_buttons) > 0 and abs(
                start_buttons[-1] - middle_buttons[0]) > 1,
            'end_sep': len(end_buttons) > 0 and len(middle_buttons) > 0 and abs(
                middle_buttons[-1] - end_buttons[0]) > 1,
            'page': page
            }


@register.inclusion_tag('main/pagination_buttons.html')
def pagination_start_buttons(page: Page):
    settings = Settings.load()
    return {
        'buttons': list(
            range(1, min(settings.pagination_outer_size + 1, max(page.number - settings.pagination_middle_size, 1))))
    }


@register.inclusion_tag('main/pagination_buttons.html')
def pagination_end_buttons(page: Page):
    settings = Settings.load()
    return {
        'buttons': list(range(max(page.paginator.num_pages - settings.pagination_outer_size + 1,
                                  min(page.number + settings.pagination_middle_size + 1, page.paginator.num_pages + 1)),
                              page.paginator.num_pages + 1))
    }


@register.filter()
def convert_None(value, js_str='undefined'):
    return js_str if value is None else value


@register.filter()
def js_str(value):
    return 'undefined' if value is None else mark_safe(f'"{value}"')


def escape_quotes(string: str):
    return string.replace('`', '\\`')


@register.filter()
def js_html_str(value):
    return 'undefined' if value is None else mark_safe(f'`{escape_quotes(value)}`')


@register.filter()
def lazyload_html(value: str):
    return mark_safe(value.replace('src=', 'full-size-src='))


@register.filter()
def month_name(month_number: int):
    num = int(month_number)
    return calendar.month_name[num]


@register.filter()
def short_month_name(month_number: int):
    num = int(month_number)
    return calendar.month_abbr[num]


def is_empty_element(tag) -> bool:
    if tag.name in ['img', 'br', 'hr'] or tag.text.strip() != '':
        return False
    else:
        if 'contents' in dir(tag):
            for child in tag.contents:
                if not is_empty_element(child):
                    return False
            return True
        else:
            return True


@register.filter()
def delay_images(value: str, request):
    # print(value, value.replace('<img src=', '<img data-filename='))
    soup = bs(value, 'html.parser')
    img_tags = soup.find_all('img')

    for img in img_tags:
        if img.get('src').startswith('/resized-image/'):
            print("Found resized image", img.get('src'))
            img['src'] = img['src'].replace('/resized-image/', '/media/')
            img['src'] = '/'.join(img['src'].split('/')[:-2])

        if img.get('data-cke-saved-src') and img.get('data-cke-saved-src').startswith('/resized-image/'):
            img['data-cke-saved-src'] = img['data-cke-saved-src'].replace('/resized-image/', '/media/')
            img['data-cke-saved-src'] = '/'.join(img['data-cke-saved-src'].split('/')[:-2])

        if not (img['src'].startswith('http://') or img['src'].startswith('https://') or request.user.is_staff):
            img['data-filename'] = img['src']
            # Remove src attribute to avoid loading image
            img.attrs.pop('src')

            src_filename = (img.get('src') or img.get('data-cke-saved-src') or img.get('data-filename')).replace('/media/media/', 'media/')
            downscaled = downscaled_image(None, settings.MEDIA_ROOT / src_filename)
            img['src'] = downscaled

    # Ensure empty paragraphs and other text tags contain <br> tags
    for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'div', 'span']):
        if is_empty_element(p):
            p.string = ""
            p.append(soup.new_tag('br'))

    # Remove divs with 'table-holder' class
    for div in soup.find_all('div', {'class': 'table-holder'}):
        div.unwrap()

    # Ensure nothing is contenteditable
    for el in soup.find_all(contenteditable=True):
        el.attrs.pop('contenteditable')

    for box in soup.find_all('span'):
        if box.find('img', {'title': 'Click and drag to move'}):
            box.decompose()

    # print('soupstr: ', soup.str())
    return mark_safe(soup.prettify())
    # return mark_safe(value.replace('<img src=', '<img data-filename='))


@register.simple_tag()
def resized_image(url: str, x: int, y: int):
    print('resized_image', url, x, y)
    return f'/resized-image/{url.removeprefix(settings.MEDIA_URL)}/{x}x{y}/'


@register.simple_tag(takes_context=True)
def downscaled_image(context, img: ImageField, width: int = 10):
    try:
        raw_image = Image.open(img, mode='r')
    except FileNotFoundError:
        print('File not found:', img)
        return ''
    image = autorotate(raw_image)

    cropped_image = crop_to_dims(image, width, math.ceil(width * image.height / image.width))

    if context is not None:
        img_format, save_func = get_image_format(context.request, image)
    else:
        img_format = 'png'
        save_func = lambda img, loc: img.save(loc, img_format)

    buff = BytesIO()
    # cropped_image.save(buff, format=img_format)
    save_func(cropped_image, buff)
    img64 = base64.b64encode(buff.getvalue()).decode('utf-8')

    return f'data:image/{img_format};base64,{img64}'

@register.filter()
def strip_params(url: str):
    return url.split('?')[0].split('#')[0]

