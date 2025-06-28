from django.contrib import admin
from .models import Task


class TaskAdmin(admin.ModelAdmin):
    list_display = ('job', 'args', 'kwargs', 'completed_bool')

    @admin.display(description='Completed')
    def completed_bool(self, obj):
        return obj.completed is not None


# Register your models here.
admin.site.register(Task, TaskAdmin)
