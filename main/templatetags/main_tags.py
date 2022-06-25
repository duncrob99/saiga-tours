import calendar

from django import template
from django.core.paginator import Page
from django.utils.safestring import mark_safe

from main.models import Settings

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
