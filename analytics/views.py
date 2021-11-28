import datetime
import json

import requests
from django.core.exceptions import ValidationError
from django.db.models import Max, Min
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.utils import timezone
from ipware import get_client_ip

from .models import UserCookie, Session, Page, PageView, MouseAction


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + datetime.timedelta(n)


def ip_location(ip: str):
    # response = requests.get(f'https://ipwhois.app/json/{ip}')
    response = requests.get(f'http://ip-api.com/json/{ip}')
    return json.loads(response.content)


# Create your views here.
def view(request):
    if 'userID' not in request.COOKIES:
        user = UserCookie.objects.create(staff=request.user.is_staff, user_agent=request.META['HTTP_USER_AGENT'])
        response = JsonResponse({'new_user': True})
        response.set_cookie('userID', user.uuid, samesite='Lax')
    else:
        try:
            user = UserCookie.objects.get(uuid=request.COOKIES['userID'])
            response = JsonResponse({'new_user': False})
            if request.user.is_staff and not user.staff:
                user.staff = True
                user.save()
            if not user.user_agent:
                user.user_agent = request.META['HTTP_USER_AGENT']
        except ValidationError:
            user = UserCookie.objects.create(staff=request.user.is_staff, user_agent=request.META['HTTP_USER_AGENT'])
            response = JsonResponse({'new_user': True})
            response.set_cookie('userID', user.uuid, samesite='Lax')

    session, _ = Session.objects.get_or_create(session_id=request.COOKIES['sessionid'], user=user)
    page, _ = Page.objects.get_or_create(path=request.POST.get('path'))
    PageView.objects.filter(session=session).update(complete=True)
    page_view = PageView.objects.create(session=session, page=page)
    page_view.duration = datetime.timedelta(milliseconds=int(request.POST.get('interval')) / 2)

    client_ip, is_routable = get_client_ip(request)
    if client_ip is not None:
        page_view.ip_info = ip_location(client_ip)
        page_view.save()

    return response


def heartbeat(request):
    user = UserCookie.objects.get(uuid=request.COOKIES['userID'])
    session = Session.objects.get(session_id=request.COOKIES['sessionid'], user=user)
    page = Page.objects.get(path=request.POST.get('path'))
    page_view = PageView.objects.get(session=session, page=page, complete=False)
    page_view.duration = timezone.now() - page_view.time + datetime.timedelta(
        milliseconds=int(request.POST.get('interval')) / 2)
    page_view.save()

    return JsonResponse({'success': True})


def close_view(request):
    user = UserCookie.objects.get(uuid=request.COOKIES['userID'])
    session = Session.objects.get(session_id=request.COOKIES['sessionid'], user=user)
    page = Page.objects.get(path=request.POST.get('path'))
    page_view = PageView.objects.get(session=session, page=page, complete=False)
    page_view.duration = timezone.now() - page_view.time
    page_view.complete = True
    page_view.save()

    return JsonResponse({'success': True})


def mouse_action(request):
    user = UserCookie.objects.get(uuid=request.COOKIES['userID'])
    session = Session.objects.get(session_id=request.COOKIES['sessionid'], user=user)
    page = Page.objects.get(path=request.POST.get('path'))
    page_view = PageView.objects.get(session=session, page=page, complete=False)
    clicked = int(request.POST.get('clicked')) + 1 if request.POST.get('clicked') is not None else None
    new_action = MouseAction.objects.create(view=page_view,
                                            x=int(request.POST.get('x')),
                                            y=int(request.POST.get('y')),
                                            clicked=clicked)

    return JsonResponse({'success': True})


def batch_close_views():
    current_time = timezone.now()
    for page_view in PageView.objects.filter(complete=False):
        if current_time - page_view.time - page_view.duration > 60:
            page_view.complete = True
            page_view.save()


def statistics(request):
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
        session_durations.append(session.duration.seconds / 60)

    context = {
        'days': daterange(min_date, max_date),
        'daily_viewcounts': daily_viewcounts,
        'daily_visitors': daily_visitors,
        'views_per_visitor': views_per_visitor,
        'session_durations': session_durations
    }
    return render(request, 'analytics/statistics.html', context)
