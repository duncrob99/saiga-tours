import datetime
import uuid
from enum import Enum

from computedfields.models import ComputedFieldsModel
from django.db import models
from django.db.models import Max, Min


# Create your models here.
class UserCookie(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    staff = models.BooleanField(default=False)


class Session(models.Model):
    user = models.ForeignKey(UserCookie, on_delete=models.CASCADE, editable=False)
    session_id = models.CharField(max_length=100, editable=False)

    @property
    def duration(self):
        return self.pageview_set.aggregate(dur=Max('end_time') - Min('time'))['dur']


class Page(models.Model):
    path = models.CharField(max_length=300, editable=False)


class PageView(ComputedFieldsModel):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, editable=False)
    time = models.DateTimeField(editable=False, auto_now_add=True)
    end_time = models.DateTimeField(null=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, editable=False)
    duration = models.DurationField(default=datetime.timedelta(0), editable=False)
    complete = models.BooleanField(default=False, editable=False)
    ip_info = models.JSONField(null=True, blank=True)


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
