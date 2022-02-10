from django import template

register = template.Library()


@register.inclusion_tag('analytics/include_script.html', takes_context=True)
def analytics_script(context):
    # return {
    #     'request': context['request'],
    # }
    return context


@register.inclusion_tag('analytics/cookie_banner.html')
def cookie_banner():
    return {}


@register.inclusion_tag('analytics/sub_request.html', takes_context=True)
def sub_request(context):
    return context
