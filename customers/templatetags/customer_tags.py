from django import template

from customers.utils import split_phone_number

register = template.Library()

@register.filter(name='phone_code')
def phone_code(phone_number):
    return split_phone_number(phone_number)[0]

@register.filter(name='phone_number')
def phone_number(phone_number):
    return split_phone_number(phone_number)[1]
