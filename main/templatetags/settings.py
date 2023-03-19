from main.models import Settings
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def set_colors():
    settings = Settings.objects.get(pk=1)
    return mark_safe(f"""
    <style>
        :root {{
            --accent-background: {settings.accent_background};
            --accent-foreground: {settings.accent_foreground};
            --accent-hover-background: {settings.accent_hover_background};
            --accent-hover-foreground: {settings.accent_hover_foreground};
        }}
    </style>
    """)
