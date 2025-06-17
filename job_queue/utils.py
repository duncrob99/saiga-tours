from .models import Task

def run_regular_tasks():
    from main.models import check_links
    check_links()

def add_task(job, *args, scheduled_time=None, **kwargs):
    job_str = f"{job.__module__}.{job.__name__}"
    task = Task(job=job_str, scheduled_time=scheduled_time, args=args, kwargs=kwargs)
    task.save()

