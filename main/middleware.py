from functools import wraps

from bs4 import BeautifulSoup
from django.http import HttpResponse

from main.models import PageCache


def minify_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    return str(soup)


class CacheForUsers:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'GET' and not request.user.is_authenticated:
            # Retrieve response from PageCache if it exists, otherwise store response
            try:
                try:
                    cache = PageCache.objects.get(url=request.path)
                    print(f'Retrieved PageCache for {request.path}')
                    response = HttpResponse(cache.content)
                except PageCache.MultipleObjectsReturned:
                    cache = PageCache.objects.filter(url=request.path).first()
                    print(f'Retrieved PageCache for {request.path}')
                    response = HttpResponse(cache.content)
                    # Delete duplicates other than the one we retrieved
                    PageCache.objects.filter(url=request.path).exclude(id=cache.id).delete()
                    print(f'Deleted duplicate PageCache(s) for {request.path}')
            except PageCache.DoesNotExist:
                response = self.get_response(request)
                if isinstance(response, HttpResponse) and response.status_code == 200 and response.get("Content-Type", "").startswith("text/html"):
                    # Minify HTML response
                    minified = minify_html(response.content)
                    PageCache.objects.create(url=request.path, content=minified)
                    print(f'Created PageCache for {request.path}')
                else:
                    print(f'Not an HttpResponse for {request.path}')
        else:
            response = self.get_response(request)

        return response
