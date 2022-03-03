from django import template

register = template.Library()


@register.inclusion_tag('stats/include_script.html', takes_context=True)
def analytics_script(context):
    # return {
    #     'request': context['request'],
    # }
    return context


@register.inclusion_tag('stats/cookie_banner.html')
def cookie_banner():
    return {}


@register.inclusion_tag('stats/sub_request.html', takes_context=True)
def sub_request(context):
    return context
