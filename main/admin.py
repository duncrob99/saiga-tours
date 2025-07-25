from django.contrib import admin, messages
from django.core.exceptions import FieldDoesNotExist
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.translation import ngettext
from simple_history.admin import SimpleHistoryAdmin

import main.models
from .models import *


class DiffHistoryAdmin(SimpleHistoryAdmin):
    history_list_display = ['changed_fields']

    def changed_fields(self, obj):
        try:
            if obj.prev_record:
                delta = obj.diff_against(obj.prev_record)
                return ", ".join(delta.changed_fields)
        except (FieldDoesNotExist, KeyError):
            return "unknown"

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


class PhotoAdmin(PublishableAdmin):
    actions = ['fix_images', 'make_published', 'draft']

    @admin.action(description='Fix image ratios')
    def fix_images(self, request, queryset):
        for obj in queryset:
            validate_image_size(None, obj, None)


class ArticleAdmin(PhotoAdmin):
    date_hierarchy = 'creation'
    list_display = ('title', 'author', 'type', 'creation', 'tag_list', 'published')
    list_filter = ('type', 'author', 'creation', 'published_bool', 'tags')
    search_fields = ('title', 'author', 'content')
    filter_horizontal = ('tags',)

    def tag_list(self, obj):
        return ', '.join(str(tag) for tag in obj.tags.all())


class ItineraryDayInline(admin.TabularInline):
    model = ItineraryDay
    extra = 0
    classes = ['collapse']


class TourAdmin(PhotoAdmin):
    date_hierarchy = 'start_date'
    list_display = ('name', 'start_date', 'end_date', 'duration', 'published')
    inlines = [ItineraryDayInline]
    list_filter = ['start_date', 'duration', 'destinations', 'published_bool']


class StateAdmin(DiffHistoryAdmin):
    list_display = ('text', 'priority', 'color_div')

    @admin.display(description='Preview')
    def color_div(self, obj):
        return format_html(
            f'<div style="background-color: {obj.color}; color: {obj.text_color}; height: 100%; width: 100%; border-radius: 5px; padding: 3px;">{obj.text}</div>')


class DestinationAdmin(PhotoAdmin):
    list_display = ('name', 'region', 'published')
    list_filter = ('region', 'published_bool')
    search_fields = ('name', 'description', 'region__name')


class ItineraryDayAdmin(DiffHistoryAdmin):
    list_display = ('tour', 'day', 'title')
    list_filter = ('tour', 'day')
    search_fields = ('tour__name', 'day', 'title', 'body')


class DestinationDetailsAdmin(PhotoAdmin):
    list_display = ('title', 'destination', 'order', 'published')
    list_filter = ('destination', 'published_bool')
    search_fields = ('title', 'destination__name', 'content')


class PageAdmin(PhotoAdmin):
    list_display = ('title', 'parent', 'published')
    list_filter = ('parent', 'published_bool')
    search_fields = ('title', 'parent__title', 'content')


class RegionAdmin(PublishableAdmin):
    list_display = ('name', 'published')
    list_filter = ('published_bool',)


class SettingsAdmin(DiffHistoryAdmin):
    list_display = ('title', 'active')
    list_editable = ('active',)


class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ('from_email', 'time', 'subject', 'success')
    readonly_fields = ('from_email', 'time', 'subject', 'success', 'message')


class BannerPhotoAdmin(DiffHistoryAdmin):
    list_display = ('filename', 'min_AR', 'max_AR', 'active')

    def filename(self, obj: BannerPhoto):
        return obj.img.name


class FileUploadAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'view_document', 'edit')
    list_display_links = ('edit',)

    def edit(self, obj):
        return 'Edit'

    def view_document(self, obj):
        return mark_safe(u"<a href='%s'>%s</a>" % (obj.get_absolute_url(), obj.file))

    view_document.allow_tags = True
    view_document.short_description = u"File"


class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'added', 'approved')
    list_editable = ('approved',)


class StopAdmin(admin.ModelAdmin):
    list_display = ('tour', 'name', 'template', 'day', 'order', 'marked')
    list_filter = ('tour', 'template', 'day', 'marked')


class LinkAdmin(admin.ModelAdmin):
    list_display = ('url', 'contained_models', 'link_type', 'broken', 'error')
    list_filter = ('broken', 'locations__type')
    search_fields = ('url',)
    actions = ('recheck_link',)

    @admin.action
    def check_all_links(self, request, queryset):
        register_all_links()

    @admin.action(description="Recheck selected links")
    def recheck_link(self, request, queryset):
        queryset.update(broken=None, last_checked=None, error=None)

    def contained_models(self, obj):
        result = ""
        url = obj.url
        for loc in obj.locations.all():
            model_instance = getattr(main.models, loc.model)
            info = (model_instance._meta.app_label, model_instance._meta.model_name)
            instance = model_instance.objects.get(pk=loc.instance)
            try:
                edit_link = instance.get_absolute_url()
            except Exception:
                edit_link = reverse('admin:%s_%s_change' % info, args=(instance.pk,))
            tag_type = 'a[href' if loc.type == "TXT" else 'img[src'
            highlight_query = urlencode({'highlight_query': f'{tag_type}="{url}"]'})
            result += f"<a href='{edit_link}?{highlight_query}'>{model_instance._meta.model_name}: {instance}</a>"
        return mark_safe(result)

    def link_type(self, obj):
        return ", ".join(set(map(lambda typ: typ.get("type", ""), obj.locations.all().values("type"))))


# Register your models here.
admin.site.register(Destination, DestinationAdmin)
admin.site.register(DestinationDetails, DestinationDetailsAdmin)
admin.site.register(Tour, TourAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(Region, RegionAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(ItineraryDay, ItineraryDayAdmin)
admin.site.register(Settings, SettingsAdmin)
admin.site.register(ContactSubmission, ContactSubmissionAdmin)
admin.site.register(BannerPhoto, BannerPhotoAdmin)
admin.site.register(Tag)
admin.site.register(Stop, StopAdmin)
admin.site.register(MapPoint)
admin.site.register(PositionTemplate)
admin.site.register(ItineraryTemplate, SimpleHistoryAdmin)
admin.site.register(Author, DiffHistoryAdmin)
admin.site.register(HightlightBox, DiffHistoryAdmin)
admin.site.register(FileUpload, FileUploadAdmin)
admin.site.register(Testimonial, TestimonialAdmin)
admin.site.register(Link, LinkAdmin)
