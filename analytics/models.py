import datetime
from datetime import timedelta
import uuid
from enum import Enum

from django.db import models
from django.db.models import Max, Min, Sum, Count
from django.utils import timezone
from ua_parser import user_agent_parser


# Create your models here.
class SubscriptionSubmission(models.Model):
    email_address = models.EmailField(unique=True)
    name = models.CharField(max_length=500, null=True, blank=True)
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email_address

    def save(self, *args, **kwargs):
        if self.pk is None:
            super(SubscriptionSubmission, self).save(*args, **kwargs)


class UserCookie(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    staff = models.BooleanField(default=False)
    user_agent = models.CharField(max_length=500)
    user_agent_info = models.JSONField(null=True, blank=True)
    accepted_cookies = models.BooleanField(default=False)
    subscription = models.OneToOneField(SubscriptionSubmission, on_delete=models.SET_NULL, null=True, blank=True)
    last_subscription_request = models.DateTimeField(null=True, blank=True)
    sub_dismissal_count = models.SmallIntegerField(default=0)

    subscription_delays = [timedelta(minutes=20),
                           timedelta(hours=1),
                           timedelta(days=1),
                           timedelta(days=3),
                           timedelta(weeks=1)]

    @property
    def should_request_subscription(self):
        return self.subscription is None and \
               (self.last_subscription_request is None or
                timezone.now() - self.last_subscription_request >= self.subscription_delays[min(len(self.subscription_delays) - 1, self.sub_dismissal_count)])

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
        # return self.pageview_set.aggregate(dur=Max('end_time') - Min('time'))['dur']
        return self.pageview_set.aggregate(sum=Sum('time_visible'))['sum']


class Page(models.Model):
    path = models.CharField(max_length=300, editable=False)


class PageView(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
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
