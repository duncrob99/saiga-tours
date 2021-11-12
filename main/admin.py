from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib import admin

from .models import *


class DestinationDetailsForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget())

    class Meta:
        exclude = ()
        model = DestinationDetails


class DestinationDetailsAdmin(admin.ModelAdmin):
    form = DestinationDetailsForm


class DestinationAdmin(admin.ModelAdmin):
    pass


class TourAdmin(admin.ModelAdmin):
    pass


class ArticleAdmin(admin.ModelAdmin):
    pass


class PageAdmin(admin.ModelAdmin):
    pass


# Register your models here.
admin.site.register(Destination, DestinationAdmin)
admin.site.register(DestinationDetails, DestinationDetailsAdmin)
admin.site.register(Tour, TourAdmin)
admin.site.register(ItineraryDay)
admin.site.register(Article, ArticleAdmin)
admin.site.register(Region)
admin.site.register(Page, PageAdmin)
