import time
import logging


logging.basicConfig(level=logging.INFO)


class StatsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()

        response = self.get_response(request)

        duration = time.perf_counter() - start_time

        # Add the header. Or do other things, my use case is to send a monitoring metric
        # response["X-Page-Generation-Duration-ms"] = int(duration * 1000)
        logging.info(f'Response time for {request.method} {request.path}: {round(duration*100, 5)}ms')
        return response


class CacheControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Prevent cache for logged in users
        if request.user is not None and request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
