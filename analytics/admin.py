from django.contrib import admin

from .models import *


class ReadOnlyAdmin(admin.ModelAdmin):

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in obj._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


class MouseActionAdmin(ReadOnlyAdmin):
    list_display = ('time', 'view', 'x', 'y', 'clicked_view')

    @admin.display(description='clicked')
    def clicked_view(self, obj):
        return MouseAction.Button(obj.clicked).name if obj.clicked is not None else None


class SubscriptionSubmissionAdmin(ReadOnlyAdmin):
    list_display = ('name', 'email_address', 'time')
    readonly_fields = ('name', 'email_address', 'time')


# Register your models here.
admin.site.register(UserCookie, ReadOnlyAdmin)
admin.site.register(Session, ReadOnlyAdmin)
admin.site.register(Page, ReadOnlyAdmin)
admin.site.register(PageView, ReadOnlyAdmin)
admin.site.register(MouseAction, MouseActionAdmin)
admin.site.register(SubscriptionSubmission, SubscriptionSubmissionAdmin)
