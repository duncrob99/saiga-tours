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


# Register your models here.
admin.site.register(Destination)
admin.site.register(DestinationDetails, DestinationDetailsAdmin)
admin.site.register(Tour)
admin.site.register(ItineraryDay)
admin.site.register(Article)
admin.site.register(Region)
