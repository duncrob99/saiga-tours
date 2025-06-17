from django.db import models

# Create your models here.
class Task(models.Model):
    job = models.CharField(max_length=100)
    args = models.JSONField()
    kwargs = models.JSONField()
    scheduled_time = models.DateTimeField(null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    started = models.DateTimeField(null=True, blank=True)
    completed = models.DateTimeField(null=True, blank=True)

    error = models.TextField(null=True, blank=True)
