import datetime
import uuid
from enum import Enum

from django.db import models
from django.db.models import Max, Min, Sum, Count
from ua_parser import user_agent_parser


# Create your models here.
class UserCookie(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    staff = models.BooleanField(default=False)
    user_agent = models.CharField(max_length=200)
    user_agent_info = models.JSONField(null=True, blank=True)
    accepted_cookies = models.BooleanField(default=False)

    @classmethod
    def calc_uas(cls):
        for user in cls.objects.filter(user_agent_info__isnull=True):
            user.user_agent_info = user_agent_parser.Parse(user.user_agent)
            user.save()

    @property
    def pageviews(self):
        return self.session_set.aggregate(pageviews=Count('pageview'))['pageviews']

    @property
    def viewtime(self):
        return self.session_set.aggregate(viewtime=Sum('pageview__duration'))['viewtime']
    #     time = 0
    #     for session in self.session_set:
    #         time += session.pageview_set.annotate(watch_time=Sum('duration'))


class Session(models.Model):
    user = models.ForeignKey(UserCookie, on_delete=models.CASCADE, editable=False)
    session_id = models.CharField(max_length=100, default=uuid.uuid4)

    @property
    def duration(self):
        return self.pageview_set.aggregate(dur=Max('end_time') - Min('time'))['dur']


class Page(models.Model):
    path = models.CharField(max_length=300, editable=False)


class PageView(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, editable=False)
    referer = models.URLField(null=True, blank=True)

    time = models.DateTimeField(editable=False, auto_now_add=True)
    end_time = models.DateTimeField(null=True)
    duration = models.DurationField(default=datetime.timedelta(0), editable=False)
    time_visible = models.DurationField(default=datetime.timedelta(0))

    complete = models.BooleanField(default=False, editable=False)
    ip_info = models.JSONField(null=True, blank=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, editable=False)

    @classmethod
    def calc_durs(cls):
        for page in cls.objects.all():
            page.end_time = page.time + page.duration
            page.save()


class MouseAction(models.Model):
    class Button(Enum):
        UNDEFINED = 0
        LEFT = 1
        MIDDLE = 2
        RIGHT = 3

    view = models.ForeignKey(PageView, on_delete=models.CASCADE, editable=False)
    x = models.IntegerField(editable=False)
    y = models.IntegerField(editable=False)
    time = models.DateTimeField(editable=False, auto_now_add=True)
    clicked = models.PositiveSmallIntegerField(null=True, blank=True,
                                               choices=[(button, button.value) for button in Button], editable=False)
