from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse, resolve
from django.contrib import messages


import nested_admin

from .models import *


class NoChangePermissionMixin:
    message_prefix = "You cannot edit this form because it is in use by "
    message_suffix = "."

    def pretty_join(self, items):
        items_list = list(map(str, items))
        if len(items_list) == 0:
            return ''
        elif len(items_list) == 1:
            return items_list[0]
        elif len(items_list) == 2:
            return ' and '.join(items_list)
        return ', '.join(items_list[:-1]) + ', and ' + items_list[-1]

    def extract_users_from_message(self, message):
        users_list = message[len(self.message_prefix):-len(self.message_suffix)]
        return set(users_list.replace(', and ', ', ').replace(' and ', ', ').split(', '))

    def notify_cant_change(self, request, affected_users):
        current_messages = messages.get_messages(request)
        previous_users = set()
        for message in current_messages:
            if message.level == messages.ERROR and message.message.startswith(self.message_prefix) and message.message.endswith(self.message_suffix):
                previous_users.update(self.extract_users_from_message(message.message))

        for message in current_messages:
            # Remove previous messages
            if message.level == messages.ERROR and message.message.startswith(self.message_prefix) and message.message.endswith(self.message_suffix):
                message.extra_tags = 'hidden'

        all_affected_users = previous_users.union(map(str, affected_users))
        messages.add_message(request, messages.ERROR, self.message_prefix + self.pretty_join(all_affected_users) + self.message_suffix)

    class Media:
        css = {
            'all': ('css/hidden_messages.css',)
        }

    def has_change_permission(self, request, obj=None):
        if obj and obj.affected_customers:
            affected_users = obj.affected_customers
            self.notify_cant_change(request, affected_users)
            return not affected_users
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.affected_customers:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.affected_customers:
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields


class InlineNoChangePermissionMixin(NoChangePermissionMixin):
    def has_add_permission(self, request, obj=None):
        resolution = resolve(request.path_info)
        if resolution.url_name != 'customers_form_change':
            return super().has_add_permission(request, obj)

        form_id = resolution.kwargs['object_id']
        form = Form.objects.get(pk=form_id)

        if form.affected_customers:
            return False

        return super().has_add_permission(request, obj)


class FormFieldOptionInline(InlineNoChangePermissionMixin, nested_admin.NestedTabularInline):
    model = FormFieldOption
    extra = 0
    classes = ('collapse',)


class FormFieldInline(InlineNoChangePermissionMixin, nested_admin.NestedTabularInline):
    model = FormField
    extra = 0
    classes = ('collapse',)
    inlines = [FormFieldOptionInline]


class FormSectionInline(InlineNoChangePermissionMixin, nested_admin.NestedStackedInline):
    model = FormSection
    extra = 0
    inlines = [FormFieldInline]
    classes = ('collapse',)


class FormAdmin(NoChangePermissionMixin, nested_admin.NestedModelAdmin):
    list_display = ('title', 'short_description')
    inlines = [FormSectionInline]
    show_change_link = True


class FormTaskGroupInline(admin.TabularInline):
    model = FormTask
    extra = 0


class FormGroupAdmin(admin.ModelAdmin):
    inlines = [FormTaskGroupInline]


class FormTaskCustomerInline(admin.TabularInline):
    model = FormTask
    extra = 0
    exclude = ('group',)


class CustomerForm(forms.ModelForm):
    def clean_email(self):
        print('cleaning email: ', self.cleaned_data['email'])
        if Customer.objects.filter(email=self.cleaned_data['email']).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Email address already in use')
        return self.cleaned_data['email']


class CustomerAdmin(admin.ModelAdmin):
    form = CustomerForm
    list_display = ('email', 'full_name', 'password_set', 'run_send_registration_email')
    readonly_fields = ('email_confirmed', 'uuid', 'stripe_customer_id', 'added')
    inlines = [FormTaskCustomerInline]

    def password_set(self, obj):
        return obj.user.has_usable_password()

    def run_send_registration_email(self, obj):
        if obj.user.has_usable_password():
            return 'Password set'
        else:
            url = reverse('send_registration_email', args=[obj.pk])
            return format_html('<a class="button" href="{}">Send Registration Email</a>', url)

    run_send_registration_email.short_description = 'Send Registration Email'

    @admin.action(description='Send registration email')
    def send_registration_email(self, request, queryset):
        for customer in queryset:
            customer.send_email_confirmation()

    actions = ['send_registration_email']


# Register your models here.
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Form, FormAdmin)
admin.site.register(FormGroup, FormGroupAdmin)
admin.site.register(FormTask)
