from operator import inv
from django.utils import timezone

from .models import Task

def log(*args, **kwargs):
    print(*args, **kwargs)

def invalidate_pages(pages_to_invalidate):
    from main.models import invalidate_pages as ip
    ip(pages_to_invalidate)

job_types = {
    'log': log,
    'invalidate_pages': invalidate_pages
}

def add_task(job, *args, scheduled_time=None, **kwargs):
    task = Task(job=job, scheduled_time=scheduled_time, args=args, kwargs=kwargs)
    task.save()
