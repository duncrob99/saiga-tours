from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
import time
from functools import reduce

from job_queue.models import Task
from job_queue.utils import run_regular_tasks

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        while True:
            print("checking for queued jobs")
            task = Task.objects.filter(Q(scheduled_time__lte=timezone.now()) | Q(scheduled_time=None), completed=None).first()
            if task is None:
                time.sleep(1)
                run_regular_tasks()
                continue

            split = task.job.split(".")
            module = __import__(split[0])
            fn = reduce(getattr, split[1:], module)

            print(task.job, fn, task.args, task.kwargs)
            task.started = timezone.now()
            task.save()
            fn(*task.args, **task.kwargs)
            task.completed = timezone.now()
            task.save()
