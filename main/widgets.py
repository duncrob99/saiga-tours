from django.conf import settings
from django.forms import widgets
from urllib import parse as urlparse
from django.utils.html import escape

from django.utils.safestring import mark_safe

COUNTRY_CHANGE_HANDLER = (
    "var e=document.getElementById('flag_' + this.id); "
    "if (e) setFlag(e, '%s'"
    # "if (e) e.src = '%s'"
    ".replace('{code}', this.value.toLowerCase() || 'xx')"
    ".replace('{code_upper}', this.value.toUpperCase() || 'xx')"
    ");"
)

FLAG_URL = urlparse.urljoin(settings.STATIC_URL, 'images/flags/{code}.svg')


class CountrySelectWidget(widgets.Select):
    def __init__(self, *args, **kwargs) -> None:
        self.layout = '<div class="country-selector"> {widget}<div class="flag-container"><img class="country-select-flag" id="{flag_id}" src=' + FLAG_URL + ' /></div></div>'
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        from django_countries.fields import Country

        attrs = attrs or {}
        widget_id = attrs and attrs.get("id")
        if widget_id:
            flag_id = f"flag_{widget_id}"
            attrs["onchange"] = COUNTRY_CHANGE_HANDLER % FLAG_URL
        else:
            flag_id = ""
        widget_render = super().render(name, value, attrs, renderer)
        if isinstance(value, Country):
            country = value
        else:
            country = Country(value or "xx")
        with country.escape:
            return mark_safe(  # nosec
                self.layout.format(
                    widget=widget_render, country=country, flag_id=escape(flag_id), code=country.code.lower()
                )
            )
