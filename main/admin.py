from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import *


class DiffHistoryAdmin(SimpleHistoryAdmin):
    history_list_display = ['changed_fields']

    def changed_fields(self, obj):
        if obj.prev_record:
            delta = obj.diff_against(obj.prev_record)
            return ", ".join(delta.changed_fields)
        return None


# Register your models here.
admin.site.register(Destination, DiffHistoryAdmin)
admin.site.register(DestinationDetails, DiffHistoryAdmin)
admin.site.register(Tour, DiffHistoryAdmin)
admin.site.register(ItineraryDay, DiffHistoryAdmin)
admin.site.register(Article, DiffHistoryAdmin)
admin.site.register(Region, DiffHistoryAdmin)
admin.site.register(Page, DiffHistoryAdmin)
