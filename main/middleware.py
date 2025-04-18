import re
from bs4 import BeautifulSoup
from typing import Any, Dict

from django.conf import settings
from django.http import HttpResponse, HttpRequest

from main.models import PageCache


def minify_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    return str(soup)


class CacheForUsers:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        bypass_urls = [
            r'^/admin/',
            r'^/static/',
            r'^/media/',
            r'^/stats/',
            r'^/testimonials/',
            r'^/customers/',
            r'^/sitemap\.xml',
            r'^/robots\.txt',
            r'^/messages',
            r'^/account/',
        ]

        path = request.path

        is_get = request.method == 'GET'
        has_no_query_params = len(request.GET) == 0
        is_anonymous = not request.user.is_authenticated
        not_bypassed_url = not any(re.match(ignored_path, path) for ignored_path in bypass_urls)

        if is_get and is_anonymous and has_no_query_params and not_bypassed_url and not settings.NOCACHE:
            # Retrieve response from PageCache if it exists, otherwise store response
            try:
                try:
                    cache = PageCache.objects.get(url=path)
                    response = HttpResponse(cache.content)
                except PageCache.MultipleObjectsReturned:
                    cache = PageCache.objects.filter(url=path).first()
                    response = HttpResponse(cache.content)
                    # Delete duplicates other than the one we retrieved
                    PageCache.objects.filter(url=path).exclude(id=cache.id).delete()
                response['DB-cache-status'] = 'HIT'
            except PageCache.DoesNotExist:
                response = self.get_response(request)
                if isinstance(response, HttpResponse) and response.status_code == 200 and response.get("Content-Type", "").startswith("text/html"):
                    # Minify HTML response
                    minified = minify_html(response.content)
                    PageCache.objects.create(url=path, content=minified)
                response['DB-cache-status'] = 'MISS'
        else:
            response = self.get_response(request)
            response['DB-cache-status'] = 'NO-CACHE' + (';is-not-get' if not is_get else '') + (';has-query' if not has_no_query_params else '') + (';authed' if not is_anonymous else '') + (';bypassed-url' if not not_bypassed_url else '') + (';nocache-env' if settings.NOCACHE else '')

        return response
