from typing import List
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve, reverse
from django.utils.html import format_html

from main.models import Link

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
            all_messages = messages.get_messages(request)
            if not isinstance(all_messages, List):
                if not any([message.message == message_text for message in all_messages]):
                    messages.warning(request, message_text, extra_tags='safe')
                all_messages.used = False

        if request.user.is_staff:
            num_broken_links = Link.objects.filter(broken=True).count()
            hidden_paths = ["/api", "/admin/jsi18n", "/media", "/stats", "/resized-image", "/messages", "/static", "/favicon.ico"]
            if num_broken_links > 0 and not resolve(request.path).view_name.startswith("admin:main_link") and not any([request.path.startswith(path) for path in hidden_paths]):
                message_text = format_html(f"There are {num_broken_links} broken links. <a data-message-origin-path='{request.path}' class='nice-link' href='{reverse('admin:main_link_changelist')}?broken__exact=1'>See them here</a>")

                all_messages = messages.get_messages(request)
                if not isinstance(all_messages, List):
                    if not any([message.message == message_text for message in all_messages]):
                        messages.warning(request, message_text, extra_tags='safe')
                    all_messages.used = False

        response = self.get_response(request)
        return response

