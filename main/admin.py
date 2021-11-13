from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import ngettext
from simple_history.admin import SimpleHistoryAdmin

from .models import *


class DiffHistoryAdmin(SimpleHistoryAdmin):
    history_list_display = ['changed_fields']

    def changed_fields(self, obj):
        if obj.prev_record:
            delta = obj.diff_against(obj.prev_record)
            return ", ".join(delta.changed_fields)
        return None


class PublishableAdmin(DiffHistoryAdmin):
    actions = ['make_published', 'draft']

    @admin.action(description='Publish all selected items')
    def make_published(self, request, queryset):
        updated = queryset.update(published=True)
        self.message_user(request, ngettext('%d was successfully marked as published.',
                                            '%d stories were successfully marked as published.',
                                            updated,
                                            ) % updated, messages.SUCCESS)

    @admin.action(description='Draft all selected items')
    def draft(self, request, queryset):
        updated = queryset.update(published=False)
        self.message_user(request, ngettext('%d was successfully marked as draft.',
                                            '%d stories were successfully marked as draft.',
                                            updated,
                                            ) % updated, messages.SUCCESS)


class ArticleAdmin(PublishableAdmin):
    date_hierarchy = 'creation'
    list_display = ('title', 'type', 'creation', 'published')
    list_filter = ('type', 'creation', 'published')
    search_fields = ('title', 'content')


class ItineraryDayInline(admin.TabularInline):
    model = ItineraryDay
    extra = 0
    classes = ['collapse']


class TourAdmin(PublishableAdmin):
    date_hierarchy = 'start_date'
    list_display = ('name', 'start_date', 'end_date', 'duration', 'published')
    inlines = [ItineraryDayInline]
    list_filter = ['start_date', 'end_date', 'destinations', 'published']


class StateAdmin(DiffHistoryAdmin):
    list_display = ('text', 'priority', 'color_div')

    @admin.display(description='Preview')
    def color_div(self, obj):
        return format_html(
            f'<div style="background-color: {obj.color}; color: {obj.text_color}; height: 100%; width: 100%; border-radius: 5px; padding: 3px;">{obj.text}</div>')


class DestinationAdmin(PublishableAdmin):
    list_display = ('name', 'region', 'published')
    list_filter = ('region', 'published')
    search_fields = ('name', 'description', 'region__name')


class ItineraryDayAdmin(DiffHistoryAdmin):
    list_display = ('tour', 'day', 'title')
    list_filter = ('tour', 'day')
    search_fields = ('tour__name', 'day', 'title', 'body')


class DestinationDetailsAdmin(PublishableAdmin):
    list_display = ('title', 'destination', 'order', 'published')
    list_filter = ('destination', 'published')
    search_fields = ('title', 'destination__name', 'content')


class PageAdmin(PublishableAdmin):
    list_display = ('title', 'parent', 'published')
    list_filter = ('parent', 'published')
    search_fields = ('title', 'parent__title', 'content')


class RegionAdmin(PublishableAdmin):
    list_display = ('name', 'published')
    list_filter = ('published',)


# Register your models here.
admin.site.register(Destination, DestinationAdmin)
admin.site.register(DestinationDetails, DestinationDetailsAdmin)
admin.site.register(Tour, TourAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(Region, RegionAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(ItineraryDay, ItineraryDayAdmin)
admin.site.register(Settings)
