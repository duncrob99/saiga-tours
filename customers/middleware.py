from django.shortcuts import redirect
from django.contrib import messages
from django.utils.html import format_html

class Enforce2FAForAdminsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        allowed_paths = ['/account/two_factor', '/static', '/messages', '/media', '/account/logout', '/favicon.ico', '/stats', '/resized-image']
        if request.user.is_staff and not request.user.is_verified() and not any([request.path.startswith(path) for path in allowed_paths]):
            print(f"User {request.user} is not verified and is trying to access {request.path}")
            #messages.warning(request, 'You must enable Two-Factor Authentication to access the site as an admin.')
            #return redirect('two_factor:setup')
            message_text = format_html('You will soon be required to enable Two-Factor Authentication to access the site as an admin. Do it now by clicking <a class="nice-link" href="/account/two_factor">here</a>.')
            # for message in messages.get_messages(request):
                # if message.message == message_text:
                    # break
            if not any([message.message == message_text for message in messages.get_messages(request)]):
                messages.warning(request, message_text, extra_tags='safe')

        response = self.get_response(request)
        return response

