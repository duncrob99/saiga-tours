import datetime
import json
import re
from collections import defaultdict

import requests
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Max, Min
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ipware import get_client_ip

from travel_website import settings
from .forms import SubscriptionForm
from .models import UserCookie, Session, Page, PageView, MouseAction, SubscriptionSubmission


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + datetime.timedelta(n)


def ip_location(ip: str):
    # response = requests.get(f'https://ipwhois.app/json/{ip}')
    response = requests.get(f'http://ip-api.com/json/{ip}')
    return json.loads(response.content)


# Create your views here.
@csrf_exempt
def view(request):
    if 'user_id' not in request.POST:
        user = UserCookie.objects.create(staff=request.user.is_staff, user_agent=request.META['HTTP_USER_AGENT'])
        new_user = True
    else:
        try:
            user = UserCookie.objects.get(uuid=request.POST.get('user_id'))
            new_user = False
            if request.user.is_staff and not user.staff:
                user.staff = True
                user.save()
            if not user.user_agent:
                user.user_agent = request.META['HTTP_USER_AGENT']
        except ValidationError:
            user = UserCookie.objects.create(staff=request.user.is_staff, user_agent=request.META['HTTP_USER_AGENT'])
            new_user = True

    # Check if referer includes allowed host
    referer_is_allowed_host = len(list(set(re.split('[/:]', request.POST.get('referer'))) & set(settings.ALLOWED_HOSTS))) > 0
    if referer_is_allowed_host and 'session_id' in request.POST and request.POST.get('session_id') != '':
        session, _ = Session.objects.get_or_create(session_id=request.POST.get('session_id'), user=user)
    else:
        session = Session.objects.create(user=user)

    show_subscription = user.should_request_subscription
    if show_subscription:
        user.last_subscription_request = timezone.now()
        user.sub_dismissal_count += 1
        user.save()

    page, _ = Page.objects.get_or_create(path=request.POST.get('path'))
    page_view = PageView.objects.create(session=session, page=page)
    page_view.duration = datetime.timedelta(milliseconds=int(request.POST.get('interval')) / 2)
    page_view.referer = request.POST.get('referer')

    response_content = {
        'new_user': new_user,
        'accepted_cookies': user.accepted_cookies,
        'show_subscription': show_subscription,
        'user_id': user.uuid,
        'pageview': page_view.uuid,
        'session_id': session.session_id,
    }
    response = JsonResponse(response_content)

    client_ip, is_routable = get_client_ip(request)
    if client_ip is not None:
        page_view.ip_info = ip_location(client_ip)
        page_view.save()

    return response


@csrf_exempt
def accept_cookies(request):
    if 'user_id' in request.POST:
        user = UserCookie.objects.get(uuid=request.POST.get('user_id'))
        user.accepted_cookies = True
        user.save()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})


@csrf_exempt
def assign_email(request):
    user = UserCookie.objects.get(uuid=request.POST.get('user_id'))
    email = request.POST.get('email')
    user.email = email

    return JsonResponse({'success': True})


@csrf_exempt
def heartbeat(request):
    if 'pageview' in request.POST:
        page_view = PageView.objects.get(uuid=request.POST.get('pageview'))

        page_view.duration = timezone.now() - page_view.time + datetime.timedelta(
            milliseconds=int(request.POST.get('interval')) / 2)
        page_view.time_visible += datetime.timedelta(milliseconds=int(request.POST.get('time_visible')))
        page_view.save()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})


@csrf_exempt
def close_view(request):
    if 'pageview' in request.POST and 'user_id' in request.POST:
        user = UserCookie.objects.get(uuid=request.POST.get('user_id'))
        # session = Session.objects.get(session_id=request.session['session_id'], user=user)
        # page = Page.objects.get(path=request.POST.get('path'))

        page_view = PageView.objects.get(uuid=request.POST.get('pageview'))
        page_view.duration = timezone.now() - page_view.time
        page_view.time_visible += datetime.timedelta(milliseconds=float(request.POST.get('time_visible')))
        page_view.complete = True
        page_view.save()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})


@csrf_exempt
def mouse_action(request):
    if 'pageview' in request.POST:
        page_view = PageView.objects.get(uuid=request.POST.get('pageview'))
        clicked = int(request.POST.get('clicked')) + 1 if request.POST.get('clicked') is not None else None
        new_action = MouseAction.objects.create(view=page_view,
                                                x=int(request.POST.get('x')),
                                                y=int(request.POST.get('y')),
                                                clicked=clicked)

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})


@csrf_exempt
def subscribe(request, return_path: str = None):
    form = SubscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            subscription = SubscriptionSubmission.objects.create(email_address=form.cleaned_data['email'],
                                                                 name=form.cleaned_data['name'])
            messages.add_message(request, messages.SUCCESS, 'Successfully subscribed')
        except IntegrityError:
            subscription = SubscriptionSubmission.objects.get(email_address=form.cleaned_data['email'])
            messages.add_message(request, messages.SUCCESS, 'Successfully subscribed')

            user = UserCookie.objects.get(uuid=request.POST.get('user_id'))
            user.subscription = subscription
            user.save()
    else:
        errors = "; ".join([f'{field}: {", ".join(errors)}' for field, errors in form.errors.items()])
        messages.add_message(request, messages.WARNING, f'Invalid attempt to subscribe: {errors}')
    if return_path is not None:
        return HttpResponseRedirect(return_path)
    else:
        return redirect('front-page')


def batch_close_views():
    current_time = timezone.now()
    for page_view in PageView.objects.filter(complete=False):
        if current_time - page_view.time - page_view.duration > datetime.timedelta(seconds=60):
            page_view.complete = True
            page_view.save()


def statistics(request):
    batch_close_views()

    if not request.user.is_staff:
        raise Http404()

    client_ip, _ = get_client_ip(request)
    if client_ip is not None:
        location = ip_location(client_ip)
        if 'timezone' in location:
            timezone.activate(location['timezone'])
        else:
            timezone.activate(ip_location('14.137.208.189')['timezone'])

    max_date = timezone.localdate(PageView.objects.all().aggregate(Max('time'))['time__max'])
    min_date = timezone.localdate(PageView.objects.all().aggregate(Min('time'))['time__min'])

    daily_viewcounts = []
    daily_visitors = []
    for date in daterange(min_date, max_date):
        day_start = datetime.datetime(date.year, date.month, date.day, tzinfo=timezone.get_current_timezone())
        day_end = day_start + datetime.timedelta(days=1)
        daily_viewcounts.append(PageView.objects.filter(time__gte=day_start, time__lt=day_end).count())
        daily_visitors.append(UserCookie.objects.filter(session__pageview__time__gte=day_start,
                                                        session__pageview__time__lt=day_end).distinct().count())

    views_per_visitor = []
    for visitor in UserCookie.objects.all():
        views_per_visitor.append(PageView.objects.filter(session__user=visitor).count())

    PageView.calc_durs()
    session_durations = []
    for session in Session.objects.all():
        if session.duration is not None:
            session_durations.append(session.duration.seconds / 60)

    UserCookie.calc_uas()
    browser_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))))
    os_stats = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))))
    device_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
    for user in UserCookie.objects.all():
        browser = user.user_agent_info['user_agent']
        os = user.user_agent_info['os']
        device = user.user_agent_info['device']

        pageviews = user.pageviews
        viewtime = (user.viewtime or datetime.timedelta(seconds=0)).seconds / 60

        browser_stats[browser['family']][browser['major']][browser['minor']][browser['patch']]['users'] += 1
        browser_stats[browser['family']][browser['major']][browser['minor']][browser['patch']][
            'pageviews'] += pageviews

        os_stats[os['family']][os['major']][os['minor']][os['patch']][os['patch_minor']]['users'] += 1
        os_stats[os['family']][os['major']][os['minor']][os['patch']][os['patch_minor']]['pageviews'] += pageviews

        device_stats[device['family']][device['brand']][device['model']]['users'] += 1
        device_stats[device['family']][device['brand']][device['model']]['pageviews'] += pageviews

        if viewtime is not None:
            browser_stats[browser['family']][browser['major']][browser['minor']][browser['patch']][
                'viewtime'] += viewtime
            os_stats[os['family']][os['major']][os['minor']][os['patch']][os['patch_minor']][
                'viewtime'] += viewtime
            device_stats[device['family']][device['brand']][device['model']]['viewtime'] += viewtime

    def format_children_for_sunburst(data: dict):
        if isinstance(list(list(data.values())[0].values())[0], dict):
            return [{'name': key, 'children': format_children_for_sunburst(value)} for key, value in data.items()]
        else:
            return [{'name': key} | values for key, values in data.items()]

    def format_for_sunburst(data: dict):
        if len(data) > 0:
            return {'name': '', 'children': format_children_for_sunburst(data)}
        else:
            return {'name': '', 'children': []}

    lats = []
    lons = []
    for view in PageView.objects.filter(ip_info__isnull=False, ip_info__lat__isnull=False, ip_info__lon__isnull=False):
        lats.append(view.ip_info['lat'])
        lons.append(view.ip_info['lon'])

    context = {
        'days': daterange(min_date, max_date),
        'daily_viewcounts': daily_viewcounts,
        'daily_visitors': daily_visitors,
        'views_per_visitor': views_per_visitor,
        'session_durations': session_durations,
        'browser_stats': json.dumps(format_for_sunburst(browser_stats)),
        'os_stats': json.dumps(format_for_sunburst(os_stats)),
        'device_stats': json.dumps(format_for_sunburst(device_stats)),
        'lats': json.dumps(lats),
        'lons': json.dumps(lons)
    }
    return render(request, 'stats/statistics.html', context)
