from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
import time

from job_queue.models import Task
from job_queue.utils import job_types

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        while True:
            print("checking for queued jobs")
            task = Task.objects.filter(Q(scheduled_time__lte=timezone.now()) | Q(scheduled_time=None), completed=None).first()
            if task is None:
                time.sleep(1)
                continue
            fn = job_types[task.job]
            print(fn, task.args, task.kwargs)
            task.started = timezone.now()
            task.save()
            fn(*task.args, **task.kwargs)
            task.completed = timezone.now()
            task.save()
